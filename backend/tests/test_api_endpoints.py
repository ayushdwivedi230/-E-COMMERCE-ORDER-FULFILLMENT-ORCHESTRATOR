import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["database"] == "CONNECTED"


def test_agents_info_endpoint(client):
    response = client.get("/api/agents/info")
    assert response.status_code == 200
    data = response.json()
    assert data["framework"] == "Microsoft Agent Framework"
    assert len(data["agents"]) == 5
    agent_names = [a["name"] for a in data["agents"]]
    assert "ValidationAgent" in agent_names
    assert "InventoryAgent" in agent_names
    assert "FraudCheckAgent" in agent_names
    assert "PricingAgent" in agent_names
    assert "DispatchCoordinator" in agent_names


def test_products_endpoint(client):
    response = client.get("/api/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 6
    skus = [p["sku"] for p in products]
    assert "KB-MECH-RGB" in skus
    assert "MON-CRV-32" in skus


def test_customers_endpoint(client):
    response = client.get("/api/customers")
    assert response.status_code == 200
    customers = response.json()
    assert len(customers) >= 4
    c1 = next(c for c in customers if c["id"] == "CUST-001")
    assert c1["history_stats"]["risk_tier"] == "LOW"
    c3 = next(c for c in customers if c["id"] == "CUST-003")
    assert c3["history_stats"]["risk_tier"] == "HIGH"


def test_process_order_happy_path(client):
    payload = {
        "customer_id": "CUST-001",
        "items": [{"sku": "KB-MECH-RGB", "quantity": 1}],
        "shipping_address": {
            "street": "742 Evergreen Terrace",
            "city": "Springfield",
            "state": "OR",
            "postal_code": "97477",
            "country": "USA",
        },
        "payment_information": {
            "payment_method": "CREDIT_CARD",
            "payment_status": "AUTHORIZED",
            "transaction_token": "tok_live_test",
        },
        "coupon_code": "WELCOME10",
    }
    response = client.post("/api/orders/process", json=payload)
    assert response.status_code == 200
    order = response.json()
    assert order["dispatch_status"] == "DISPATCHED"
    assert order["tracking_id"].startswith("TRK-")
    assert float(order["final_amount"]) > 0
    assert len(order["agent_execution_logs"]) == 5


def test_process_order_fraud_escalation_held(client):
    payload = {
        "customer_id": "CUST-003",  # High risk user with prior chargebacks
        "items": [{"sku": "MON-4K-27", "quantity": 2}],
        "shipping_address": {
            "street": "PO Box 9999",
            "city": "Unknown Island",
            "state": "FL",
            "postal_code": "33040",
            "country": "USA",
        },
        "payment_information": {
            "payment_method": "CREDIT_CARD",
            "payment_status": "AUTHORIZED",
            "transaction_token": "tok_suspicious",
            "billing_address": {
                "street": "PO Box 111",
                "city": "Anchorage",
                "state": "AK",
                "postal_code": "99501",
                "country": "USA",
            },
        },
        "simulate_recent_failed_attempts": 2,
    }
    response = client.post("/api/orders/process", json=payload)
    assert response.status_code == 200
    order = response.json()
    assert order["dispatch_status"] == "HELD"
    assert order["fraud_status"] == "HIGH_RISK_HELD"
    assert order["fraud_score"] >= 70
    assert order["tracking_id"] is None
    assert "Fraud Escalation Hold" in order["hold_reason"]
