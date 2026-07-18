import datetime
from sqlalchemy.orm import Session
from backend.models import CardMember, EntitlementBalance, Transaction, TriggerEvent, Claim
from backend.database import engine, Base

def seed_db(db: Session):
    # Clear existing data to make it idempotent
    db.query(Claim).delete()
    db.query(TriggerEvent).delete()
    db.query(Transaction).delete()
    db.query(EntitlementBalance).delete()
    db.query(CardMember).delete()
    db.commit()

    print("Seeding database...")

    # 1. Create Card Members
    members = [
        CardMember(id="cm_platinum_1", name="Sarah Jenkins", card_product="Amex Platinum Card"),
        CardMember(id="cm_gold_1", name="Michael Chang", card_product="Amex Gold Card"),
        CardMember(id="cm_everyday_1", name="Emily Rodriguez", card_product="Amex Everyday Cashback")
    ]
    for m in members:
        db.add(m)
    db.commit()

    # 2. Create Entitlement Balances
    entitlements = [
        # Sarah Jenkins (Platinum)
        EntitlementBalance(id="cm_platinum_1_purchase_protection", card_member_id="cm_platinum_1", benefit_type="purchase_protection", annual_limit=50000.0, utilized_amount=0.0),
        EntitlementBalance(id="cm_platinum_1_return_protection", card_member_id="cm_platinum_1", benefit_type="return_protection", annual_limit=1000.0, utilized_amount=0.0),
        EntitlementBalance(id="cm_platinum_1_travel_delay", card_member_id="cm_platinum_1", benefit_type="travel_delay", annual_limit=2000.0, utilized_amount=0.0),
        
        # Michael Chang (Gold)
        EntitlementBalance(id="cm_gold_1_purchase_protection", card_member_id="cm_gold_1", benefit_type="purchase_protection", annual_limit=10000.0, utilized_amount=0.0),
        EntitlementBalance(id="cm_gold_1_travel_delay", card_member_id="cm_gold_1", benefit_type="travel_delay", annual_limit=1200.0, utilized_amount=0.0)
        
        # Emily Rodriguez (Everyday Cashback) has no policy coverage, so no entitlements are created
    ]
    for e in entitlements:
        db.add(e)
    db.commit()

    # 3. Create Seed Transactions
    now = datetime.datetime.utcnow()
    
    txs = [
        # Sarah Jenkins
        Transaction(
            id="tx_plat_1",
            card_member_id="cm_platinum_1",
            merchant_name="Apple Store",
            mcc="5732",
            amount=1199.00,
            currency="USD",
            timestamp=now - datetime.timedelta(days=12),
            product_description="iPhone 15 Pro Max 256GB Gold",
            transaction_type="purchase"
        ),
        Transaction(
            id="tx_plat_2",
            card_member_id="cm_platinum_1",
            merchant_name="Delta Air Lines",
            mcc="3000",
            amount=850.00,
            currency="USD",
            timestamp=now - datetime.timedelta(days=4),
            product_description="Roundtrip Flight JFK to LHR DL102",
            transaction_type="purchase"
        ),
        Transaction(
            id="tx_plat_3",
            card_member_id="cm_platinum_1",
            merchant_name="Zara",
            mcc="5651",
            amount=249.50,
            currency="USD",
            timestamp=now - datetime.timedelta(days=20),
            product_description="Italian Wool Blend Designer Overcoat",
            transaction_type="purchase"
        ),
        Transaction(
            id="tx_plat_4",
            card_member_id="cm_platinum_1",
            merchant_name="Whole Foods",
            mcc="5411",
            amount=125.40,
            currency="USD",
            timestamp=now - datetime.timedelta(days=1),
            product_description="Weekly Groceries and Produce",
            transaction_type="purchase"
        ),
        # Michael Chang
        Transaction(
            id="tx_gold_1",
            card_member_id="cm_gold_1",
            merchant_name="United Airlines",
            mcc="3001",
            amount=420.00,
            currency="USD",
            timestamp=now - datetime.timedelta(days=15),
            product_description="One-way flight LAX to ORD UA883",
            transaction_type="purchase"
        ),
        Transaction(
            id="tx_gold_2",
            card_member_id="cm_gold_1",
            merchant_name="Best Buy",
            mcc="5732",
            amount=349.99,
            currency="USD",
            timestamp=now - datetime.timedelta(days=3),
            product_description="Sony WH-1000XM5 Noise Cancelling Headphones",
            transaction_type="purchase"
        ),
        # Emily Rodriguez
        Transaction(
            id="tx_every_1",
            card_member_id="cm_everyday_1",
            merchant_name="Best Buy",
            mcc="5732",
            amount=599.99,
            currency="USD",
            timestamp=now - datetime.timedelta(days=5),
            product_description="iPad Air 128GB Blue",
            transaction_type="purchase"
        )
    ]
    
    for t in txs:
        db.add(t)
    db.commit()

    print("Database seeded successfully.")

if __name__ == "__main__":
    from backend.database import SessionLocal
    db = SessionLocal()
    seed_db(db)
    db.close()
