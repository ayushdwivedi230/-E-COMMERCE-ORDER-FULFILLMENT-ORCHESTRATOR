import pytest
from fastapi import BackgroundTasks
from backend.app.api.orders import get_orders, process_order, get_held_orders, get_order_details
from backend.app.api.products import get_products
from backend.app.api.customers import get_customers, get_customer_memory
from backend.app.api.agents import get_agents_info, get_agents_telemetry
from backend.app.api.dashboard import get_dashboard_analytics
from backend.app.schemas.order import ProcessOrderRequest, OrderItemInput
from backend.app.schemas.order_state import AddressState, PaymentState


def test_agents_info_endpoint():
    data = get_agents_info()
    assert data["framework"] == "Microsoft Agent Framework"
    assert len(data["agents"]) == 5
    agent_names = [a["name"] for a in data["agents"]]
    assert "ValidationAgent" in agent_names
    assert "InventoryAgent" in agent_names
    assert "FraudCheckAgent" in agent_names
    assert "PricingAgent" in agent_names
    assert "DispatchCoordinator" in agent_names


def test_products_endpoint(db_session):
    products = get_products(db=db_session)
    assert len(products) >= 6
    skus = [p.sku for p in products]
    assert "KB-MECH-RGB" in skus
    assert "MON-CRV-32" in skus


def test_customers_endpoint(db_session):
    customers = get_customers(db=db_session)
    assert len(customers) >= 4
    c1 = next(c for c in customers if c.id == "CUST-001")
    assert c1.history_stats.risk_tier == "LOW"
    c3 = next(c for c in customers if c.id == "CUST-003")
    assert c3.history_stats.risk_tier == "HIGH"


def test_process_order_happy_path(db_session):
    bg_tasks = BackgroundTasks()
    request = ProcessOrderRequest(
        customer_id="CUST-001",
        items=[OrderItemInput(sku="KB-MECH-RGB", quantity=1)],
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
            transaction_token="tok_live_test",
        ),
        coupon_code="WELCOME10",
    )
    final_state = process_order(request=request, background_tasks=bg_tasks, db=db_session)
    assert final_state.dispatch_status == "DISPATCHED"
    assert final_state.tracking_id.startswith("TRK-")
    assert float(final_state.final_amount) > 0
    assert len(final_state.agent_execution_logs) == 5


def test_process_order_fraud_escalation_held(db_session):
    bg_tasks = BackgroundTasks()
    request = ProcessOrderRequest(
        customer_id="CUST-003",
        items=[OrderItemInput(sku="MON-4K-27", quantity=2)],
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
        simulate_recent_failed_attempts=2,
    )
    final_state = process_order(request=request, background_tasks=bg_tasks, db=db_session)
    assert final_state.dispatch_status == "HELD"
    assert final_state.fraud_status == "HIGH_RISK_HELD"
    assert final_state.fraud_score >= 70
    assert final_state.tracking_id is None
    assert "Fraud Escalation Hold" in final_state.hold_reason


def test_get_orders_endpoint(db_session):
    orders = get_orders(db=db_session)
    assert isinstance(orders, list)


def test_get_dashboard_analytics(db_session):
    data = get_dashboard_analytics(db=db_session)
    assert "total_orders" in data
    assert "fraud_stats" in data
    assert "status_distribution" in data
    assert "risk_distribution" in data
    assert "recent_activity" in data


def test_get_agents_telemetry(db_session):
    data = get_agents_telemetry(db=db_session)
    telemetry = data["agents"]
    assert len(telemetry) == 5
    names = [t["agent_name"] for t in telemetry]
    assert "ValidationAgent" in names
    assert "InventoryAgent" in names
    assert "FraudCheckAgent" in names
    assert "PricingAgent" in names
    assert "DispatchCoordinator" in names
