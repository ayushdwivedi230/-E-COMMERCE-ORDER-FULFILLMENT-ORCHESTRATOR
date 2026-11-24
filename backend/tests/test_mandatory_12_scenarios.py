import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from backend.app.models.product import Product
from backend.app.models.customer import Customer
from backend.app.models.order import Order, OrderItem
from backend.app.models.inventory import InventoryReservation
from backend.app.schemas.order_state import (
    OrderState,
    OrderItemState,
    AddressState,
    PaymentState,
)
from backend.app.orchestrator.pipeline import OrderFulfillmentOrchestrator
from backend.app.services.seed_data import seed_database
from backend.app.agents.tools import (
    validate_catalog_and_quantities,
    check_stock_availability,
    calculate_subtotal_and_discounts,
    calculate_tax_and_shipping,
)


@pytest.fixture(autouse=True)
def ensure_db_seeded(db_session: Session):
    """Ensure baseline products and customers exist in isolated test db."""
    seed_database(db_session)
    return db_session


# -----------------------------------------------------------------------------
# TEST 1 — Valid product resolution (SKU KB-MECH-RGB -> PROD-001)
# -----------------------------------------------------------------------------
def test_1_valid_product_resolution(db_session: Session):
    items = [OrderItemState(sku="KB-MECH-RGB", quantity=1)]
    res = validate_catalog_and_quantities(db_session, items)
    assert res["valid"] is True
    assert items[0].product_id == "PROD-001"
    assert items[0].name == "Pro Mechanical RGB Gaming Keyboard"
    assert items[0].unit_price == Decimal("99.99")


# -----------------------------------------------------------------------------
# TEST 2 — Invalid product ID placeholder (product_id = PENDING handled safely)
# -----------------------------------------------------------------------------
def test_2_invalid_product_id_placeholder_resolved(db_session: Session):
    items = [OrderItemState(product_id="PENDING", sku="KB-MECH-RGB", quantity=1)]
    res = validate_catalog_and_quantities(db_session, items)
    assert res["valid"] is True
    # The system must overwrite any bogus PENDING placeholder with the real DB id
    assert items[0].product_id == "PROD-001"


