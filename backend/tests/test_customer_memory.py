from decimal import Decimal
from backend.app.services.customer_memory import CustomerMemoryService


def test_customer_memory_good_customer(db_session):
    stats = CustomerMemoryService.get_customer_history(db_session, "CUST-001")
    assert stats.customer_id == "CUST-001"
    assert stats.total_orders >= 4
    assert stats.successful_orders >= 4
    assert stats.suspicious_orders == 0
    assert stats.failed_payment_attempts == 0
    assert stats.risk_tier == "LOW"
    assert stats.average_order_value > Decimal("0.00")


def test_customer_memory_high_risk_customer(db_session):
    stats = CustomerMemoryService.get_customer_history(db_session, "CUST-003")
    assert stats.customer_id == "CUST-003"
    assert stats.suspicious_orders >= 2
    assert stats.failed_payment_attempts >= 3
    assert stats.risk_tier == "HIGH"
    assert stats.suspicion_rate >= 0.50


def test_customer_memory_new_customer(db_session):
    stats = CustomerMemoryService.get_customer_history(db_session, "CUST-004")
    assert stats.customer_id == "CUST-004"
    assert stats.total_orders == 0
    assert stats.successful_orders == 0
    assert stats.risk_tier == "LOW"
    assert stats.average_order_value == Decimal("0.00")
