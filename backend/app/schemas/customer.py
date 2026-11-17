from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class OrderHistoryEntry(BaseModel):
    id: str
    order_id: str
    status: str
    amount: Decimal
    is_suspicious: bool
    failed_payment_attempts: int
    notes: Optional[str] = None
    created_at: datetime


class CustomerHistoryStats(BaseModel):
    customer_id: str
    total_orders: int
    successful_orders: int
    suspicious_orders: int
    failed_payment_attempts: int
    total_spent: Decimal
    average_order_value: Decimal
    suspicion_rate: float
    risk_tier: str  # LOW, MEDIUM, HIGH
    prior_orders: List[OrderHistoryEntry] = []


class CustomerBase(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    address: str
    billing_address: Optional[str] = None
    status: str = "ACTIVE"


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime
    history_stats: Optional[CustomerHistoryStats] = None
