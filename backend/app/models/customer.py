import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=False)
    billing_address = Column(Text, nullable=True)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, FLAGGED, BLOCKED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="customer")
    order_history = relationship("OrderHistory", back_populates="customer", cascade="all, delete-orphan")
    fraud_reviews = relationship("FraudReview", back_populates="customer")
