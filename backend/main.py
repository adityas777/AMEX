import os
import uuid
import datetime
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from backend.database import engine, Base, get_db
from backend.models import CardMember, Transaction, TriggerEvent, Claim, EntitlementBalance
from backend.schemas import (
    CardMemberResponse, TransactionCreate, TransactionResponse,
    TriggerEventCreate, TriggerEventResponse, ClaimResponse,
    ClaimStatusUpdate, ClaimSubmit, EntitlementBalanceResponse,
    EntitlementSummary, DemoScenarioRequest
)
from backend.rules import evaluate_rules
from backend.ml_layer import ml_engine
from backend.seed import seed_db

# Create DB tables
Base.metadata.create_all(bind=engine)

# Dynamically inject source_email_id column if it is missing (self-healing migration)
from sqlalchemy import text
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE transactions ADD COLUMN source_email_id VARCHAR;"))
        conn.commit()
        print("Successfully injected column source_email_id into transactions table.")
except Exception:
    # Column already exists, swallow exception
    pass

app = FastAPI(title="Amex Card Benefit Activation Engine API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Pre-train/load model
    ml_engine.load_or_train()
    
    # Auto-seed database if empty
    db = next(get_db())
    try:
        if db.query(CardMember).count() == 0:
            seed_db(db)
    finally:
        db.close()

# Helper to process claim evaluation
def process_claim_detection(db: Session, transaction: Transaction, event: Optional[TriggerEvent] = None):
    # Get card member info
    member = db.query(CardMember).filter(CardMember.id == transaction.card_member_id).first()
    if not member:
        return None

    # Get active entitlements
    entitlements = db.query(EntitlementBalance).filter(
        EntitlementBalance.card_member_id == transaction.card_member_id
    ).all()

    # 1. Run deterministic rules matcher
    rule_matches = evaluate_rules(transaction, event, member.card_product, entitlements)
    
    # 2. Run ML classifier
    ml_predicted_class, ml_confidence = ml_engine.predict_transaction(
        product_description=transaction.product_description,
        merchant_name=transaction.merchant_name,
        mcc=transaction.mcc,
        amount=transaction.amount
    )

    # 3. Resolve the claim recommendation
    # We find the best matching policy
    matched_claim_data = None
    
    # Check if any rule matched deterministically (is_eligible == True)
    eligible_matches = [m for m in rule_matches if m["is_eligible"]]
    
    if eligible_matches:
        # Rules match takes precedence
        matched_claim_data = eligible_matches[0]
        # Rules matches have 1.0 confidence score
        confidence_score = 1.0
        reasoning_details = matched_claim_data["reasoning"]
        reasoning_details["ml_classifier_validation"] = {
            "status": "PASS" if ml_predicted_class == matched_claim_data["benefit_type"] else "INFO",
            "message": f"ML model predicted benefit '{ml_predicted_class}' with confidence {ml_confidence:.2f}"
        }
    else:
        # Check if ML suggests a potential benefit with high confidence (>= 0.70)
        if ml_predicted_class != "none" and ml_confidence >= 0.70:
            # Find the policy corresponding to the ML prediction
            policy_matches = [m for m in rule_matches if m["benefit_type"] == ml_predicted_class]
            if policy_matches:
                candidate = policy_matches[0]
                # If the card product is eligible, flag as potential claim pending evidence/event
                if candidate["reasoning"]["card_product_eligibility"]["status"] == "PASS":
                    matched_claim_data = candidate
                    confidence_score = ml_confidence
                    reasoning_details = candidate["reasoning"]
                    reasoning_details["ml_classifier_validation"] = {
                        "status": "PASS",
                        "message": f"ML model identified potential benefit '{ml_predicted_class}' in purchase description with confidence {ml_confidence:.2f}."
                    }

    if matched_claim_data:
        benefit_type = matched_claim_data["benefit_type"]
        policy_id = matched_claim_data["matched_policy_id"]
        pre_filled = matched_claim_data["pre_filled_fields"]

        # Check if claim already exists for this transaction and benefit
        existing_claim = db.query(Claim).filter(
            Claim.transaction_id == transaction.id,
            Claim.benefit_type == benefit_type
        ).first()

        if existing_claim:
            # Update fields, reasoning, confidence
            existing_claim.confidence_score = confidence_score
            existing_claim.reasoning = reasoning_details
            existing_claim.pre_filled_fields = pre_filled
            # If rules passed, upgrade status to detected if it was previously different
            if eligible_matches and existing_claim.status == "detected":
                existing_claim.status = "detected"
            db.commit()
            db.refresh(existing_claim)
            return existing_claim
        else:
            # Create new claim
            new_claim = Claim(
                id=f"clm_{uuid.uuid4().hex[:8]}",
                transaction_id=transaction.id,
                benefit_type=benefit_type,
                confidence_score=confidence_score,
                matched_policy_id=policy_id,
                reasoning=reasoning_details,
                pre_filled_fields=pre_filled,
                status="detected"
            )
            db.add(new_claim)
            db.commit()
            db.refresh(new_claim)
            return new_claim
            
    return None

# Endpoints
@app.get("/card-members", response_model=List[CardMemberResponse])
def get_card_members(db: Session = Depends(get_db)):
    return db.query(CardMember).all()

@app.post("/transactions/ingest", response_model=TransactionResponse)
def ingest_transaction(tx: TransactionCreate, db: Session = Depends(get_db)):
    tx_id = tx.id or f"tx_{uuid.uuid4().hex[:8]}"
    existing = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Transaction ID already exists")
    
    timestamp = tx.timestamp or datetime.datetime.utcnow()
    
    db_tx = Transaction(
        id=tx_id,
        card_member_id=tx.card_member_id,
        merchant_name=tx.merchant_name,
        mcc=tx.mcc,
        amount=tx.amount,
        currency=tx.currency,
        timestamp=timestamp,
        product_description=tx.product_description,
        transaction_type=tx.transaction_type
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)

    # Automatically run detection
    process_claim_detection(db, db_tx)
    return db_tx

@app.post("/events/ingest", response_model=TriggerEventResponse)
def ingest_event(evt: TriggerEventCreate, db: Session = Depends(get_db)):
    evt_id = evt.id or f"evt_{uuid.uuid4().hex[:8]}"
    timestamp = evt.event_timestamp or datetime.datetime.utcnow()
    
    db_evt = TriggerEvent(
        id=evt_id,
        event_type=evt.event_type,
        related_transaction_id=evt.related_transaction_id,
        event_data=evt.event_data,
        event_timestamp=timestamp
    )
    db.add(db_evt)
    db.commit()
    db.refresh(db_evt)

    # Re-evaluate claim for related transaction
    if evt.related_transaction_id:
        tx = db.query(Transaction).filter(Transaction.id == evt.related_transaction_id).first()
        if tx:
            process_claim_detection(db, tx, db_evt)
            
    return db_evt

@app.get("/card-members/{id}/detected-benefits", response_model=List[ClaimResponse])
def get_detected_benefits(id: str, db: Session = Depends(get_db)):
    claims = db.query(Claim).join(Transaction).filter(
        Transaction.card_member_id == id
    ).all()
    return claims

@app.get("/claims/{claim_id}", response_model=ClaimResponse)
def get_claim_detail(claim_id: str, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim

@app.post("/claims/{claim_id}/submit", response_model=ClaimResponse)
def submit_claim(claim_id: str, submission: ClaimSubmit, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    if claim.status not in ["detected", "pending_review"]:
        raise HTTPException(status_code=400, detail=f"Claim in status '{claim.status}' cannot be submitted")
        
    # Update pre-filled fields with user-edited form values
    claim.pre_filled_fields = submission.pre_filled_fields
    claim.status = "submitted"
    db.commit()
    db.refresh(claim)
    return claim

@app.patch("/claims/{claim_id}/status", response_model=ClaimResponse)
def update_claim_status(claim_id: str, update: ClaimStatusUpdate, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    new_status = update.status.lower()
    allowed_statuses = ["detected", "pending_review", "submitted", "approved", "paid", "denied"]
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {allowed_statuses}")

    # If transitioning to Approved or Paid, perform entitlement check and utilization deduction
    if new_status in ["approved", "paid"] and claim.status not in ["approved", "paid"]:
        # Find transaction
        tx = db.query(Transaction).filter(Transaction.id == claim.transaction_id).first()
        if not tx:
            raise HTTPException(status_code=400, detail="Transaction not found for this claim")

        # Find entitlement balance
        entitlement = db.query(EntitlementBalance).filter(
            EntitlementBalance.card_member_id == tx.card_member_id,
            EntitlementBalance.benefit_type == claim.benefit_type
        ).first()

        if not entitlement:
            raise HTTPException(status_code=400, detail="No entitlement balance found for this cardholder and benefit")

        # Calculate claim request amount
        claim_amt = claim.pre_filled_fields.get("claim_amount_requested", tx.amount)
        
        # Check annual limit
        remaining_cap = entitlement.annual_limit - entitlement.utilized_amount
        if remaining_cap < claim_amt:
            # Underwrite only up to remaining limit
            claim_amt = remaining_cap
            # Update requested amount
            fields = dict(claim.pre_filled_fields)
            fields["claim_amount_requested"] = claim_amt
            claim.pre_filled_fields = fields
            
        if claim_amt <= 0:
            raise HTTPException(status_code=400, detail="No remaining annual coverage available for this benefit")
            
        # Deduct from entitlement balance
        entitlement.utilized_amount += claim_amt
        
    # If transitioning AWAY from Approved/Paid to Denied/Submitted (reversing a decision)
    elif new_status not in ["approved", "paid"] and claim.status in ["approved", "paid"]:
        tx = db.query(Transaction).filter(Transaction.id == claim.transaction_id).first()
        if tx:
            entitlement = db.query(EntitlementBalance).filter(
                EntitlementBalance.card_member_id == tx.card_member_id,
                EntitlementBalance.benefit_type == claim.benefit_type
            ).first()
            if entitlement:
                claim_amt = claim.pre_filled_fields.get("claim_amount_requested", tx.amount)
                entitlement.utilized_amount = max(0.0, entitlement.utilized_amount - claim_amt)

    claim.status = new_status
    db.commit()
    db.refresh(claim)
    return claim

@app.get("/card-members/{id}/entitlement-summary", response_model=EntitlementSummary)
def get_entitlement_summary(id: str, db: Session = Depends(get_db)):
    balances = db.query(EntitlementBalance).filter(EntitlementBalance.card_member_id == id).all()
    return EntitlementSummary(card_member_id=id, balances=balances)

@app.get("/admin/claims", response_model=List[ClaimResponse])
def get_admin_claims(db: Session = Depends(get_db)):
    return db.query(Claim).all()

# Simulator Scenario Runner
@app.post("/simulator/run-scenario")
def run_scenario(req: DemoScenarioRequest, db: Session = Depends(get_db)):
    now = datetime.datetime.utcnow()
    
    if req.scenario_type == "purchase_protection_theft":
        # Sarah Jenkins (Platinum) purchase of high-end camera, then police report of theft
        tx_id = f"sim_tx_{uuid.uuid4().hex[:6]}"
        tx = Transaction(
            id=tx_id,
            card_member_id=req.card_member_id,
            merchant_name="B&H Photo Video",
            mcc="5732",
            amount=1899.99,
            currency="USD",
            timestamp=now - datetime.timedelta(days=2),
            product_description="Sony Alpha a7 IV Mirrorless Camera Body",
            transaction_type="purchase"
        )
        db.add(tx)
        db.commit()
        
        # Immediate ML potential claim created
        process_claim_detection(db, tx)
        
        # Simulate theft report 1 day later
        evt_id = f"sim_evt_{uuid.uuid4().hex[:6]}"
        evt = TriggerEvent(
            id=evt_id,
            event_type="theft_report",
            related_transaction_id=tx_id,
            event_data={"police_report_number": "PR-90184-NY", "theft_details": "Camera bag stolen from parked vehicle rental"},
            event_timestamp=now - datetime.timedelta(days=1)
        )
        db.add(evt)
        db.commit()
        
        # Process detection with event
        claim = process_claim_detection(db, tx, evt)
        return {"message": "Purchase protection theft scenario triggered", "transaction_id": tx_id, "event_id": evt_id, "claim_id": claim.id if claim else None}
        
    elif req.scenario_type == "travel_delay_flight":
        # Flight delay: Gold Card or Platinum Card. Let's say Sarah Jenkins (Platinum) flight delay
        tx_id = f"sim_tx_{uuid.uuid4().hex[:6]}"
        tx = Transaction(
            id=tx_id,
            card_member_id=req.card_member_id,
            merchant_name="Lufthansa",
            mcc="3008",
            amount=1450.00,
            currency="USD",
            timestamp=now - datetime.timedelta(hours=24),
            product_description="Lufthansa Munich to Boston Business Flight Booking",
            transaction_type="purchase"
        )
        db.add(tx)
        db.commit()
        
        process_claim_detection(db, tx)
        
        # Delay report
        evt_id = f"sim_evt_{uuid.uuid4().hex[:6]}"
        evt = TriggerEvent(
            id=evt_id,
            event_type="flight_delay",
            related_transaction_id=tx_id,
            event_data={"delay_hours": 8, "flight_number": "LH424", "carrier_refusal_reason": "Air traffic control strike"},
            event_timestamp=now - datetime.timedelta(hours=12)
        )
        db.add(evt)
        db.commit()
        
        claim = process_claim_detection(db, tx, evt)
        return {"message": "Travel delay scenario triggered", "transaction_id": tx_id, "event_id": evt_id, "claim_id": claim.id if claim else None}
        
    elif req.scenario_type == "return_protection_refusal":
        # Return protection: Zara coat return refusal. 
        # Note: Sarah (Platinum) has return protection. Emily (Everyday) or Michael (Gold) do not.
        tx_id = f"sim_tx_{uuid.uuid4().hex[:6]}"
        tx = Transaction(
            id=tx_id,
            card_member_id=req.card_member_id,
            merchant_name="Nike Town NY",
            mcc="5651",
            amount=280.00,
            currency="USD",
            timestamp=now - datetime.timedelta(days=45),
            product_description="Nike Air VaporMax Running Shoes - Limited Edition",
            transaction_type="purchase"
        )
        db.add(tx)
        db.commit()
        
        process_claim_detection(db, tx)
        
        evt_id = f"sim_evt_{uuid.uuid4().hex[:6]}"
        evt = TriggerEvent(
            id=evt_id,
            event_type="return_denied",
            related_transaction_id=tx_id,
            event_data={"store_return_policy": "30 days", "denial_reason": "Customer tried to return shoes after 45 days. Store manager refused."},
            event_timestamp=now - datetime.timedelta(days=44)
        )
        db.add(evt)
        db.commit()
        
        claim = process_claim_detection(db, tx, evt)
        return {"message": "Return protection scenario triggered", "transaction_id": tx_id, "event_id": evt_id, "claim_id": claim.id if claim else None}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid scenario type")

@app.post("/simulator/reset-db")
def reset_db(db: Session = Depends(get_db)):
    seed_db(db)
    return {"message": "Database reset and seeded."}

@app.post("/gmail/poll-now")
def poll_gmail_now(cardmember_id: str = "cm_platinum_1"):
    try:
        from backend.gmail_poller import run_poll_cycle
        results = run_poll_cycle(cardmember_id)
        return {
            "status": "success",
            "message": f"Gmail sync complete. Ingested {results['transactions_ingested']} transactions and {results['events_ingested']} flight delays. Skipped {results['skipped']} emails.",
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

