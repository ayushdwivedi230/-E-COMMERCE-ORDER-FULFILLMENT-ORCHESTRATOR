# E-Commerce Order Fulfillment Orchestrator
### CSE476 Agentic AI and Intelligent Automation

An enterprise-grade, multi-agent automated order fulfillment and orchestration platform built with **Python 3.12**, **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL / SQLite**, **Microsoft Agent Framework (`agent-framework-core` v1.26.0)**, and **React + TypeScript + Vite**.

---

## 1. System Architecture

The orchestrator models a high-throughput e-commerce fulfillment pipeline coordinating **five specialised agents** over a shared, type-safe `OrderState` object. The pipeline incorporates a dedicated **Fraud Escalation Route** that diverts anomalous transactions to a human auditor review queue while maintaining atomic inventory integrity.

```mermaid
flowchart TD
    A([Incoming Order Request]) --> B[Initialize Shared OrderState]
    B --> C[Agent 1: Validation Agent]
    
    C -->|Validation Failure| H1[Hold Queue: Structural Errors]
    C -->|Validation Passed| D[Agent 2: Inventory Agent]
    
    D -->|Insufficient Stock / Substitute| H2[Hold Queue: Customer Approval Required]
    D -->|Atomic Stock Reserved| E[Agent 3: Fraud Check Agent]
    
    E -->|Customer Memory Retrieval| M[(Prior-Order Memory DB)]
    M -->|Historical Suspicion & Retries| E
    
    E -->|Score >= 70 High Risk| F{Fraud Escalation Branch}
    F -->|Release Inventory Locks| H3[Fraud Hold Queue & Human Auditor Review]
    
    E -->|Score < 70 Cleared| G[Agent 4: Pricing Agent]
    G -->|Deterministic Decimal Arithmetic| I[Agent 5: Dispatch Coordinator]
    
    I -->|Tracking ID & Shipment Record| J([Dispatched Order])
    J -->|Record Transaction| M
```

---

## 2. The Five Specialised Agents

Each agent is implemented as an independent Python module adhering to Microsoft Agent Framework abstractions (`agent_framework.BaseAgent`):

1. **Validation Agent (`backend/app/agents/validation_agent.py`)**
   - Validates catalog product existence and positive quantity boundaries.
   - Validates shipping address completeness (street, city, state, postal code, country).
   - Validates customer account existence and non-blocked standing.
   - Verifies payment method presence and payment token validity.

2. **Inventory Agent (`backend/app/agents/inventory_agent.py`)**
   - Performs atomic stock verification and reservation in database transactions.
   - Detects insufficient stock without silently substituting products.
   - Proposes active substitute recommendations (`substitute_sku`) and backorders.
   - Enforces the strict guardrail: **Customer approval must be obtained before altering an order.**

3. **Fraud Check Agent (`backend/app/agents/fraud_check_agent.py`)**
   - Retrieves historical customer memory via `CustomerMemoryService`.
   - Computes deterministic risk scores on a scale from **0 to 100**:
     - *0–29*: Low Risk (Approved)
     - *30–69*: Medium Risk (Cautionary Flag, Cleared with Warning)
     - *70–100*: High Risk (**Routed to Escalation Hold Queue**)
   - Evaluates:
     - Prior suspicious orders and chargeback history.
     - Velocity and recent failed payment retries.
     - Shipping vs. Billing address mismatches.
     - Unusually high order values compared to customer history or thresholds.
   - Generates contextual **AI reasoning explanations** for human auditor compliance.

4. **Pricing Agent (`backend/app/agents/pricing_agent.py`)**
   - Executes deterministic financial arithmetic using `decimal.Decimal` (never LLM estimations).
   - Computes subtotals, bulk volume discounts (>= 5 units), coupon discounts (`WELCOME10`, `SAVE20`, `FREESHIP`), regional sales tax (8%), and dynamic shipping fees (free shipping on orders >= $100.00).

5. **Dispatch Coordinator (`backend/app/agents/dispatch_coordinator.py`)**
   - Validates completion of all prior pipeline phases.
   - Selects optimal logistics carrier (FedEx Priority Express, UPS Ground, USPS Priority, DHL Express).
   - Generates simulated carrier tracking numbers (`TRK-FDX-XXXXXXXX`).
   - Creates persistent shipment records in the `shipments` table.
   - Commits atomic inventory reservations permanently.

---

## 3. Database Architecture (SQLAlchemy & PostgreSQL)

The system manages 9 relational tables:

| Table | Purpose |
| :--- | :--- |
| `customers` | Customer accounts, contact details, status, addresses |
| `products` | Product catalog, pricing, stock quantities, substitute SKU links |
| `orders` | Central order state, financial totals, status, tracking ID |
| `order_items` | Line items associated with each order |
| `order_history` | **Prior-Order Customer Memory** (past orders, dispute flags, failed retries) |
| `agent_logs` | Audit trail of every agent action, execution duration in ms, and I/O snapshots |
| `inventory_reservations` | Atomic inventory reservation holds with expiry timestamps |
| `fraud_reviews` | Fraud risk scores, risk levels, trigger factors, and AI contextual justifications |
| `shipments` | Shipping carrier details, tracking IDs, dispatch statuses, and estimated delivery |

---

## 4. Project Directory Structure

