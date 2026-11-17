import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from backend.app.schemas.order_state import OrderState, OrderItemState, AddressState, PaymentState
from backend.app.orchestrator.pipeline import OrderFulfillmentOrchestrator
from backend.app.models.order import Order
from backend.app.models.inventory import InventoryReservation
from backend.app.services.customer_memory import CustomerMemoryService


@pytest.fixture
def orchestrator():
    return OrderFulfillmentOrchestrator()


# Scenario 1: Valid order with successful dispatch
def test_scenario_1_valid_order_successful_dispatch(db_session, orchestrator):
    order_state = OrderState(
        order_id="TEST-SCENARIO-01",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-001", sku="KB-MECH-RGB", name="Pro Mechanical Keyboard", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace",
            city="Springfield",
            state="OR",
            postal_code="97477",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_valid_live",
        ),
        coupon_code="WELCOME10",
    )
    final_state = orchestrator.process_order_pipeline(order_state, db_session)
    assert final_state.dispatch_status == "DISPATCHED"
    assert final_state.tracking_id is not None
    assert final_state.tracking_id.startswith("TRK-")
    assert final_state.final_amount > 0
    assert final_state.carrier is not None
    assert len(final_state.agent_execution_logs) == 5


# Scenario 2: Invalid product
def test_scenario_2_invalid_product(db_session, orchestrator):
    order_state = OrderState(
        order_id="TEST-SCENARIO-02",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-XXX", sku="NON-EXISTENT-SKU", name="Ghost Item", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace",
            city="Springfield",
            state="OR",
            postal_code="97477",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_valid_live",
        ),
    )
    final_state = orchestrator.process_order_pipeline(order_state, db_session)
    assert final_state.dispatch_status == "HELD"
    assert final_state.validation_status == "FAILED"
    assert "does not exist in catalog" in final_state.hold_reason
    assert final_state.tracking_id is None


# Scenario 3: Invalid address
def test_scenario_3_invalid_address(db_session, orchestrator):
    order_state = OrderState(
        order_id="TEST-SCENARIO-03",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-001", sku="KB-MECH-RGB", name="Pro Mechanical Keyboard", quantity=1)],
        shipping_address=AddressState(
            street="",  # Empty street
            city="Springfield",
            state="OR",
            postal_code="97477",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_valid_live",
        ),
    )
    final_state = orchestrator.process_order_pipeline(order_state, db_session)
    assert final_state.dispatch_status == "HELD"
    assert final_state.validation_status == "FAILED"
    assert "street is missing or empty" in final_state.hold_reason


# Scenario 4: Failed payment
def test_scenario_4_failed_payment(db_session, orchestrator):
    order_state = OrderState(
        order_id="TEST-SCENARIO-04",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-001", sku="KB-MECH-RGB", name="Pro Mechanical Keyboard", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace",
            city="Springfield",
            state="OR",
            postal_code="97477",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="FAILED",  # Explicit failed status
            transaction_token="tok_failed",
        ),
    )
    final_state = orchestrator.process_order_pipeline(order_state, db_session)
    assert final_state.dispatch_status == "HELD"
    assert final_state.validation_status == "FAILED"
    assert "Payment status is FAILED" in final_state.hold_reason


# Scenario 5: Inventory shortage
def test_scenario_5_inventory_shortage(db_session, orchestrator):
    order_state = OrderState(
        order_id="TEST-SCENARIO-05",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-001", sku="KB-MECH-RGB", name="Pro Mechanical Keyboard", quantity=999)], # Exceeds stock (45)
        shipping_address=AddressState(
            street="742 Evergreen Terrace",
            city="Springfield",
            state="OR",
            postal_code="97477",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_valid_live",
        ),
    )
    final_state = orchestrator.process_order_pipeline(order_state, db_session)
    assert final_state.dispatch_status == "HELD"
    assert final_state.inventory_status in ["BACKORDER_PROPOSED", "INSUFFICIENT_STOCK"]
    assert "backorder" in final_state.hold_reason.lower() or "insufficient" in final_state.hold_reason.lower()
    assert len(final_state.backorder_proposals) > 0


