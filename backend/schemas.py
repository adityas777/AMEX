from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class CardMemberBase(BaseModel):
    id: str
    name: str
    card_product: str

class CardMemberResponse(CardMemberBase):
    class Config:
        from_attributes = True

class TransactionBase(BaseModel):
    id: str
    card_member_id: str
    merchant_name: str
    mcc: str
    amount: float
    currency: str = "USD"
    timestamp: datetime
    product_description: Optional[str] = None
    transaction_type: str = "purchase"

class TransactionCreate(BaseModel):
    id: Optional[str] = None
    card_member_id: str
    merchant_name: str
    mcc: str
    amount: float
    currency: str = "USD"
    timestamp: Optional[datetime] = None
    product_description: Optional[str] = None
    transaction_type: str = "purchase"

class TransactionResponse(TransactionBase):
    class Config:
        from_attributes = True

class TriggerEventBase(BaseModel):
    id: str
    event_type: str
    related_transaction_id: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    event_timestamp: datetime

class TriggerEventCreate(BaseModel):
    id: Optional[str] = None
    event_type: str
    related_transaction_id: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    event_timestamp: Optional[datetime] = None

class TriggerEventResponse(TriggerEventBase):
    class Config:
        from_attributes = True

class ClaimResponse(BaseModel):
    id: str
    transaction_id: str
    benefit_type: str
    confidence_score: float
    matched_policy_id: str
    reasoning: Dict[str, Any]
    pre_filled_fields: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    transaction: Optional[TransactionResponse] = None

    class Config:
        from_attributes = True

class ClaimStatusUpdate(BaseModel):
    status: str

class ClaimSubmit(BaseModel):
    pre_filled_fields: Dict[str, Any]

class EntitlementBalanceResponse(BaseModel):
    id: str
    card_member_id: str
    benefit_type: str
    annual_limit: float
    utilized_amount: float

    class Config:
        from_attributes = True

class EntitlementSummary(BaseModel):
    card_member_id: str
    balances: List[EntitlementBalanceResponse]

class DemoScenarioRequest(BaseModel):
    scenario_type: str  # purchase_protection_theft | return_protection_refusal | travel_delay_flight
    card_member_id: str
