export interface CardMember {
  id: string;
  name: string;
  card_product: string;
}

export interface Transaction {
  id: string;
  card_member_id: string;
  merchant_name: string;
  mcc: string;
  amount: number;
  currency: string;
  timestamp: string;
  product_description: string | null;
  transaction_type: string;
}

export interface RuleCheckDetail {
  status: "PASS" | "FAIL" | "INFO";
  message: string;
}

export interface Reasoning {
  card_product_eligibility: RuleCheckDetail;
  merchant_category_eligibility: RuleCheckDetail;
  transaction_type: RuleCheckDetail;
  coverage_window: RuleCheckDetail;
  trigger_condition: RuleCheckDetail;
  entitlement_limit: RuleCheckDetail;
  ml_classifier_validation?: RuleCheckDetail;
}

export interface PreFilledFields {
  cardholder_name: string;
  card_product: string;
  merchant_name: string;
  product_description: string;
  purchase_amount: number;
  purchase_date: string;
  claim_amount_requested: number;
  required_evidence: string[];
  event_type?: string;
  event_date?: string;
  delay_hours?: number;
  flight_number?: string;
  store_return_policy?: string;
  denial_reason?: string;
}

export interface Claim {
  id: string;
  transaction_id: string;
  benefit_type: "purchase_protection" | "return_protection" | "travel_delay";
  confidence_score: number;
  matched_policy_id: string;
  reasoning: Reasoning;
  pre_filled_fields: PreFilledFields;
  status: "detected" | "pending_review" | "submitted" | "approved" | "paid" | "denied";
  created_at: string;
  updated_at: string;
  transaction?: Transaction;
}

export interface EntitlementBalance {
  id: string;
  card_member_id: string;
  benefit_type: "purchase_protection" | "return_protection" | "travel_delay";
  annual_limit: number;
  utilized_amount: number;
}
