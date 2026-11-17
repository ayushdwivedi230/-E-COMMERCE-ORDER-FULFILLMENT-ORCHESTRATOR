from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.order_state import (
    AddressState,
    PaymentState,
    OrderItemState,
    OrderState,
    AgentLogEntry,
)


class OrderItemInput(BaseModel):
    sku: str
    quantity: int = Field(gt=0, description="Quantity to purchase")


class ProcessOrderRequest(BaseModel):
    customer_id: str
    items: List[OrderItemInput]
    shipping_address: AddressState
    payment_information: PaymentState
    coupon_code: Optional[str] = None
    simulate_recent_failed_attempts: Optional[int] = 0


class OrderSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    order_id: str
    customer_id: str
    customer_name: Optional[str] = None
    item_count: Optional[int] = 0
    status: str
    final_amount: Decimal
    fraud_score: float
    hold_reason: Optional[str] = None
    tracking_id: Optional[str] = None
    created_at: datetime
