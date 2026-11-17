from decimal import Decimal
from backend.app.orchestrator.pipeline import OrderFulfillmentOrchestrator
from backend.app.schemas.order_state import OrderState, OrderItemState, AddressState, PaymentState
from backend.app.models.order import Order
from backend.app.models.shipment import Shipment


def test_pipeline_happy_path_dispatched(db_session):
    orchestrator = OrderFulfillmentOrchestrator()
    state = OrderState(
        order_id="ORD-HAPPY-01",
        customer_id="CUST-001",
        items=[
            OrderItemState(
                product_id="PROD-001",
                sku="KB-MECH-RGB",
                name="Pro Mechanical RGB Gaming Keyboard",
                quantity=1,
            )
        ],
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
            transaction_token="tok_valid_test",
        ),
        coupon_code="WELCOME10",
    )

    result = orchestrator.process_order_pipeline(state, db_session)

    # Verifications
    assert result.validation_status == "PASSED"
    assert result.inventory_status == "RESERVED"
    assert result.fraud_status == "LOW_RISK"
    assert result.pricing_status == "CALCULATED"
    assert result.dispatch_status == "DISPATCHED"
    assert result.tracking_id is not None
    assert result.tracking_id.startswith("TRK-")
    assert result.final_amount > Decimal("0.00")
    assert result.hold_reason is None

    # Verify DB persistence
    db_order = db_session.query(Order).filter(Order.id == "ORD-HAPPY-01").first()
    assert db_order is not None
    assert db_order.status == "DISPATCHED"
    assert db_order.tracking_id == result.tracking_id

    db_shipment = db_session.query(Shipment).filter(Shipment.order_id == "ORD-HAPPY-01").first()
    assert db_shipment is not None
    assert db_shipment.tracking_id == result.tracking_id


def test_pipeline_fraud_escalation_hold(db_session):
    orchestrator = OrderFulfillmentOrchestrator()
    # CUST-003 is high-risk customer with prior suspicious chargebacks
    state = OrderState(
        order_id="ORD-FRAUD-01",
        customer_id="CUST-003",
        items=[
            OrderItemState(
                product_id="PROD-003",
                sku="MON-4K-27",
                name="Ultra HD 27-inch 4K Designer Monitor",
                quantity=3,
            )
        ],
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
            transaction_token="tok_risky_test",
            billing_address=AddressState(
                street="PO Box 111",
                city="Anchorage",
                state="AK",
                postal_code="99501",
                country="USA",
            ),
        ),
    )

    result = orchestrator.process_order_pipeline(state, db_session, simulated_failed_attempts=2)

    # Verifications
    assert result.validation_status == "PASSED"
    assert result.inventory_status == "RESERVED"
    assert result.fraud_status == "HIGH_RISK_HELD"
    assert result.fraud_score >= 70
    assert result.dispatch_status == "HELD"
    assert result.tracking_id is None
    assert result.hold_reason is not None
    assert "Fraud Escalation Hold" in result.hold_reason

    # Verify DB persistence
    db_order = db_session.query(Order).filter(Order.id == "ORD-FRAUD-01").first()
    assert db_order is not None
    assert db_order.status == "HELD"
    assert db_order.hold_reason == result.hold_reason


def test_pipeline_out_of_stock_substitute_hold(db_session):
    orchestrator = OrderFulfillmentOrchestrator()
    # MON-CRV-32 has 0 stock
    state = OrderState(
        order_id="ORD-STOCK-01",
        customer_id="CUST-001",
        items=[
            OrderItemState(
                product_id="PROD-004",
                sku="MON-CRV-32",
                name="Curved 32-inch Monitor",
                quantity=1,
            )
        ],
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
            transaction_token="tok_valid_test",
        ),
    )

    result = orchestrator.process_order_pipeline(state, db_session)

    assert result.validation_status == "PASSED"
    assert result.inventory_status == "SUBSTITUTE_RECOMMENDED"
    assert result.dispatch_status == "HELD"
    assert len(result.substitute_recommendations) >= 1
    assert "Customer approval required" in result.hold_reason
