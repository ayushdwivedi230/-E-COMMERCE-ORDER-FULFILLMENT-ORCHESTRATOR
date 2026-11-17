import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    tracking_id = Column(String(100), nullable=False, unique=True, index=True)
    carrier = Column(String(100), nullable=False)  # FedEx, UPS, DHL, USPS
    shipping_method = Column(String(50), nullable=False)  # Standard, Express, Overnight, Freight
    status = Column(String(30), default="LABEL_CREATED", nullable=False)
    estimated_delivery = Column(DateTime, nullable=True)
    dispatch_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="shipment")
