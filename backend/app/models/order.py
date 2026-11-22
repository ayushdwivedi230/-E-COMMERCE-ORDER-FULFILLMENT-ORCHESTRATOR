import datetime
from sqlalchemy import Column, String, DateTime, Text, Numeric, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base, utc_now


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(50), primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False, index=True)
    status = Column(String(30), default="PENDING", index=True)  # PENDING, VALIDATED, RESERVED, FRAUD_HELD, PRICED, DISPATCHED, CANCELLED
    shipping_address = Column(Text, nullable=False)
    billing_address = Column(Text, nullable=True)
    payment_method = Column(String(50), nullable=False)
    subtotal = Column(Numeric(10, 2), default=0.00)
    discount_amount = Column(Numeric(10, 2), default=0.00)
    tax_amount = Column(Numeric(10, 2), default=0.00)
    shipping_cost = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(10, 2), default=0.00)
    coupon_code = Column(String(50), nullable=True)
    fraud_score = Column(Numeric(5, 2), nullable=True)
    hold_reason = Column(Text, nullable=True)
    tracking_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    reservations = relationship("InventoryReservation", back_populates="order", cascade="all, delete-orphan")
    fraud_reviews = relationship("FraudReview", back_populates="order", cascade="all, delete-orphan")
    shipment = relationship("Shipment", back_populates="order", uselist=False, cascade="all, delete-orphan")
    agent_logs = relationship("AgentLog", back_populates="order", cascade="all, delete-orphan")

    @property
    def order_id(self) -> str:
        return self.id

    @property
    def final_amount(self):
        return self.total_amount


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.id"), nullable=True, index=True)
    sku = Column(String(50), nullable=False)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class OrderHistory(Base):
    __tablename__ = "order_history"

    id = Column(String(50), primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False, index=True)
    order_id = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False)  # DELIVERED, CANCELLED, REFUNDED, CHARGEBACK, SUSPICIOUS
    amount = Column(Numeric(10, 2), nullable=False)
    is_suspicious = Column(Boolean, default=False, nullable=False)
    failed_payment_attempts = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    customer = relationship("Customer", back_populates="order_history")
