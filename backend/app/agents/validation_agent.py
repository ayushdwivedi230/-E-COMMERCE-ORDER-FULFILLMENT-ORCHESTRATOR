import time
import re
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseOrchestratorAgent
from backend.app.schemas.order_state import OrderState
from backend.app.models.customer import Customer
from backend.app.models.product import Product


class ValidationAgent(BaseOrchestratorAgent):
    """
    Agent 1: Validation Agent
    Validates:
    - Product existence
    - Product quantities (positive integer, reasonable bounds)
    - Address completeness (street, city, state, postal_code, country)
    - Payment presence and status
    - Required customer information
    """

    def __init__(self) -> None:
        super().__init__(
            name="ValidationAgent",
            description="Validates incoming order integrity, customer status, item catalogs, and payment details.",
            agent_id="agt-validation-001",
        )

    def validate_order(self, order_state: OrderState, db: Session) -> bool:
        start_time = time.time()
        validation_errors: List[str] = []
        validation_warnings: List[str] = []

        # 1. Required Customer Information
        if not order_state.customer_id:
            validation_errors.append("Customer ID is missing.")
        else:
            customer = db.query(Customer).filter(Customer.id == order_state.customer_id).first()
            if not customer:
                validation_errors.append(f"Customer with ID '{order_state.customer_id}' does not exist.")
            elif customer.status == "BLOCKED":
                validation_errors.append(f"Customer '{customer.name}' account is BLOCKED.")
            else:
                order_state.customer_name = customer.name
                order_state.customer_email = customer.email
                order_state.customer_phone = customer.phone

                if customer.status == "FLAGGED":
                    validation_warnings.append(f"Customer '{customer.name}' has prior FLAGGED standing.")

        # 2. Product Existence & Quantity
        if not order_state.items or len(order_state.items) == 0:
            validation_errors.append("Order must contain at least one item.")
        else:
            for item in order_state.items:
                if item.quantity <= 0:
                    validation_errors.append(f"Invalid quantity {item.quantity} for item '{item.sku}'. Must be > 0.")
                elif item.quantity > 100:
                    validation_warnings.append(f"Unusually large quantity ({item.quantity}) for item '{item.sku}'.")

                product = db.query(Product).filter(Product.sku == item.sku).first()
                if not product:
                    validation_errors.append(f"Product with SKU '{item.sku}' does not exist in catalog.")
                else:
                    item.product_id = product.id
                    item.name = product.name
                    item.unit_price = product.price
                    item.total_price = product.price * item.quantity

        # 3. Address Completeness
        addr = order_state.shipping_address
        if not addr:
            validation_errors.append("Shipping address is missing.")
        else:
            if not addr.street or not addr.street.strip():
                validation_errors.append("Shipping address street is missing or empty.")
            if not addr.city or not addr.city.strip():
                validation_errors.append("Shipping address city is missing or empty.")
            if not addr.state or not addr.state.strip():
                validation_errors.append("Shipping address state is missing or empty.")
            if not addr.postal_code or not addr.postal_code.strip():
                validation_errors.append("Shipping address postal code is missing or empty.")
            elif not re.match(r"^\d{5}(-\d{4})?$", addr.postal_code.strip()):
                validation_warnings.append(f"Postal code '{addr.postal_code}' does not match standard US format.")

        # 4. Payment Presence & Status
        pay = order_state.payment_information
        if not pay:
            validation_errors.append("Payment information is missing.")
        else:
            if not pay.payment_method:
                validation_errors.append("Payment method is not specified.")
            if pay.payment_status == "FAILED":
                validation_errors.append("Payment status is FAILED; cannot proceed.")
            if not pay.transaction_token:
                validation_errors.append("Payment authorization token is missing.")

        # Determine outcome
        if validation_errors:
            order_state.validation_status = "FAILED"
            order_state.hold_reason = f"Validation Failed: {'; '.join(validation_errors)}"
            self.record_agent_log(
                order_state,
                action="OrderValidation",
                status="FAILED",
                message=f"Order validation rejected with {len(validation_errors)} error(s).",
                start_time=start_time,
                details={"errors": validation_errors, "warnings": validation_warnings},
            )
            return False

        order_state.validation_status = "PASSED"
        self.record_agent_log(
            order_state,
            action="OrderValidation",
            status="SUCCESS",
            message=f"Order validation passed successfully with {len(order_state.items)} item(s).",
            start_time=start_time,
            details={"warnings": validation_warnings, "item_count": len(order_state.items)},
        )
        return True
