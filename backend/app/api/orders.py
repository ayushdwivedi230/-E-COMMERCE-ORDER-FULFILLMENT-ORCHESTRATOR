import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.order import Order, OrderItem
from backend.app.models.agent_log import AgentLog
from backend.app.models.shipment import Shipment
from backend.app.models.fraud import FraudReview
from backend.app.schemas.order import ProcessOrderRequest, OrderSummaryResponse
from backend.app.schemas.order_state import OrderState, OrderItemState
from backend.app.orchestrator.pipeline import OrderFulfillmentOrchestrator

router = APIRouter(prefix="/api/orders", tags=["Orders"])
orchestrator = OrderFulfillmentOrchestrator()


@router.post("/process", response_model=OrderState)
def process_order(request: ProcessOrderRequest, db: Session = Depends(get_db)):
    """
    Primary endpoint: submits an order to the 5-Agent Multi-Agent Fulfillment Pipeline.
    Returns either a confirmed and dispatched order with tracking information,
    or a held order with the reason.
    """
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    # Build initial items state
    items_state: List[OrderItemState] = [
        OrderItemState(
            product_id="PENDING",
            sku=item.sku,
            name=item.sku,
            quantity=item.quantity,
        )
        for item in request.items
    ]

    order_state = OrderState(
        order_id=order_id,
        customer_id=request.customer_id,
        items=items_state,
        shipping_address=request.shipping_address,
        payment_information=request.payment_information,
        coupon_code=request.coupon_code,
    )

    # Execute orchestrator pipeline
    final_state = orchestrator.process_order_pipeline(
        order_state=order_state,
        db=db,
        simulated_failed_attempts=request.simulate_recent_failed_attempts or 0,
    )
    return final_state


@router.get("", response_model=List[OrderSummaryResponse])
def get_orders(db: Session = Depends(get_db)):
    """List all orders in the system with their status and totals."""
    return db.query(Order).order_by(Order.created_at.desc()).all()


@router.get("/queue/held")
def get_held_orders(db: Session = Depends(get_db)):
    """Retrieve orders currently held in the escalation review queue."""
    held_orders = db.query(Order).filter(Order.status == "HELD").order_by(Order.created_at.desc()).all()
    results = []
    for o in held_orders:
        reviews = db.query(FraudReview).filter(FraudReview.order_id == o.id).all()
        results.append({
            "order_id": o.id,
            "customer_id": o.customer_id,
            "status": o.status,
            "hold_reason": o.hold_reason,
            "fraud_score": float(o.fraud_score or 0.0),
            "created_at": o.created_at,
            "fraud_reviews": [
                {
                    "fraud_score": float(r.fraud_score),
                    "risk_level": r.risk_level,
                    "reasons": r.reasons,
                    "ai_explanation": r.ai_explanation,
                    "decision": r.decision,
                }
                for r in reviews
            ],
        })
    return results


@router.get("/{order_id}")
def get_order_details(order_id: str, db: Session = Depends(get_db)):
    """Retrieve full order details, items, agent execution logs, and shipment info."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    logs = db.query(AgentLog).filter(AgentLog.order_id == order_id).order_by(AgentLog.created_at.asc()).all()
    shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
    reviews = db.query(FraudReview).filter(FraudReview.order_id == order_id).all()

    return {
        "order_id": order.id,
        "customer_id": order.customer_id,
        "status": order.status,
        "shipping_address": order.shipping_address,
        "billing_address": order.billing_address,
        "payment_method": order.payment_method,
        "subtotal": float(order.subtotal or 0.0),
        "discount_amount": float(order.discount_amount or 0.0),
        "tax_amount": float(order.tax_amount or 0.0),
        "shipping_cost": float(order.shipping_cost or 0.0),
        "total_amount": float(order.total_amount or 0.0),
        "fraud_score": float(order.fraud_score or 0.0),
        "hold_reason": order.hold_reason,
        "tracking_id": order.tracking_id,
        "created_at": order.created_at,
        "items": [
            {
                "sku": i.sku,
                "name": i.product_name,
                "quantity": i.quantity,
                "unit_price": float(i.unit_price),
                "total_price": float(i.total_price),
            }
            for i in items
        ],
        "agent_logs": [
            {
                "agent_name": l.agent_name,
                "action": l.action,
                "status": l.status,
                "message": l.output_data,
                "details": l.input_data,
                "execution_time_ms": l.execution_time_ms,
                "created_at": l.created_at,
            }
            for l in logs
        ],
        "shipment": (
            {
                "tracking_id": shipment.tracking_id,
                "carrier": shipment.carrier,
                "shipping_method": shipment.shipping_method,
                "status": shipment.status,
                "estimated_delivery": shipment.estimated_delivery,
                "dispatch_notes": shipment.dispatch_notes,
            }
            if shipment
            else None
        ),
        "fraud_reviews": [
            {
                "fraud_score": float(r.fraud_score),
                "risk_level": r.risk_level,
                "reasons": r.reasons,
                "ai_explanation": r.ai_explanation,
                "decision": r.decision,
            }
            for r in reviews
        ],
    }


@router.post("/{order_id}/override-hold")
def override_held_order(order_id: str, auditor_notes: str = "Auditor manual verification passed", db: Session = Depends(get_db)):
    """Human auditor overrides a held order and resumes fulfillment through pricing and dispatch."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "HELD":
        raise HTTPException(status_code=400, detail=f"Order is not in HELD status (current: {order.status})")

    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    items_state = [
        OrderItemState(
            product_id=i.product_id,
            sku=i.sku,
            name=i.product_name,
            quantity=i.quantity,
            unit_price=i.unit_price,
            total_price=i.total_price,
        )
        for i in items
    ]

    order_state = OrderState(
        order_id=order.id,
        customer_id=order.customer_id,
        items=items_state,
        shipping_address={"street": order.shipping_address, "city": "City", "state": "State", "postal_code": "00000", "country": "USA"},
        payment_information={"payment_method": order.payment_method, "payment_status": "AUTHORIZED"},
        validation_status="PASSED",
        inventory_status="RESERVED",
        fraud_status="OVERRIDDEN_BY_AUDITOR",
    )

    # Run remaining stages: Pricing & Dispatch
    orchestrator.pricing_agent.calculate_pricing(order_state, db)
    orchestrator.dispatch_coordinator.coordinate_dispatch(order_state, db)
    orchestrator._finalize_dispatched_order(order_state, db, order)

    return {"message": "Order successfully released from hold and dispatched.", "order_state": order_state}
