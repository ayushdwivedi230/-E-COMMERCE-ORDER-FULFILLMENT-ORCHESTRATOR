from decimal import Decimal
from backend.app.orchestrator.pipeline import OrderFulfillmentOrchestrator
from backend.app.schemas.order_state import OrderState, OrderItemState, AddressState, PaymentState
from backend.app.models.order import Order
from backend.app.models.product import Product
from backend.app.models.inventory import InventoryReservation
from backend.app.services.customer_memory import CustomerMemoryService


# --------------------------------------------------------------------------
# Demonstration 1: Successful Order
# Output: Confirmed order + final amount + shipping method + tracking ID
# --------------------------------------------------------------------------
def test_demo_1_successful_order(db_session):
    orchestrator = OrderFulfillmentOrchestrator()
    state = OrderState(
        order_id="DEMO-SUCCESS-001",
        customer_id="CUST-001",
        items=[
            OrderItemState(
                product_id="PROD-001",
                sku="KB-MECH-RGB",
                name="Mechanical Keyboard",
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
            transaction_token="tok_valid_demo1",
        ),
        coupon_code="WELCOME10",
    )

    result = orchestrator.process_order_pipeline(state, db_session)
    output = result.get_structured_output()

    # Verify Prompt 4 Output Requirements
    assert output["order_result"] == "CONFIRMED_AND_DISPATCHED"
    assert result.dispatch_status == "DISPATCHED"
    assert output["tracking_id"].startswith("TRK-")
    assert Decimal(output["final_amount"]) > Decimal("0.00")
    assert output["shipping_method"] is not None
    assert output["carrier"] is not None
    assert result.hold_reason is None

    # Verify DB persistence
    db_order = db_session.query(Order).filter(Order.id == "DEMO-SUCCESS-001").first()
    assert db_order.status == "DISPATCHED"
    assert db_order.tracking_id == output["tracking_id"]


# --------------------------------------------------------------------------
# Demonstration 2: Invalid Order
# Rule: Invalid orders must stop processing immediately
# --------------------------------------------------------------------------
def test_demo_2_invalid_order_stops_processing(db_session):
    orchestrator = OrderFulfillmentOrchestrator()
    # Invalid order: non-existent SKU and missing street address
    state = OrderState(
        order_id="DEMO-INVALID-002",
        customer_id="CUST-001",
        items=[
            OrderItemState(
                product_id="PROD-UNKNOWN",
                sku="NON-EXISTENT-SKU",
                name="Unknown Item",
                quantity=1,
            )
        ],
        shipping_address=AddressState(
            street="",  # Missing street
            city="Springfield",
            state="OR",
            postal_code="97477",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="FAILED",  # Failed payment
            transaction_token="",
        ),
    )

    result = orchestrator.process_order_pipeline(state, db_session)

    # Validation agent must fail and stop immediately
    assert result.validation_status == "FAILED"
    assert result.inventory_status == "PENDING"  # Did not proceed to inventory
    assert result.fraud_status == "PENDING"      # Did not proceed to fraud
    assert result.pricing_status == "PENDING"    # Did not proceed to pricing
    assert result.dispatch_status == "HELD"      # Did not dispatch
    assert result.tracking_id is None
    assert "Validation Failed" in result.hold_reason


# --------------------------------------------------------------------------
# Demonstration 3: High-Risk Fraudulent Order (Fraud Escalation Route)
# Output: Held order + fraud score + explanation + review status
# --------------------------------------------------------------------------
def test_demo_3_high_risk_fraudulent_order_escalation(db_session):
    orchestrator = OrderFulfillmentOrchestrator()
    # High-risk profile: CUST-003 with address mismatch and failed retries
    state = OrderState(
        order_id="DEMO-FRAUD-003",
        customer_id="CUST-003",
        items=[
            OrderItemState(
                product_id="PROD-003",
                sku="MON-4K-27",
                name="Ultra HD Monitor",
                quantity=2,
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
            transaction_token="tok_risky_card",
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
    output = result.get_structured_output()

    # Verify Prompt 4 Output Requirements for Suspicious Orders
    assert output["order_result"] == "HELD_SUSPICIOUS_ORDER"
    assert output["status"] == "HELD"
    assert output["review_status"] == "HELD_ESCALATED"
    assert output["fraud_score"] >= 70.0
    assert "explanation" in output
    assert "Fraud Escalation Hold" in output["hold_reason"]
    assert result.pricing_status == "PENDING"  # Must NOT proceed to pricing
    assert result.dispatch_status == "HELD"    # Must NOT proceed to dispatch
    assert result.tracking_id is None


# --------------------------------------------------------------------------
# Demonstration 4: Insufficient Inventory (Substitute / Backorder Proposal)
# Rule: Never silently substitute; requires customer approval
# --------------------------------------------------------------------------
def test_demo_4_insufficient_inventory_substitute(db_session):
    orchestrator = OrderFulfillmentOrchestrator()
    # SKU MON-CRV-32 has 0 stock; substitute is MON-4K-27
    state = OrderState(
        order_id="DEMO-INVENTORY-004",
        customer_id="CUST-001",
        items=[
            OrderItemState(
                product_id="PROD-004",
                sku="MON-CRV-32",
                name="Curved Gaming Monitor",
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

    assert result.inventory_status == "SUBSTITUTE_RECOMMENDED"
    assert result.dispatch_status == "HELD"
    assert len(result.substitute_recommendations) >= 1
    assert result.substitute_recommendations[0].substitute_sku == "MON-4K-27"
    assert "Customer approval required" in result.hold_reason
    assert result.fraud_status == "PENDING"  # Must stop before fraud / dispatch


# --------------------------------------------------------------------------
# Demonstration 5: Customer with Previous Successful Transactions
# Rule: Prior-order memory verifies clean profile
# --------------------------------------------------------------------------
def test_demo_5_customer_with_successful_transactions(db_session):
    orchestrator = OrderFulfillmentOrchestrator()
    history = CustomerMemoryService.get_customer_history(db_session, "CUST-001")
    assert history.successful_orders >= 4
    assert history.suspicious_orders == 0
    assert history.risk_tier == "LOW"

    state = OrderState(
        order_id="DEMO-GOOD-CUST-005",
        customer_id="CUST-001",
        items=[
            OrderItemState(
                product_id="PROD-005",
                sku="HUB-USBC-8P",
                name="USB-C Multiport Hub",
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
            transaction_token="tok_good_cust",
        ),
    )

    result = orchestrator.process_order_pipeline(state, db_session)
    assert result.fraud_status == "LOW_RISK"
    assert result.fraud_score <= 29.0
    assert result.dispatch_status == "DISPATCHED"
    assert result.tracking_id is not None


# --------------------------------------------------------------------------
# Demonstration 6: Customer with Suspicious Historical Transactions
# Rule: Prior memory raises fraud score due to chargebacks
# --------------------------------------------------------------------------
def test_demo_6_customer_with_suspicious_historical_transactions(db_session):
    orchestrator = OrderFulfillmentOrchestrator()
    # CUST-002 has 1 prior chargeback in history
    history = CustomerMemoryService.get_customer_history(db_session, "CUST-002")
    assert history.suspicious_orders == 1
    assert history.risk_tier in ["MEDIUM", "HIGH"]

    state = OrderState(
        order_id="DEMO-SUSP-CUST-006",
        customer_id="CUST-002",
        items=[
            OrderItemState(
                product_id="PROD-001",
                sku="KB-MECH-RGB",
                name="Mechanical Keyboard",
                quantity=1,
            )
        ],
        shipping_address=AddressState(
            street="1200 Market Street",
            city="San Francisco",
            state="CA",
            postal_code="94102",
            country="USA",
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_susp_card",
        ),
    )

    result = orchestrator.process_order_pipeline(state, db_session)
    # The prior chargeback pushes risk score above baseline (> 35 pts)
    assert result.fraud_score >= 35.0
    assert any("prior suspicious" in f.lower() for f in result.fraud_risk_factors)


# --------------------------------------------------------------------------
# Demonstration 7: Prevent Duplicate Order Processing & Release Stock on Cancel
# Rule: Prevent duplicate order processing; release stock on hold/cancel
# --------------------------------------------------------------------------
def test_demo_7_duplicate_order_and_stock_release(db_session):
    orchestrator = OrderFulfillmentOrchestrator()
    state = OrderState(
        order_id="DEMO-DUP-007",
        customer_id="CUST-001",
        items=[
            OrderItemState(
                product_id="PROD-001",
                sku="KB-MECH-RGB",
                name="Mechanical Keyboard",
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
            transaction_token="tok_dup_test",
        ),
    )

    # First run: Dispatches successfully
    res1 = orchestrator.process_order_pipeline(state, db_session)
    assert res1.dispatch_status == "DISPATCHED"

    # Second run with same order_id: Must reject duplicate!
    dup_state = OrderState(
        order_id="DEMO-DUP-007",
        customer_id="CUST-001",
        items=[
            OrderItemState(
                product_id="PROD-001",
                sku="KB-MECH-RGB",
                name="Mechanical Keyboard",
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
            transaction_token="tok_dup_test",
        ),
    )
    res2 = orchestrator.process_order_pipeline(dup_state, db_session)
    assert res2.dispatch_status == "REJECTED_DUPLICATE"
    assert "Duplicate Order Error" in res2.hold_reason
