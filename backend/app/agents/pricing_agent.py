import time
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseOrchestratorAgent
from backend.app.schemas.order_state import OrderState
from backend.app.models.product import Product
from backend.app.config import settings


def quantize_currency(amount: Decimal) -> Decimal:
    """Helper to round decimals strictly to 2 decimal places using standard financial round-half-up."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PricingAgent(BaseOrchestratorAgent):
    """
    Agent 4: Pricing Agent
    Implements deterministic financial decimal arithmetic:
    - Base price calculation per item (price * quantity)
    - Subtotal calculation
    - Volume discount rules
    - Coupon code validation & application
    - State/regional sales tax calculation
    - Dynamic shipping calculation with free shipping thresholds
    - Final payable amount
    """

    def __init__(self) -> None:
        super().__init__(
            name="PricingAgent",
            description="Executes deterministic financial arithmetic for subtotals, coupons, taxes, and shipping.",
            agent_id="agt-pricing-004",
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

        # 1. Product price calculation & subtotal
        raw_subtotal = Decimal("0.00")
        for item in order_state.items:
            product = db.query(Product).filter(Product.sku == item.sku).first()
            if product:
                item.unit_price = Decimal(str(product.price))
            item.total_price = quantize_currency(item.unit_price * Decimal(str(item.quantity)))
            raw_subtotal += item.total_price

        order_state.subtotal = quantize_currency(raw_subtotal)

        # 2. Volume & Quantity Discounts
        discount_amount = Decimal("0.00")
        applied_rules: List[str] = []

        total_item_quantity = sum(item.quantity for item in order_state.items)
        if total_item_quantity >= 5:
            vol_discount = quantize_currency(order_state.subtotal * Decimal("0.05"))
            discount_amount += vol_discount
            applied_rules.append(f"Bulk Volume Discount (5% for >=5 units: -${vol_discount})")

        # 3. Coupon Validation & Application
        coupon_free_shipping = False
        if order_state.coupon_code:
            code = order_state.coupon_code.strip().upper()
            if code == "WELCOME10":
                coupon_discount = quantize_currency(order_state.subtotal * Decimal("0.10"))
                discount_amount += coupon_discount
                applied_rules.append(f"Coupon WELCOME10 (10% off: -${coupon_discount})")
            elif code == "SAVE20":
                if order_state.subtotal >= Decimal("100.00"):
                    coupon_discount = Decimal("20.00")
                    discount_amount += coupon_discount
                    applied_rules.append("Coupon SAVE20 (-$20.00)")
                else:
                    applied_rules.append("Coupon SAVE20 rejected: minimum subtotal of $100.00 required")
            elif code == "FREESHIP":
                coupon_free_shipping = True
                applied_rules.append("Coupon FREESHIP (100% off shipping applied)")
            else:
                applied_rules.append(f"Invalid coupon code '{code}' ignored")

        # Cap discount to subtotal
        discount_amount = min(discount_amount, order_state.subtotal)
        order_state.discount_amount = quantize_currency(discount_amount)

        # 4. Tax Calculation (deterministic 8% on taxable subtotal after discount)
        taxable_subtotal = max(order_state.subtotal - order_state.discount_amount, Decimal("0.00"))
        calculated_tax = quantize_currency(taxable_subtotal * settings.DEFAULT_TAX_RATE)
        order_state.tax_amount = calculated_tax

        # 5. Shipping Charges
        shipping_fee = Decimal("0.00")
        if coupon_free_shipping or taxable_subtotal >= settings.FREE_SHIPPING_THRESHOLD:
            shipping_fee = Decimal("0.00")
            applied_rules.append("Free shipping qualified (Order >= $100 or Free Shipping coupon)")
        else:
            if order_state.shipping_method == "Express":
                shipping_fee = settings.EXPRESS_SHIPPING_COST
            else:
                shipping_fee = settings.STANDARD_SHIPPING_COST
            applied_rules.append(f"Standard shipping charge applied (+${shipping_fee})")

        order_state.shipping_cost = quantize_currency(shipping_fee)

        # 6. Final Payable Amount
        final_total = taxable_subtotal + order_state.tax_amount + order_state.shipping_cost
        order_state.final_amount = quantize_currency(final_total)
        order_state.pricing_status = "CALCULATED"

        self.record_agent_log(
            order_state,
            action="PricingCalculation",
            status="SUCCESS",
            message=f"Financial calculations finalized: Final Payable = ${order_state.final_amount}.",
            start_time=start_time,
            details={
                "subtotal": str(order_state.subtotal),
                "discount_amount": str(order_state.discount_amount),
                "tax_amount": str(order_state.tax_amount),
                "shipping_cost": str(order_state.shipping_cost),
                "final_amount": str(order_state.final_amount),
                "applied_rules": applied_rules,
            },
        )
        return True
