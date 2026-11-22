import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from backend.app.schemas.order_state import OrderState

logger = logging.getLogger("ecommerce.run_logger")


class AppendOnlyRunLogger:
    """
    Append-only run log that records actual execution events and never
    overwrites historical entries.
    Persists pipeline run summaries and detailed agent tool traces to JSONL format.
    """

    LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs"))
    LOG_FILE = os.path.join(LOG_DIR, "execution_run_log.jsonl")

    @classmethod
    def get_log_file_path(cls) -> str:
        return cls.LOG_FILE

    @classmethod
    def log_order_run(cls, order_state: OrderState) -> Dict[str, Any]:
        """
        Append a complete order execution run record to the JSONL log file.
        Thread-safe file append with immediate disk flush.
        """
        try:
            os.makedirs(cls.LOG_DIR, exist_ok=True)
            run_id = f"RUN-{uuid.uuid4().hex[:12].upper()}"
            now_iso = datetime.now(timezone.utc).isoformat()

            # Count total agent steps and tool invocations
            tool_calls = order_state.tool_execution_logs

            log_entry = {
                "run_id": run_id,
                "timestamp": now_iso,
                "order_id": order_state.order_id,
                "customer_id": order_state.customer_id,
                "customer_name": order_state.customer_name,
                "dispatch_status": order_state.dispatch_status,
                "validation_status": order_state.validation_status,
                "inventory_status": order_state.inventory_status,
                "fraud_status": order_state.fraud_status,
                "fraud_score": order_state.fraud_score,
                "pricing_status": order_state.pricing_status,
                "subtotal": str(order_state.subtotal),
                "discount_amount": str(order_state.discount_amount),
                "tax_amount": str(order_state.tax_amount),
                "shipping_cost": str(order_state.shipping_cost),
                "final_amount": str(order_state.final_amount),
                "carrier": order_state.carrier,
                "shipping_method": order_state.shipping_method,
                "tracking_id": order_state.tracking_id,
                "hold_reason": order_state.hold_reason,
                "review_status": order_state.review_status,
                "notification_status": order_state.notification_status,
                "notification_draft": (
                    order_state.customer_notification_draft.model_dump()
                    if order_state.customer_notification_draft
                    else None
                ),
                "total_steps": len(order_state.agent_execution_logs),
                "total_tool_calls": len(tool_calls),
                "agent_execution_logs": [
                    log.model_dump() for log in order_state.agent_execution_logs
                ],
                "tool_execution_logs": [
                    log.model_dump() for log in order_state.tool_execution_logs
                ],
            }

            with open(cls.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, default=str) + "\n")
                f.flush()

            logger.info(f"Append-only log record committed: {run_id} for order {order_state.order_id}.")
            return log_entry
        except Exception as e:
            logger.error(f"Failed to append execution log: {e}", exc_info=True)
            return {"error": str(e), "logged": False}

    @classmethod
    def read_recent_runs(cls, limit: int = 50) -> list:
        """Read recent runs from the append-only log file in reverse chronological order."""
        if not os.path.exists(cls.LOG_FILE):
            return []
        runs = []
        try:
            with open(cls.LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            runs.append(json.loads(line))
                        except Exception:
                            pass
            return runs[-limit:][::-1]
        except Exception as e:
            logger.error(f"Failed to read run logs: {e}")
            return []
