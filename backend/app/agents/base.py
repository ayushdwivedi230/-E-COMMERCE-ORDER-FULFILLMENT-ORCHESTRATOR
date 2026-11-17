import time
import json
import logging
from typing import Any, Dict, Optional
from agent_framework import BaseAgent, AgentResponse

logger = logging.getLogger("ecommerce.agents")


class BaseOrchestratorAgent(BaseAgent):
    """
    Base class for all specialised e-commerce fulfillment agents.
    Inherits from Microsoft Agent Framework's `BaseAgent` for framework compliance,
    session management, and tool integration.
    """

    def __init__(
        self,
        name: str,
        description: str,
        agent_id: Optional[str] = None,
        additional_properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            id=agent_id,
            name=name,
            description=description,
            additional_properties=additional_properties or {},
        )
        self.logger = logging.getLogger(f"ecommerce.agents.{name}")

    async def run(
        self,
        messages=None,
        *,
        stream: bool = False,
        session=None,
        function_invocation_kwargs=None,
        client_kwargs=None,
        **kwargs,
    ) -> AgentResponse:
        """Framework protocol compliance method."""
        return AgentResponse(
            messages=[],
            response_id=f"{self.name}-resp-{int(time.time())}"
        )

    def record_agent_log(
        self,
        order_state,
        action: str,
        status: str,
        message: str,
        start_time: float,
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Utility method to record standard performance and execution telemetry."""
        elapsed_ms = int((time.time() - start_time) * 1000)
        order_state.add_log(
            agent_name=self.name,
            action=action,
            status=status,
            message=message,
            execution_time_ms=elapsed_ms,
            details=details,
        )
        self.logger.info(f"[{self.name}] {action} -> {status} ({elapsed_ms}ms): {message}")
        return elapsed_ms
