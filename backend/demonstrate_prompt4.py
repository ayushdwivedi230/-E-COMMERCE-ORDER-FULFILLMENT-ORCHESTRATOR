"""
Prompt 4 Demonstration Script: Multi-Agent Orchestration and Fraud Escalation
CSE476 Agentic AI and Intelligent Automation

Demonstrates all required test cases:
1. Successful order (Confirmed order + final amount + shipping method + tracking ID)
2. Invalid order (Stops processing immediately)
3. High-risk fraudulent order (Fraud escalation route to hold queue + release stock)
4. Insufficient inventory (Substitute and backorder proposals, customer approval required)
5. Customer with previous successful transactions (Prior-order memory retrieval)
6. Customer with suspicious historical transactions (Chargeback memory retrieval)
"""

import os
import sys
import json
from decimal import Decimal

sys.path.insert(0, os.path.abspath("."))

from backend.app.database import init_db, SessionLocal
from backend.app.services.seed_data import seed_database
from backend.app.services.customer_memory import CustomerMemoryService
from backend.app.orchestrator.pipeline import OrderFulfillmentOrchestrator
from backend.app.schemas.order_state import OrderState, OrderItemState, AddressState, PaymentState


def print_separator(title: str):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)


def print_agent_trace(state: OrderState):
    print("\n--- AGENT EXECUTION TRACE LOGS ---")
    for log in state.agent_execution_logs:
        status_color = "PASS" if log.status in ["SUCCESS", "PASSED"] else log.status
        print(f"  [{log.agent_name:<20}] {log.action:<25} -> {status_color:<7} ({log.execution_time_ms:>2}ms): {log.message}")


