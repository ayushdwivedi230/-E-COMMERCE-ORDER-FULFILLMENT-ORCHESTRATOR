from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session
from backend.app.models.order import OrderHistory, Order
from backend.app.models.customer import Customer
from backend.app.schemas.customer import CustomerHistoryStats, OrderHistoryEntry


class CustomerMemoryService:
    """
    Manages customer memory and historical transaction retrieval.
    Computes prior behavioral patterns and transaction metrics for fraud evaluation.
    Preserves historical records and isolates prior data from the current order in flight.
    """

    @staticmethod
    def get_customer_history(db: Session, customer_id: str) -> CustomerHistoryStats:
        """
        Retrieve prior order history for a customer and calculate statistical risk features.
        Only reads existing committed historical records from `order_history`.
        """
        history_rows: List[OrderHistory] = (
            db.query(OrderHistory)
            .filter(OrderHistory.customer_id == customer_id)
            .order_by(OrderHistory.created_at.desc())
            .all()
        )

        total_orders = len(history_rows)
        if total_orders == 0:
            return CustomerHistoryStats(
                customer_id=customer_id,
                total_orders=0,
                successful_orders=0,
                suspicious_orders=0,
                failed_payment_attempts=0,
                total_spent=Decimal("0.00"),
                average_order_value=Decimal("0.00"),
                suspicion_rate=0.0,
                risk_tier="LOW",
                prior_orders=[],
            )

        successful_orders = 0
        suspicious_orders = 0
        failed_payment_attempts = 0
        total_spent = Decimal("0.00")
        prior_entries: List[OrderHistoryEntry] = []

        for row in history_rows:
            prior_entries.append(
                OrderHistoryEntry(
                    id=row.id,
                    order_id=row.order_id,
                    status=row.status,
                    amount=Decimal(str(row.amount)),
                    is_suspicious=row.is_suspicious,
                    failed_payment_attempts=row.failed_payment_attempts,
                    notes=row.notes,
                    created_at=row.created_at,
                )
            )

            failed_payment_attempts += row.failed_payment_attempts

            if row.is_suspicious or row.status in ["CHARGEBACK", "SUSPICIOUS"]:
                suspicious_orders += 1

            if row.status in ["DELIVERED", "COMPLETED"]:
                successful_orders += 1
                total_spent += Decimal(str(row.amount))

        avg_order_value = (
            total_spent / Decimal(str(successful_orders))
            if successful_orders > 0
            else Decimal("0.00")
        )
        suspicion_rate = (
            float(suspicious_orders) / float(total_orders)
            if total_orders > 0
            else 0.0
        )

        # Risk tier classification
        if suspicious_orders >= 2 or suspicion_rate >= 0.40 or failed_payment_attempts >= 3:
            risk_tier = "HIGH"
        elif suspicious_orders == 1 or suspicion_rate >= 0.15 or failed_payment_attempts >= 1:
            risk_tier = "MEDIUM"
        else:
            risk_tier = "LOW"

        return CustomerHistoryStats(
            customer_id=customer_id,
            total_orders=total_orders,
            successful_orders=successful_orders,
            suspicious_orders=suspicious_orders,
            failed_payment_attempts=failed_payment_attempts,
            total_spent=total_spent,
            average_order_value=avg_order_value,
            suspicion_rate=round(suspicion_rate, 4),
            risk_tier=risk_tier,
            prior_orders=prior_entries,
        )

    @staticmethod
    def record_prior_order(
        db: Session,
        customer_id: str,
        order_id: str,
        status: str,
        amount: Decimal,
        is_suspicious: bool = False,
        failed_attempts: int = 0,
        notes: Optional[str] = None,
    ) -> OrderHistory:
        """Record an order into persistent historical memory."""
        import uuid

        history_entry = OrderHistory(
            id=f"HIST-{uuid.uuid4().hex[:8].upper()}",
            customer_id=customer_id,
            order_id=order_id,
            status=status,
            amount=amount,
            is_suspicious=is_suspicious,
            failed_payment_attempts=failed_attempts,
            notes=notes,
        )
        db.add(history_entry)
        db.commit()
        db.refresh(history_entry)
        return history_entry
