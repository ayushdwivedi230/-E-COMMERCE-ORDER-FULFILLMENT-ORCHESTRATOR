import json
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("ecommerce.websocket")
router = APIRouter(tags=["WebSocket"])


class WebSocketManager:
    """Manages active WebSocket client connections and broadcasts live fulfillment events."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Broadcast an event to all connected frontend clients."""
        if not self.active_connections:
            return

        message = json.dumps({"type": event_type, "data": payload}, default=str)
        dead_connections: List[WebSocket] = []

        for conn in self.active_connections:
            try:
                await conn.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                dead_connections.append(conn)

        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = WebSocketManager()


@router.websocket("/ws/orders")
async def websocket_orders_endpoint(websocket: WebSocket):
    """Real-time WebSocket stream for order fulfillment and agent telemetry events."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; clients can send ping/commands
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
