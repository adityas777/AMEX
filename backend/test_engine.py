import datetime
import pytest
from backend.models import Transaction, TriggerEvent, EntitlementBalance
from backend.rules import evaluate_rules
from backend.ml_layer import ml_engine

# Mock objects for test cases
class MockTransaction:
    def __init__(self, id, mcc, amount, timestamp, product_description, transaction_type="purchase", merchant_name="Mock"):
        self.id = id
        self.mcc = mcc
        self.amount = amount
        self.timestamp = timestamp
        self.product_description = product_description
        self.transaction_type = transaction_type
        self.merchant_name = merchant_name

class MockTriggerEvent:
    def __init__(self, event_type, event_timestamp, event_data=None):
        self.event_type = event_type
        self.event_timestamp = event_timestamp
        self.event_data = event_data or {}

class MockEntitlement:
    def __init__(self, benefit_type, annual_limit, utilized_amount):
        self.benefit_type = benefit_type
        self.annual_limit = annual_limit
        self.utilized_amount = utilized_amount

def test_purchase_protection_eligibility():
    # Transaction 5 days ago, Platinum card
    now = datetime.datetime.utcnow()
    tx = MockTransaction(
        id="t1",
        mcc="5732", # Electronics (eligible)
        amount=1500.0,
        timestamp=now - datetime.timedelta(days=5),
        product_description="Sony Bravia TV"
    )
    # Trigger event of theft
    evt = MockTriggerEvent(
        event_type="theft_report",
        event_timestamp=now,
        event_data={"police_report_number": "12345"}
    )
    entitlements = [
        MockEntitlement("purchase_protection", 50000.0, 0.0),
        MockEntitlement("return_protection", 1000.0, 0.0),
        MockEntitlement("travel_delay", 2000.0, 0.0)
    ]
    
    matches = evaluate_rules(tx, evt, "Amex Platinum Card", entitlements)
    
    # We expect the purchase protection policy to be matches[0] or matching by benefit_type
    pp_match = next((m for m in matches if m["benefit_type"] == "purchase_protection"), None)
    assert pp_match is not None
    assert pp_match["is_eligible"] is True
    assert pp_match["reasoning"]["card_product_eligibility"]["status"] == "PASS"
    assert pp_match["reasoning"]["coverage_window"]["status"] == "PASS"

def test_purchase_protection_ineligible_card():
    # Transaction 5 days ago, Everyday Cashback card (not eligible in policies)
    now = datetime.datetime.utcnow()
    tx = MockTransaction(
        id="t1",
        mcc="5732",
        amount=1500.0,
        timestamp=now - datetime.timedelta(days=5),
        product_description="Sony Bravia TV"
    )
    evt = MockTriggerEvent(
        event_type="theft_report",
        event_timestamp=now,
        event_data={"police_report_number": "12345"}
    )
    
    matches = evaluate_rules(tx, evt, "Amex Everyday Cashback", [])
    
    pp_match = next((m for m in matches if m["benefit_type"] == "purchase_protection"), None)
    assert pp_match is not None
    assert pp_match["is_eligible"] is False
    assert pp_match["reasoning"]["card_product_eligibility"]["status"] == "FAIL"

def test_travel_delay_hours_checks():
    # Flight ticket transaction, Platinum card
    now = datetime.datetime.utcnow()
    tx = MockTransaction(
        id="t2",
        mcc="3000", # Airline
        amount=500.0,
        timestamp=now - datetime.timedelta(days=1),
        product_description="JFK to LAX Flight ticket"
    )
    
    # Delay 8 hours (Platinum threshold is 6 hours, so this should PASS)
    evt_pass = MockTriggerEvent(
        event_type="flight_delay",
        event_timestamp=now,
        event_data={"delay_hours": 8}
    )
    
    entitlements = [
        MockEntitlement("travel_delay", 2000.0, 0.0)
    ]
    
    matches_pass = evaluate_rules(tx, evt_pass, "Amex Platinum Card", entitlements)
    td_pass = next((m for m in matches_pass if m["benefit_type"] == "travel_delay"), None)
    assert td_pass is not None
    assert td_pass["is_eligible"] is True
    assert td_pass["reasoning"]["trigger_condition"]["status"] == "PASS"
    
    # Delay 2 hours (Platinum threshold is 6 hours, so this should FAIL)
    evt_fail = MockTriggerEvent(
        event_type="flight_delay",
        event_timestamp=now,
        event_data={"delay_hours": 2}
    )
    
    matches_fail = evaluate_rules(tx, evt_fail, "Amex Platinum Card", entitlements)
    td_fail = next((m for m in matches_fail if m["benefit_type"] == "travel_delay"), None)
    assert td_fail is not None
    assert td_fail["is_eligible"] is False
    assert td_fail["reasoning"]["trigger_condition"]["status"] == "FAIL"

def test_ml_layer_predictions():
    # Let's ensure the model is trained and check a few description classifications
    ml_engine.load_or_train()
    
    # Check physical damage
    label_pp, conf_pp = ml_engine.predict_transaction("iPhone 15 screen crack", "Apple Store", "5732", 1199.0)
    assert label_pp == "purchase_protection"
    assert conf_pp > 0.60
    
    # Check flight delay
    label_td, conf_td = ml_engine.predict_transaction("flight delay DL230 meal stay", "Delta Air Lines", "3000", 650.0)
    assert label_td == "travel_delay"
    assert conf_td > 0.60
    
    # Check non-qualifying
    label_none, conf_none = ml_engine.predict_transaction("Whole foods groceries weekly shopping", "Whole Foods", "5411", 85.0)
    assert label_none == "none"
