from decimal import Decimal
from backend.app.schemas.order_state import OrderState, OrderItemState, AddressState, PaymentState
from backend.app.agents.validation_agent import ValidationAgent
from backend.app.agents.inventory_agent import InventoryAgent
from backend.app.agents.fraud_check_agent import FraudCheckAgent
from backend.app.agents.pricing_agent import PricingAgent
from backend.app.agents.dispatch_coordinator import DispatchCoordinator
from backend.app.models.product import Product


def make_sample_state(
    customer_id: str = "CUST-001",
    sku: str = "KB-MECH-RGB",
    qty: int = 1,
    coupon: str = None,
) -> OrderState:
    return OrderState(
        order_id="TEST-ORD-01",
        customer_id=customer_id,
        items=[
            OrderItemState(
                product_id="PROD-001",
                sku=sku,
                name="Test Item",
                quantity=qty,
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
            transaction_token="tok_12345",
            billing_address=AddressState(
                street="742 Evergreen Terrace",
                city="Springfield",
                state="OR",
                postal_code="97477",
                country="USA",
            ),
        ),
        coupon_code=coupon,
    )


def test_validation_agent_success(db_session):
    agent = ValidationAgent()
    state = make_sample_state()
    passed = agent.validate_order(state, db_session)
    assert passed is True
    assert state.validation_status == "PASSED"
    assert len(state.agent_execution_logs) >= 1


def test_validation_agent_invalid_sku(db_session):
    agent = ValidationAgent()
    state = make_sample_state(sku="NON-EXISTENT-SKU")
    passed = agent.validate_order(state, db_session)
    assert passed is False
    assert state.validation_status == "FAILED"
    assert "does not exist" in state.hold_reason


def test_inventory_agent_reservation(db_session):
    agent = InventoryAgent()
    state = make_sample_state(qty=2)
    state.validation_status = "PASSED"

    initial_stock = db_session.query(Product).filter(Product.sku == "KB-MECH-RGB").first().stock_quantity
    success = agent.process_inventory(state, db_session)

    assert success is True
    assert state.inventory_status == "RESERVED"
    updated_stock = db_session.query(Product).filter(Product.sku == "KB-MECH-RGB").first().stock_quantity
    assert updated_stock == initial_stock - 2


def test_inventory_agent_substitute_recommendation(db_session):
    agent = InventoryAgent()
    # SKU MON-CRV-32 has 0 stock in seed data with substitute MON-4K-27
    state = make_sample_state(sku="MON-CRV-32", qty=1)
    state.validation_status = "PASSED"

    success = agent.process_inventory(state, db_session)
    assert success is False
    assert state.inventory_status == "SUBSTITUTE_RECOMMENDED"
    assert len(state.substitute_recommendations) >= 1
    assert state.substitute_recommendations[0].substitute_sku == "MON-4K-27"
    assert "Customer approval required" in state.hold_reason


def test_fraud_check_agent_low_risk(db_session):
    agent = FraudCheckAgent()
    state = make_sample_state(customer_id="CUST-001")
    state.inventory_status = "RESERVED"

    cleared = agent.evaluate_fraud(state, db_session)
    assert cleared is True
    assert state.fraud_score <= 29
    assert state.fraud_status == "LOW_RISK"
    assert "APPROVED" in state.fraud_ai_reasoning


def test_fraud_check_agent_high_risk_escalation(db_session):
    agent = FraudCheckAgent()
    # CUST-003 has multiple prior chargebacks
    state = make_sample_state(customer_id="CUST-003")
    state.inventory_status = "RESERVED"

    cleared = agent.evaluate_fraud(state, db_session, simulated_failed_attempts=2)
    assert cleared is False
    assert state.fraud_score >= 70
    assert state.fraud_status == "HIGH_RISK_HELD"
    assert "Fraud Escalation Hold" in state.hold_reason


def test_pricing_agent_deterministic_calculations(db_session):
    agent = PricingAgent()
    # 2 keyboards @ $99.99 = $199.98 with coupon WELCOME10 (10% off)
    state = make_sample_state(qty=2, coupon="WELCOME10")
    state.fraud_status = "LOW_RISK"

    ok = agent.calculate_pricing(state, db_session)
    assert ok is True
    assert state.pricing_status == "CALCULATED"
    assert state.subtotal == Decimal("199.98")
    assert state.discount_amount == Decimal("20.00")  # 10% of 199.98 rounded to 20.00
    # Tax on 179.98 @ 8% = 14.40
    assert state.tax_amount == Decimal("14.40")
    # Free shipping since subtotal >= $100.00
    assert state.shipping_cost == Decimal("0.00")
    # Final = 179.98 + 14.40 = 194.38
    assert state.final_amount == Decimal("194.38")


def test_dispatch_coordinator(db_session):
    agent = DispatchCoordinator()
    state = make_sample_state()
    state.validation_status = "PASSED"
    state.inventory_status = "RESERVED"
    state.fraud_status = "LOW_RISK"
    state.pricing_status = "CALCULATED"
    state.final_amount = Decimal("99.99")

    dispatched = agent.coordinate_dispatch(state, db_session)
    assert dispatched is True
    assert state.dispatch_status == "DISPATCHED"
    assert state.tracking_id is not None
    assert state.tracking_id.startswith("TRK-")
    assert state.carrier is not None
