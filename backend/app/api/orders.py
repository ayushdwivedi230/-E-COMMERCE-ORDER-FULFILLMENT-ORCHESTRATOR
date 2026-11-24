import uuid
import asyncio
from decimal import Decimal
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.order import Order, OrderItem
from backend.app.models.product import Product
from backend.app.models.agent_log import AgentLog
from backend.app.models.shipment import Shipment
from backend.app.models.fraud import FraudReview
from backend.app.schemas.order import ProcessOrderRequest, OrderSummaryResponse
from backend.app.schemas.order_state import OrderState, OrderItemState
from backend.app.orchestrator.pipeline import OrderFulfillmentOrchestrator
from backend.app.services.inventory_service import InventoryService
from backend.app.services.catalog_service import resolve_product_by_sku, quantize_currency
from backend.app.api.websocket import ws_manager

router = APIRouter(prefix="/api/orders", tags=["Orders"])
orchestrator = OrderFulfillmentOrchestrator()


async def broadcast_order_event(event_type: str, payload: dict):
    """Helper to broadcast WebSocket events asynchronously."""
    try:
        await ws_manager.broadcast(event_type, payload)
    except Exception as e:
        pass


@router.post("/process", response_model=OrderState)
def process_order(
    request: ProcessOrderRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Primary endpoint: submits an order to the 5-Agent Multi-Agent Fulfillment Pipeline.
    Returns either a confirmed and dispatched order with tracking information,
    or a held order with the reason.
    """
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    # Build initial items state from authoritative catalog (never fabricate PENDING or placeholder IDs)
    items_state: List[OrderItemState] = []
    for item in request.items:
        prod = resolve_product_by_sku(db, item.sku)
        if prod and prod.is_active and prod.price is not None and Decimal(str(prod.price)) > Decimal("0.00"):
            unit_price = quantize_currency(Decimal(str(prod.price)))
            total_price = quantize_currency(unit_price * Decimal(str(item.quantity)))
            items_state.append(
                OrderItemState(
                    product_id=prod.id,
                    sku=prod.sku,
                    name=prod.name,
                    quantity=item.quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                )
            )
        else:
            items_state.append(
                OrderItemState(
                    product_id=None,
                    sku=item.sku,
                    name=item.sku,
                    quantity=item.quantity,
                    unit_price=Decimal("0.00"),
                    total_price=Decimal("0.00"),
                )
            )

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

    # Broadcast event via WebSocket
    background_tasks.add_task(
        broadcast_order_event,
        "ORDER_PROCESSED",
        final_state.model_dump(mode="json"),
    )

    return final_state


@router.get("", response_model=List[OrderSummaryResponse])
def get_orders(db: Session = Depends(get_db)):
    """List all orders in the system with their status and totals."""
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    results = []
    for o in orders:
        c_name = o.customer.name if o.customer else None
        i_count = sum(item.quantity for item in o.items) if o.items else 0
        results.append(
            OrderSummaryResponse(
                order_id=o.id,
                customer_id=o.customer_id,
                customer_name=c_name,
                item_count=i_count,
                status=o.status,
                final_amount=o.total_amount or 0.0,
                fraud_score=float(o.fraud_score or 0.0),
                hold_reason=o.hold_reason,
                tracking_id=o.tracking_id,
                created_at=o.created_at,
            )
        )
    return results


@router.get("/queue/held")
def get_held_orders(db: Session = Depends(get_db)):
    """Retrieve orders currently held in the escalation review queue with full customer and fraud audit data."""
    held_orders = db.query(Order).filter(Order.status == "HELD").order_by(Order.created_at.desc()).all()
    results = []
    for o in held_orders:
        reviews = db.query(FraudReview).filter(FraudReview.order_id == o.id).all()
        items = db.query(OrderItem).filter(OrderItem.order_id == o.id).all()
        c = o.customer
        results.append({
            "order_id": o.id,
            "customer_id": o.customer_id,
            "customer_name": c.name if c else "Unknown Customer",
            "customer_email": c.email if c else None,
            "shipping_address": o.shipping_address,
            "total_amount": float(o.total_amount or 0.0),
            "status": o.status,
            "hold_reason": o.hold_reason,
            "fraud_score": float(o.fraud_score or 0.0),
            "created_at": o.created_at,
            "items": [
                {
                    "sku": item.sku,
                    "name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "total_price": float(item.total_price),
                }
                for item in items
            ],
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
        "notification_draft": (
            {
                "channel": "EMAIL_AND_SMS",
                "recipient_email": order.customer.email if order.customer else "customer@example.com",
                "subject": f"Order Update: {order.id} ({order.status})",
                "body": (
                    f"Dear {order.customer.name if order.customer else 'Valued Customer'},\n\n"
                    f"Your order {order.id} is {order.status}."
                    + (f" Carrier: {shipment.carrier}, Tracking: {order.tracking_id}." if order.tracking_id else f" Notice: {order.hold_reason or 'Order currently held for processing.'}")
                ),
                "sms_summary": f"Order {order.id} is {order.status}." + (f" Tracking: {order.tracking_id}" if order.tracking_id else ""),
                "status": "DRAFTED",
                "intent": "CONFIRMED" if order.status == "DISPATCHED" else ("HELD_FRAUD" if (order.fraud_score or 0) >= 70 else "HELD_GENERAL"),
            }
        ),
    }


@router.get("/runs/logs")
def get_execution_run_logs(limit: int = 50):
    """Retrieve recent append-only execution log records."""
    from backend.app.services.run_logger import AppendOnlyRunLogger
    return AppendOnlyRunLogger.read_recent_runs(limit=limit)


@router.post("/{order_id}/override-hold")
def override_held_order(
    order_id: str,
    background_tasks: BackgroundTasks,
    auditor_notes: str = "Auditor manual verification passed",
    db: Session = Depends(get_db),
):
    """Human auditor overrides a held order and resumes fulfillment through pricing and dispatch."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "HELD":
        raise HTTPException(status_code=400, detail=f"Order is not in HELD status (current: {order.status})")

    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    items_state = []
    for i in items:
        prod = resolve_product_by_sku(db, i.sku)
        resolved_id = i.product_id if i.product_id and i.product_id not in ("PENDING", "UNKNOWN") else (prod.id if prod else None)
        if not resolved_id:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot override order {order_id}: item '{i.sku}' has no valid catalog product reference.",
            )
        unit_price = quantize_currency(Decimal(str(prod.price))) if prod and prod.price else quantize_currency(Decimal(str(i.unit_price)))
        total_price = quantize_currency(unit_price * Decimal(str(i.quantity)))
        items_state.append(
            OrderItemState(
                product_id=resolved_id,
                sku=i.sku,
                name=i.product_name,
                quantity=i.quantity,
                unit_price=unit_price,
                total_price=total_price,
            )
        )

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

    # Broadcast update
    background_tasks.add_task(
        broadcast_order_event,
        "ORDER_OVERRIDDEN",
        {"order_id": order.id, "status": "DISPATCHED", "tracking_id": order_state.tracking_id},
    )

    return {"message": "Order successfully released from hold and dispatched.", "order_state": order_state}


@router.post("/{order_id}/reject")
def reject_held_order(
    order_id: str,
    background_tasks: BackgroundTasks,
    rejection_reason: str = "Rejected by compliance auditor due to fraudulent pattern",
    db: Session = Depends(get_db),
):
    """Human auditor rejects a held order permanently, marks it CANCELLED, and releases any inventory."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = "REJECTED_FRAUD"
    order.hold_reason = f"Auditor Rejection: {rejection_reason}"

    # Release any reservations
    InventoryService.release_reservations(db, order_id)

    # Update fraud review decision
    review = db.query(FraudReview).filter(FraudReview.order_id == order_id).first()
    if review:
        review.decision = "REJECTED_AUDITOR"

    db.commit()

    # Broadcast update
    background_tasks.add_task(
        broadcast_order_event,
        "ORDER_REJECTED",
        {"order_id": order.id, "status": "REJECTED_FRAUD", "reason": rejection_reason},
    )

    return {"message": f"Order {order_id} rejected and cancelled.", "status": "REJECTED_FRAUD"}
