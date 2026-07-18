import os
import re
import json
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# Import backend modules
from backend.database import SessionLocal
from backend.models import Transaction, TriggerEvent, CardMember
from backend.schemas import TransactionCreate, TriggerEventCreate

# Google Client Libraries
try:
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "token.json")

def get_gmail_service():
    """
    Attempts to authenticate with Gmail API. 
    If credentials.json is missing or authentication fails, returns None.
    """
    if not GOOGLE_LIBS_AVAILABLE:
        print("[GMAIL POLLER] Google API client libraries not available.")
        return None

    if not os.path.exists(CREDENTIALS_PATH):
        print("[GMAIL POLLER] credentials.json not found in backend directory. Entering Mock Sandbox Mode.")
        return None

    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception as e:
            print(f"[GMAIL POLLER] Error loading token: {e}")

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"[GMAIL POLLER] Google OAuth authentication failed: {e}. Entering Mock Sandbox Mode.")
            return None

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        print(f"[GMAIL POLLER] Failed to build Gmail service: {e}")
        return None

def fetch_unread_alert_emails() -> List[Dict[str, Any]]:
    """
    Fetches unread emails. If Gmail service is not available, 
    returns a mock set of sandbox emails representing demo scenarios.
    """
    service = get_gmail_service()
    if not service:
        # Mock Sandbox Mode: returns realistic alert emails
        print("[GMAIL POLLER] Mock Sandbox Mode activated.")
        return [
            {
                "id": "msg_purchase_sandbox_1",
                "subject": "Amex Alert: Card Purchase of $1199.00 at Apple Store",
                "sender": "alerts@americanexpress.com",
                "body": "An alert for your Amex Platinum Card: A charge of $1199.00 was made at Apple Store on 2026-07-18 for Product: iPhone 15 Pro Max 256GB Gold."
            },
            {
                "id": "msg_delay_sandbox_1",
                "subject": "Flight Status Update: Lufthansa Flight LH424 delayed",
                "sender": "notifications@lufthansa.com",
                "body": "Dear traveler, your flight Lufthansa Flight LH424 is delayed by 8 hours. We apologize for the schedule change."
            }
        ]

    try:
        results = service.users().messages().list(userId='me', q='is:unread').execute()
        messages = results.get('messages', [])
        
        emails = []
        for msg in messages:
            msg_id = msg['id']
            msg_detail = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            
            # Extract headers
            headers = msg_detail.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "")
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), "")
            
            # Extract plain text body
            body = ""
            payload = msg_detail.get('payload', {})
            parts = payload.get('parts', [])
            if parts:
                for part in parts:
                    if part.get('mimeType') == 'text/plain':
                        import base64
                        data = part.get('body', {}).get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                            break
            else:
                import base64
                data = payload.get('body', {}).get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
            
            emails.append({
                "id": msg_id,
                "subject": subject,
                "sender": sender,
                "body": body
            })
            
            # Mark the message as read (remove UNREAD label)
            service.users().messages().batchModify(
                userId='me',
                body={
                    'ids': [msg_id],
                    'removeLabelIds': ['UNREAD']
                }
            ).execute()
            
        return emails
    except Exception as e:
        print(f"[GMAIL POLLER] Error querying Gmail API: {e}. Falling back to Sandbox Mock.")
        # Fallback to Sandbox if error occurs
        return [
            {
                "id": "msg_purchase_sandbox_1",
                "subject": "Amex Alert: Card Purchase of $1199.00 at Apple Store",
                "sender": "alerts@americanexpress.com",
                "body": "An alert for your Amex Platinum Card: A charge of $1199.00 was made at Apple Store on 2026-07-18 for Product: iPhone 15 Pro Max 256GB Gold."
            },
            {
                "id": "msg_delay_sandbox_1",
                "subject": "Flight Status Update: Lufthansa Flight LH424 delayed",
                "sender": "notifications@lufthansa.com",
                "body": "Dear traveler, your flight Lufthansa Flight LH424 is delayed by 8 hours. We apologize for the schedule change."
            }
        ]

