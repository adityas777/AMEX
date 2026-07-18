import datetime
import json
import os
from typing import List, Dict, Any, Optional

POLICIES_PATH = os.path.join(os.path.dirname(__file__), "policies.json")

def load_policies() -> List[Dict[str, Any]]:
    if not os.path.exists(POLICIES_PATH):
        return []
    with open(POLICIES_PATH, "r") as f:
        data = json.load(f)
        return data.get("policies", [])

def evaluate_rules(
    transaction: Any,  # SQLAlchemy model object
    event: Optional[Any],  # SQLAlchemy model object
    card_product: str,
    entitlements: List[Any]  # list of SQLAlchemy EntitlementBalance objects
) -> List[Dict[str, Any]]:
    """
    Evaluates a transaction and optional linked event against all policies.
    Returns a list of match results. Each result contains:
      - benefit_type
      - matched_policy_id
      - confidence_score (deterministic component, 1.0 if rules pass, else 0.0 or intermediate)
      - pre_filled_fields
      - reasoning (transparency dictionary detailing rule check results)
      - is_eligible (boolean indicating if all hard rules passed)
    """
    policies = load_policies()
    matches = []

    # Map entitlements by benefit type
    entitlement_map = {e.benefit_type: e for e in entitlements}

    for policy in policies:
        policy_id = policy["id"]
        benefit_type = policy["benefit_type"]
        policy_name = policy["name"]
        
        reasoning = {}
        is_eligible = True

        # 1. Card eligibility check
        card_eligible = card_product in policy["eligible_card_products"]
        reasoning["card_product_eligibility"] = {
            "status": "PASS" if card_eligible else "FAIL",
            "message": f"Card product '{card_product}' is eligible for '{policy_name}'" 
            if card_eligible else f"Card product '{card_product}' is not eligible for '{policy_name}' (requires {policy['eligible_card_products']})"
        }
        if not card_eligible:
            is_eligible = False

        # 2. MCC checks
        mcc_eligible = True
        mcc_details = ""
        if policy.get("eligible_categories"):
            mcc_eligible = transaction.mcc in policy["eligible_categories"]
            mcc_details = f"MCC '{transaction.mcc}' matches eligible categories" if mcc_eligible else f"MCC '{transaction.mcc}' not in eligible categories {policy['eligible_categories']}"
        elif policy.get("excluded_categories"):
            mcc_eligible = transaction.mcc not in policy["excluded_categories"]
            mcc_details = f"MCC '{transaction.mcc}' is not excluded" if mcc_eligible else f"MCC '{transaction.mcc}' is in excluded categories {policy['excluded_categories']}"
        else:
            mcc_details = "No MCC constraints for this policy"

        reasoning["merchant_category_eligibility"] = {
            "status": "PASS" if mcc_eligible else "FAIL",
            "message": mcc_details
        }
        if not mcc_eligible:
            is_eligible = False

        # 3. Transaction Type check
        tx_type_eligible = transaction.transaction_type == "purchase"
        reasoning["transaction_type"] = {
            "status": "PASS" if tx_type_eligible else "FAIL",
            "message": f"Transaction type is '{transaction.transaction_type}'" if tx_type_eligible else f"Transaction type must be 'purchase'"
        }
        if not tx_type_eligible:
            is_eligible = False

        # 4. Coverage Time Window check
        window_eligible = True
        time_details = ""
        ref_timestamp = event.event_timestamp if event else datetime.datetime.utcnow()
        
        # Calculate days elapsed between transaction and triggering event / current time
        days_elapsed = (ref_timestamp - transaction.timestamp).total_seconds() / 86400.0
        
        if days_elapsed < 0:
            window_eligible = False
            time_details = f"Event timestamp precedes purchase timestamp (invalid)"
        elif days_elapsed > policy["coverage_window_days"]:
            window_eligible = False
            time_details = f"Event occurred {days_elapsed:.1f} days after purchase, exceeding the {policy['coverage_window_days']}-day coverage window"
        else:
            time_details = f"Event occurred {days_elapsed:.1f} days after purchase, within the {policy['coverage_window_days']}-day coverage window"

        reasoning["coverage_window"] = {
            "status": "PASS" if window_eligible else "FAIL",
            "message": time_details
        }
        if not window_eligible:
            is_eligible = False

        # 5. Trigger event checks
        trigger_eligible = True
        trigger_details = ""
        if event:
            event_type_ok = event.event_type in policy["trigger_conditions"]["event_types"]
            if not event_type_ok:
                trigger_eligible = False
                trigger_details = f"Trigger event type '{event.event_type}' is not supported by this policy"
            else:
                # Custom check for travel delays
                if benefit_type == "travel_delay":
                    min_delay = policy["trigger_conditions"].get("min_delay_hours", 4)
                    event_data = event.event_data or {}
                    delay_hours = event_data.get("delay_hours", 0)
                    
                    if float(delay_hours) < min_delay:
                        trigger_eligible = False
                        trigger_details = f"Flight delay of {delay_hours} hours is less than the required {min_delay} hours"
                    else:
                        trigger_details = f"Flight delay of {delay_hours} hours meets or exceeds the required {min_delay} hours"
                elif benefit_type == "return_protection":
                    event_data = event.event_data or {}
                    denied = event_data.get("denial_reason", "")
                    if not denied:
                        trigger_eligible = False
                        trigger_details = "Merchant return refusal proof is missing"
                    else:
                        trigger_details = f"Merchant return refusal proof present: '{denied}'"
                else:
                    trigger_details = f"Eligible trigger event '{event.event_type}' detected"
        else:
            # Without a secondary event, the claim cannot be automatically finalized, but it might be flagged as a 'potential' benefit
            # (e.g. purchase protection is potentially applicable for any eligible items, but requires an event like theft/damage to trigger)
            trigger_eligible = False
            trigger_details = "No trigger event (damage report, theft report, flight delay, return refusal) has been linked yet"

        reasoning["trigger_condition"] = {
            "status": "PASS" if trigger_eligible else "FAIL",
            "message": trigger_details
        }
        if not trigger_eligible:
            is_eligible = False

        # 6. Entitlement limits check (annual cap & per-claim limits)
        entitlement = entitlement_map.get(benefit_type)
        limit_eligible = True
        limit_details = ""
        if entitlement:
            remaining_cap = entitlement.annual_limit - entitlement.utilized_amount
            if remaining_cap <= 0:
                limit_eligible = False
                limit_details = f"Annual limit of ${entitlement.annual_limit:.2f} for '{benefit_type}' has been exhausted (utilized: ${entitlement.utilized_amount:.2f})"
            else:
                limit_details = f"Available annual coverage for '{benefit_type}': ${remaining_cap:.2f} (Annual limit: ${entitlement.annual_limit:.2f})"
        else:
            limit_eligible = False
            limit_details = f"No active entitlement account found for '{benefit_type}'"

        reasoning["entitlement_limit"] = {
            "status": "PASS" if limit_eligible else "FAIL",
            "message": limit_details
        }
        if not limit_eligible:
            is_eligible = False

        # Pre-fill fields if eligible or partially eligible
        pre_filled = {}
        if is_eligible or (card_eligible and mcc_eligible and tx_type_eligible):
            claimable_amount = min(transaction.amount, policy["max_coverage_amount"])
            if entitlement:
                remaining_cap = entitlement.annual_limit - entitlement.utilized_amount
                claimable_amount = min(claimable_amount, remaining_cap)
            
            pre_filled = {
                "cardholder_name": "Valued Cardholder",  # will pull from actual cardholder in db if populated
                "card_product": card_product,
                "merchant_name": transaction.merchant_name,
                "product_description": transaction.product_description or "",
                "purchase_amount": transaction.amount,
                "purchase_date": transaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "claim_amount_requested": max(0.0, claimable_amount),
                "required_evidence": policy["required_evidence"]
            }
            if event:
                pre_filled["event_type"] = event.event_type
                pre_filled["event_date"] = event.event_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                if event.event_type == "flight_delay":
                    pre_filled["delay_hours"] = event.event_data.get("delay_hours", 0)
                    pre_filled["flight_number"] = event.event_data.get("flight_number", "N/A")
                elif event.event_type == "return_denied":
                    pre_filled["store_return_policy"] = event.event_data.get("store_return_policy", "30 days")
                    pre_filled["denial_reason"] = event.event_data.get("denial_reason", "")

        matches.append({
            "benefit_type": benefit_type,
            "matched_policy_id": policy_id,
            "confidence_score": 1.0 if is_eligible else 0.0,
            "pre_filled_fields": pre_filled,
            "reasoning": reasoning,
            "is_eligible": is_eligible
        })

    return matches
