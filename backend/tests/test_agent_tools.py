"""
Unit Tests for Microsoft Agent Framework Specialized Python Tools
CSE476 Agentic AI and Intelligent Automation

Verifies that every working agent calls at least TWO real tools written as
plain Python functions decorated with @tool from `agent-framework-core`.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from backend.app.schemas.order_state import (
    OrderState,
    OrderItemState,
    AddressState,
    PaymentState,
)
from backend.app.agents.tools import (
    # Validation Agent Tools
    validate_customer_standing,
    validate_catalog_and_quantities,
    validate_shipping_and_payment,
    # Inventory Agent Tools
    check_stock_availability,
    reserve_stock_atomic,
    release_stock_reservation,
    # Fraud Check Agent Tools
    retrieve_customer_history,
    calculate_fraud_risk_score,
    persist_fraud_review,
    # Pricing Agent Tools
    calculate_subtotal_and_discounts,
    calculate_tax_and_shipping,
    finalize_order_total,
    # Dispatch Coordinator Tools
    select_optimal_carrier,
    generate_tracking_and_manifest,
    create_shipment_record,
    # Notification Agent Tools
    draft_customer_notification,
    record_notification_log,
)


# ==============================================================================
# VALIDATION AGENT TOOLS TESTS
# ==============================================================================

def test_tool_validate_customer_standing_active(db_session):
    """Tool 1: Verify active customer lookup."""
    res = validate_customer_standing(db_session, "CUST-001")
    assert res["valid"] is True
    assert res["name"] == "John Verified"
    assert res["status"] == "ACTIVE"
    assert len(res["errors"]) == 0


def test_tool_validate_customer_standing_missing(db_session):
    """Tool 1: Verify non-existent customer failure."""
    res = validate_customer_standing(db_session, "CUST-NONEXISTENT")
    assert res["valid"] is False
    assert any("does not exist" in e for e in res["errors"])


def test_tool_validate_catalog_and_quantities_success(db_session):
    """Tool 2: Verify valid catalog SKUs and positive quantities."""
    items = [OrderItemState(product_id="P1", sku="KB-MECH-RGB", name="Keyboard", quantity=2)]
    res = validate_catalog_and_quantities(db_session, items)
    assert res["valid"] is True
    assert res["item_count"] == 1
    assert items[0].unit_price == Decimal("99.99")
    assert items[0].total_price == Decimal("199.98")


def test_tool_validate_catalog_and_quantities_invalid_sku(db_session):
    """Tool 2: Verify detection of non-existent catalog SKUs."""
    items = [OrderItemState(product_id="P1", sku="INVALID-SKU-999", name="Fake", quantity=1)]
    res = validate_catalog_and_quantities(db_session, items)
    assert res["valid"] is False
    assert any("does not exist in catalog" in e for e in res["errors"])


def test_tool_validate_shipping_and_payment_valid():
    """Tool 3: Verify complete address and valid payment."""
    addr = AddressState(street="123 Main St", city="Portland", state="OR", postal_code="97201", country="USA")
    pay = PaymentState(payment_method="CREDIT_CARD", payment_status="AUTHORIZED", transaction_token="tok_123")
    res = validate_shipping_and_payment(addr, pay)
    assert res["valid"] is True
    assert len(res["errors"]) == 0


def test_tool_validate_shipping_and_payment_failed_status():
    """Tool 3: Verify rejection on payment failure or missing address."""
    addr = AddressState(street="", city="Portland", state="OR", postal_code="97201", country="USA")
    pay = PaymentState(payment_method="CREDIT_CARD", payment_status="FAILED", transaction_token="")
    res = validate_shipping_and_payment(addr, pay)
    assert res["valid"] is False
    assert any("street is missing" in e for e in res["errors"])
    assert any("FAILED" in e for e in res["errors"])


# ==============================================================================
# INVENTORY AGENT TOOLS TESTS
# ==============================================================================

def test_tool_check_stock_availability(db_session):
    """Tool 1: Verify real-time stock inspection."""
    items = [OrderItemState(product_id="P1", sku="KB-MECH-RGB", name="Keyboard", quantity=5)]
    res = check_stock_availability(db_session, items)
    assert res["all_available"] is True
    assert len(res["insufficient_items"]) == 0


def test_tool_check_stock_availability_shortage(db_session):
    """Tool 1: Verify shortfall detection and substitute recommendation."""
    items = [OrderItemState(product_id="P1", sku="KB-MECH-RGB", name="Keyboard", quantity=9999)]
    res = check_stock_availability(db_session, items)
    assert res["all_available"] is False
    assert len(res["backorders"]) > 0


def test_tool_reserve_and_release_stock_atomic(db_session):
    """Tool 2 & 3: Verify atomic reservation deduction and subsequent rollback release."""
    order_id = "TEST-TOOL-RES-01"
    items = [OrderItemState(product_id="P1", sku="KB-MECH-RGB", name="Keyboard", quantity=2)]

    # Reserve
    res = reserve_stock_atomic(db_session, order_id, items)
    assert res["success"] is True
    assert len(res["reservation_ids"]) == 1

    # Release (Rollback)
    rel = release_stock_reservation(db_session, order_id)
    assert rel["success"] is True
    assert rel["released_count"] == 1


# ==============================================================================
# FRAUD CHECK AGENT TOOLS TESTS
# ==============================================================================

def test_tool_retrieve_customer_history(db_session):
    """Tool 1: Verify customer prior-order history statistics retrieval."""
    stats = retrieve_customer_history(db_session, "CUST-001")
    assert stats["total_orders"] == 4
    assert stats["successful_orders"] == 4
    assert stats["suspicious_orders"] == 0
    assert stats["risk_tier"] == "LOW"


def test_tool_calculate_fraud_risk_score():
    """Tool 2: Verify deterministic risk scoring."""
    order_state = OrderState(
        order_id="TEST-FRD-SCORE-01",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="P1", sku="KB-MECH-RGB", name="KB", quantity=1, unit_price=Decimal("99.99"))],
        shipping_address=AddressState(street="742 Evergreen", city="Springfield", state="OR", postal_code="97477"),
        payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="AUTHORIZED"),
    )
    history_stats = {
        "customer_id": "CUST-001",
        "total_orders": 4,
        "successful_orders": 4,
        "suspicious_orders": 0,
        "average_order_value": "150.00",
    }
    eval_res = calculate_fraud_risk_score(order_state, history_stats, simulated_failed_attempts=0)
    assert eval_res["score"] <= 29.0
    assert eval_res["risk_tier"] == "LOW"
    assert eval_res["decision"] == "APPROVED"
    assert "APPROVED" in eval_res["ai_explanation"]


def test_tool_persist_fraud_review(db_session):
    """Tool 3: Verify fraud review entity persistence."""
    res = persist_fraud_review(
        db=db_session,
        order_id="TEST-FRD-REC-01",
        customer_id="CUST-001",
        score=15.0,
        risk_tier="LOW",
        risk_factors=["Low baseline"],
        ai_explanation="Customer approved.",
        decision="APPROVED",
    )
    assert res["recorded"] is True
    assert res["review_id"].startswith("FRD-")


# ==============================================================================
# PRICING AGENT TOOLS TESTS
# ==============================================================================

def test_tool_calculate_subtotal_and_discounts():
    """Tool 1: Verify subtotal, volume discounts, and coupon application."""
    items = [
        OrderItemState(product_id="P1", sku="KB-MECH-RGB", name="KB", quantity=5, unit_price=Decimal("100.00"))
    ]
    res = calculate_subtotal_and_discounts(items, coupon_code="WELCOME10")
    assert res["subtotal"] == Decimal("500.00")
    # 5% volume ($25) + 10% coupon ($50) = $75
    assert res["discount_amount"] == Decimal("75.00")


def test_tool_calculate_tax_and_shipping():
    """Tool 2: Verify tax and dynamic shipping cost calculation."""
    res = calculate_tax_and_shipping(
        subtotal=Decimal("200.00"),
        discount_amount=Decimal("0.00"),
        shipping_method="Standard",
        coupon_free_shipping=False,
    )
    # Tax: 8% of $200 = $16.00
    assert res["tax_amount"] == Decimal("16.00")
    # Subtotal >= $100 -> Free shipping
    assert res["shipping_cost"] == Decimal("0.00")


def test_tool_finalize_order_total():
    """Tool 3: Verify non-negative rounded final payable calculation."""
    total = finalize_order_total(
        subtotal=Decimal("100.00"),
        discount_amount=Decimal("10.00"),
        tax_amount=Decimal("7.20"),
        shipping_cost=Decimal("5.00"),
    )
    # 100 - 10 + 7.20 + 5.00 = 102.20
    assert total == Decimal("102.20")


# ==============================================================================
# DISPATCH COORDINATOR TOOLS TESTS
# ==============================================================================

def test_tool_select_optimal_carrier():
    """Tool 1: Verify carrier assignment."""
    res = select_optimal_carrier(shipping_method="Express", destination_state="OR")
    assert res["carrier"] == "FedEx Priority Express"

    res_std = select_optimal_carrier(shipping_method="Standard", destination_state="OR")
    assert res_std["carrier"] == "UPS Ground Logistics"


def test_tool_generate_tracking_and_manifest():
    """Tool 2: Verify tracking number and packaging manifest generation."""
    res = generate_tracking_and_manifest("UPS Ground Logistics", "Standard", item_count=2)
    assert res["tracking_id"].startswith("TRK-UPS-")
    assert "manifest" in res
    assert res["manifest"]["carrier"] == "UPS Ground Logistics"


def test_tool_create_shipment_record(db_session):
    """Tool 3: Verify database shipment record creation."""
    now_utc = datetime.now(timezone.utc)
    res = create_shipment_record(
        db=db_session,
        order_id="TEST-SHIP-01",
        tracking_id="TRK-UPS-99887766",
        carrier="UPS Ground Logistics",
        shipping_method="Standard",
        estimated_delivery=now_utc,
    )
    assert res["status"] == "DISPATCHED"
    assert res["shipment_id"].startswith("SHP-")


# ==============================================================================
# NOTIFICATION AGENT TOOLS TESTS
# ==============================================================================

def test_tool_draft_customer_notification_confirmed():
    """Tool 1: Verify drafted email and SMS for confirmed order."""
    state = OrderState(
        order_id="ORD-NOTIF-01",
        customer_id="CUST-001",
        customer_name="John Verified",
        customer_email="john@example.com",
        customer_phone="555-0101",
        items=[OrderItemState(product_id="P1", sku="KB-MECH-RGB", name="KB", quantity=1)],
        shipping_address=AddressState(street="742 Evergreen", city="Springfield", state="OR", postal_code="97477"),
        payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="AUTHORIZED"),
        dispatch_status="DISPATCHED",
        tracking_id="TRK-FDX-12345678",
        carrier="FedEx Priority Express",
        shipping_method="Express",
        final_amount=Decimal("107.99"),
    )
    draft = draft_customer_notification(state)
    assert draft.intent == "CONFIRMED"
    assert "Order Confirmed & Shipped!" in draft.subject
    assert "TRK-FDX-12345678" in draft.body
    assert "TRK-FDX-12345678" in draft.sms_summary
    assert draft.status == "DRAFTED"


def test_tool_record_notification_log():
    """Tool 2: Verify notification attachment to state."""
    state = OrderState(
        order_id="ORD-NOTIF-02",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="P1", sku="KB-MECH-RGB", name="KB", quantity=1)],
        shipping_address=AddressState(street="742 Evergreen", city="Springfield", state="OR", postal_code="97477"),
        payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="AUTHORIZED"),
        dispatch_status="DISPATCHED",
        tracking_id="TRK-FDX-999",
    )
    draft = draft_customer_notification(state)
    res = record_notification_log(state, draft)
    assert res["status"] == "DRAFTED_PREVIEW"
    assert state.customer_notification_draft is not None
    assert state.notification_status == "DRAFTED"
