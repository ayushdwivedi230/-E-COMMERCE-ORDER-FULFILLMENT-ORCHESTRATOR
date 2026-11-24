"""
Microsoft Agent Framework Specialized Python Tools
CSE476 Agentic AI and Intelligent Automation

Every working agent calls at least TWO real tools written as plain Python functions
and decorated with @tool from Microsoft Agent Framework (`agent-framework-core`).
These tools execute deterministic business logic, database queries, calculations,
and logistics operations.
"""

import re
import uuid
import random
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from agent_framework import tool
from backend.app.schemas.order_state import (
    OrderState,
    OrderItemState,
    AddressState,
    PaymentState,
    SubstituteRecommendation,
    BackorderProposal,
    NotificationDraft,
)
from backend.app.models.customer import Customer
from backend.app.models.product import Product
from backend.app.models.order import OrderHistory
from backend.app.models.inventory import InventoryReservation
from backend.app.models.fraud import FraudReview
from backend.app.models.shipment import Shipment
from backend.app.schemas.customer import CustomerHistoryStats, OrderHistoryEntry
from backend.app.config import settings
from backend.app.services.catalog_service import quantize_currency, validate_and_resolve_order_items


# ==============================================================================
# AGENT 1: VALIDATION AGENT TOOLS
# ==============================================================================

@tool(
    name="validate_customer_standing",
    description="Validates customer existence in database, active standing, and retrieves contact details."
)
def validate_customer_standing(
    db: Any,
    customer_id: str
) -> Dict[str, Any]:
    """Inspect customer standing, checking for blocked status or missing record."""
    if not customer_id:
        return {"valid": False, "errors": ["Customer ID is missing."], "warnings": []}

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return {
            "valid": False,
            "errors": [f"Customer with ID '{customer_id}' does not exist."],
            "warnings": [],
        }

    if customer.status == "BLOCKED":
        return {
            "valid": False,
            "errors": [f"Customer '{customer.name}' account is BLOCKED."],
            "warnings": [],
        }

    warnings = []
    if customer.status == "FLAGGED":
        warnings.append(f"Customer '{customer.name}' has prior FLAGGED standing.")

    return {
        "valid": True,
        "customer_id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "status": customer.status,
        "errors": [],
        "warnings": warnings,
    }


@tool(
    name="validate_catalog_and_quantities",
    description="Validates that requested SKUs exist in product catalog and quantities are strictly positive and within bounds."
)
def validate_catalog_and_quantities(
    db: Any,
    items: List[OrderItemState]
) -> Dict[str, Any]:
    """Verify each requested SKU against the product catalog and validate quantity bounds."""
    return validate_and_resolve_order_items(db, items)