```
ecommerce/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI application entrypoint & lifespan
│   │   ├── config.py                   # Pydantic Settings (.env configuration)
│   │   ├── database.py                 # SQLAlchemy engine, session maker, SQLite/PostgreSQL
│   │   ├── models/                     # 9 SQLAlchemy ORM Models
│   │   │   ├── __init__.py
│   │   │   ├── customer.py             # Customer entity
│   │   │   ├── product.py              # Product & SKU entity
│   │   │   ├── order.py                # Order, OrderItem & OrderHistory (Memory)
│   │   │   ├── inventory.py            # InventoryReservation entity
│   │   │   ├── fraud.py                # FraudReview entity
│   │   │   ├── shipment.py             # Shipment entity
│   │   │   └── agent_log.py            # AgentLog telemetry entity
│   │   ├── schemas/                    # Pydantic Schemas & Shared State
│   │   │   ├── __init__.py
│   │   │   ├── order_state.py          # Central Shared OrderState Model
│   │   │   ├── customer.py             # Customer & Memory Schemas
│   │   │   ├── product.py              # Product Catalog Schemas
│   │   │   └── order.py                # API Request & Summary Schemas
│   │   ├── services/                   # Business Services
│   │   │   ├── __init__.py
│   │   │   ├── customer_memory.py      # Prior-Order History Memory Service
│   │   │   ├── inventory_service.py    # Atomic Stock Reservation Service
│   │   │   └── seed_data.py            # Initial seed dataset (4 customers, 6 products)
│   │   ├── agents/                     # Five Specialised Agents
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # Microsoft Agent Framework Adapter (BaseAgent)
│   │   │   ├── validation_agent.py     # Agent 1
│   │   │   ├── inventory_agent.py      # Agent 2
│   │   │   ├── fraud_check_agent.py    # Agent 3
│   │   │   ├── pricing_agent.py        # Agent 4
│   │   │   └── dispatch_coordinator.py # Agent 5
│   │   ├── orchestrator/
│   │   │   ├── __init__.py
│   │   │   └── pipeline.py             # Pipeline with Fraud-Escalation Route
│   │   └── api/                        # FastAPI Router Endpoints
│   │       ├── __init__.py
│   │       ├── orders.py               # Order submission, held queue, override
│   │       ├── products.py             # Product catalog & stock levels
│   │       ├── customers.py            # Customer lookup & prior memory
│   │       └── agents.py               # Agent introspection & testing
│   ├── tests/                          # 20 Automated Tests (100% Pass)
│   │   ├── conftest.py                 # Isolated SQLite In-Memory Fixtures
│   │   ├── test_customer_memory.py     # Memory statistics tests
│   │   ├── test_agents.py              # Individual agent tests
│   │   ├── test_pipeline.py            # End-to-end pipeline & hold route tests
│   │   └── test_api_endpoints.py       # FastAPI HTTP endpoint tests
│   └── requirements.txt
├── frontend/                           # React + TypeScript + Vite + Tailwind CSS
│   ├── src/
│   │   ├── api/index.ts                # API client
│   │   ├── types/index.ts              # TypeScript domain interfaces
│   │   ├── components/
│   │   │   ├── PipelineStepper.tsx     # Visual 5-Agent Stepper with Latencies
│   │   │   ├── AgentLogViewer.tsx      # Real-Time Telemetry Log Viewer
│   │   │   ├── CustomerMemoryView.tsx  # Customer Prior-Order Memory Profiler
│   │   │   ├── FraudQueueView.tsx      # Held Orders & Auditor Override
│   │   │   └── InventoryView.tsx       # Live Catalog & Stock Monitor
│   │   ├── App.tsx                     # Main interactive dashboard
│   │   └── index.css                   # Tailwind CSS styles
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── docker-compose.yml                  # PostgreSQL 16 & pgAdmin container setup
├── .env.example                        # Environment variables template
├── .env                                # Local configuration
├── .gitignore                          # Git ignore rules
└── README.md
```

---

## 5. Installation and Setup Instructions

### Prerequisites
- Python 3.10+ (tested on Python 3.12.10)
- Node.js 18+ & npm (tested on Node v24.4.1)
- Optional: Docker & Docker Compose (for PostgreSQL container)

### Step 1: Set up the Python Environment
```bash
# Clone the repository
git clone <repository_url>
cd ecommerce

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
# source .venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt
pip install agent-framework-core
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
By default, `DATABASE_URL=sqlite:///./ecommerce.db` is configured for instant zero-setup execution.

To use PostgreSQL:
```bash
# Start PostgreSQL via Docker Compose:
docker compose up -d

# In .env set:
DATABASE_URL=postgresql+psycopg2://postgres:postgrespassword@localhost:5432/ecommerce_db
```

### Step 3: Run Automated Backend Tests
Verify all 20 unit and integration tests:
```bash
python -m pytest backend/tests
```

### Step 4: Start the Backend Server
```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```
- API Documentation (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### Step 5: Start the Frontend Application
In a separate terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open your browser at [http://localhost:5173](http://localhost:5173).

---

## 6. Pre-Configured Test Scenarios

The interactive dashboard provides quick-load buttons for testing key orchestrator pathways:

1. **Scenario A (Clean Dispatch)**: Verified customer (`CUST-001`), in-stock mechanical keyboard, coupon `WELCOME10`. All 5 agents pass; tracking ID generated (`TRK-FDX-...`).
2. **Scenario B (Fraud Escalation Hold)**: High-risk customer (`CUST-003`) with 2 prior chargebacks, 2 failed payment retries, and shipping/billing address mismatch. Fraud risk score >= 70 triggers immediate escalation to the Fraud Hold Queue.
3. **Scenario C (Out of Stock / Substitute)**: Item `MON-CRV-32` has 0 stock. Inventory Agent proposes active substitute `MON-4K-27` and backorder estimate, holding the order for customer confirmation.
4. **Scenario D (Bulk Volume Discount)**: Order with 6 units of `HUB-USBC-8P` triggers the deterministic 5% bulk volume discount rule plus coupon `SAVE20`.
