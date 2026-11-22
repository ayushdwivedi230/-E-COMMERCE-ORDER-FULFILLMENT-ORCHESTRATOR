"""
Unit Tests for Append-Only Run Logger
CSE476 Agentic AI and Intelligent Automation
"""

import os
import json
import pytest
from decimal import Decimal
from backend.app.schemas.order_state import (
    OrderState,
    OrderItemState,
    AddressState,
    PaymentState,
)
from backend.app.services.run_logger import AppendOnlyRunLogger


def test_append_only_run_logger(tmp_path):
    """Verify that runs are appended to log file and preserve history."""
    state = OrderState(
        order_id="TEST-LOG-RUN-01",
        customer_id="CUST-001",
        customer_name="John Verified",
        items=[OrderItemState(product_id="P1", sku="KB-MECH-RGB", name="Keyboard", quantity=1)],
        shipping_address=AddressState(street="742 Evergreen", city="Springfield", state="OR", postal_code="97477"),
        payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="AUTHORIZED"),
        dispatch_status="DISPATCHED",
        tracking_id="TRK-UPS-12345678",
        carrier="UPS Ground Logistics",
        final_amount=Decimal("104.99"),
    )
    state.add_log("ValidationAgent", "Validation", "SUCCESS", "Validation passed")
    state.add_tool_log("ValidationAgent", "validate_customer_standing", "Check", "SUCCESS", "Customer OK")

    res = AppendOnlyRunLogger.log_order_run(state)
    assert "run_id" in res
    assert res["order_id"] == "TEST-LOG-RUN-01"
    assert res["tracking_id"] == "TRK-UPS-12345678"

    # Read back
    recent = AppendOnlyRunLogger.read_recent_runs(limit=10)
    assert len(recent) > 0
    match = next(r for r in recent if r["order_id"] == "TEST-LOG-RUN-01")
    assert match["dispatch_status"] == "DISPATCHED"
    assert match["total_steps"] == 1
    assert match["total_tool_calls"] == 1
