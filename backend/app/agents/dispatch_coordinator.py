import time
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseOrchestratorAgent
from backend.app.schemas.order_state import OrderState
from backend.app.agents.tools import (
    select_optimal_carrier,
    generate_tracking_and_manifest,
    create_shipment_record,
)


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

    Microsoft Agent Framework Integration:
    Calls 3 plain Python tools decorated with @tool:
      1. select_optimal_carrier
      2. generate_tracking_and_manifest
      3. create_shipment_record
    """

    def __init__(self) -> None:
        tools = [
            select_optimal_carrier,
            generate_tracking_and_manifest,
            create_shipment_record,
        ]
        super().__init__(
            name="DispatchCoordinator",
            description="Coordinates warehouse packaging, selects carrier logistics, generates tracking, and dispatches orders.",
            agent_id="agt-dispatch-005",
            tools=tools,
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

        # TOOL 1: Select Optimal Logistics Carrier
        t1_start = time.time()
        dest_state = order_state.shipping_address.state if order_state.shipping_address else None
        carrier_res = select_optimal_carrier(
            shipping_method=order_state.shipping_method,
            destination_state=dest_state,
            item_count=len(order_state.items),
        )
        order_state.carrier = carrier_res["carrier"]
        order_state.shipping_method = carrier_res["shipping_method"]

        self.record_tool_call(
            order_state=order_state,
            tool_name="select_optimal_carrier",
            action="CarrierSelection",
            status="SUCCESS",
            message=f"Carrier assigned: {carrier_res['carrier']} ({carrier_res['shipping_method']}).",
            start_time=t1_start,
            details=carrier_res,
        )

        # TOOL 2: Generate Tracking Number and Packaging Manifest
        t2_start = time.time()
        manifest_res = generate_tracking_and_manifest(
            carrier=order_state.carrier,
            method=order_state.shipping_method,
            item_count=len(order_state.items),
        )
        order_state.tracking_id = manifest_res["tracking_id"]

        self.record_tool_call(
            order_state=order_state,
            tool_name="generate_tracking_and_manifest",
            action="ManifestGeneration",
            status="SUCCESS",
            message=f"Tracking ID generated: {manifest_res['tracking_id']}.",
            start_time=t2_start,
            details={
                "tracking_id": manifest_res["tracking_id"],
                "manifest": manifest_res["manifest"],
            },
        )

        # TOOL 3: Create Shipment Record & Commit Reservations
        t3_start = time.time()
        ship_res = create_shipment_record(
            db=db,
            order_id=order_state.order_id,
            tracking_id=order_state.tracking_id,
            carrier=order_state.carrier,
            shipping_method=order_state.shipping_method,
            estimated_delivery=manifest_res["estimated_delivery"],
        )
        self.record_tool_call(
            order_state=order_state,
            tool_name="create_shipment_record",
            action="ShipmentPersistence",
            status="SUCCESS",
            message=f"Shipment {ship_res['shipment_id']} created. Committed {ship_res['committed_reservations']} reservation hold(s).",
            start_time=t3_start,
            details=ship_res,
        )

        # Finalize OrderState
        order_state.dispatch_status = "DISPATCHED"
        self.record_agent_log(
            order_state,
            action="OrderDispatchSummary",
            status="SUCCESS",
            message=f"Order {order_state.order_id} successfully confirmed and dispatched via {order_state.carrier}. Tracking ID: {order_state.tracking_id}.",
            start_time=start_time,
            details={
                "tracking_id": order_state.tracking_id,
                "carrier": order_state.carrier,
                "shipping_method": order_state.shipping_method,
                "status": "DISPATCHED",
            },
        )
        return True
