import uuid
import datetime
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.models.product import Product
from backend.app.models.inventory import InventoryReservation
from backend.app.schemas.order_state import (
    OrderItemState,
    SubstituteRecommendation,
    BackorderProposal,
)


class InventoryService:
    """
    Handles atomic stock reservation, verification, and replenishment options.
    Guarantees isolation through explicit row locking (with_for_update) or transactional safety.
    """

    @staticmethod
    def verify_and_reserve_stock(
        db: Session,
        order_id: str,
        items: List[OrderItemState],
        reservation_timeout_minutes: int = 15,
    ) -> Tuple[bool, List[SubstituteRecommendation], List[BackorderProposal], str]:
        """
        Verify stock for all items atomically.
        If all items are in stock, create inventory reservations and deduct available stock atomically.
        If any item has insufficient stock, DO NOT commit deductions.
        Instead, detect substitutes or generate backorder proposals.
        Returns:
            (success: bool, substitutes: List, backorders: List, message: str)
        """
        substitutes: List[SubstituteRecommendation] = []
        backorders: List[BackorderProposal] = []
        insufficient_items: List[str] = []

        # Begin transaction inspection
        try:
            with db.begin_nested():
                # 1. First pass: verify availability of all items
                for item in items:
                    # Select with lock if supported, otherwise standard select
                    product: Optional[Product] = (
                        db.query(Product)
                        .filter(Product.sku == item.sku)
                        .with_for_update(nowait=False)
                        .first()
                        if db.bind.dialect.name == "postgresql"
                        else db.query(Product).filter(Product.sku == item.sku).first()
                    )

                    if not product:
                        insufficient_items.append(f"SKU {item.sku} does not exist.")
                        continue

                    if product.stock_quantity < item.quantity:
                        insufficient_items.append(
                            f"SKU {item.sku} ({product.name}) has insufficient stock. Requested: {item.quantity}, Available: {product.stock_quantity}"
                        )
                        # Backorder proposal
                        backorders.append(
                            BackorderProposal(
                                sku=product.sku,
                                product_name=product.name,
                                requested_quantity=item.quantity,
                                available_quantity=product.stock_quantity,
                                estimated_restock_days=7,
                            )
                        )
                        # Substitute recommendation (never silently substituted)
                        if product.substitute_sku:
                            sub_prod = db.query(Product).filter(Product.sku == product.substitute_sku).first()
                            if sub_prod and sub_prod.stock_quantity >= item.quantity:
                                substitutes.append(
                                    SubstituteRecommendation(
                                        original_sku=product.sku,
                                        substitute_sku=sub_prod.sku,
                                        substitute_name=sub_prod.name,
                                        substitute_price=sub_prod.price,
                                        reason=f"Recommended substitute for out-of-stock {product.name}. Customer approval required.",
                                    )
                                )

                # If any item failed stock check, abort reservation
                if insufficient_items:
                    return (
                        False,
                        substitutes,
                        backorders,
                        f"Stock verification failed: {'; '.join(insufficient_items)}",
                    )

                # 2. Second pass: All items available, commit atomic reservations
                expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=reservation_timeout_minutes)
                for item in items:
                    product = db.query(Product).filter(Product.sku == item.sku).first()
                    product.stock_quantity -= item.quantity

                    reservation = InventoryReservation(
                        id=f"RES-{uuid.uuid4().hex[:8].upper()}",
                        order_id=order_id,
                        product_id=product.id,
                        quantity_reserved=item.quantity,
                        status="RESERVED",
                        expires_at=expires_at,
                    )
                    db.add(reservation)

                db.commit()
                return True, [], [], "All inventory items verified and atomically reserved."

        except Exception as e:
            db.rollback()
            return False, [], [], f"Inventory transaction error: {str(e)}"

    @staticmethod
    def release_reservations(db: Session, order_id: str) -> None:
        """Release reserved inventory back to available stock if order is cancelled or held indefinitely."""
        reservations = (
            db.query(InventoryReservation)
            .filter(InventoryReservation.order_id == order_id, InventoryReservation.status == "RESERVED")
            .all()
        )
        for res in reservations:
            product = db.query(Product).filter(Product.id == res.product_id).first()
            if product:
                product.stock_quantity += res.quantity_reserved
            res.status = "RELEASED"
        db.commit()

    @staticmethod
    def commit_reservations(db: Session, order_id: str) -> None:
        """Commit reserved inventory permanently on successful dispatch."""
        reservations = (
            db.query(InventoryReservation)
            .filter(InventoryReservation.order_id == order_id, InventoryReservation.status == "RESERVED")
            .all()
        )
        for res in reservations:
            res.status = "COMMITTED"
        db.commit()