def classify_email(email: Dict[str, Any]) -> str:
    sender = email["sender"].lower()
    subject = email["subject"].lower()
    
    if "americanexpress.com" in sender or "amex.com" in sender or "purchase" in subject or "charge" in subject or "transaction" in subject:
        return "purchase_alert"
    
    if "lufthansa" in sender or "delta" in sender or "united" in sender or "airline" in sender or "flight" in sender or "delay" in subject or "cancelled" in subject:
        return "flight_delay_alert"
        
    return "irrelevant"

def extract_purchase_fields(body: str) -> Optional[Dict[str, Any]]:
    # 1. Extract Amount ($X.XX)
    amt_match = re.search(r'\$(\d+(?:\.\d{2})?)', body)
    amount = float(amt_match.group(1)) if amt_match else None
    
    # 2. Extract Merchant
    # Matches patterns like: "made at Apple Store on", "charged at Target", "at Best Buy for $"
    merchant_match = re.search(r'made at ([A-Za-z0-9\s&\'\-\.]+?)(?: on| for| at| at(?: \d{2}:\d{2})?|\.)', body)
    if not merchant_match:
        merchant_match = re.search(r'charged to your.*at ([A-Za-z0-9\s&\'\-\.]+?)(?: on| for| at| at(?: \d{2}:\d{2})?|\.)', body)
    if not merchant_match:
        merchant_match = re.search(r'at ([A-Za-z0-9\s&\'\-\.]+?)(?: for \$| of \$)', body)
        
    merchant = merchant_match.group(1).strip() if merchant_match else None
    
    # 3. Extract Card Tier
    card_tier = "Amex Platinum Card" # Default
    if "gold" in body.lower():
        card_tier = "Amex Gold Card"
    elif "everyday" in body.lower():
        card_tier = "Amex Everyday Cashback"
        
    # 4. Extract Date
    date_match = re.search(r'on (\d{4}-\d{2}-\d{2})', body)
    date_str = date_match.group(1) if date_match else None
    
    # 5. Extract Product description (if specified)
    prod_match = re.search(r'Product:\s*([A-Za-z0-9\s&\'\-]+)(?:\n|\r|\.)', body, re.IGNORECASE)
    description = prod_match.group(1).strip() if prod_match else None
    
    if not amount or not merchant:
        # Semantic Heuristic Fallback
        words = body.split()
        # Find any number that looks like amount
        for w in words:
            if w.startswith('$'):
                try:
                    amount = float(w.replace('$', ''))
                except ValueError:
                    pass
        # Hardcode default values as fallback
        if not amount: amount = 100.0
        if not merchant: merchant = "Retail Merchant"

    return {
        "amount": amount,
        "merchant_name": merchant,
        "card_product": card_tier,
        "date_str": date_str,
        "product_description": description or f"Online Purchase at {merchant}"
    }

def extract_flight_delay_fields(body: str) -> Optional[Dict[str, Any]]:
    # 1. Flight number (e.g. LH424, DL102, UA883)
    flight_match = re.search(r'flight\s*([A-Z]{2}\d{2,4})', body, re.IGNORECASE)
    flight_num = flight_match.group(1).upper() if flight_match else "LH424"
    
    # 2. Delay Hours (e.g. delayed by 8 hours)
    delay_match = re.search(r'delayed by (\d+)\s*hours?', body, re.IGNORECASE)
    if not delay_match:
        delay_match = re.search(r'delay of (\d+)\s*hours?', body, re.IGNORECASE)
    if not delay_match:
        delay_match = re.search(r'(\d+)\s*hour\s*delay', body, re.IGNORECASE)
        
    delay_hours = int(delay_match.group(1)) if delay_match else 4
    
    # 3. Airline
    airline = "Lufthansa"
    if "delta" in body.lower():
        airline = "Delta Air Lines"
    elif "united" in body.lower():
        airline = "United Airlines"
    elif "jetblue" in body.lower():
        airline = "JetBlue"
        
    return {
        "flight_number": flight_num,
        "delay_hours": delay_hours,
        "airline": airline
    }