# Scenario 6: Substitute recommendation (zero stock)
def test_scenario_6_substitute_recommendation(db_session, orchestrator):
    order_state = OrderState(
        order_id="TEST-SCENARIO-06",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-004", sku="MON-CRV-32", name="Curved 32-inch Monitor", quantity=1)], # Stock is 0
        shipping_address=AddressState(
            street="742 Evergreen Terrace",
            city="Springfield",
            state="OR",
            postal_code="97477",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_valid_live",
        ),
    )
    final_state = orchestrator.process_order_pipeline(order_state, db_session)
    assert final_state.dispatch_status == "HELD"
    assert final_state.inventory_status in ["SUBSTITUTE_RECOMMENDED", "INSUFFICIENT_STOCK"]
    assert len(final_state.substitute_recommendations) > 0
    assert final_state.substitute_recommendations[0].substitute_sku == "MON-4K-27"
    assert len(final_state.backorder_proposals) > 0


# Scenario 7: High-risk fraud detection
def test_scenario_7_high_risk_fraud_detection(db_session, orchestrator):
    order_state = OrderState(
        order_id="TEST-SCENARIO-07",
        customer_id="CUST-003", # High risk customer with 2 past chargebacks
        items=[OrderItemState(product_id="PROD-003", sku="MON-4K-27", name="Ultra HD 27-inch 4K Monitor", quantity=3)],
        shipping_address=AddressState(
            street="PO Box 9999",
            city="Unknown Island",
            state="FL",
            postal_code="33040",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_suspicious",
            billing_address=AddressState(
                street="PO Box 111",
                city="Anchorage",
                state="AK",
                postal_code="99501",
                country="USA",
            ),
        ),
    )
    final_state = orchestrator.process_order_pipeline(order_state, db_session, simulated_failed_attempts=2)
    assert final_state.dispatch_status == "HELD"
    assert final_state.fraud_status == "HIGH_RISK_HELD"
    assert final_state.fraud_score >= 70
    assert final_state.tracking_id is None
    # Stock must have been released back
    reservations = db_session.query(InventoryReservation).filter(InventoryReservation.order_id == "TEST-SCENARIO-07").all()
    assert all(r.status == "RELEASED" for r in reservations)


# Scenario 8: Historical customer risk assessment
def test_scenario_8_historical_customer_risk_assessment(db_session, orchestrator):
    # Customer 1 (clean history) vs Customer 2 (prior dispute) vs Customer 3 (multiple chargebacks)
    stats1 = CustomerMemoryService.get_customer_history(db_session, "CUST-001")
    stats2 = CustomerMemoryService.get_customer_history(db_session, "CUST-002")
    stats3 = CustomerMemoryService.get_customer_history(db_session, "CUST-003")

    assert stats1.risk_tier == "LOW"
    assert stats1.suspicious_orders == 0
    assert stats1.failed_payment_attempts == 0

    assert stats2.suspicious_orders == 1
    assert stats2.failed_payment_attempts == 1

    assert stats3.risk_tier == "HIGH"
    assert stats3.suspicious_orders >= 2
    assert stats3.failed_payment_attempts >= 3


