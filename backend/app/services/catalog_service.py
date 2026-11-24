from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.models.product import Product
from backend.app.schemas.order_state import OrderItemState

PLACEHOLDER_PRODUCT_IDS = frozenset({"", "PENDING", "UNKNOWN", "PROD-UNKNOWN", "NONE", "NULL"})


def quantize_currency(amount: Decimal) -> Decimal:
    """Round decimal monetary amounts strictly to 2 decimal places (ROUND_HALF_UP)."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def resolve_product_by_sku(db: Session, sku: Optional[str]) -> Optional[Product]:
    """Look up an authoritative catalog Product by exact SKU."""
    if not sku or not isinstance(sku, str):
        return None
    normalized_sku = sku.strip()
    if not normalized_sku:
        return None
    return db.query(Product).filter(Product.sku == normalized_sku).first()


def validate_and_resolve_order_items(
    db: Session,
    items: List[OrderItemState],
) -> Dict[str, Any]:
    """
    Validate requested order items against the authoritative database catalog and
    overwrite any missing, placeholder, or mismatched metadata with real DB values.

    Enforces:
    - Non-empty item list and positive quantity (> 0)
    - Product exists in database (rejects with PRODUCT_NOT_FOUND otherwise)
    - Product is active
    - Authoritative Product.price > 0
    - Never retains PENDING, UNKNOWN, null, or fabricated product_id values
    """
    if not items or len(items) == 0:
        return {
            "valid": False,
            "errors": ["ORDER_EMPTY: Order must contain at least one item."],
            "warnings": [],
            "item_count": 0,
            "validated_items": [],
        }

    errors: List[str] = []
    warnings: List[str] = []
    validated_items: List[Dict[str, Any]] = []

    for item in items:
        if item.quantity <= 0:
            errors.append(
                f"INVALID_QUANTITY: Invalid quantity {item.quantity} for item '{item.sku}'. Must be > 0."
            )
            item.product_id = None
            item.unit_price = Decimal("0.00")
            item.total_price = Decimal("0.00")
            continue
        if item.quantity > 100:
            warnings.append(f"Unusually large quantity ({item.quantity}) for item '{item.sku}'.")

        product = resolve_product_by_sku(db, item.sku)
        if not product:
            item.product_id = None
            item.unit_price = Decimal("0.00")
            item.total_price = Decimal("0.00")
            errors.append(
                f"PRODUCT_NOT_FOUND: Product with SKU '{item.sku}' does not exist in catalog."
            )
            continue

        if not product.is_active:
            item.product_id = None
            item.unit_price = Decimal("0.00")
            item.total_price = Decimal("0.00")
            errors.append(
                f"PRODUCT_INACTIVE: Product with SKU '{item.sku}' is inactive and cannot be ordered."
            )
            continue

        if product.price is None or Decimal(str(product.price)) <= Decimal("0.00"):
            item.product_id = None
            item.unit_price = Decimal("0.00")
            item.total_price = Decimal("0.00")
            errors.append(
                f"INVALID_CATALOG_PRICE: Product with SKU '{item.sku}' has missing or invalid catalog price."
            )
            continue

        unit_price = quantize_currency(Decimal(str(product.price)))
        total_price = quantize_currency(unit_price * Decimal(str(item.quantity)))

        item.product_id = product.id
        item.sku = product.sku
        item.name = product.name
        item.unit_price = unit_price
        item.total_price = total_price

        validated_items.append({
            "sku": product.sku,
            "product_id": product.id,
            "name": product.name,
            "quantity": item.quantity,
            "unit_price": str(unit_price),
            "total_price": str(total_price),
        })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "item_count": len(items),
        "validated_items": validated_items,
    }