# -----------------------------------------------------------------------------
# TEST 3 — Unknown SKU (PRODUCT_NOT_FOUND, no invalid order item inserted)
# -----------------------------------------------------------------------------
def test_3_unknown_sku_rejected_without_db_item_insert(db_session: Session):
    orchestrator = OrderFulfillmentOrchestrator()
    state = OrderState(
        order_id="ORD-TEST-UNKNOWN-SKU",
        customer_id="CUST-001",
        items=[OrderItemState(sku="NON-EXISTENT-SKU", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace", city="Springfield", state="OR", postal_code="97477"
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD", payment_status="AUTHORIZED", transaction_token="tok_test"
        ),
    )
    result = orchestrator.process_order_pipeline(state, db_session)
    assert result.validation_status == "FAILED"
    assert result.dispatch_status == "HELD"
    assert "does not exist in catalog" in result.hold_reason

    # Verify that NO invalid order item row was inserted into the database
    db_items = db_session.query(OrderItem).filter(OrderItem.order_id == "ORD-TEST-UNKNOWN-SKU").all()
    assert len(db_items) == 0


# -----------------------------------------------------------------------------
# TEST 4 — Inactive product (Order rejected before inventory reservation)
# -----------------------------------------------------------------------------
def test_4_inactive_product_rejected(db_session: Session):
    # Set a product to inactive
    prod = db_session.query(Product).filter(Product.sku == "HUB-USBC-8P").first()
    prod.is_active = False
    db_session.commit()

    orchestrator = OrderFulfillmentOrchestrator()
    state = OrderState(
        order_id="ORD-TEST-INACTIVE",
        customer_id="CUST-001",
        items=[OrderItemState(sku="HUB-USBC-8P", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace", city="Springfield", state="OR", postal_code="97477"
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD", payment_status="AUTHORIZED", transaction_token="tok_test"
        ),
    )
    result = orchestrator.process_order_pipeline(state, db_session)
    assert result.validation_status == "FAILED"
    assert result.inventory_status in ("SKIPPED", "PENDING")
    assert "inactive" in result.hold_reason

    # Clean up
    prod.is_active = True
    db_session.commit()


# -----------------------------------------------------------------------------
# TEST 5 — Insufficient inventory (No reservation, no dispatch)
# -----------------------------------------------------------------------------
def test_5_insufficient_inventory(db_session: Session):
    orchestrator = OrderFulfillmentOrchestrator()
    # MON-CRV-32 has stock 0
    state = OrderState(
        order_id="ORD-TEST-OUT-OF-STOCK",
        customer_id="CUST-001",
        items=[OrderItemState(sku="MON-CRV-32", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace", city="Springfield", state="OR", postal_code="97477"
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD", payment_status="AUTHORIZED", transaction_token="tok_test"
        ),
    )
    result = orchestrator.process_order_pipeline(state, db_session)
    assert result.validation_status == "PASSED"
    assert result.inventory_status in ("INSUFFICIENT_STOCK", "SUBSTITUTE_RECOMMENDED")
    assert result.dispatch_status == "HELD"
    assert result.tracking_id is None
    assert len(result.substitute_recommendations) > 0


# -----------------------------------------------------------------------------
# TEST 6 — Valid complete order (All five agents execute successfully)
# -----------------------------------------------------------------------------
def test_6_valid_complete_order(db_session: Session):
    orchestrator = OrderFulfillmentOrchestrator()
    state = OrderState(
        order_id="ORD-TEST-CLEAN-SUCCESS",
        customer_id="CUST-001",
        items=[OrderItemState(sku="KB-MECH-RGB", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace", city="Springfield", state="OR", postal_code="97477"
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD", payment_status="AUTHORIZED", transaction_token="tok_valid"
        ),
    )
    result = orchestrator.process_order_pipeline(state, db_session)
    assert result.validation_status == "PASSED"
    assert result.inventory_status == "RESERVED"
    assert result.fraud_status == "LOW_RISK"
    assert result.pricing_status == "CALCULATED"
    assert result.dispatch_status == "DISPATCHED"
    assert result.tracking_id is not None
    assert result.tracking_id.startswith("TRK-")


# -----------------------------------------------------------------------------
# TEST 7 — Fraud escalation (Order enters HELD, dispatch does not execute)
# -----------------------------------------------------------------------------
def test_7_fraud_escalation_hold(db_session: Session):
    orchestrator = OrderFulfillmentOrchestrator()
    # High-risk profile: CUST-003 with address mismatch and multiple failed attempts
    state = OrderState(
        order_id="ORD-TEST-FRAUD-HOLD",
        customer_id="CUST-003",
        items=[OrderItemState(sku="MON-4K-27", quantity=2)],
        shipping_address=AddressState(
            street="PO Box 9999", city="Unknown Island", state="FL", postal_code="33040"
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_high_risk",
            billing_address=AddressState(
                street="PO Box 111", city="Anchorage", state="AK", postal_code="99501"
            ),
        ),
    )
    result = orchestrator.process_order_pipeline(state, db_session, simulated_failed_attempts=3)
    assert result.validation_status == "PASSED"
    assert result.fraud_status == "HIGH_RISK_HELD"
    assert result.fraud_score >= 70
    assert result.dispatch_status == "HELD"
    assert result.tracking_id is None

    # Stock reservations must have been rolled back
    active_res = (
        db_session.query(InventoryReservation)
        .filter(InventoryReservation.order_id == "ORD-TEST-FRAUD-HOLD", InventoryReservation.status == "RESERVED")
        .all()
    )
    assert len(active_res) == 0


# -----------------------------------------------------------------------------
# TEST 8 — Pricing calculation (Decimal accuracy)
# -----------------------------------------------------------------------------
def test_8_pricing_calculation_decimal_accuracy(db_session: Session):
    items = [OrderItemState(sku="KB-MECH-RGB", quantity=2, unit_price=Decimal("99.99"))]
    subtotal_res = calculate_subtotal_and_discounts(items, coupon_code="WELCOME10")
    assert subtotal_res["subtotal"] == Decimal("199.98")
    assert subtotal_res["discount_amount"] == Decimal("20.00")

    tax_res = calculate_tax_and_shipping(
        subtotal=subtotal_res["subtotal"],
        discount_amount=subtotal_res["discount_amount"],
        shipping_method="Standard",
    )
    assert isinstance(tax_res["tax_amount"], Decimal)
    assert isinstance(tax_res["shipping_cost"], Decimal)


# -----------------------------------------------------------------------------
# TEST 9 — Database rollback (No invalid order items on validation failure)
# -----------------------------------------------------------------------------
def test_9_database_rollback_on_failure(db_session: Session):
    orchestrator = OrderFulfillmentOrchestrator()
    state = OrderState(
        order_id="ORD-TEST-FAIL-ROLLBACK",
        customer_id="CUST-001",
        items=[OrderItemState(sku="INVALID-SKU-XYZ", quantity=1)],
        shipping_address=AddressState(
            street="", city="", state="", postal_code=""
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD", payment_status="FAILED", transaction_token=""
        ),
    )
    result = orchestrator.process_order_pipeline(state, db_session)
    assert result.dispatch_status == "HELD"

    # Confirm no orphan order items were inserted
    items_in_db = db_session.query(OrderItem).filter(OrderItem.order_id == "ORD-TEST-FAIL-ROLLBACK").all()
    assert len(items_in_db) == 0


# -----------------------------------------------------------------------------
# TEST 10 — Duplicate request idempotency
# -----------------------------------------------------------------------------
def test_10_duplicate_order_idempotency(db_session: Session):
    orchestrator = OrderFulfillmentOrchestrator()
    state = OrderState(
        order_id="ORD-TEST-DUP-IDEMPOTENT",
        customer_id="CUST-001",
        items=[OrderItemState(sku="KB-MECH-RGB", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace", city="Springfield", state="OR", postal_code="97477"
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD", payment_status="AUTHORIZED", transaction_token="tok_valid"
        ),
    )
    # First submission
    res1 = orchestrator.process_order_pipeline(state, db_session)
    assert res1.dispatch_status == "DISPATCHED"

    # Duplicate submission with same ID
    state2 = OrderState(
        order_id="ORD-TEST-DUP-IDEMPOTENT",
        customer_id="CUST-001",
        items=[OrderItemState(sku="KB-MECH-RGB", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace", city="Springfield", state="OR", postal_code="97477"
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD", payment_status="AUTHORIZED", transaction_token="tok_valid"
        ),
    )
    res2 = orchestrator.process_order_pipeline(state2, db_session)
    assert res2.dispatch_status == "REJECTED_DUPLICATE"


# -----------------------------------------------------------------------------
# TEST 11 — Concurrent stock reservation protection
# -----------------------------------------------------------------------------
def test_11_stock_cannot_become_negative(db_session: Session):
    # Set stock of a product to 1
    prod = db_session.query(Product).filter(Product.sku == "AUD-NC-HD7").first()
    original_stock = prod.stock_quantity
    prod.stock_quantity = 1
    db_session.commit()

    orchestrator = OrderFulfillmentOrchestrator()

    # Order 1 takes the 1 available unit
    state1 = OrderState(
        order_id="ORD-TEST-RACE-1",
        customer_id="CUST-001",
        items=[OrderItemState(sku="AUD-NC-HD7", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace", city="Springfield", state="OR", postal_code="97477"
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD", payment_status="AUTHORIZED", transaction_token="tok_race1"
        ),
    )
    res1 = orchestrator.process_order_pipeline(state1, db_session)
    assert res1.inventory_status == "RESERVED"

    # Order 2 tries to take 1 unit when available stock is 0
    state2 = OrderState(
        order_id="ORD-TEST-RACE-2",
        customer_id="CUST-001",
        items=[OrderItemState(sku="AUD-NC-HD7", quantity=1)],
        shipping_address=AddressState(
            street="742 Evergreen Terrace", city="Springfield", state="OR", postal_code="97477"
        ),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD", payment_status="AUTHORIZED", transaction_token="tok_race2"
        ),
    )
    res2 = orchestrator.process_order_pipeline(state2, db_session)
    assert res2.inventory_status == "INSUFFICIENT_STOCK"
    assert res2.dispatch_status == "HELD"

    # Verify stock never went below 0
    db_session.refresh(prod)
    assert prod.stock_quantity >= 0

    # Restore stock
    prod.stock_quantity = original_stock
    db_session.commit()


# -----------------------------------------------------------------------------
# TEST 12 — Seed idempotency (Repeated seed calls do not duplicate records)
# -----------------------------------------------------------------------------
def test_12_seed_idempotency(db_session: Session):
    count_before_p = db_session.query(Product).count()
    count_before_c = db_session.query(Customer).count()

    # Call seed_database multiple times
    seed_database(db_session)
    seed_database(db_session)
    seed_database(db_session)

    count_after_p = db_session.query(Product).count()
    count_after_c = db_session.query(Customer).count()

    assert count_after_p == count_before_p
    assert count_after_c == count_before_c
