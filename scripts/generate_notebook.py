"""
Script to generate and execute the CSE476 Multi-Agent Fulfillment Orchestrator Demo Notebook
Generates notebooks/demo_orchestrator.ipynb and demo_orchestrator.ipynb conforming to nbformat v4.
"""

import os
import json

def create_markdown_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in source.strip().split("\n")]
    }

def create_code_cell(source: str, outputs=None) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": outputs or [],
        "source": [line + "\n" for line in source.strip().split("\n")]
    }

def build_notebook():
    cells = []

    # Title & Introduction
    cells.append(create_markdown_cell("""
# CSE476 Agentic AI and Intelligent Automation — Group 11
## E-Commerce Order Fulfillment Multi-Agent Orchestrator
**Group Members:** Ayush Dwivedi & Tushar  
**Framework:** Microsoft Agent Framework (`agent-framework-core` v1.26.0)  
**Architecture:** Sequential Pipeline with Fraud-Escalation Route  
**Memory:** Shared `OrderState` & Prior-Order Customer Historical Memory  
**Primary Deliverables:** Dispatched Order with Carrier Tracking ID, OR Escalated Hold with Reason
"""))

    cells.append(create_markdown_cell("""
### 1. Architectural Pipeline & Specialised Agents
The fulfillment pipeline coordinates **five specialised agents** (plus a multi-channel **Notification Agent** extension):
1. **Validation Agent**: Customer standing, product existence, positive quantity bounds, address completeness, and payment authorization.
2. **Inventory Agent**: Real-time stock verification, atomic database reservations, shortage detection, substitute SKU proposals, and backorder proposals.
3. **Fraud Check Agent**: Deterministic 0-100 risk scoring evaluating prior dispute memory, retry velocity, order value anomalies, and shipping/billing mismatches.
4. **Pricing Agent**: Deterministic financial decimal arithmetic for subtotals, volume discounts (>=5 units), coupon codes, regional tax (8%), and dynamic shipping.
5. **Dispatch Coordinator**: Carrier selection (FedEx, UPS, USPS, DHL), unique tracking ID generation (`TRK-XXX-XXXX`), shipment persistence, and inventory commitment.
6. **Notification Agent**: Previews multi-channel customer communications across Confirmed, Substituted, and Held outcomes.

Every agent calls at least **TWO plain Python functions decorated with `@tool`** from Microsoft Agent Framework.
"""))

    # Cell 1: Imports and Setup
    cells.append(create_code_cell(r"""
import os
import sys
import json
from decimal import Decimal

# Set workspace root
sys.path.insert(0, os.path.abspath("."))

from backend.app.database import init_db, SessionLocal
from backend.app.services.seed_data import seed_database
from backend.app.services.customer_memory import CustomerMemoryService
from backend.app.services.run_logger import AppendOnlyRunLogger
from backend.app.orchestrator.pipeline import OrderFulfillmentOrchestrator
from backend.app.schemas.order_state import OrderState, OrderItemState, AddressState, PaymentState
from backend.app.models.order import Order, OrderItem
from backend.app.models.shipment import Shipment
from backend.app.models.fraud import FraudReview
from backend.app.models.agent_log import AgentLog
from backend.app.models.inventory import InventoryReservation

print("[OK] Microsoft Agent Framework and Orchestrator modules successfully imported.")
"""))

    # Cell 2: Database Initialization & Clean Seed
    cells.append(create_code_cell(r"""
# Initialize SQLite database and seed initial test customers & catalog
init_db()
db = SessionLocal()
seed_database(db)

# Clean up previous demonstration orders for idempotent reruns
for tbl in [Shipment, FraudReview, AgentLog, InventoryReservation, OrderItem]:
    db.query(tbl).filter(tbl.order_id.like("ORD-NB-%")).delete()
db.query(Order).filter(Order.id.like("ORD-NB-%")).delete()
db.commit()

orchestrator = OrderFulfillmentOrchestrator()
print("[OK] Database initialized and clean demonstration workspace prepared.")
"""))

    # Helper function for pretty printing traces
    cells.append(create_code_cell(r"""
def display_execution_summary(order_state: OrderState):
    print("=" * 80)
    print(f"  ORDER EXECUTION SUMMARY: {order_state.order_id}")
    print("=" * 80)
    print(f"Customer ID:     {order_state.customer_id} ({order_state.customer_name})")
    print(f"Final Status:    {order_state.dispatch_status}")
    print(f"Validation:      {order_state.validation_status}")
    print(f"Inventory:       {order_state.inventory_status}")
    print(f"Fraud Status:    {order_state.fraud_status} (Score: {order_state.fraud_score}/100)")
    print(f"Pricing Status:  {order_state.pricing_status} (Final Amount: ${order_state.final_amount})")
    if order_state.tracking_id:
        print(f"Carrier Logistics: {order_state.carrier} ({order_state.shipping_method})")
        print(f"Tracking ID:     {order_state.tracking_id}")
    if order_state.hold_reason:
        print(f"Hold Reason:     {order_state.hold_reason}")
        
    print("")
    print("--- 5-AGENT PIPELINE EXECUTION TRACE ---")
    for log in order_state.agent_execution_logs:
        status_tag = "PASS" if log.status in ["SUCCESS", "PASSED"] else log.status
        print(f"  [{log.agent_name:<20}] {log.action:<26} -> {status_tag:<7} ({log.execution_time_ms:>2}ms): {log.message}")
        
    print("")
    print("--- MICROSOFT AGENT FRAMEWORK TOOL CALLS (Granular) ---")
    for tool_log in order_state.tool_execution_logs:
        print(f"  [@tool {tool_log.tool_name:<30}] -> {tool_log.status:<7} ({tool_log.execution_time_ms:>2}ms): {tool_log.message}")
"""))

    # Scenario 1: Clean Dispatched Order
    cells.append(create_markdown_cell("""
### 2. Scenario 1: Clean Order with Successful Dispatch
A verified repeat customer (`CUST-001`) with complete address, valid payment token, and standard coupon `WELCOME10`.
- All 5 agents complete successfully.
- Final result: **Confirmed order + final amount + shipping carrier + tracking ID**.
"""))

    cells.append(create_code_cell(r"""
state1 = OrderState(
    order_id="ORD-NB-01",
    customer_id="CUST-001",
    items=[OrderItemState(product_id="PROD-001", sku="KB-MECH-RGB", name="Pro Mechanical Keyboard", quantity=1)],
    shipping_address=AddressState(
        street="742 Evergreen Terrace",
        city="Springfield",
        state="OR",
        postal_code="97477",
        country="USA"
    ),
    payment_information=PaymentState(
        payment_method="CREDIT_CARD",
        payment_status="AUTHORIZED",
        transaction_token="tok_valid_live"
    ),
    coupon_code="WELCOME10",
)

res1 = orchestrator.process_order_pipeline(state1, db)
display_execution_summary(res1)
"""))

    # Scenario 2: Validation Failure
    cells.append(create_markdown_cell("""
### 3. Scenario 2: Invalid Order (Structural & Payment Failure)
An incoming order containing a non-existent catalog SKU, blank address street, and `FAILED` payment status.
- Strict guardrail: Pipeline **halts immediately at Stage 1**.
- Inventory, Fraud, Pricing, and Dispatch agents are never invoked.
"""))

    cells.append(create_code_cell(r"""
state2 = OrderState(
    order_id="ORD-NB-02",
    customer_id="CUST-001",
    items=[OrderItemState(product_id="PROD-UNKNOWN", sku="NON-EXISTENT-SKU", name="Bad Item", quantity=1)],
    shipping_address=AddressState(street="", city="Springfield", state="OR", postal_code="97477", country="USA"),
    payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="FAILED", transaction_token=""),
)

res2 = orchestrator.process_order_pipeline(state2, db)
display_execution_summary(res2)
"""))

    # Scenario 3: High Risk Fraud Escalation
    cells.append(create_markdown_cell("""
### 4. Scenario 3: High-Risk Fraudulent Order (Fraud Escalation Route)
Customer `CUST-003` has 2 past chargebacks, failed payment retry velocity, and shipping/billing mismatch.
- Fraud Check Agent scores order at **100/100 (>= 70 critical threshold)**.
- **Fraud Escalation Route**: Diverts order to Hold Queue for human auditor review.
- **Rollback Guarantee**: Atomic inventory reservations are released immediately.
- Order is blocked from entering Pricing or Dispatch.
"""))

    cells.append(create_code_cell(r"""
state3 = OrderState(
    order_id="ORD-NB-03",
    customer_id="CUST-003",
    items=[OrderItemState(product_id="PROD-003", sku="MON-4K-27", name="4K Designer Monitor", quantity=3)],
    shipping_address=AddressState(street="PO Box 9999", city="Unknown Island", state="FL", postal_code="33040", country="USA"),
    payment_information=PaymentState(
        payment_method="CREDIT_CARD",
        payment_status="AUTHORIZED",
        transaction_token="tok_suspicious",
        billing_address=AddressState(street="100 Glacier Way", city="Anchorage", state="AK", postal_code="99501", country="USA")
    ),
)

res3 = orchestrator.process_order_pipeline(state3, db, simulated_failed_attempts=2)
display_execution_summary(res3)
"""))

    # Scenario 4: Insufficient Inventory
    cells.append(create_markdown_cell("""
### 5. Scenario 4: Insufficient Inventory (No Silent Substitution)
Order requests an out-of-stock ultrawide monitor (`MON-CRV-32`).
- Inventory Agent detects stock shortage and identifies compatible substitute (`MON-4K-27`) and backorder timeline (7 days).
- **Strict Business Rule**: Never silently alter an order. Customer approval required before changing order.
- Order is held with clear proposed substitute.
"""))

    cells.append(create_code_cell(r"""
state4 = OrderState(
    order_id="ORD-NB-04",
    customer_id="CUST-001",
    items=[OrderItemState(product_id="PROD-004", sku="MON-CRV-32", name="Curved Ultrawide Monitor", quantity=1)],
    shipping_address=AddressState(street="742 Evergreen Terrace", city="Springfield", state="OR", postal_code="97477", country="USA"),
    payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="AUTHORIZED", transaction_token="tok_valid_d4"),
)

res4 = orchestrator.process_order_pipeline(state4, db)
display_execution_summary(res4)
"""))

    # Scenario 5: Repeat Customer Memory
    cells.append(create_markdown_cell("""
### 6. Scenario 5: Customer Historical Memory Inspection
Prior-order memory retrieved by `CustomerMemoryService` and used by `FraudCheckAgent`.
"""))

    cells.append(create_code_cell(r"""
print("--- CUSTOMER 1 (TRUSTED REPEAT PROFILE) ---")
h1 = CustomerMemoryService.get_customer_history(db, "CUST-001")
print(f"Total Orders:      {h1.total_orders}")
print(f"Successful Orders: {h1.successful_orders}")
print(f"Suspicious Orders: {h1.suspicious_orders}")
print(f"Average Spend:     ${h1.average_order_value:.2f}")
print(f"Risk Tier:         {h1.risk_tier}")

print("")
print("--- CUSTOMER 3 (HIGH RISK / DISPUTE PROFILE) ---")
h3 = CustomerMemoryService.get_customer_history(db, "CUST-003")
print(f"Total Orders:      {h3.total_orders}")
print(f"Successful Orders: {h3.successful_orders}")
print(f"Suspicious Orders: {h3.suspicious_orders}")
print(f"Suspicion Rate:    {h3.suspicion_rate * 100:.1f}%")
print(f"Risk Tier:         {h3.risk_tier}")
"""))

    # Scenario 6: Customer Notification Draft Preview
    cells.append(create_markdown_cell("""
### 7. Customer Notification Draft Preview (Group Extension)
The `NotificationAgent` drafts personalized customer communications across Email and SMS channels without transmitting real messages externally without credentials.
"""))

    cells.append(create_code_cell(r"""
print("=== DRAFTED NOTIFICATION FOR CONFIRMED ORDER (ORD-NB-01) ===")
draft1 = res1.customer_notification_draft
print(f"Channel: {draft1.channel}")
print(f"Subject: {draft1.subject}")
print(f"Body:\n{draft1.body}")
print(f"SMS:     {draft1.sms_summary}")

print("")
print("=== DRAFTED NOTIFICATION FOR HELD FRAUD ORDER (ORD-NB-03) ===")
draft3 = res3.customer_notification_draft
print(f"Subject: {draft3.subject}")
print(f"Body:\n{draft3.body}")
"""))

    # Scenario 7: Append-Only Run Log Inspection
    cells.append(create_markdown_cell("""
### 8. Append-Only Run Log Verification
Every pipeline execution is committed to `logs/execution_run_log.jsonl` sequentially without overwriting past entries.
"""))

    cells.append(create_code_cell(r"""
recent_runs = AppendOnlyRunLogger.read_recent_runs(limit=3)
print(f"Retrieved {len(recent_runs)} recent append-only execution records:\n")
for run in recent_runs:
    print(f"Run ID:      {run['run_id']}")
    print(f"Timestamp:   {run['timestamp']}")
    print(f"Order ID:    {run['order_id']} -> {run['dispatch_status']}")
    print(f"Total Steps: {run['total_steps']} agent logs, {run['total_tool_calls']} tool calls")
    print("-" * 60)
"""))

    # Viva Defense Summary
    cells.append(create_markdown_cell("""
## 9. Viva Defense Quick Reference
- **Why Pipeline Architecture?** E-commerce fulfillment has strict operational prerequisites: an order cannot reserve inventory if invalid; cannot calculate pricing or dispatch if fraudulent; and must release reservations on cancellation.
- **Why Microsoft Agent Framework?** Provides standard `BaseAgent` and `@tool` abstractions, tool invocation metadata, schema validation, and modular decoupling.
- **How is Atomic Stock Integrity Guaranteed?** Transactions lock rows (`with_for_update`) during verification; if an order is diverted to the fraud hold queue or cancelled, reservations are released back to stock.
- **How Does Customer Memory Prevent Fraud?** Repeat customers with clean delivery histories gain low baseline scores; users with past chargebacks or rapid payment retries are flagged or escalated.
"""))

    notebook_content = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.12.10"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }

    os.makedirs("notebooks", exist_ok=True)
    nb_path_1 = "notebooks/demo_orchestrator.ipynb"
    nb_path_2 = "demo_orchestrator.ipynb"

    with open(nb_path_1, "w", encoding="utf-8") as f:
        json.dump(notebook_content, f, indent=2)

    with open(nb_path_2, "w", encoding="utf-8") as f:
        json.dump(notebook_content, f, indent=2)

    print(f"[OK] Generated {nb_path_1} and {nb_path_2}")

if __name__ == "__main__":
    build_notebook()
