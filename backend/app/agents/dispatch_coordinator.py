import time
import uuid
import datetime
import random
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseOrchestratorAgent
from backend.app.schemas.order_state import OrderState
from backend.app.models.shipment import Shipment
from backend.app.services.inventory_service import InventoryService


class DispatchCoordinator(BaseOrchestratorAgent):
    """
    Agent 5: Dispatch Coordinator
    Implements:
    - Order confirmation & status verification
    - Shipping method & courier carrier selection
    - Simulated tracking ID generation
    - Shipment record creation in database
    - Commits atomic inventory reservation
    - Simulates courier dispatch operations manifest
    """

    def __init__(self) -> None:
        super().__init__(
            name="DispatchCoordinator",
            description="Coordinates warehouse packaging, selects carrier logistics, generates tracking, and dispatches orders.",
            agent_id="agt-dispatch-005",
        )

    def coordinate_dispatch(self, order_state: OrderState, db: Session) -> bool:
        start_time = time.time()

        # Gate check: Prior phases must have passed
        if (
            order_state.validation_status != "PASSED"
            or order_state.inventory_status != "RESERVED"
            or order_state.fraud_status == "HIGH_RISK_HELD"
            or order_state.pricing_status != "CALCULATED"
        ):
            order_state.dispatch_status = "HELD"
            self.record_agent_log(
                order_state,
                action="OrderDispatch",
                status="HELD",
                message="Cannot dispatch order: One or more prior pipeline prerequisites failed or order is held.",
                start_time=start_time,
                details={
                    "validation_status": order_state.validation_status,
                    "inventory_status": order_state.inventory_status,
                    "fraud_status": order_state.fraud_status,
                    "pricing_status": order_state.pricing_status,
                },
            )
            return False

        # 1. Carrier & Shipping Method Selection
        carrier, method = self._select_carrier_and_method(order_state)
        order_state.carrier = carrier
        order_state.shipping_method = method

        # 2. Tracking ID Generation (Simulated Carrier Standard Format)
        carrier_prefix = {
            "FedEx Priority Express": "FDX",
            "UPS Ground Logistics": "UPS",
            "USPS Priority Commerce": "USP",
            "DHL Express Worldwide": "DHL",
        }.get(carrier, "EXP")
        tracking_number = f"TRK-{carrier_prefix}-{random.randint(10000000, 99999999)}"
        order_state.tracking_id = tracking_number

        # 3. Simulate Courier Operations Manifest
        now = datetime.datetime.utcnow()
        estimated_delivery = now + datetime.timedelta(days=2 if "Express" in method else 5)
        dispatch_manifest = {
            "warehouse_id": "WH-CENTRAL-01",
            "assigned_carrier": carrier,
            "service_level": method,
            "package_weight_kg": round(len(order_state.items) * 0.85, 2),
            "estimated_pickup": (now + datetime.timedelta(hours=4)).isoformat(),
            "estimated_delivery": estimated_delivery.isoformat(),
            "simulation_note": "Courier logistics operations simulated in accordance with CSE476 specifications.",
        }

        # 4. Create Shipment Record in Database
        shipment = Shipment(
            id=f"SHP-{uuid.uuid4().hex[:8].upper()}",
            order_id=order_state.order_id,
            tracking_id=tracking_number,
            carrier=carrier,
            shipping_method=method,
            status="DISPATCHED",
            estimated_delivery=estimated_delivery,
            dispatch_notes=f"Dispatched via {carrier} ({method}). Estimated arrival: {estimated_delivery.strftime('%Y-%m-%d')}.",
        )
        db.add(shipment)

        # 5. Commit Inventory Reservations Permanently
        InventoryService.commit_reservations(db, order_state.order_id)

        # 6. Update Final Dispatch State
        order_state.dispatch_status = "DISPATCHED"

        self.record_agent_log(
            order_state,
            action="OrderDispatch",
            status="SUCCESS",
            message=f"Order confirmed and dispatched via {carrier}. Tracking Number: {tracking_number}.",
            start_time=start_time,
            details={
                "tracking_id": tracking_number,
                "carrier": carrier,
                "method": method,
                "manifest": dispatch_manifest,
            },
        )
        return True

    def _select_carrier_and_method(self, order_state: OrderState) -> tuple[str, str]:
        """Logistics carrier recommendation engine based on destination, items, and speed."""
        if order_state.shipping_method == "Express" or order_state.final_amount > 300:
            return "FedEx Priority Express", "2-Day Priority"
        elif any("Monitor" in item.name for item in order_state.items):
            return "UPS Ground Logistics", "Heavy Freight Ground"
        else:
            return "USPS Priority Commerce", "Standard Tracked Parcel"
