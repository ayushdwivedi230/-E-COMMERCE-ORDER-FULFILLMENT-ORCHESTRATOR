from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    price: Decimal = Field(gt=Decimal("0.00"))
    stock_quantity: int = Field(ge=0)
    substitute_sku: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True


class ProductCreate(ProductBase):
    id: str


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
