from decimal import Decimal
import pytest
from fastapi import BackgroundTasks
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from backend.app.api.orders import process_order
from backend.app.models.customer import Customer
from backend.app.models.order import Order, OrderItem
from backend.app.models.product import Product
from backend.app.orchestrator.pipeline import OrderFulfillmentOrchestrator
from backend.app.schemas.order import OrderItemInput, ProcessOrderRequest
from backend.app.schemas.order_state import (
    AddressState,
    OrderItemState,
    OrderState,
    PaymentState,
)
from backend.app.services.catalog_service import validate_and_resolve_order_items
from backend.app.services.seed_data import seed_database


def _make_address() -> AddressState:
    return AddressState(
        street="742 Evergreen Terrace",
        city="Springfield",
        state="OR",
        postal_code="97477",
        country="USA",
    )


def _make_payment(status: str = "AUTHORIZED", token: str = "tok_valid") -> PaymentState:
    return PaymentState(
        payment_method="CREDIT_CARD",
        payment_status=status,
        transaction_token=token,
    )


def test_exact_reproduction_kb_mech_rgb_resolves_to_prod_001(db_session: Session):
    """Exact reproduction: KB-MECH-RGB qty 1 via API persists PROD-001 and Decimal 99.99."""
    bg = BackgroundTasks()
    req = ProcessOrderRequest(
        customer_id="CUST-001",
        items=[OrderItemInput(sku="KB-MECH-RGB", quantity=1)],
        shipping_address=_make_address(),
        payment_information=_make_payment(),
    )

    result = process_order(request=req, background_tasks=bg, db=db_session)
    assert result.dispatch_status == "DISPATCHED"
    assert len(result.items) == 1
    assert result.items[0].product_id == "PROD-001"
    assert result.items[0].sku == "KB-MECH-RGB"
    assert result.items[0].unit_price == Decimal("99.99")
    assert result.items[0].total_price == Decimal("99.99")

    db_items = (
        db_session.query(OrderItem).filter(OrderItem.order_id == result.order_id).all()
    )
    assert len(db_items) == 1
    assert db_items[0].product_id == "PROD-001"
    assert db_items[0].sku == "KB-MECH-RGB"
    assert db_items[0].unit_price == Decimal("99.99")
    assert db_items[0].total_price == Decimal("99.99")


def test_partially_populated_db_repairs_missing_product_without_duplicating_skus():
    """Partially populated DB repairs missing PROD-001 without wiping orders or duplicating SKUs."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Pre-seed only PROD-002 with an existing customer and existing order
        db.add(
            Customer(
                id="CUST-001",
                name="John Verified",
                email="john.verified@example.com",
                address="742 Evergreen Terrace",
                status="ACTIVE",
            )
        )
        db.add(
            Product(
                id="PROD-002",
                sku="KB-ERG-WRL",
                name="Ergonomic Split Wireless Keyboard",
                price=Decimal("89.99"),
                stock_quantity=25,
                is_active=True,
            )
        )
        db.add(
            Order(
                id="ORD-EXISTING-01",
                customer_id="CUST-001",
                status="DISPATCHED",
                shipping_address="742 Evergreen Terrace",
                payment_method="CREDIT_CARD",
                subtotal=Decimal("89.99"),
                total_amount=Decimal("89.99"),
            )
        )
        db.add(
            OrderItem(
                id="ITEM-EXISTING-01",
                order_id="ORD-EXISTING-01",
                product_id="PROD-002",
                sku="KB-ERG-WRL",
                product_name="Ergonomic Split Wireless Keyboard",
                quantity=1,
                unit_price=Decimal("89.99"),
                total_price=Decimal("89.99"),
            )
        )
        db.commit()

        # Run seed_database on partially populated DB
        seed_database(db)

        # Missing PROD-001 is repaired
        p1 = db.query(Product).filter(Product.sku == "KB-MECH-RGB").first()
        assert p1 is not None
        assert p1.id == "PROD-001"
        assert p1.is_active is True
        assert p1.price == Decimal("99.99")

        # Existing PROD-002 is preserved and NOT duplicated
        p2_all = db.query(Product).filter(Product.sku == "KB-ERG-WRL").all()
        assert len(p2_all) == 1
        assert p2_all[0].stock_quantity == 25

        # Existing order & order_items remain untouched
        existing_order = db.query(Order).filter(Order.id == "ORD-EXISTING-01").first()
        assert existing_order is not None
        assert existing_order.status == "DISPATCHED"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_seed_does_not_duplicate_sku_with_different_id():
    """If KB-MECH-RGB exists under another ID, seed_database must NOT insert a duplicate SKU."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        db.add(
            Product(
                id="CUSTOM-KB-ID",
                sku="KB-MECH-RGB",
                name="Pro Mechanical RGB Gaming Keyboard",
                price=Decimal("99.99"),
                stock_quantity=10,
                is_active=True,
            )
        )
        db.commit()

        seed_database(db)

        matches = db.query(Product).filter(Product.sku == "KB-MECH-RGB").all()
        assert len(matches) == 1
        assert matches[0].id == "CUSTOM-KB-ID"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.mark.parametrize("bad_id", [None, "", "PENDING", "UNKNOWN", "PROD-FAKE-999"])
