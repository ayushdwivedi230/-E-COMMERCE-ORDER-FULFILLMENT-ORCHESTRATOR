from typing import List, Dict, Any
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database import get_db
from backend.app.models.order import Order
from backend.app.models.fraud import FraudReview
from backend.app.models.agent_log import AgentLog

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard Analytics"])


@router.get("/analytics")
def get_dashboard_analytics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Computes real-time SaaS dashboard metrics and analytics directly from the database.
    Never uses fake or hardcoded stats.
    """
    # 1. Order Status Counts
    total_orders = db.query(Order).count()
    completed_orders = db.query(Order).filter(Order.status == "DISPATCHED").count()
    held_orders = db.query(Order).filter(Order.status == "HELD").count()
    pending_orders = db.query(Order).filter(Order.status.in_(["PENDING", "PROCESSING"])).count()

    # 2. Revenue Calculations (Dispatched Orders)
    revenue_query = db.query(func.sum(Order.total_amount)).filter(Order.status == "DISPATCHED").scalar()
    total_revenue = float(revenue_query or 0.0)
    avg_order_value = (
        round(total_revenue / completed_orders, 2)
        if completed_orders > 0
        else 0.0
    )

    # 3. Fraud Statistics
    total_reviews = db.query(FraudReview).count()
    high_risk_count = db.query(FraudReview).filter(FraudReview.risk_level == "HIGH").count()
    medium_risk_count = db.query(FraudReview).filter(FraudReview.risk_level == "MEDIUM").count()
    low_risk_count = db.query(FraudReview).filter(FraudReview.risk_level == "LOW").count()
    avg_score_query = db.query(func.avg(FraudReview.fraud_score)).scalar()
    avg_fraud_score = round(float(avg_score_query or 0.0), 1)

    # 4. Recent Agent Activity Log Stream
    recent_logs = (
        db.query(AgentLog)
        .order_by(AgentLog.created_at.desc())
        .limit(10)
        .all()
    )
    activity_stream = [
        {
            "id": l.id,
            "order_id": l.order_id,
            "agent_name": l.agent_name,
            "action": l.action,
            "status": l.status,
            "message": l.output_data,
            "execution_time_ms": l.execution_time_ms,
            "timestamp": l.created_at.isoformat() if l.created_at else None,
        }
        for l in recent_logs
    ]

    # 5. Order Status Distribution for Donut Chart
    status_distribution = [
        {"name": "Dispatched", "value": completed_orders, "color": "#10b981"},
        {"name": "Held (Escalated)", "value": held_orders, "color": "#f43f5e"},
        {"name": "Processing", "value": pending_orders, "color": "#6366f1"},
    ]

    # 6. Risk Distribution for Bar Chart
    risk_distribution = [
        {"tier": "Low Risk (0-29)", "count": low_risk_count, "color": "#10b981"},
        {"tier": "Medium Risk (30-69)", "count": medium_risk_count, "color": "#f59e0b"},
        {"tier": "High Risk (70-100)", "count": high_risk_count, "color": "#ef4444"},
    ]

    return {
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "held_orders": held_orders,
        "pending_orders": pending_orders,
        "total_revenue": total_revenue,
        "average_order_value": avg_order_value,
        "fraud_stats": {
            "total_evaluated": total_reviews,
            "high_risk_count": high_risk_count,
            "medium_risk_count": medium_risk_count,
            "low_risk_count": low_risk_count,
            "average_fraud_score": avg_fraud_score,
            "escalation_rate": (
                round((high_risk_count / total_reviews) * 100, 1)
                if total_reviews > 0
                else 0.0
            ),
        },
        "status_distribution": status_distribution,
        "risk_distribution": risk_distribution,
        "recent_activity": activity_stream,
    }
