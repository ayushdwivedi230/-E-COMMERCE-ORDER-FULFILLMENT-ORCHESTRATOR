import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseOrchestratorAgent
from backend.app.schemas.order_state import OrderState
from backend.app.agents.tools import (
    validate_customer_standing,
    validate_catalog_and_quantities,
    validate_shipping_and_payment,
)


class ValidationAgent(BaseOrchestratorAgent):
    """
    Agent 1: Validation Agent
    Validates:
    - Product existence & quantity boundaries
    - Address completeness (street, city, state, postal_code, country)
    - Payment presence and status
    - Required customer information

    Microsoft Agent Framework Integration:
    Calls 3 plain Python tools decorated with @tool:
      1. validate_customer_standing
      2. validate_catalog_and_quantities
      3. validate_shipping_and_payment
    """

    def __init__(self) -> None:
        tools = [
            validate_customer_standing,
            validate_catalog_and_quantities,
            validate_shipping_and_payment,
        ]
        super().__init__(
            name="ValidationAgent",
            description="Validates incoming order integrity, customer standing, catalog SKUs, and payment authorization.",
            agent_id="agt-validation-001",
            tools=tools,
        )

    def validate_order(self, order_state: OrderState, db: Session) -> bool:
        start_time = time.time()
        validation_errors: List[str] = []
        validation_warnings: List[str] = []

        # TOOL 1: Validate Customer Standing
        t1_start = time.time()
        cust_res = validate_customer_standing(db, order_state.customer_id)
        if not cust_res["valid"]:
            validation_errors.extend(cust_res["errors"])
        else:
            order_state.customer_name = cust_res.get("name")
            order_state.customer_email = cust_res.get("email")
            order_state.customer_phone = cust_res.get("phone")
            validation_warnings.extend(cust_res.get("warnings", []))

        self.record_tool_call(
            order_state=order_state,
            tool_name="validate_customer_standing",
            action="CustomerValidation",
            status="SUCCESS" if cust_res["valid"] else "FAILED",
            message=f"Customer standing check {'passed' if cust_res['valid'] else 'failed'} for {order_state.customer_id}.",
            start_time=t1_start,
            details=cust_res,
        )

        # TOOL 2: Validate Catalog SKUs and Quantities
        t2_start = time.time()
        cat_res = validate_catalog_and_quantities(db, order_state.items)
        if not cat_res["valid"]:
            validation_errors.extend(cat_res["errors"])
        validation_warnings.extend(cat_res.get("warnings", []))

        self.record_tool_call(
            order_state=order_state,
            tool_name="validate_catalog_and_quantities",
            action="CatalogValidation",
            status="SUCCESS" if cat_res["valid"] else "FAILED",
            message=f"Catalog SKU check {'passed' if cat_res['valid'] else 'failed'} with {len(order_state.items)} line item(s).",
            start_time=t2_start,
            details=cat_res,
        )

        # TOOL 3: Validate Shipping Address & Payment Authorization
        t3_start = time.time()
        pay_res = validate_shipping_and_payment(
            order_state.shipping_address,
            order_state.payment_information,
        )
        if not pay_res["valid"]:
            validation_errors.extend(pay_res["errors"])
        validation_warnings.extend(pay_res.get("warnings", []))

        self.record_tool_call(
            order_state=order_state,
            tool_name="validate_shipping_and_payment",
            action="AddressPaymentValidation",
            status="SUCCESS" if pay_res["valid"] else "FAILED",
            message=f"Address and payment authorization check {'passed' if pay_res['valid'] else 'failed'}.",
            start_time=t3_start,
            details=pay_res,
        )

        # Aggregate Result
        if validation_errors:
            order_state.validation_status = "FAILED"
            order_state.hold_reason = f"Validation Failed: {'; '.join(validation_errors)}"
            self.record_agent_log(
                order_state,
                action="OrderValidationSummary",
                status="FAILED",
                message=f"Order validation rejected with {len(validation_errors)} error(s).",
                start_time=start_time,
                details={"errors": validation_errors, "warnings": validation_warnings},
            )
            return False

        order_state.validation_status = "PASSED"
        self.record_agent_log(
            order_state,
            action="OrderValidationSummary",
            status="SUCCESS",
            message=f"Order validation passed successfully with {len(order_state.items)} item(s).",
            start_time=start_time,
            details={"warnings": validation_warnings, "item_count": len(order_state.items)},
        )
        return True
