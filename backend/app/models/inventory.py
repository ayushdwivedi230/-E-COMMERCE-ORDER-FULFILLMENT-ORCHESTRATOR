import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.id"), nullable=False, index=True)
    quantity_reserved = Column(Integer, nullable=False)
    status = Column(String(30), default="RESERVED", nullable=False)  # RESERVED, COMMITTED, RELEASED
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="reservations")
    product = relationship("Product", back_populates="reservations")