def test_placeholder_or_fabricated_product_ids_overwritten_for_valid_sku(
    db_session: Session, bad_id
):
    """Any placeholder, null, or fabricated product_id is overwritten by real DB Product.id."""
    orchestrator = OrderFulfillmentOrchestrator()
    state = OrderState(
        order_id=f"ORD-OVERWRITE-{bad_id or 'NONE'}",
        customer_id="CUST-001",
        items=[
            OrderItemState(
                product_id=bad_id,
                sku="KB-MECH-RGB",
                name="Wrong Name",
                quantity=2,
                unit_price=Decimal("0.01"),  # Fabricated client price must be overwritten
                total_price=Decimal("0.02"),
            )
        ],
        shipping_address=_make_address(),
        payment_information=_make_payment(),
    )

    result = orchestrator.process_order_pipeline(state, db_session)
    assert result.dispatch_status == "DISPATCHED"
    assert result.items[0].product_id == "PROD-001"
    assert result.items[0].unit_price == Decimal("99.99")
    assert result.items[0].total_price == Decimal("199.98")

    db_items = (
        db_session.query(OrderItem).filter(OrderItem.order_id == state.order_id).all()
    )
    assert len(db_items) == 1
    assert db_items[0].product_id == "PROD-001"
    assert db_items[0].unit_price == Decimal("99.99")
    assert db_items[0].total_price == Decimal("199.98")


def test_unknown_sku_rejected_before_persisting_order_or_order_items(db_session: Session):
    """Unknown SKU is rejected with PRODUCT_NOT_FOUND BEFORE persisting Order or OrderItem."""
    bg = BackgroundTasks()
    req = ProcessOrderRequest(
        customer_id="CUST-001",
        items=[OrderItemInput(sku="NON-EXISTENT-SKU-XYZ", quantity=1)],
        shipping_address=_make_address(),
        payment_information=_make_payment(),
    )

    result = process_order(request=req, background_tasks=bg, db=db_session)
    assert result.validation_status == "FAILED"
    assert result.dispatch_status == "HELD"
    assert "PRODUCT_NOT_FOUND" in result.hold_reason

    assert db_session.query(Order).filter(Order.id == result.order_id).first() is None
    assert db_session.query(OrderItem).filter(OrderItem.order_id == result.order_id).count() == 0


def test_missing_product_in_db_rejected_via_api(db_session: Session):
    """If KB-MECH-RGB is missing from DB, API rejects cleanly with PRODUCT_NOT_FOUND without FK crash."""
    prod = db_session.query(Product).filter(Product.sku == "KB-MECH-RGB").first()
    db_session.delete(prod)
    db_session.commit()

    bg = BackgroundTasks()
    req = ProcessOrderRequest(
        customer_id="CUST-001",
        items=[OrderItemInput(sku="KB-MECH-RGB", quantity=1)],
        shipping_address=_make_address(),
        payment_information=_make_payment(),
    )

    result = process_order(request=req, background_tasks=bg, db=db_session)
    assert result.validation_status == "FAILED"
    assert result.dispatch_status == "HELD"
    assert "PRODUCT_NOT_FOUND" in result.hold_reason
    assert db_session.query(Order).filter(Order.id == result.order_id).first() is None
    assert db_session.query(OrderItem).filter(OrderItem.order_id == result.order_id).count() == 0


def test_inactive_product_rejected_before_persistence(db_session: Session):
    """Inactive catalog item is rejected before persisting Order or OrderItem."""
    prod = db_session.query(Product).filter(Product.sku == "KB-MECH-RGB").first()
    prod.is_active = False
    db_session.commit()

    bg = BackgroundTasks()
    req = ProcessOrderRequest(
        customer_id="CUST-001",
        items=[OrderItemInput(sku="KB-MECH-RGB", quantity=1)],
        shipping_address=_make_address(),
        payment_information=_make_payment(),
    )

    result = process_order(request=req, background_tasks=bg, db=db_session)
    assert result.validation_status == "FAILED"
    assert "PRODUCT_INACTIVE" in result.hold_reason
    assert db_session.query(Order).filter(Order.id == result.order_id).first() is None
    assert db_session.query(OrderItem).filter(OrderItem.order_id == result.order_id).count() == 0


def test_missing_catalog_price_rejected_before_persistence(db_session: Session):
    """Product with zero/invalid catalog price is rejected with INVALID_CATALOG_PRICE."""
    prod = db_session.query(Product).filter(Product.sku == "KB-MECH-RGB").first()
    prod.price = Decimal("0.00")
    db_session.commit()

    items = [OrderItemState(product_id="PENDING", sku="KB-MECH-RGB", quantity=1)]
    res = validate_and_resolve_order_items(db_session, items)
    assert res["valid"] is False
    assert any("INVALID_CATALOG_PRICE" in err for err in res["errors"])
    assert items[0].product_id is None


def test_direct_initialize_order_record_rejects_pending_and_unknown_sku(db_session: Session):
    """Even if called directly, _initialize_order_record refuses to persist unknown SKU or PENDING."""
    orchestrator = OrderFulfillmentOrchestrator()
    bad_state = OrderState(
        order_id="ORD-DIRECT-BAD",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PENDING", sku="NO-SUCH-SKU", quantity=1)],
        shipping_address=_make_address(),
        payment_information=_make_payment(),
    )
    with pytest.raises(ValueError, match="PRODUCT_NOT_FOUND"):
        orchestrator._initialize_order_record(bad_state, db_session)

    db_session.rollback()
    assert db_session.query(Order).filter(Order.id == "ORD-DIRECT-BAD").first() is None
    assert db_session.query(OrderItem).filter(OrderItem.order_id == "ORD-DIRECT-BAD").count() == 0
