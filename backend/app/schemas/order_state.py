from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class OrderItemState(BaseModel):
    product_id: str
    sku: str
    name: str
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    total_price: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))


class AddressState(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "USA"

    def full_address(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.postal_code}, {self.country}"


class PaymentState(BaseModel):
    payment_method: str = "CREDIT_CARD"  # CREDIT_CARD, PAYPAL, DEBIT_CARD, APPLE_PAY
    payment_status: str = "AUTHORIZED"  # AUTHORIZED, PENDING, FAILED, CAPTURED
    card_last4: Optional[str] = "4242"
    transaction_token: Optional[str] = "tok_simulated_valid"
    billing_address: Optional[AddressState] = None


class AgentLogEntry(BaseModel):
    agent_name: str
    action: str
    status: str  # SUCCESS, FAILED, WARNING, HELD
    message: str
    execution_time_ms: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    details: Optional[Dict[str, Any]] = None


class SubstituteRecommendation(BaseModel):
    original_sku: str
    substitute_sku: str
    substitute_name: str
    substitute_price: Decimal
    reason: str


class BackorderProposal(BaseModel):
    sku: str
    product_name: str
    requested_quantity: int
    available_quantity: int
    estimated_restock_days: int = 7


class OrderState(BaseModel):
    """
    Central shared state object passed across all five specialised agents
    in the multi-agent fulfillment pipeline.
    """
    order_id: str
    customer_id: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    
    # Items & Address
    items: List[OrderItemState]
    shipping_address: AddressState
    payment_information: PaymentState
    coupon_code: Optional[str] = None

    # Five Agent Pipeline Statuses
    validation_status: str = "PENDING"  # PENDING, PASSED, FAILED
    inventory_status: str = "PENDING"   # PENDING, RESERVED, INSUFFICIENT_STOCK, BACKORDER_PROPOSED
    fraud_status: str = "PENDING"       # PENDING, LOW_RISK, MEDIUM_RISK, HIGH_RISK_HELD
    pricing_status: str = "PENDING"     # PENDING, CALCULATED
    dispatch_status: str = "PENDING"    # PENDING, CONFIRMED, DISPATCHED, HELD

    # Quantitative & Financial State (Deterministic Decimals)
    fraud_score: float = 0.0
    subtotal: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    shipping_cost: Decimal = Decimal("0.00")
    final_amount: Decimal = Decimal("0.00")

    # Routing, Escalation & Tracking
    hold_reason: Optional[str] = None
    tracking_id: Optional[str] = None
    carrier: Optional[str] = None
    shipping_method: Optional[str] = "Standard"
    review_status: str = "PENDING"  # PENDING, APPROVED, FLAGGED_REVIEW, HELD_ESCALATED

    # Contextual recommendations & AI reasoning
    substitute_recommendations: List[SubstituteRecommendation] = []
    backorder_proposals: List[BackorderProposal] = []
    fraud_risk_factors: List[str] = []
    fraud_ai_reasoning: Optional[str] = None

    # Shared Audit Execution Logs
    agent_execution_logs: List[AgentLogEntry] = []

    @property
    def is_successful(self) -> bool:
        return self.dispatch_status == "DISPATCHED" and self.tracking_id is not None

    def get_structured_output(self) -> Dict[str, Any]:
        """
        Required output format from Prompt 4:
        - For successful orders: Confirmed order + final amount + shipping method + tracking ID.
        - For suspicious orders: Held order + fraud score + explanation + review status.
        """
        if self.is_successful:
            return {
                "order_result": "CONFIRMED_AND_DISPATCHED",
                "order_id": self.order_id,
                "final_amount": str(self.final_amount),
                "shipping_method": self.shipping_method,
                "carrier": self.carrier,
                "tracking_id": self.tracking_id,
                "review_status": self.review_status,
                "status": self.dispatch_status,
            }
        else:
            return {
                "order_result": "HELD_SUSPICIOUS_ORDER" if self.fraud_status == "HIGH_RISK_HELD" else "HELD_ORDER",
                "order_id": self.order_id,
                "fraud_score": self.fraud_score,
                "explanation": self.fraud_ai_reasoning or self.hold_reason or "Order processing halted.",
                "review_status": self.review_status,
                "hold_reason": self.hold_reason,
                "status": self.dispatch_status,
            }

    def add_log(
        self,
        agent_name: str,
        action: str,
        status: str,
        message: str,
        execution_time_ms: int = 0,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Helper to append an execution log entry to the shared state."""
        self.agent_execution_logs.append(
            AgentLogEntry(
                agent_name=agent_name,
                action=action,
                status=status,
                message=message,
                execution_time_ms=execution_time_ms,
                details=details,
            )
        )
