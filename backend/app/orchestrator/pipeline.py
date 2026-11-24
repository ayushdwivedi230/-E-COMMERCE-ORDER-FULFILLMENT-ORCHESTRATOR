import uuid
import datetime
import json
from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.schemas.order_state import OrderState
from backend.app.models.order import Order, OrderItem
from backend.app.models.product import Product
from backend.app.models.agent_log import AgentLog
from backend.app.agents.validation_agent import ValidationAgent
from backend.app.agents.inventory_agent import InventoryAgent
from backend.app.agents.fraud_check_agent import FraudCheckAgent
from backend.app.agents.pricing_agent import PricingAgent
from backend.app.agents.dispatch_coordinator import DispatchCoordinator
from backend.app.agents.notification_agent import NotificationAgent
from backend.app.services.inventory_service import InventoryService
from backend.app.services.customer_memory import CustomerMemoryService
from backend.app.services.run_logger import AppendOnlyRunLogger


class OrderFulfillmentOrchestrator:
    """
    Multi-Agent Pipeline Orchestrator with Fraud Escalation Route Architecture.
    Coordinates the specialised agents across a shared OrderState.
    Routes high-risk or problematic transactions to the escalation hold queue.
    Guarantees final output is either:
      1. Confirmed and dispatched order with tracking ID and carrier details, OR
      2. Held order with explicit hold reason and audit justification.

    Integrates:
    - Validation Agent
    - Inventory Agent
    - Fraud Check Agent
    - Pricing Agent
    - Dispatch Coordinator
    - Notification Agent (Drafts customer communications across all outcomes)
    - Append-Only Run Logger (logs/execution_run_log.jsonl)
    """

    def __init__(self) -> None:
        self.validation_agent = ValidationAgent()
        self.inventory_agent = InventoryAgent()
        self.fraud_agent = FraudCheckAgent()
        self.pricing_agent = PricingAgent()
        self.dispatch_coordinator = DispatchCoordinator()
        self.notification_agent = NotificationAgent()

    def process_order_pipeline(
        self,
        order_state: OrderState,
        db: Session,
        simulated_failed_attempts: int = 0,
    ) -> OrderState:
        """
        Execute the complete multi-agent pipeline over the shared OrderState.
        Includes top-level transaction safety and rollback on system exceptions.
        """
        try:
            # Step 0: Ensure Order record exists in DB in PENDING status, and guard against duplicate processing
            db_order = self._initialize_order_record(order_state, db)
            if db_order is None:
                # Duplicate order detected and blocked
                self.notification_agent.process_notification(order_state)
                AppendOnlyRunLogger.log_order_run(order_state)
                return order_state

            # STAGE 1: Validation Agent (Must stop processing if invalid or payment failed)
            valid = self.validation_agent.validate_order(order_state, db)
            if not valid:
                self._route_to_hold(
                    order_state=order_state,
                    db=db,
                    db_order=db_order,
                    reason=order_state.hold_reason or "Order failed structural validation or payment check.",
                    stage="VALIDATION_FAILED",
                )
                self.notification_agent.process_notification(order_state)
                self._persist_agent_logs(order_state, db)
                db.commit()
                AppendOnlyRunLogger.log_order_run(order_state)
                return order_state

            # STAGE 2: Inventory Agent (Atomic stock verification & reservation)
            inventory_ok = self.inventory_agent.process_inventory(order_state, db)
            if not inventory_ok:
                self._route_to_hold(
                    order_state=order_state,
                    db=db,
                    db_order=db_order,
                    reason=order_state.hold_reason or "Inventory reservation incomplete.",
                    stage="INVENTORY_HELD",
                )
                self.notification_agent.process_notification(order_state)
                self._persist_agent_logs(order_state, db)
                db.commit()
                AppendOnlyRunLogger.log_order_run(order_state)
                return order_state

            # STAGE 3: Fraud Check Agent (Deterministic risk scoring & Customer Memory)
            fraud_cleared = self.fraud_agent.evaluate_fraud(
                order_state=order_state,
                db=db,
                simulated_failed_attempts=simulated_failed_attempts,
            )

            # FRAUD ESCALATION ROUTE BRANCHING
            if not fraud_cleared or order_state.fraud_score >= 70:
                # Release temporarily held inventory back to available stock
                InventoryService.release_reservations(db, order_state.order_id)
                self._route_to_hold(
                    order_state=order_state,
                    db=db,
                    db_order=db_order,
                    reason=order_state.hold_reason or f"Fraud Risk Escalation: Score {order_state.fraud_score} >= 70.",
                    stage="FRAUD_HELD",
                )
                self.notification_agent.process_notification(order_state)
                self._persist_agent_logs(order_state, db)
                db.commit()
                AppendOnlyRunLogger.log_order_run(order_state)
                return order_state

            # STAGE 4: Pricing Agent (Deterministic decimal arithmetic)
            pricing_ok = self.pricing_agent.calculate_pricing(order_state, db)
            if not pricing_ok:
                InventoryService.release_reservations(db, order_state.order_id)
                self._route_to_hold(
                    order_state=order_state,
                    db=db,
                    db_order=db_order,
                    reason="Pricing calculation could not be completed.",
                    stage="PRICING_FAILED",
                )
                self.notification_agent.process_notification(order_state)
                self._persist_agent_logs(order_state, db)
                db.commit()
                AppendOnlyRunLogger.log_order_run(order_state)
                return order_state

            # STAGE 5: Dispatch Coordinator (Tracking, carrier selection, courier simulation)
            dispatch_ok = self.dispatch_coordinator.coordinate_dispatch(order_state, db)
            if not dispatch_ok:
                InventoryService.release_reservations(db, order_state.order_id)
                self._route_to_hold(
                    order_state=order_state,
                    db=db,
                    db_order=db_order,
                    reason=order_state.hold_reason or "Dispatch coordination failed.",
                    stage="DISPATCH_FAILED",
                )
                self.notification_agent.process_notification(order_state)
                self._persist_agent_logs(order_state, db)
                db.commit()
                AppendOnlyRunLogger.log_order_run(order_state)
                return order_state

            # STAGE 6: Notification Agent (Draft Customer Confirmation Message)
            self.notification_agent.process_notification(order_state)

            # SUCCESSFUL FULFILLMENT: Finalize DB Order & Record to History Memory
            self._finalize_dispatched_order(order_state, db, db_order)

            # Append run to persistent run log
            AppendOnlyRunLogger.log_order_run(order_state)
            return order_state

        except Exception as exc:
            db.rollback()
            try:
                InventoryService.release_reservations(db, order_state.order_id)
            except Exception:
                pass
            order_state.dispatch_status = "FAILED"
            exc_str = str(exc)
            # Sanitize technical traceback: avoid leaking raw SQL queries, credentials, or internal schema
            if "ForeignKeyViolation" in exc_str or "foreign key constraint" in exc_str:
                clean_msg = "Catalog Integrity Error: One or more requested items could not be linked to valid product records."
            elif "IntegrityError" in exc_str or "NOT NULL constraint" in exc_str:
                clean_msg = "Database Constraint Error: Required order fields or relationships are missing."
            else:
                clean_msg = f"Internal fulfillment error ({type(exc).__name__})."
            order_state.hold_reason = f"System Error / Database Exception: {clean_msg}"
            order_state.add_log(
                agent_name="OrderOrchestrator",
                action="PipelineExecutionRecovery",
                status="FAILED",
                message=f"Pipeline aborted: {clean_msg}",
                execution_time_ms=0,
                details={"error_type": type(exc).__name__, "summary": clean_msg},
            )
            try:
                self.notification_agent.process_notification(order_state)
            except Exception:
                pass
            AppendOnlyRunLogger.log_order_run(order_state)
            return order_state

    def _initialize_order_record(self, order_state: OrderState, db: Session) -> Optional[Order]:
        """Create or update database Order row with duplicate processing prevention."""
        existing_order = db.query(Order).filter(Order.id == order_state.order_id).first()
        if existing_order:
            if existing_order.status in ["DISPATCHED", "HELD", "PROCESSING"]:
                order_state.dispatch_status = "REJECTED_DUPLICATE"
                order_state.hold_reason = (
                    f"Duplicate Order Error: Order '{order_state.order_id}' has already been processed "
                    f"(Current status: {existing_order.status}). Duplicate execution aborted."
                )
                order_state.add_log(
                    agent_name="OrderOrchestrator",
                    action="DuplicateOrderPrevention",
                    status="FAILED",
                    message=f"Duplicate order submission rejected for ID '{order_state.order_id}'.",
                    execution_time_ms=0,
                    details={"existing_status": existing_order.status},
                )
                return None
            return existing_order

        db_order = Order(
            id=order_state.order_id,
            customer_id=order_state.customer_id,
            status="PROCESSING",
            shipping_address=order_state.shipping_address.full_address(),
            billing_address=(
                order_state.payment_information.billing_address.full_address()
                if order_state.payment_information.billing_address
                else order_state.shipping_address.full_address()
            ),
            payment_method=order_state.payment_information.payment_method,
            coupon_code=order_state.coupon_code,
            subtotal=Decimal("0.00"),
            total_amount=Decimal("0.00"),
        )
        db.add(db_order)

        # Add Order Items
        for item in order_state.items:
            # Resolve product_id from database if missing or placeholder
            real_product_id = item.product_id if item.product_id not in (None, "PENDING", "UNKNOWN") else None
            if real_product_id is None:
                prod = db.query(Product).filter(Product.sku == item.sku).first()
                if prod:
                    real_product_id = prod.id
                    item.product_id = prod.id
                    if not item.name or item.name == item.sku:
                        item.name = prod.name
                    if item.unit_price == Decimal("0.00"):
                        item.unit_price = prod.price
                        item.total_price = prod.price * item.quantity

            if real_product_id:
                db_item = OrderItem(
                    id=f"ITEM-{uuid.uuid4().hex[:8].upper()}",
                    order_id=order_state.order_id,
                    product_id=real_product_id,
                    sku=item.sku,
                    product_name=item.name or item.sku,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                )
                db.add(db_item)

        db.commit()
        db.refresh(db_order)
        return db_order

    def _route_to_hold(
        self,
        order_state: OrderState,
        db: Session,
        db_order: Order,
        reason: str,
        stage: str,
    ) -> None:
        """Route order to the Hold Queue, release any reserved stock, and persist execution logs."""
        InventoryService.release_reservations(db, order_state.order_id)
        order_state.dispatch_status = "HELD"
        order_state.hold_reason = reason

        if stage == "VALIDATION_FAILED":
            order_state.validation_status = "FAILED"
        elif stage == "INVENTORY_HELD":
            if order_state.substitute_recommendations:
                order_state.inventory_status = "SUBSTITUTE_RECOMMENDED"
            else:
                order_state.inventory_status = "INSUFFICIENT_STOCK"
        elif stage == "FRAUD_HELD":
            order_state.fraud_status = "HIGH_RISK_HELD"
        elif stage == "PRICING_FAILED":
            order_state.pricing_status = "FAILED"

        db_order.status = "HELD"
        db_order.hold_reason = reason
        db_order.fraud_score = order_state.fraud_score

        # Persist Agent execution logs to DB
        self._persist_agent_logs(order_state, db)
        db.commit()

    def _finalize_dispatched_order(
        self,
        order_state: OrderState,
        db: Session,
        db_order: Order,
    ) -> None:
        """Update Order record with final amounts, tracking ID, and record in customer history memory."""
        db_order.status = "DISPATCHED"
        db_order.subtotal = order_state.subtotal
        db_order.discount_amount = order_state.discount_amount
        db_order.tax_amount = order_state.tax_amount
        db_order.shipping_cost = order_state.shipping_cost
        db_order.total_amount = order_state.final_amount
        db_order.fraud_score = order_state.fraud_score
        db_order.tracking_id = order_state.tracking_id

        # Persist Agent execution logs to DB
        self._persist_agent_logs(order_state, db)

        # Record this successful transaction into customer memory
        CustomerMemoryService.record_prior_order(
            db=db,
            customer_id=order_state.customer_id,
            order_id=order_state.order_id,
            status="DELIVERED",
            amount=order_state.final_amount,
            is_suspicious=False,
            failed_attempts=0,
            notes=f"Dispatched via {order_state.carrier} (Tracking: {order_state.tracking_id}).",
        )
        db.commit()

    def _persist_agent_logs(self, order_state: OrderState, db: Session) -> None:
        """Store in-memory agent execution logs into the agent_logs database table."""
        # Query existing log count for this order to avoid duplicating already written logs
        existing_log_count = db.query(AgentLog).filter(AgentLog.order_id == order_state.order_id).count()
        new_entries = order_state.agent_execution_logs[existing_log_count:]

        for entry in new_entries:
            db_log = AgentLog(
                id=f"LOG-{uuid.uuid4().hex[:8].upper()}",
                order_id=order_state.order_id,
                agent_name=entry.agent_name,
                action=f"{entry.tool_name + ' -> ' if entry.tool_name else ''}{entry.action}",
                status=entry.status,
                input_data=json.dumps(entry.details or {}, default=str),
                output_data=entry.message,
                execution_time_ms=entry.execution_time_ms,
            )
            db.add(db_log)
