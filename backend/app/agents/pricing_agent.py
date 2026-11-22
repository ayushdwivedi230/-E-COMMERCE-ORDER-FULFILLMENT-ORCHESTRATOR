import time
from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseOrchestratorAgent
from backend.app.schemas.order_state import OrderState
from backend.app.models.product import Product
from backend.app.agents.tools import (
    calculate_subtotal_and_discounts,
    calculate_tax_and_shipping,
    finalize_order_total,
)


class PricingAgent(BaseOrchestratorAgent):
    """
    Agent 4: Pricing Agent
    Implements deterministic financial decimal arithmetic:
    - Base price calculation per item (price * quantity)
    - Subtotal calculation
    - Volume discount rules (>= 5 units = 5% off)
    - Coupon code validation & application (WELCOME10, SAVE20, FREESHIP)
    - Regional sales tax calculation (8%)
    - Dynamic shipping calculation with free shipping thresholds ($100+)
    - Final payable amount

    Microsoft Agent Framework Integration:
    Calls 3 plain Python tools decorated with @tool:
      1. calculate_subtotal_and_discounts
      2. calculate_tax_and_shipping
      3. finalize_order_total
    """

    def __init__(self) -> None:
        tools = [
            calculate_subtotal_and_discounts,
            calculate_tax_and_shipping,
            finalize_order_total,
        ]
        super().__init__(
            name="PricingAgent",
            description="Executes deterministic financial arithmetic for subtotals, coupons, taxes, and shipping.",
            agent_id="agt-pricing-004",
            tools=tools,
        )

    def calculate_pricing(self, order_state: OrderState, db: Session) -> bool:
        start_time = time.time()

        if order_state.fraud_status == "HIGH_RISK_HELD":
            order_state.pricing_status = "SKIPPED"
            self.record_agent_log(
                order_state,
                action="PricingCalculation",
                status="SKIPPED",
                message="Skipping pricing calculation because order is currently HELD in fraud review queue.",
                start_time=start_time,
            )
            return False

        # Ensure unit prices are populated from catalog
        for item in order_state.items:
            if item.unit_price <= Decimal("0.00"):
                product = db.query(Product).filter(Product.sku == item.sku).first()
                if product:
                    item.unit_price = Decimal(str(product.price))

        # TOOL 1: Calculate Subtotal and Discounts
        t1_start = time.time()
        sub_res = calculate_subtotal_and_discounts(
            items=order_state.items,
            coupon_code=order_state.coupon_code,
        )
        order_state.subtotal = sub_res["subtotal"]
        order_state.discount_amount = sub_res["discount_amount"]

        self.record_tool_call(
            order_state=order_state,
            tool_name="calculate_subtotal_and_discounts",
            action="DiscountCalculation",
            status="SUCCESS",
            message=f"Subtotal: ${sub_res['subtotal']}, Discounts: -${sub_res['discount_amount']}.",
            start_time=t1_start,
            details={
                "subtotal": str(sub_res["subtotal"]),
                "discount_amount": str(sub_res["discount_amount"]),
                "applied_rules": sub_res["applied_rules"],
            },
        )

        # TOOL 2: Calculate Tax and Shipping Charges
        t2_start = time.time()
        tax_ship_res = calculate_tax_and_shipping(
            subtotal=order_state.subtotal,
            discount_amount=order_state.discount_amount,
            shipping_method=order_state.shipping_method,
            coupon_free_shipping=sub_res["coupon_free_shipping"],
        )
        order_state.tax_amount = tax_ship_res["tax_amount"]
        order_state.shipping_cost = tax_ship_res["shipping_cost"]

        self.record_tool_call(
            order_state=order_state,
            tool_name="calculate_tax_and_shipping",
            action="TaxShippingCalculation",
            status="SUCCESS",
            message=f"Tax (8%): +${tax_ship_res['tax_amount']}, Shipping: +${tax_ship_res['shipping_cost']}.",
            start_time=t2_start,
            details={
                "tax_amount": str(tax_ship_res["tax_amount"]),
                "shipping_cost": str(tax_ship_res["shipping_cost"]),
            },
        )

        # TOOL 3: Finalize Order Total
        t3_start = time.time()
        final_amt = finalize_order_total(
            subtotal=order_state.subtotal,
            discount_amount=order_state.discount_amount,
            tax_amount=order_state.tax_amount,
            shipping_cost=order_state.shipping_cost,
        )
        order_state.final_amount = final_amt
        order_state.pricing_status = "CALCULATED"

        self.record_tool_call(
            order_state=order_state,
            tool_name="finalize_order_total",
            action="FinalTotalResolution",
            status="SUCCESS",
            message=f"Final payable order amount finalized at ${final_amt}.",
            start_time=t3_start,
            details={"final_amount": str(final_amt)},
        )

        # Agent Summary Log
        self.record_agent_log(
            order_state,
            action="PricingSummary",
            status="SUCCESS",
            message=f"Pricing completed: Final Payable Amount is ${final_amt}.",
            start_time=start_time,
            details={
                "subtotal": str(order_state.subtotal),
                "discount": str(order_state.discount_amount),
                "tax": str(order_state.tax_amount),
                "shipping": str(order_state.shipping_cost),
                "final_amount": str(order_state.final_amount),
            },
        )
        return True