# Scenario 9: Correct discount and tax calculation
def test_scenario_9_correct_discount_and_tax_calculation(db_session, orchestrator):
    # Order 5 units to trigger bulk discount (5%) + SAVE20 coupon ($20 off)
    order_state = OrderState(
        order_id="TEST-SCENARIO-09",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-005", sku="HUB-USBC-8P", name="USB-C Hub", quantity=5)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace",
            city="Springfield",
            state="OR",
            postal_code="97477",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_calc_test",
        ),
        coupon_code="SAVE20",
    )
    final_state = orchestrator.process_order_pipeline(order_state, db_session)
    assert final_state.dispatch_status == "DISPATCHED"
    # Subtotal = 5 * 49.99 = 249.95
    # Bulk 5% discount = 12.50
    # Coupon SAVE20 = 20.00
    # Total discount = 32.50
    # Taxable = 217.45 * 0.08 = 17.40
    # Shipping = $0 (>= $100 threshold)
    # Final = 217.45 + 17.40 = 234.85
    assert final_state.subtotal == Decimal("249.95")
    assert final_state.discount_amount == Decimal("32.50")
    assert final_state.tax_amount == Decimal("17.40")
    assert final_state.shipping_cost == Decimal("0.00")
    assert final_state.final_amount == Decimal("234.85")


# Scenario 10: Dispatch failure handling & rollback
def test_scenario_10_dispatch_failure(db_session, orchestrator):
    order_state = OrderState(
        order_id="TEST-SCENARIO-10",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-001", sku="KB-MECH-RGB", name="Pro Mechanical Keyboard", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace",
            city="Springfield",
            state="OR",
            postal_code="97477",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_live",
        ),
    )
    # Simulate carrier dispatch service outage
    original_dispatch = orchestrator.dispatch_coordinator.coordinate_dispatch
    try:
        orchestrator.dispatch_coordinator.coordinate_dispatch = MagicMock(return_value=False)
        final_state = orchestrator.process_order_pipeline(order_state, db_session)
        assert final_state.dispatch_status == "HELD"
        assert "Dispatch coordination failed" in final_state.hold_reason
        # Verify reserved stock was released
        reservations = db_session.query(InventoryReservation).filter(InventoryReservation.order_id == "TEST-SCENARIO-10").all()
        assert all(r.status == "RELEASED" for r in reservations)
    finally:
        orchestrator.dispatch_coordinator.coordinate_dispatch = original_dispatch


# Scenario 11: Duplicate order submission prevention
def test_scenario_11_duplicate_order_submission(db_session, orchestrator):
    order_id = "TEST-SCENARIO-11-DUP"
    order_state_1 = OrderState(
        order_id=order_id,
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-001", sku="KB-MECH-RGB", name="Pro Mechanical Keyboard", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace",
            city="Springfield",
            state="OR",
            postal_code="97477",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_dup_test",
        ),
    )
    # First submission completes successfully
    result_1 = orchestrator.process_order_pipeline(order_state_1, db_session)
    assert result_1.dispatch_status == "DISPATCHED"

    # Second submission with identical ID is rejected as duplicate
    order_state_2 = OrderState(
        order_id=order_id,
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-001", sku="KB-MECH-RGB", name="Pro Mechanical Keyboard", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace",
            city="Springfield",
            state="OR",
            postal_code="97477",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_dup_test",
        ),
    )
    result_2 = orchestrator.process_order_pipeline(order_state_2, db_session)
    assert result_2.dispatch_status == "REJECTED_DUPLICATE"
    assert "Duplicate Order Error" in result_2.hold_reason


# Scenario 12: Database failure handling & rollback
def test_scenario_12_database_failure_handling(db_session, orchestrator):
    order_state = OrderState(
        order_id="TEST-SCENARIO-12-DBFAIL",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-001", sku="KB-MECH-RGB", name="Pro Mechanical Keyboard", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace",
            city="Springfield",
            state="OR",
            postal_code="97477",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_db_fail",
        ),
    )
    # Inject a database failure during initialize
    original_init = orchestrator._initialize_order_record
    try:
        orchestrator._initialize_order_record = MagicMock(side_effect=Exception("Simulated Database I/O Lock Error"))
        final_state = orchestrator.process_order_pipeline(order_state, db_session)
        assert final_state.dispatch_status == "FAILED"
        assert "System Error / Database Exception" in final_state.hold_reason
        assert any(l.agent_name == "OrderOrchestrator" and l.status == "FAILED" for l in final_state.agent_execution_logs)
    finally:
        orchestrator._initialize_order_record = original_init
