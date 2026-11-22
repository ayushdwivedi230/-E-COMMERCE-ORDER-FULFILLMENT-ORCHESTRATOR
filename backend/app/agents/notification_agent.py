import time
from typing import Dict, Any, Optional
from backend.app.agents.base import BaseOrchestratorAgent
from backend.app.schemas.order_state import OrderState, NotificationDraft
from backend.app.agents.tools import (
    draft_customer_notification,
    record_notification_log,
)


class NotificationAgent(BaseOrchestratorAgent):
    """
    Agent 6: Notification Agent (Group Extension & Customer Communications Preview)
    Implements:
    - Drafts personalized multi-channel customer messages across outcomes:
        * CONFIRMED / DISPATCHED: Order confirmation with tracking link and carrier.
        * SUBSTITUTED / BACKORDER: Transparent inventory shortfall notice with proposed substitute / timeline.
        * HELD_FRAUD: Professional, neutral security verification advisory.
        * HELD_VALIDATION: Structural issue explanation.
    - Preserves safety constraint: Drafts messages for inspection/preview without sending
      real external emails/SMS unless explicitly configured with external provider credentials.

    Microsoft Agent Framework Integration:
    Calls 2 plain Python tools decorated with @tool:
      1. draft_customer_notification
      2. record_notification_log
    """

    def __init__(self) -> None:
        tools = [
            draft_customer_notification,
            record_notification_log,
        ]
        super().__init__(
            name="NotificationAgent",
            description="Drafts personalized multi-channel customer communications for confirmed, substituted, or held outcomes.",
            agent_id="agt-notification-006",
            tools=tools,
        )

    def process_notification(self, order_state: OrderState) -> NotificationDraft:
        start_time = time.time()

        # TOOL 1: Draft Customer Notification
        t1_start = time.time()
        draft = draft_customer_notification(order_state)
        self.record_tool_call(
            order_state=order_state,
            tool_name="draft_customer_notification",
            action="NotificationDrafting",
            status="SUCCESS",
            message=f"Drafted customer communication for intent '{draft.intent}' (Subject: {draft.subject}).",
            start_time=t1_start,
            details={
                "channel": draft.channel,
                "intent": draft.intent,
                "subject": draft.subject,
                "sms_summary": draft.sms_summary,
            },
        )

        # TOOL 2: Record Notification Log and Attach to OrderState
        t2_start = time.time()
        log_res = record_notification_log(order_state, draft)
        self.record_tool_call(
            order_state=order_state,
            tool_name="record_notification_log",
            action="NotificationAttachment",
            status="SUCCESS",
            message=f"Notification attached to shared order state ({log_res['notification_id']}).",
            start_time=t2_start,
            details=log_res,
        )

        # Extension Notification Log (Recorded in tool execution telemetry to maintain 5-core pipeline roster)
        order_state.add_tool_log(
            agent_name=self.name,
            tool_name="NotificationAgent",
            action="NotificationSummary",
            status="SUCCESS",
            message=f"Customer notification successfully prepared for intent '{draft.intent}'. Preview mode active.",
            execution_time_ms=int((time.time() - start_time) * 1000),
            details={
                "intent": draft.intent,
                "subject": draft.subject,
                "status": "DRAFTED",
            },
        )

        return draft
