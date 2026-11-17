import time
from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseOrchestratorAgent
from backend.app.schemas.order_state import OrderState
from backend.app.services.inventory_service import InventoryService


class InventoryAgent(BaseOrchestratorAgent):
    """
    Agent 2: Inventory Agent
    Implements:
    - Product stock verification
    - Atomic inventory reservation
    - Insufficient-stock detection
    - Substitute recommendations
    - Backorder proposals
    - Enforces constraint: Never silently substitute products; customer approval required.
    """

    def __init__(self) -> None:
        super().__init__(
            name="InventoryAgent",
            description="Performs atomic stock checks, handles reservations, substitutes, and backorders.",
            agent_id="agt-inventory-002",
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

        # Execute atomic stock verification and reservation
        success, substitutes, backorders, msg = InventoryService.verify_and_reserve_stock(
            db=db,
            order_id=order_state.order_id,
            items=order_state.items,
        )

        order_state.substitute_recommendations = substitutes
        order_state.backorder_proposals = backorders

        if not success:
            # Handle out-of-stock / substitute scenario
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
                order_state.hold_reason = f"Inventory Hold: {msg}"

            self.record_agent_log(
                order_state,
                action="InventoryReservation",
                status="HELD",
                message=msg,
                start_time=start_time,
                details={
                    "substitutes": [s.model_dump() for s in substitutes],
                    "backorders": [b.model_dump() for b in backorders],
                    "requires_customer_approval": True,
                },
            )
            return False

        # Success path
        order_state.inventory_status = "RESERVED"
        self.record_agent_log(
            order_state,
            action="InventoryReservation",
            status="SUCCESS",
            message=f"All items successfully reserved atomically for order {order_state.order_id}.",
            start_time=start_time,
            details={"reserved_items_count": len(order_state.items)},
        )
        return True
