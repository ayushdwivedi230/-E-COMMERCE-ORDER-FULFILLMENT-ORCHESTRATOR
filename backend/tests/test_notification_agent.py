"""
Unit Tests for NotificationAgent (Group Extension & Customer Communications Preview)
CSE476 Agentic AI and Intelligent Automation
"""

import pytest
from decimal import Decimal
from backend.app.schemas.order_state import (
    OrderState,
    OrderItemState,
    AddressState,
    PaymentState,
    SubstituteRecommendation,
    BackorderProposal,
)
from backend.app.agents.notification_agent import NotificationAgent


@pytest.fixture
def agent():
    return NotificationAgent()


def test_notification_agent_confirmed_order(agent):
    """Test notification draft generation for confirmed/dispatched order."""
    state = OrderState(
        order_id="ORD-CONFIRM-01",
        customer_id="CUST-001",
        customer_name="Alice Smith",
        customer_email="alice@example.com",
        customer_phone="555-0100",
        items=[OrderItemState(product_id="P1", sku="KB-MECH-RGB", name="Keyboard", quantity=1)],
        shipping_address=AddressState(street="123 Oak St", city="Springfield", state="OR", postal_code="97477"),
        payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="AUTHORIZED"),
        dispatch_status="DISPATCHED",
        tracking_id="TRK-FDX-77665544",
        carrier="FedEx Priority Express",
        shipping_method="Express Air",
        final_amount=Decimal("110.00"),
    )
    draft = agent.process_notification(state)
    assert draft.intent == "CONFIRMED"
    assert "TRK-FDX-77665544" in draft.body
    assert "Alice Smith" in draft.body
    assert state.customer_notification_draft is not None
    assert state.notification_status == "DRAFTED"


def test_notification_agent_substituted_order(agent):
    """Test notification draft for inventory shortage with recommended substitute."""
    state = OrderState(
        order_id="ORD-SUB-01",
        customer_id="CUST-001",
        customer_name="Bob Jones",
        items=[OrderItemState(product_id="P1", sku="KB-MECH-RGB", name="Keyboard", quantity=100)],
        shipping_address=AddressState(street="456 Elm St", city="Springfield", state="OR", postal_code="97477"),
        payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="AUTHORIZED"),
        inventory_status="SUBSTITUTE_RECOMMENDED",
        substitute_recommendations=[
            SubstituteRecommendation(
                original_sku="KB-MECH-RGB",
                substitute_sku="KB-ERG-WRL",
                substitute_name="Ergonomic Split Wireless Keyboard",
                substitute_price=Decimal("119.99"),
                reason="Direct alternative in stock",
            )
        ],
    )
    draft = agent.process_notification(state)
    assert draft.intent == "SUBSTITUTED"
    assert "KB-ERG-WRL" in draft.body
    assert "approval" in draft.body.lower()


def test_notification_agent_held_fraud_order(agent):
    """Test notification draft for security review hold (neutral wording, no heuristic leak)."""
    state = OrderState(
        order_id="ORD-FRAUD-01",
        customer_id="CUST-003",
        customer_name="Charlie Risk",
        items=[OrderItemState(product_id="P1", sku="MON-4K-27", name="Monitor", quantity=3)],
        shipping_address=AddressState(street="PO Box 99", city="Miami", state="FL", postal_code="33101"),
        payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="AUTHORIZED"),
        fraud_status="HIGH_RISK_HELD",
        fraud_score=85.0,
        hold_reason="Fraud Escalation: Score 85.0 exceeds threshold",
    )
    draft = agent.process_notification(state)
    assert draft.intent == "HELD_FRAUD"
    assert "Security Verification" in draft.subject
    assert "verification queue" in draft.body.lower()
    # Ensure internal fraud heuristics or scores are not exposed to customer
    assert "85.0" not in draft.body
    assert "heuristic" not in draft.body.lower()


def test_notification_agent_held_validation_order(agent):
    """Test notification draft for validation/address failure."""
    state = OrderState(
        order_id="ORD-VAL-01",
        customer_id="CUST-001",
        items=[],
        shipping_address=AddressState(street="", city="Springfield", state="OR", postal_code="97477"),
        payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="FAILED"),
        validation_status="FAILED",
        hold_reason="Validation Failed: Shipping address street is missing or empty; Payment status is FAILED",
    )
    draft = agent.process_notification(state)
    assert draft.intent == "HELD_VALIDATION"
    assert "Issue Processing Order" in draft.subject
    assert "Validation Failed" in draft.body