@tool(
    name="validate_shipping_and_payment",
    description="Validates shipping destination address completeness and payment token presence and status."
)
def validate_shipping_and_payment(
    address: Optional[AddressState],
    payment: Optional[PaymentState]
) -> Dict[str, Any]:
    """Validate address completeness (street, city, state, postal code) and payment token presence."""
    errors: List[str] = []
    warnings: List[str] = []

    # Address validation
    if not address:
        errors.append("Shipping address is missing.")
    else:
        if not address.street or not address.street.strip():
            errors.append("Shipping address street is missing or empty.")
        if not address.city or not address.city.strip():
            errors.append("Shipping address city is missing or empty.")
        if not address.state or not address.state.strip():
            errors.append("Shipping address state is missing or empty.")
        if not address.postal_code or not address.postal_code.strip():
            errors.append("Shipping address postal code is missing or empty.")
        elif not re.match(r"^\d{5}(-\d{4})?$", address.postal_code.strip()):
            warnings.append(f"Postal code '{address.postal_code}' does not match standard 5-digit US format.")

    # Payment validation
    if not payment:
        errors.append("Payment information is missing.")
    else:
        if not payment.payment_method:
            errors.append("Payment method is not specified.")
        if payment.payment_status == "FAILED":
            errors.append("Payment status is FAILED; transaction cannot proceed.")
        if not payment.transaction_token:
            errors.append("Payment authorization token is missing.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# ==============================================================================
# AGENT 2: INVENTORY AGENT TOOLS
# ==============================================================================

@tool(
    name="check_stock_availability",
    description="Inspects real-time inventory levels, identifies shortfalls, substitute SKU recommendations, and backorder proposals."
)
def check_stock_availability(
    db: Any,
    items: List[OrderItemState]
) -> Dict[str, Any]:
    """Inspect current catalog stock for all items without placing holds."""
    all_available = True
    insufficient_items: List[str] = []
    substitutes: List[Dict[str, Any]] = []
    backorders: List[Dict[str, Any]] = []

    for item in items:
        product = db.query(Product).filter(Product.sku == item.sku).first()
        if not product:
            all_available = False
            insufficient_items.append(f"SKU {item.sku} does not exist.")
            continue

        if product.stock_quantity < item.quantity:
            all_available = False
            insufficient_items.append(
                f"SKU {item.sku} ({product.name}) has insufficient stock. Requested: {item.quantity}, Available: {product.stock_quantity}"
            )
            backorders.append({
                "sku": product.sku,
                "product_name": product.name,
                "requested_quantity": item.quantity,
                "available_quantity": product.stock_quantity,
                "estimated_restock_days": 7,
            })
            if product.substitute_sku:
                sub_prod = db.query(Product).filter(Product.sku == product.substitute_sku).first()
                if sub_prod and sub_prod.stock_quantity >= item.quantity:
                    substitutes.append({
                        "original_sku": product.sku,
                        "substitute_sku": sub_prod.sku,
                        "substitute_name": sub_prod.name,
                        "substitute_price": float(sub_prod.price),
                        "reason": f"Recommended substitute for out-of-stock {product.name}. Customer approval required.",
                    })

    return {
        "all_available": all_available,
        "insufficient_items": insufficient_items,
        "substitutes": substitutes,
        "backorders": backorders,
    }


@tool(
    name="reserve_stock_atomic",
    description="Performs atomic stock deduction and creates persistent InventoryReservation records with timeout."
)
def reserve_stock_atomic(
    db: Any,
    order_id: str,
    items: List[OrderItemState],
    timeout_minutes: int = 15
) -> Dict[str, Any]:
    """Deduct stock and insert inventory reservations atomically."""
    # Check availability first
    check = check_stock_availability(db, items)
    if not check["all_available"]:
        return {
            "success": False,
            "message": f"Stock verification failed: {'; '.join(check['insufficient_items'])}",
            "substitutes": check["substitutes"],
            "backorders": check["backorders"],
            "reservation_ids": [],
        }

    now_utc = datetime.now(timezone.utc)
    expires_at = now_utc + timedelta(minutes=timeout_minutes)
    reservation_ids = []

    for item in items:
        query = db.query(Product).filter(Product.sku == item.sku)
        if hasattr(db, "bind") and db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update(nowait=False)
        product = query.first()
        if product:
            product.stock_quantity -= item.quantity
            res_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
            reservation = InventoryReservation(
                id=res_id,
                order_id=order_id,
                product_id=product.id,
                quantity_reserved=item.quantity,
                status="RESERVED",
                expires_at=expires_at,
            )
            db.add(reservation)
            reservation_ids.append(res_id)

    db.commit()
    return {
        "success": True,
        "message": f"All {len(items)} item(s) reserved atomically.",
        "substitutes": [],
        "backorders": [],
        "reservation_ids": reservation_ids,
        "expires_at": expires_at.isoformat(),
    }


@tool(
    name="release_stock_reservation",
    description="Releases active inventory reservations and restores stock quantities on cancellation or fraud hold."
)
def release_stock_reservation(
    db: Any,
    order_id: str
) -> Dict[str, Any]:
    """Release active inventory reservations back to catalog stock."""
    reservations = (
        db.query(InventoryReservation)
        .filter(InventoryReservation.order_id == order_id, InventoryReservation.status == "RESERVED")
        .all()
    )
    if not reservations:
        return {"success": True, "released_count": 0, "message": "No active reservations found to release."}

    released_count = 0
    for res in reservations:
        product = db.query(Product).filter(Product.id == res.product_id).first()
        if product:
            product.stock_quantity += res.quantity_reserved
        res.status = "RELEASED"
        released_count += 1

    db.commit()
    return {
        "success": True,
        "released_count": released_count,
        "message": f"Successfully released {released_count} reservation hold(s) for order {order_id}.",
    }


# ==============================================================================
# AGENT 3: FRAUD CHECK AGENT TOOLS
# ==============================================================================

@tool(
    name="retrieve_customer_history",
    description="Retrieves prior customer order memory and calculates historical risk statistics."
)
def retrieve_customer_history(
    db: Any,
    customer_id: str
) -> Dict[str, Any]:
    """Retrieve historical transaction memory from order_history table."""
    history_rows = (
        db.query(OrderHistory)
        .filter(OrderHistory.customer_id == customer_id)
        .order_by(OrderHistory.created_at.desc())
        .all()
    )
    total_orders = len(history_rows)
    if total_orders == 0:
        return {
            "customer_id": customer_id,
            "total_orders": 0,
            "successful_orders": 0,
            "suspicious_orders": 0,
            "failed_payment_attempts": 0,
            "total_spent": "0.00",
            "average_order_value": "0.00",
            "suspicion_rate": 0.0,
            "risk_tier": "LOW",
        }

    successful = 0
    suspicious = 0
    failed_attempts = 0
    total_spent = Decimal("0.00")

    for row in history_rows:
        failed_attempts += row.failed_payment_attempts
        if row.is_suspicious or row.status in ["CHARGEBACK", "SUSPICIOUS"]:
            suspicious += 1
        if row.status in ["DELIVERED", "COMPLETED"]:
            successful += 1
            total_spent += Decimal(str(row.amount))

    avg_order = total_spent / Decimal(str(successful)) if successful > 0 else Decimal("0.00")
    suspicion_rate = float(suspicious) / float(total_orders) if total_orders > 0 else 0.0

    if suspicious >= 2 or suspicion_rate >= 0.40 or failed_attempts >= 3:
        risk_tier = "HIGH"
    elif suspicious == 1 or suspicion_rate >= 0.15 or failed_attempts >= 1:
        risk_tier = "MEDIUM"
    else:
        risk_tier = "LOW"

    return {
        "customer_id": customer_id,
        "total_orders": total_orders,
        "successful_orders": successful,
        "suspicious_orders": suspicious,
        "failed_payment_attempts": failed_attempts,
        "total_spent": str(quantize_currency(total_spent)),
        "average_order_value": str(quantize_currency(avg_order)),
        "suspicion_rate": round(suspicion_rate, 4),
        "risk_tier": risk_tier,
    }


@tool(
    name="calculate_fraud_risk_score",
    description="Calculates deterministic 0-100 fraud risk score combining historical memory, velocity, and transaction features."
)
def calculate_fraud_risk_score(
    order_state: OrderState,
    history_stats: Dict[str, Any],
    simulated_failed_attempts: int = 0
) -> Dict[str, Any]:
    """Calculate multi-factor deterministic fraud risk score on 0-100 scale."""
    risk_score = 0.0
    risk_factors: List[str] = []

    # 1. Historical chargeback and suspicion
    suspicious_count = history_stats.get("suspicious_orders", 0)
    if suspicious_count >= 2:
        risk_score += 45.0
        risk_factors.append(f"Customer has {suspicious_count} prior chargebacks / suspicious orders (+45)")
    elif suspicious_count == 1:
        risk_score += 25.0
        risk_factors.append("Customer has 1 prior suspicious transaction / chargeback in history (+25)")

    # 2. Payment retries & velocity
    total_retries = history_stats.get("failed_payment_attempts", 0) + simulated_failed_attempts
    if total_retries >= 3:
        risk_score += 30.0
        risk_factors.append(f"High payment retry velocity ({total_retries} failed attempts) (+30)")
    elif total_retries in [1, 2]:
        risk_score += 15.0
        risk_factors.append(f"Moderate payment retries ({total_retries} attempts) (+15)")

    # 3. First-time customer high value anomaly
    est_subtotal = sum(item.unit_price * item.quantity for item in order_state.items)
    if history_stats.get("total_orders", 0) == 0:
        if est_subtotal > Decimal("500.00"):
            risk_score += 25.0
            risk_factors.append(f"First-time customer with high cart value (${est_subtotal:.2f}) (+25)")
        else:
            risk_score += 5.0
            risk_factors.append("First-time customer baseline (+5)")
    else:
        avg_spent = Decimal(history_stats.get("average_order_value", "0.00"))
        if avg_spent > Decimal("0.00") and est_subtotal > (avg_spent * Decimal("3.0")):
            risk_score += 20.0
            risk_factors.append(f"Order value (${est_subtotal:.2f}) is >3x customer's historical average (${avg_spent:.2f}) (+20)")

    # 4. Shipping vs Billing address mismatch
    pay = order_state.payment_information
    if pay and pay.billing_address and order_state.shipping_address:
        ship_addr = order_state.shipping_address
        bill_addr = pay.billing_address
        if (
            ship_addr.postal_code.strip() != bill_addr.postal_code.strip()
            or ship_addr.state.strip().upper() != bill_addr.state.strip().upper()
        ):
            risk_score += 15.0
            risk_factors.append(f"Shipping ({ship_addr.city}, {ship_addr.state}) and Billing ({bill_addr.city}, {bill_addr.state}) mismatch (+15)")

    # 5. PO Box or freight forwarding address heuristic
    if order_state.shipping_address and order_state.shipping_address.street:
        st_lower = order_state.shipping_address.street.lower()
        if "po box" in st_lower or "p.o. box" in st_lower or "suite 9999" in st_lower:
            risk_score += 10.0
            risk_factors.append("Destination matches PO Box / Mail Drop profile (+10)")

    # Cap score strictly between 0 and 100
    final_score = min(max(round(risk_score, 1), 0.0), 100.0)

    # Classify Tier
    if final_score <= settings.FRAUD_LOW_THRESHOLD:
        tier = "LOW"
        decision = "APPROVED"
    elif final_score <= settings.FRAUD_MEDIUM_THRESHOLD:
        tier = "MEDIUM"
        decision = "FLAGGED"
    else:
        tier = "HIGH"
        decision = "HELD"

    # Contextual Explanation
    if tier == "HIGH":
        explanation = (
            f"HIGH-RISK ANOMALY DETECTED (Score {final_score}/100 >= {settings.FRAUD_HIGH_THRESHOLD}): "
            f"Order halted and escalated to human review queue. Triggers: {'; '.join(risk_factors)}. "
            f"Atomic inventory reservations have been released."
        )
    elif tier == "MEDIUM":
        explanation = (
            f"MEDIUM-RISK WARNING (Score {final_score}/100): Transaction permitted to proceed under cautionary flag. "
            f"Contributing factors: {'; '.join(risk_factors)}."
        )
    else:
        explanation = (
            f"APPROVED / CLEARED (Score {final_score}/100): Customer transaction profile meets all trust metrics. "
            f"Zero critical fraud indicators detected."
        )

    return {
        "score": final_score,
        "risk_tier": tier,
        "decision": decision,
        "risk_factors": risk_factors,
        "ai_explanation": explanation,
    }


@tool(
    name="persist_fraud_review",
    description="Persists formal FraudReview entity to database with score, decision, and audit attribution."
)
def persist_fraud_review(
    db: Any,
    order_id: str,
    customer_id: str,
    score: float,
    risk_tier: str,
    risk_factors: List[str],
    ai_explanation: str,
    decision: str
) -> Dict[str, Any]:
    """Persist fraud evaluation to database."""
    review_id = f"FRD-{uuid.uuid4().hex[:8].upper()}"
    record = FraudReview(
        id=review_id,
        order_id=order_id,
        customer_id=customer_id,
        fraud_score=score,
        risk_level=risk_tier,
        reasons="; ".join(risk_factors) if risk_factors else "None",
        ai_explanation=ai_explanation,
        decision=decision,
        reviewed_by="FraudCheckAgent",
    )
    db.add(record)
    db.commit()
    return {"review_id": review_id, "recorded": True}


# ==============================================================================
# AGENT 4: PRICING AGENT TOOLS
# ==============================================================================

@tool(
    name="calculate_subtotal_and_discounts",
    description="Computes exact item subtotals, applies bulk volume discounts, and validates promotional coupon codes."
)
def calculate_subtotal_and_discounts(
    items: List[OrderItemState],
    coupon_code: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate subtotal, volume discounts, and coupon discounts using Decimal."""
    raw_subtotal = Decimal("0.00")
    for item in items:
        item.total_price = quantize_currency(item.unit_price * Decimal(str(item.quantity)))
        raw_subtotal += item.total_price

    subtotal = quantize_currency(raw_subtotal)
    discount_amount = Decimal("0.00")
    applied_rules: List[str] = []
    coupon_free_shipping = False

    # Bulk Volume Discount (>= 5 units)
    total_qty = sum(item.quantity for item in items)
    if total_qty >= 5:
        vol_discount = quantize_currency(subtotal * Decimal("0.05"))
        discount_amount += vol_discount
        applied_rules.append(f"Bulk Volume Discount (5% for >=5 units: -${vol_discount})")

    # Coupon Evaluation
    if coupon_code:
        code = coupon_code.strip().upper()
        if code == "WELCOME10":
            c_disc = quantize_currency(subtotal * Decimal("0.10"))
            discount_amount += c_disc
            applied_rules.append(f"Coupon WELCOME10 (10% off: -${c_disc})")
        elif code == "SAVE20":
            if subtotal >= Decimal("100.00"):
                discount_amount += Decimal("20.00")
                applied_rules.append("Coupon SAVE20 (-$20.00)")
            else:
                applied_rules.append("Coupon SAVE20 rejected: minimum subtotal of $100.00 required")
        elif code == "FREESHIP":
            coupon_free_shipping = True
            applied_rules.append("Coupon FREESHIP (100% off shipping applied)")
        else:
            applied_rules.append(f"Invalid coupon code '{code}' ignored")

    # Cap discount at subtotal
    discount_amount = min(discount_amount, subtotal)
    return {
        "subtotal": subtotal,
        "discount_amount": quantize_currency(discount_amount),
        "applied_rules": applied_rules,
        "coupon_free_shipping": coupon_free_shipping,
    }


@tool(
    name="calculate_tax_and_shipping",
    description="Calculates regional sales tax on taxable subtotal and dynamic shipping cost based on thresholds."
)
def calculate_tax_and_shipping(
    subtotal: Decimal,
    discount_amount: Decimal,
    shipping_method: Optional[str] = "Standard",
    coupon_free_shipping: bool = False
) -> Dict[str, Any]:
    """Calculate sales tax (8%) and shipping fees using Decimal arithmetic."""
    taxable_subtotal = max(subtotal - discount_amount, Decimal("0.00"))
    tax_amount = quantize_currency(taxable_subtotal * settings.DEFAULT_TAX_RATE)

    # Dynamic Shipping calculation
    if coupon_free_shipping or subtotal >= settings.FREE_SHIPPING_THRESHOLD:
        shipping_cost = Decimal("0.00")
    elif shipping_method and "Express" in shipping_method:
        shipping_cost = settings.EXPRESS_SHIPPING_COST
    else:
        shipping_cost = settings.STANDARD_SHIPPING_COST

    return {
        "tax_amount": tax_amount,
        "shipping_cost": quantize_currency(shipping_cost),
    }


@tool(
    name="finalize_order_total",
    description="Computes final payable total ensuring non-negative balance and 2-decimal financial rounding."
)
def finalize_order_total(
    subtotal: Decimal,
    discount_amount: Decimal,
    tax_amount: Decimal,
    shipping_cost: Decimal
) -> Decimal:
    """Final total = subtotal - discount + tax + shipping."""
    final_amount = max(subtotal - discount_amount + tax_amount + shipping_cost, Decimal("0.00"))
    return quantize_currency(final_amount)


# ==============================================================================
# AGENT 5: DISPATCH COORDINATOR TOOLS
# ==============================================================================

@tool(
    name="select_optimal_carrier",
    description="Evaluates order parameters and logistics SLAs to assign optimal freight/courier carrier."
)
def select_optimal_carrier(
    shipping_method: Optional[str],
    destination_state: Optional[str] = None,
    item_count: int = 1
) -> Dict[str, str]:
    """Select appropriate carrier based on requested service level."""
    method = shipping_method or "Standard"
    if "Express" in method or "Priority" in method:
        carrier = "FedEx Priority Express"
        service = "Express Air (1-2 Business Days)"
    elif destination_state in ["AK", "HI", "PR"]:
        carrier = "USPS Priority Commerce"
        service = "USPS Priority Island Logistics (3-5 Days)"
    elif item_count >= 10:
        carrier = "DHL Express Worldwide"
        service = "DHL Heavy Freight Logistics"
    else:
        carrier = "UPS Ground Logistics"
        service = "UPS Ground Tracked (3-5 Business Days)"

    return {
        "carrier": carrier,
        "shipping_method": method,
        "service_level": service,
    }


@tool(
    name="generate_tracking_and_manifest",
    description="Generates simulated carrier tracking number and operational warehouse packaging manifest."
)
def generate_tracking_and_manifest(
    carrier: str,
    method: str,
    item_count: int = 1
) -> Dict[str, Any]:
    """Generate carrier tracking ID and packaging manifest."""
    carrier_prefix = {
        "FedEx Priority Express": "FDX",
        "UPS Ground Logistics": "UPS",
        "USPS Priority Commerce": "USP",
        "DHL Express Worldwide": "DHL",
    }.get(carrier, "EXP")

    tracking_id = f"TRK-{carrier_prefix}-{random.randint(10000000, 99999999)}"
    now = datetime.now(timezone.utc)
    est_delivery = now + timedelta(days=2 if "Express" in method else 4)

    manifest = {
        "warehouse_id": "WH-CENTRAL-01",
        "carrier": carrier,
        "service_level": method,
        "package_weight_kg": round(item_count * 0.85, 2),
        "estimated_pickup": (now + timedelta(hours=3)).isoformat(),
        "estimated_delivery": est_delivery.isoformat(),
    }
    return {
        "tracking_id": tracking_id,
        "manifest": manifest,
        "estimated_delivery": est_delivery,
    }


@tool(
    name="create_shipment_record",
    description="Persists formal Shipment entity to database and commits active inventory reservations."
)
def create_shipment_record(
    db: Any,
    order_id: str,
    tracking_id: str,
    carrier: str,
    shipping_method: str,
    estimated_delivery: Any
) -> Dict[str, Any]:
    """Persist shipment record in database and commit inventory reservations."""
    shipment_id = f"SHP-{uuid.uuid4().hex[:8].upper()}"
    shipment = Shipment(
        id=shipment_id,
        order_id=order_id,
        tracking_id=tracking_id,
        carrier=carrier,
        shipping_method=shipping_method,
        status="DISPATCHED",
        estimated_delivery=estimated_delivery,
        dispatch_notes=f"Dispatched via {carrier} ({shipping_method}). Tracking: {tracking_id}.",
    )
    db.add(shipment)

    # Commit inventory reservations
    reservations = (
        db.query(InventoryReservation)
        .filter(InventoryReservation.order_id == order_id, InventoryReservation.status == "RESERVED")
        .all()
    )
    for res in reservations:
        res.status = "COMMITTED"

    db.commit()
    return {"shipment_id": shipment_id, "status": "DISPATCHED", "committed_reservations": len(reservations)}


# ==============================================================================
# AGENT 6: NOTIFICATION AGENT TOOLS (Group Extension & Customer Preview)
# ==============================================================================

@tool(
    name="draft_customer_notification",
    description="Drafts tailored multi-channel customer communications (Email + SMS) across Confirmed, Substituted, or Held outcomes."
)
def draft_customer_notification(
    order_state: OrderState
) -> NotificationDraft:
    """Generate professional, contextual customer-facing notification drafts."""
    customer_name = order_state.customer_name or "Valued Customer"
    order_id = order_state.order_id
    email = order_state.customer_email
    phone = order_state.customer_phone

    # Case 1: Confirmed & Dispatched Order
    if order_state.dispatch_status == "DISPATCHED" and order_state.tracking_id:
        subject = f"Order Confirmed & Shipped! ({order_id})"
        body = (
            f"Dear {customer_name},\n\n"
            f"Great news! Your order {order_id} has been confirmed, carefully packaged, and dispatched.\n\n"
            f"Carrier: {order_state.carrier} ({order_state.shipping_method})\n"
            f"Tracking ID: {order_state.tracking_id}\n"
            f"Total Paid: ${order_state.final_amount:.2f}\n\n"
            f"You can track your delivery in real time through our operations dashboard.\n\n"
            f"Thank you for shopping with us!"
        )
        sms = f"Your order {order_id} has shipped via {order_state.carrier}! Tracking: {order_state.tracking_id}."
        intent = "CONFIRMED"

    # Case 2: Insufficient Stock / Substitute or Backorder Notice
    elif order_state.inventory_status in ["SUBSTITUTE_RECOMMENDED", "BACKORDER_PROPOSED", "INSUFFICIENT_STOCK"]:
        sub_info = ""
        if order_state.substitute_recommendations:
            rec = order_state.substitute_recommendations[0]
            sub_info = f"\nProposed Substitute: {rec.substitute_name} ({rec.substitute_sku}) - ${rec.substitute_price:.2f}."
        elif order_state.backorder_proposals:
            prop = order_state.backorder_proposals[0]
            sub_info = f"\nBackorder Restock Timeline: Estimated {prop.estimated_restock_days} business days."

        subject = f"Action Required: Inventory Update for Order {order_id}"
        body = (
            f"Dear {customer_name},\n\n"
            f"We are preparing your order {order_id}; however, an item in your order is currently out of stock.{sub_info}\n\n"
            f"In accordance with our customer protection policy, we never silently alter orders. "
            f"Please visit your order portal to provide your explicit approval for this substitution or confirm a backorder.\n\n"
            f"Our team is standing by to assist you."
        )
        sms = f"Update on order {order_id}: Stock shortage. Please review and approve suggested substitute in your portal."
        intent = "SUBSTITUTED"

    # Case 3: High-Risk Fraud Hold
    elif order_state.fraud_status == "HIGH_RISK_HELD":
        subject = f"Security Verification: Order {order_id} Under Review"
        body = (
            f"Dear {customer_name},\n\n"
            f"Thank you for your order {order_id}. As part of our standard security procedures to protect our "
            f"cardholders, this order has been routed to our verification queue for routine confirmation.\n\n"
            f"No additional charges have been applied. Our customer trust and safety team will complete "
            f"this review within 1 business day.\n\n"
            f"If you did not authorize this purchase, please contact our 24/7 security hotline immediately."
        )
        sms = f"Order {order_id} is temporarily held for standard security review. We will notify you once cleared."
        intent = "HELD_FRAUD"

    # Case 4: Validation or Payment Structural Failure
    else:
        subject = f"Notice: Issue Processing Order {order_id}"
        body = (
            f"Dear {customer_name},\n\n"
            f"We were unable to complete processing for order {order_id}.\n"
            f"Reason: {order_state.hold_reason or 'Validation requirements could not be verified'}.\n\n"
            f"Please verify your payment details and shipping destination address in your account settings."
        )
        sms = f"Unable to process order {order_id}. Please check your payment details or address: {order_state.hold_reason}."
        intent = "HELD_VALIDATION"

    return NotificationDraft(
        channel="EMAIL_AND_SMS",
        recipient_email=email,
        recipient_phone=phone,
        subject=subject,
        body=body,
        sms_summary=sms,
        status="DRAFTED",
        intent=intent,
    )


@tool(
    name="record_notification_log",
    description="Attaches drafted customer notification to order state and logs dispatch preview event."
)
def record_notification_log(
    order_state: OrderState,
    draft: NotificationDraft
) -> Dict[str, Any]:
    """Attach notification to order state and mark drafted status."""
    order_state.customer_notification_draft = draft
    order_state.notification_status = "DRAFTED"
    return {
        "notification_id": f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
        "channel": draft.channel,
        "intent": draft.intent,
        "subject": draft.subject,
        "status": "DRAFTED_PREVIEW",
    }
