import time
import agent_framework
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
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
