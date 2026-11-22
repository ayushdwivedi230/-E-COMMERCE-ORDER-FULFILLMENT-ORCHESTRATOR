import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseOrchestratorAgent
from backend.app.schemas.order_state import OrderState, SubstituteRecommendation, BackorderProposal
from backend.app.agents.tools import (
    check_stock_availability,
    reserve_stock_atomic,
    release_stock_reservation,
)


class InventoryAgent(BaseOrchestratorAgent):
    """
    Agent 2: Inventory Agent
    Implements:
    - Product stock verification
    - Atomic inventory reservation
    - Insufficient-stock detection
    - Substitute recommendations & Backorder proposals
    - Enforces constraint: Never silently substitute products; customer approval required.

    Microsoft Agent Framework Integration:
    Calls 3 plain Python tools decorated with @tool:
      1. check_stock_availability
      2. reserve_stock_atomic
      3. release_stock_reservation
    """

    def __init__(self) -> None:
        tools = [
            check_stock_availability,
            reserve_stock_atomic,
            release_stock_reservation,
        ]
        super().__init__(
            name="InventoryAgent",
            description="Performs atomic stock checks, handles reservations, substitutes, and backorders.",
            agent_id="agt-inventory-002",
            tools=tools,
        )

    def process_inventory(self, order_state: OrderState, db: Session) -> bool:
        start_time = time.time()

        if order_state.validation_status != "PASSED":
            order_state.inventory_status = "SKIPPED"
            self.record_agent_log(
                order_state,
                action="InventoryReservation",
                status="SKIPPED",
                message="Skipping inventory reservation because validation did not pass.",
                start_time=start_time,
            )
            return False

        # TOOL 1: Check Stock Availability
        t1_start = time.time()
        check_res = check_stock_availability(db, order_state.items)
        self.record_tool_call(
            order_state=order_state,
            tool_name="check_stock_availability",
            action="StockInspection",
            status="SUCCESS" if check_res["all_available"] else "WARNING",
            message=f"Stock availability check completed. All available: {check_res['all_available']}.",
            start_time=t1_start,
            details=check_res,
        )

        # Convert substitutes and backorders into state schemas
        substitutes = [
            SubstituteRecommendation(**s) for s in check_res.get("substitutes", [])
        ]
        backorders = [
            BackorderProposal(**b) for b in check_res.get("backorders", [])
        ]
        order_state.substitute_recommendations = substitutes
        order_state.backorder_proposals = backorders

        if not check_res["all_available"]:
            if substitutes:
                order_state.inventory_status = "SUBSTITUTE_RECOMMENDED"
                order_state.hold_reason = (
                    f"Inventory Notice: Out of stock. Substitute suggested: {substitutes[0].substitute_name} "
                    f"({substitutes[0].substitute_sku}). Customer approval required before changing order."
                )
            elif backorders:
                order_state.inventory_status = "BACKORDER_PROPOSED"
                order_state.hold_reason = (
                    f"Inventory Notice: Item {backorders[0].sku} is on backorder. "
                    f"Estimated restock: {backorders[0].estimated_restock_days} days. Customer confirmation needed."
                )
            else:
                order_state.inventory_status = "INSUFFICIENT_STOCK"
                order_state.hold_reason = f"Inventory Hold: {'; '.join(check_res['insufficient_items'])}"

            self.record_agent_log(
                order_state,
                action="InventoryHoldDecision",
                status="HELD",
                message=order_state.hold_reason or "Stock unavailable.",
                start_time=start_time,
                details={
                    "substitutes": [s.model_dump() for s in substitutes],
                    "backorders": [b.model_dump() for b in backorders],
                    "requires_customer_approval": True,
                },
            )
            return False

        # TOOL 2: Reserve Stock Atomic
        t2_start = time.time()
        reserve_res = reserve_stock_atomic(db, order_state.order_id, order_state.items)
        self.record_tool_call(
            order_state=order_state,
            tool_name="reserve_stock_atomic",
            action="AtomicReservation",
            status="SUCCESS" if reserve_res["success"] else "FAILED",
            message=reserve_res["message"],
            start_time=t2_start,
            details=reserve_res,
        )

        if not reserve_res["success"]:
            order_state.inventory_status = "INSUFFICIENT_STOCK"
            order_state.hold_reason = reserve_res["message"]
            return False

        # Success path
        order_state.inventory_status = "RESERVED"
        self.record_agent_log(
            order_state,
            action="InventoryReservationSummary",
            status="SUCCESS",
            message=f"All items successfully reserved atomically for order {order_state.order_id}.",
            start_time=start_time,
            details={"reserved_items_count": len(order_state.items)},
        )
        return True

    def release_reservations(self, order_state: OrderState, db: Session) -> Dict[str, Any]:
        """TOOL 3: Release stock reservation (Compensation / Rollback)."""
        t3_start = time.time()
        res = release_stock_reservation(db, order_state.order_id)
        self.record_tool_call(
            order_state=order_state,
            tool_name="release_stock_reservation",
            action="InventoryRollback",
            status="SUCCESS" if res["success"] else "WARNING",
            message=res["message"],
            start_time=t3_start,
            details=res,
        )
        return res
