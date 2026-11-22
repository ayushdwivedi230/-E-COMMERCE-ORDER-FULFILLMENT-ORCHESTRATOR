import time
import agent_framework
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models.agent_log import AgentLog
from backend.app.orchestrator.pipeline import OrderFulfillmentOrchestrator

router = APIRouter(prefix="/api/agents", tags=["Agents"])
orchestrator = OrderFulfillmentOrchestrator()


def _format_agent_entry(agent, role: str) -> Dict[str, Any]:
    return {
        "name": agent.name,
        "id": agent.id,
        "description": agent.description,
        "role": role,
        "tools": [
            {
                "name": getattr(t, "name", getattr(t, "__name__", str(t))),
                "description": getattr(t, "description", getattr(t, "__doc__", "") or "").strip(),
            }
            for t in getattr(agent, "tools", [])
        ],
    }


@router.get("/info")
def get_agents_info():
    """Introspect all specialised agents and Microsoft Agent Framework metadata."""
    return {
        "framework": "Microsoft Agent Framework",
        "framework_version": getattr(agent_framework, "__version__", "1.26.0"),
        "agents": [
            _format_agent_entry(orchestrator.validation_agent, "Agent 1: Structural & Business Validation"),
            _format_agent_entry(orchestrator.inventory_agent, "Agent 2: Atomic Inventory Reservation & Stock Intelligence"),
            _format_agent_entry(orchestrator.fraud_agent, "Agent 3: Deterministic Risk Scoring & Contextual AI Analysis"),
            _format_agent_entry(orchestrator.pricing_agent, "Agent 4: Deterministic Financial Decimal Arithmetic"),
            _format_agent_entry(orchestrator.dispatch_coordinator, "Agent 5: Courier Simulation, Tracking Generation & Dispatch"),
        ],
        "extension_agents": [
            _format_agent_entry(orchestrator.notification_agent, "Agent 6: Multi-Channel Customer Notification Drafting"),
        ],
    }


@router.get("/telemetry")
def get_agents_telemetry(db: Session = Depends(get_db)):
    """Retrieve operational telemetry and metrics aggregated per agent from actual database logs."""
    agent_names = [
        "ValidationAgent",
        "InventoryAgent",
        "FraudCheckAgent",
        "PricingAgent",
        "DispatchCoordinator",
    ]

    telemetry = []
    for name in agent_names:
        total = db.query(AgentLog).filter(AgentLog.agent_name == name).count()
        successes = db.query(AgentLog).filter(AgentLog.agent_name == name, AgentLog.status == "SUCCESS").count()
        held_or_warn = db.query(AgentLog).filter(AgentLog.agent_name == name, AgentLog.status.in_(["HELD", "WARNING"])).count()
        failures = db.query(AgentLog).filter(AgentLog.agent_name == name, AgentLog.status == "FAILED").count()
        avg_lat = db.query(func.avg(AgentLog.execution_time_ms)).filter(AgentLog.agent_name == name).scalar()

        recent_logs = (
            db.query(AgentLog)
            .filter(AgentLog.agent_name == name)
            .order_by(AgentLog.created_at.desc())
            .limit(5)
            .all()
        )

        telemetry.append({
            "agent_name": name,
            "total_executions": total,
            "successful_executions": successes,
            "held_or_warning_executions": held_or_warn,
            "failed_executions": failures,
            "average_latency_ms": round(float(avg_lat or 0.0), 1),
            "status": "OPERATIONAL" if failures == 0 else "WARNING",
            "recent_events": [
                {
                    "order_id": l.order_id,
                    "action": l.action,
                    "status": l.status,
                    "message": l.output_data,
                    "execution_time_ms": l.execution_time_ms,
                    "timestamp": l.created_at.isoformat() if l.created_at else None,
                }
                for l in recent_logs
            ],
        })

    return {"agents": telemetry}
