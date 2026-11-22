# E-Commerce Order Fulfillment Orchestrator
### CSE476 Agentic AI and Intelligent Automation — Group 11 (Q11)

**Group Members:** Ayush Dwivedi & Tushar  
**Agent Framework:** Microsoft Agent Framework (`agent-framework-core` v1.26.0)  
**Backend:** Python 3.12 + FastAPI + SQLAlchemy 2.0 (PostgreSQL / SQLite)  
**Frontend:** React 18 + TypeScript + Tailwind CSS  

---

## 1. Project Overview & Agent Roster
The platform is a multi-agent e-commerce order fulfillment orchestrator that processes incoming orders through five specialised agents and a dedicated **Fraud Escalation Route**. Every working agent is a separate module that inherits from Microsoft Agent Framework's `BaseAgent` and calls at least **TWO plain Python functions decorated with `@tool`**.

| Agent | Module | Role & Responsibilities | Genuine Python Tools Called |
|---|---|---|---|
| **1. Validation Agent** | `backend/app/agents/validation_agent.py` | Validates customer standing, catalog SKU existence, positive quantity bounds, address completeness, and payment authorization tokens. | `@tool validate_customer_standing`<br>`@tool validate_catalog_and_quantities`<br>`@tool validate_shipping_and_payment` |
| **2. Inventory Agent** | `backend/app/agents/inventory_agent.py` | Performs atomic stock verification and reservation; detects stockouts; recommends substitutes without silent alterations; handles backorders. | `@tool check_stock_availability`<br>`@tool reserve_stock_atomic`<br>`@tool release_stock_reservation` |
| **3. Fraud Check Agent** | `backend/app/agents/fraud_check_agent.py` | Retrieves customer history; calculates deterministic 0–100 risk score based on velocity, prior chargebacks, and address mismatch; routes $\ge 70$ to hold. | `@tool retrieve_customer_history`<br>`@tool calculate_fraud_risk_score`<br>`@tool persist_fraud_review` |
| **4. Pricing Agent** | `backend/app/agents/pricing_agent.py` | Executes exact `Decimal` arithmetic for line subtotals, bulk volume discounts ($\ge 5$ units = 5%), coupon codes (`WELCOME10`, `SAVE20`, `FREESHIP`), sales tax (8%), and shipping. | `@tool calculate_subtotal_and_discounts`<br>`@tool calculate_tax_and_shipping`<br>`@tool finalize_order_total` |
| **5. Dispatch Coordinator** | `backend/app/agents/dispatch_coordinator.py` | Verifies prior prerequisites; assigns carrier (FedEx, UPS, USPS, DHL); generates tracking ID (`TRK-XXX-XXXX`); commits inventory locks; creates shipment record. | `@tool select_optimal_carrier`<br>`@tool generate_tracking_and_manifest`<br>`@tool create_shipment_record` |
| **6. Notification Agent** *(Ext)* | `backend/app/agents/notification_agent.py` | Drafts personalized customer messages (Email + SMS) across Confirmed, Substituted, and Held outcomes in preview mode without unauthenticated transmission. | `@tool draft_customer_notification`<br>`@tool record_notification_log` |

---

## 2. Architecture and Why It Fits
The system implements a **Sequential Pipeline with a Fraud-Escalation Route**:
```
Customer Order ──> Validation ──> Inventory ──> Fraud Check ──┬──[Score < 70]──> Pricing ──> Dispatch ──> Dispatched Result
                                                              └──[Score >= 70]─> Release Stock ──> Hold Queue
```
**Why this architecture fits:**
1. **Strict Dependency Flow:** Orders cannot reserve inventory if malformed, and cannot calculate pricing or dispatch if fraudulent.
2. **Fraud Isolation:** Suspicious orders branch off into a human auditor queue without stalling the automated pipeline.
3. **Atomic Stock Rollback:** Stock is temporarily held during fraud check; if high risk is detected, reservations are released immediately, preventing inventory lockups.
4. **Deterministic Accuracy:** Financial calculations use Python `Decimal` (`ROUND_HALF_UP`), preventing LLM calculation hallucinations.

---

## 3. Shared State & Prior-Order Customer Memory
- **Shared `OrderState` (`backend/app/schemas/order_state.py`):** Central typed Pydantic object holding `order_id`, `customer_id`, `items`, `shipping_address`, `payment_information`, 5 agent phase statuses, quantitative amounts (`subtotal`, `tax_amount`, `shipping_cost`, `final_amount`), `fraud_score`, `tracking_id`, `carrier`, `customer_notification_draft`, and both `agent_execution_logs` and `tool_execution_logs`.
- **Prior-Order Memory (`backend/app/services/customer_memory.py`):** Reads the `order_history` table to evaluate historical customer trust signals: successful deliveries, dispute/chargeback count, average spend, and failed retry velocity.

---

## 4. Handled Failure: Inventory Reservation Rollback on Fraud Hold
- **Scenario:** Customer `CUST-003` attempts a high-value purchase ($890+).
- **Execution:** Validation passes and Inventory Agent executes `reserve_stock_atomic()`.
- **Detection:** Fraud Check Agent scores the order at **100/100 (High Risk)** due to 2 prior chargebacks and 5 failed payment retries.
- **Rollback Compensation:** The orchestrator intercepts the hold, triggers `release_stock_reservation()`, restores stock quantities to the catalog, marks reservation rows as `RELEASED`, drafts a security review notification, and logs the event to `logs/execution_run_log.jsonl`. No items are leaked or orphaned.

---

## 5. Setup & Run Instructions

### Prerequisites
- Python 3.12+ (Virtual environment recommended)
- Node.js 18+ & npm
- PostgreSQL (or automated SQLite fallback: `sqlite:///./ecommerce.db`)

### Backend Setup & Execution
```bash
# 1. Activate Python virtual environment
.\.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate    # Linux/macOS

# 2. Run backend API server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
Swagger API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend Setup & Execution
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```
Operations Dashboard: [http://localhost:5173](http://localhost:5173)

---

## 6. Demo & Verification Instructions

### 1. Run Automated Test Suite (66 Tests Passing)
```bash
$env:PYTHONPATH="."
pytest backend/tests/ -v
```

### 2. Run Python CLI Demonstration Script
Demonstrates all 6 core scenarios (Clean dispatch, validation stop, fraud hold, stock shortage, repeat customer memory, suspicious transaction memory):
```bash
$env:PYTHONPATH="."
python backend/demonstrate_prompt4.py
```

### 3. Run Pre-Rendered Jupyter Demo Notebook
The interactive notebook prints complete multi-agent traces and tool invocations:
```bash
# Open in VS Code, JupyterLab, or run via CLI
jupyter notebook notebooks/demo_orchestrator.ipynb
```

### 4. Append-Only Run Log Inspection
Every pipeline execution is appended to `logs/execution_run_log.jsonl` without overwriting historical records:
```bash
Get-Content logs/execution_run_log.jsonl -Tail 2
```

---

## 7. Viva Defense Quick Reference
- **Agent Framework:** Microsoft Agent Framework (`agent-framework-core` 1.26.0) using `BaseAgent` and `@tool` function decorators.
- **Tools Count:** 17 plain Python tool functions with explicit schemas (documented in `docs/TOOLS_REGISTRY.md`).
- **Data Flow:** `OrderState` instance is passed through each agent sequentially; each agent reads state, executes tools, and records audit telemetry.
- **Output Guarantee:** Every order produces either **Confirmed & Dispatched (with tracking ID and carrier)** OR **Held (with explicit hold reason and audit trail)**.
