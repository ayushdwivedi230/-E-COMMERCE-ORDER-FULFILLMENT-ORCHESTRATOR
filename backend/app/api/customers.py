from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.customer import Customer
from backend.app.schemas.customer import CustomerResponse, CustomerHistoryStats
from backend.app.services.customer_memory import CustomerMemoryService

router = APIRouter(prefix="/api/customers", tags=["Customers"])


@router.get("", response_model=List[CustomerResponse])
def get_customers(db: Session = Depends(get_db)):
    """List all customers with attached prior-order customer memory statistics."""
    customers = db.query(Customer).order_by(Customer.id.asc()).all()
    results = []
    for c in customers:
        stats = CustomerMemoryService.get_customer_history(db, c.id)
        results.append(
            CustomerResponse(
                id=c.id,
                name=c.name,
                email=c.email,
                phone=c.phone,
                address=c.address,
                billing_address=c.billing_address,
                status=c.status,
                created_at=c.created_at,
                history_stats=stats,
            )
        )
    return results


@router.get("/{customer_id}/memory", response_model=CustomerHistoryStats)
def get_customer_memory(customer_id: str, db: Session = Depends(get_db)):
    """Retrieve prior-order memory, suspicion statistics, and risk tier for a customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerMemoryService.get_customer_history(db, customer_id)
