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


@router.get("/info")
def get_agents_info():
    """Introspect all five specialised agents and Microsoft Agent Framework metadata."""
    return {
        "framework": "Microsoft Agent Framework",
        "framework_version": getattr(agent_framework, "__version__", "1.26.0"),
        "agents": [
            {
                "name": orchestrator.validation_agent.name,
                "id": orchestrator.validation_agent.id,
                "description": orchestrator.validation_agent.description,
                "role": "Agent 1: Structural & Business Validation",
            },
            {
                "name": orchestrator.inventory_agent.name,
                "id": orchestrator.inventory_agent.id,
                "description": orchestrator.inventory_agent.description,
                "role": "Agent 2: Atomic Inventory Reservation & Stock Intelligence",
            },
            {
                "name": orchestrator.fraud_agent.name,
                "id": orchestrator.fraud_agent.id,
                "description": orchestrator.fraud_agent.description,
                "role": "Agent 3: Deterministic Risk Scoring & Contextual AI Analysis",
            },
            {
                "name": orchestrator.pricing_agent.name,
                "id": orchestrator.pricing_agent.id,
                "description": orchestrator.pricing_agent.description,
                "role": "Agent 4: Deterministic Financial Decimal Arithmetic",
            },
            {
                "name": orchestrator.dispatch_coordinator.name,
                "id": orchestrator.dispatch_coordinator.id,
                "description": orchestrator.dispatch_coordinator.description,
                "role": "Agent 5: Courier Simulation, Tracking Generation & Dispatch",
            },
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

    return {
        "framework": "Microsoft Agent Framework",
        "version": getattr(agent_framework, "__version__", "1.26.0"),
        "agents": telemetry,
    }