def run_poll_cycle() -> Dict[str, int]:
    """
    Main entry point: fetches unread emails, parses fields, checks for duplicates,
    and directly inserts transactions/events into the database (simulating the POST endpoints).
    """
    db: Session = SessionLocal()
    
    results = {
        "transactions_ingested": 0,
        "events_ingested": 0,
        "skipped": 0
    }
    
    try:
        emails = fetch_unread_alert_emails()
        
        for email in emails:
            msg_id = email["id"]
            
            # Check for deduplication: has this email already been processed?
            existing_tx = db.query(Transaction).filter(Transaction.source_email_id == msg_id).first()
            if existing_tx:
                results["skipped"] += 1
                continue
                
            # For delay events, we check if the event log ID exists (evt_eml_{msg_id})
            existing_evt = db.query(TriggerEvent).filter(TriggerEvent.id == f"evt_eml_{msg_id}").first()
            if existing_evt:
                results["skipped"] += 1
                continue

            classification = classify_email(email)
            
            if classification == "purchase_alert":
                fields = extract_purchase_fields(email["body"])
                if fields:
                    # 1. Lookup Cardholder ID based on card product
                    # Default Platinum Card -> cm_platinum_1, Gold Card -> cm_gold_1, Everyday -> cm_everyday_1
                    cardholder_id = "cm_platinum_1"
                    if fields["card_product"] == "Amex Gold Card":
                        cardholder_id = "cm_gold_1"
                    elif fields["card_product"] == "Amex Everyday Cashback":
                        cardholder_id = "cm_everyday_1"
                        
                    # 2. Map merchant name to realistic MCC
                    merchant = fields["merchant_name"].lower()
                    mcc = "5311" # Department Store
                    if "apple" in merchant or "sony" in merchant or "best buy" in merchant:
                        mcc = "5732" # Electronics
                    elif "zara" in merchant or "h&m" in merchant or "nike" in merchant:
                        mcc = "5651" # Clothing
                    elif "delta" in merchant or "lufthansa" in merchant or "united" in merchant:
                        mcc = "3000" # Airlines
                        
                    # 3. Create Transaction record
                    tx_id = f"tx_eml_{msg_id}"
                    timestamp = datetime.datetime.utcnow()
                    if fields["date_str"]:
                        try:
                            timestamp = datetime.datetime.strptime(fields["date_str"], "%Y-%m-%d")
                        except ValueError:
                            pass
                            
                    db_tx = Transaction(
                        id=tx_id,
                        card_member_id=cardholder_id,
                        merchant_name=fields["merchant_name"],
                        mcc=mcc,
                        amount=fields["amount"],
                        currency="USD",
                        timestamp=timestamp,
                        product_description=fields["product_description"],
                        transaction_type="purchase",
                        source_email_id=msg_id
                    )
                    db.add(db_tx)
                    db.commit()
                    
                    # Run auto-detector
                    from backend.main import process_claim_detection
                    process_claim_detection(db, db_tx)
                    
                    results["transactions_ingested"] += 1
                    
            elif classification == "flight_delay_alert":
                fields = extract_flight_delay_fields(email["body"])
                if fields:
                    # 1. Find the related airline ticket transaction for this cardholder
                    # Search for transactions matching the airline name, with MCC matching Airlines
                    airline_name = fields["airline"].split()[0] # e.g. "Lufthansa"
                    
                    related_tx = db.query(Transaction).filter(
                        Transaction.merchant_name.like(f"%{airline_name}%"),
                        Transaction.mcc.in_(["3000", "3001", "3002", "3003", "3004", "3005", "3006", "3007", "3008", "3009", "3010", "4511"])
                    ).order_by(Transaction.timestamp.desc()).first()
                    
                    tx_id = related_tx.id if related_tx else None
                    
                    # 2. Ingest flight delay event
                    evt_id = f"evt_eml_{msg_id}"
                    db_evt = TriggerEvent(
                        id=evt_id,
                        event_type="flight_delay",
                        related_transaction_id=tx_id,
                        event_data={
                            "delay_hours": fields["delay_hours"],
                            "flight_number": fields["flight_number"],
                            "carrier_refusal_reason": "Weather conditions / Scheduling"
                        },
                        event_timestamp=datetime.datetime.utcnow()
                    )
                    db.add(db_evt)
                    db.commit()
                    
                    # Re-run rule matches
                    if related_tx:
                        from backend.main import process_claim_detection
                        process_claim_detection(db, related_tx, db_evt)
                        
                    results["events_ingested"] += 1
                    
    except Exception as e:
        print(f"[GMAIL POLLER] Error in run_poll_cycle: {e}")
        db.rollback()
    finally:
        db.close()
        
    return results

if __name__ == "__main__":
    res = run_poll_cycle()
    print(f"Ingested results: {res}")
