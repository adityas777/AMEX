import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship
from backend.database import Base

class CardMember(Base):
    __tablename__ = "card_members"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    card_product = Column(String, nullable=False)  # e.g., "Platinum Card", "Gold Card", "Blue Cash"
    
    transactions = relationship("Transaction", back_populates="card_member")
    entitlements = relationship("EntitlementBalance", back_populates="card_member")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    card_member_id = Column(String, ForeignKey("card_members.id"), nullable=False)
    merchant_name = Column(String, nullable=False)
    mcc = Column(String, nullable=False)  # Merchant Category Code
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    product_description = Column(String, nullable=True)
    transaction_type = Column(String, default="purchase")  # purchase | return

    card_member = relationship("CardMember", back_populates="transactions")
    events = relationship("TriggerEvent", back_populates="transaction")
    claims = relationship("Claim", back_populates="transaction")

class TriggerEvent(Base):
    __tablename__ = "trigger_events"

    id = Column(String, primary_key=True, index=True)
    event_type = Column(String, nullable=False)  # theft_report | damage_report | return_denied | flight_delay
    related_transaction_id = Column(String, ForeignKey("transactions.id"), nullable=True)
    event_data = Column(JSON, nullable=True)  # custom fields e.g., delay_hours, merchant_denial_reason
    event_timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    transaction = relationship("Transaction", back_populates="events")

class Claim(Base):
    __tablename__ = "claims"

    id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    benefit_type = Column(String, nullable=False)  # purchase_protection | return_protection | travel_delay
    confidence_score = Column(Float, nullable=False)
    matched_policy_id = Column(String, nullable=False)
    reasoning = Column(JSON, nullable=False)  # explanation rules logic
    pre_filled_fields = Column(JSON, nullable=False)  # form inputs
    status = Column(String, default="detected")  # detected | pending_review | submitted | approved | paid | denied
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    transaction = relationship("Transaction", back_populates="claims")

class EntitlementBalance(Base):
    __tablename__ = "entitlement_balances"

    id = Column(String, primary_key=True, index=True)  # card_member_id + "_" + benefit_type
    card_member_id = Column(String, ForeignKey("card_members.id"), nullable=False)
    benefit_type = Column(String, nullable=False)  # purchase_protection | return_protection | travel_delay
    annual_limit = Column(Float, nullable=False)
    utilized_amount = Column(Float, default=0.0)

    card_member = relationship("CardMember", back_populates="entitlements")
