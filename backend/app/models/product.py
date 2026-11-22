import datetime
from sqlalchemy import Column, String, DateTime, Text, Numeric, Integer, Boolean
from sqlalchemy.orm import relationship
from backend.app.database import Base, utc_now


class Product(Base):
    __tablename__ = "products"

    id = Column(String(50), primary_key=True, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)
    substitute_sku = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    order_items = relationship("OrderItem", back_populates="product")
    reservations = relationship("InventoryReservation", back_populates="product")
