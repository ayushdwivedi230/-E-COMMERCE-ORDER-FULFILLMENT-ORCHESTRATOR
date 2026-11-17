import datetime
from sqlalchemy import Column, String, DateTime, Text, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class FraudReview(Base):
    __tablename__ = "fraud_reviews"

    id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.id"), nullable=False, index=True)
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False, index=True)
    fraud_score = Column(Numeric(5, 2), nullable=False)
    risk_level = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH
    reasons = Column(Text, nullable=False)  # JSON-encoded array of triggers
    ai_explanation = Column(Text, nullable=True)  # Contextual reasoning
    decision = Column(String(30), nullable=False)  # APPROVED, FLAGGED, HELD
    reviewed_by = Column(String(100), default="SYSTEM_AGENT")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="fraud_reviews")
    customer = relationship("Customer", back_populates="fraud_reviews")