def run_demonstrations():
    print_separator("CSE476 E-Commerce Order Fulfillment Orchestrator — Prompt 4 Demonstrations")
    print("Initializing Database & Seeding Baseline Customer Profiles & Catalogs...")
    init_db()
    db = SessionLocal()
    seed_database(db)
    orchestrator = OrderFulfillmentOrchestrator()

    # --------------------------------------------------------------------------
    # DEMO 1: Successful Order
    # --------------------------------------------------------------------------
    print_separator("Demonstration 1: Successful Order (Clean Dispatch)")
    state1 = OrderState(
        order_id="ORD-DEMO-01",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-001", sku="KB-MECH-RGB", name="Mechanical RGB Keyboard", quantity=1)],
        shipping_address=AddressState(street="742 Evergreen Terrace", city="Springfield", state="OR", postal_code="97477", country="USA"),
        payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="AUTHORIZED", transaction_token="tok_valid_d1"),
        coupon_code="WELCOME10",
    )
    res1 = orchestrator.process_order_pipeline(state1, db)
    out1 = res1.get_structured_output()
    print_agent_trace(res1)
    print("\n[REQUIRED OUTPUT - SUCCESSFUL ORDER]:")
    print(f"  * Status:          {out1['status']}")
    print(f"  * Order ID:        {out1['order_id']}")
    print(f"  * Final Amount:    ${out1['final_amount']}")
    print(f"  * Carrier:         {out1['carrier']}")
    print(f"  * Shipping Method: {out1['shipping_method']}")
    print(f"  * Tracking ID:     {out1['tracking_id']}")

    # --------------------------------------------------------------------------
    # DEMO 2: Invalid Order
    # --------------------------------------------------------------------------
    print_separator("Demonstration 2: Invalid Order (Stops Processing Immediately)")
    state2 = OrderState(
        order_id="ORD-DEMO-02",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-UNKNOWN", sku="NON-EXISTENT-SKU", name="Bad Item", quantity=1)],
        shipping_address=AddressState(street="", city="Springfield", state="OR", postal_code="97477", country="USA"),
        payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="FAILED", transaction_token=""),
    )
    res2 = orchestrator.process_order_pipeline(state2, db)
    print_agent_trace(res2)
    print("\n[PIPELINE STOP RESULT]:")
    print(f"  * Validation Status: {res2.validation_status} (Pipeline Stopped Immediately)")
    print(f"  * Inventory Status:  {res2.inventory_status} (Never invoked)")
    print(f"  * Fraud Status:      {res2.fraud_status} (Never invoked)")
    print(f"  * Dispatch Status:   {res2.dispatch_status}")
    print(f"  * Hold Reason:       {res2.hold_reason}")

    # --------------------------------------------------------------------------
    # DEMO 3: High-Risk Fraudulent Order (Fraud Escalation Route)
    # --------------------------------------------------------------------------
    print_separator("Demonstration 3: High-Risk Fraudulent Order (Escalated to Hold Queue)")
    state3 = OrderState(
        order_id="ORD-DEMO-03",
        customer_id="CUST-003", # High-risk user with 2 past chargebacks & multiple retries
        items=[OrderItemState(product_id="PROD-003", sku="MON-4K-27", name="4K Monitor", quantity=3)],
        shipping_address=AddressState(street="PO Box 9999", city="Unknown Island", state="FL", postal_code="33040", country="USA"),
        payment_information=PaymentState(
            payment_method="CREDIT_CARD",
            payment_status="AUTHORIZED",
            transaction_token="tok_risky_card",
            billing_address=AddressState(street="PO Box 111", city="Anchorage", state="AK", postal_code="99501", country="USA"),
        ),
    )
    res3 = orchestrator.process_order_pipeline(state3, db, simulated_failed_attempts=2)
    out3 = res3.get_structured_output()
    print_agent_trace(res3)
    print("\n[REQUIRED OUTPUT - SUSPICIOUS ORDER]:")
    print(f"  * Status:          {out3['status']}")
    print(f"  * Review Status:   {out3['review_status']}")
    print(f"  * Fraud Score:     {out3['fraud_score']}/100 (Threshold >= 70)")
    print(f"  * Hold Reason:     {out3['hold_reason']}")
    print(f"  * Pricing/Dispatch:{res3.pricing_status} / {res3.dispatch_status} (Never dispatched)")
    print(f"  * AI Explanation:  {out3['explanation']}")

    # --------------------------------------------------------------------------
    # DEMO 4: Insufficient Inventory (Substitute / Backorder Proposal)
    # --------------------------------------------------------------------------
    print_separator("Demonstration 4: Insufficient Inventory (Customer Approval Required)")
    state4 = OrderState(
        order_id="ORD-DEMO-04",
        customer_id="CUST-001",
        items=[OrderItemState(product_id="PROD-004", sku="MON-CRV-32", name="Curved Gaming Monitor (0 Stock)", quantity=1)],
        shipping_address=AddressState(street="742 Evergreen Terrace", city="Springfield", state="OR", postal_code="97477", country="USA"),
        payment_information=PaymentState(payment_method="CREDIT_CARD", payment_status="AUTHORIZED", transaction_token="tok_valid_d4"),
    )
    res4 = orchestrator.process_order_pipeline(state4, db)
    print_agent_trace(res4)
    print("\n[GUARDRAIL RESULT - NO SILENT SUBSTITUTION]:")
    print(f"  * Inventory Status:    {res4.inventory_status}")
    print(f"  * Substitute Proposed: {res4.substitute_recommendations[0].substitute_name} ({res4.substitute_recommendations[0].substitute_sku})")
    print(f"  * Customer Approval:   REQUIRED (Order Held)")
    print(f"  * Hold Reason:         {res4.hold_reason}")

    # --------------------------------------------------------------------------
    # DEMO 5: Customer with Previous Successful Transactions
    # --------------------------------------------------------------------------
    print_separator("Demonstration 5: Customer with Previous Successful Transactions (CUST-001)")
    mem1 = CustomerMemoryService.get_customer_history(db, "CUST-001")
    print(f"  * Customer ID:        {mem1.customer_id}")
    print(f"  * Total Past Orders:  {mem1.total_orders}")
    print(f"  * Successful Orders:  {mem1.successful_orders}")
    print(f"  * Suspicious Orders:  {mem1.suspicious_orders}")
    print(f"  * Risk Tier:          {mem1.risk_tier}")
    print(f"  * Average Order Val:  ${mem1.average_order_value:.2f}")

    # --------------------------------------------------------------------------
    # DEMO 6: Customer with Suspicious Historical Transactions
    # --------------------------------------------------------------------------
    print_separator("Demonstration 6: Customer with Suspicious Historical Transactions (CUST-003)")
    mem3 = CustomerMemoryService.get_customer_history(db, "CUST-003")
    print(f"  * Customer ID:        {mem3.customer_id}")
    print(f"  * Total Past Orders:  {mem3.total_orders}")
    print(f"  * Suspicious Orders:  {mem3.suspicious_orders}")
    print(f"  * Failed Attempts:    {mem3.failed_payment_attempts}")
    print(f"  * Risk Tier:          {mem3.risk_tier}")
    print(f"  * Suspicion Rate:     {mem3.suspicion_rate * 100:.1f}%")
    for po in mem3.prior_orders:
        print(f"      - {po.order_id}: Status={po.status}, Suspicious={po.is_suspicious}, Notes={po.notes}")

    db.close()
    print_separator("All 6 Demonstrations Completed Successfully")


if __name__ == "__main__":
    run_demonstrations()
