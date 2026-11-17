from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.product import Product
from backend.app.schemas.product import ProductResponse

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.get("", response_model=List[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    """Retrieve all catalog products and live stock inventory."""
    return db.query(Product).order_by(Product.id.asc()).all()
