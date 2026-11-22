# Microsoft Agent Framework Tools Registry
### CSE476 Agentic AI and Intelligent Automation — Group 11 (Q11)

This registry documents all specialized Python tool functions implemented in `backend/app/agents/tools.py`.
Every tool is a plain Python function decorated with `@tool` from Microsoft Agent Framework (`agent-framework-core` v1.26.0).

---

## 1. Agent 1: Validation Agent (`agt-validation-001`)

### Tool 1.1: `validate_customer_standing`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Queries the `Customer` table, verifies account existence, checks for `BLOCKED` or `FLAGGED` account standing, and retrieves customer profile details.
- **Input Schema:** `db: Any` (SQLAlchemy Session), `customer_id: str`
- **Output Schema:**
  ```python
  {
      "valid": bool,
      "customer_id": str,
      "name": Optional[str],
      "email": Optional[str],
      "phone": Optional[str],
      "status": str,  # ACTIVE, FLAGGED, BLOCKED
      "errors": List[str],
      "warnings": List[str],
  }
  ```
- **Where Invoked:** `ValidationAgent.validate_order()` (`backend/app/agents/validation_agent.py`)
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_validate_customer_standing_active`

### Tool 1.2: `validate_catalog_and_quantities`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Verifies that requested SKUs exist in the product catalog and that quantities are positive integers within reasonable upper boundaries (`0 < qty <= 100`). Populates unit and total item prices.
- **Input Schema:** `db: Any`, `items: List[OrderItemState]`
- **Output Schema:**
  ```python
  {
      "valid": bool,
      "errors": List[str],
      "warnings": List[str],
      "item_count": int,
      "validated_items": List[Dict[str, Any]],
  }
  ```
- **Where Invoked:** `ValidationAgent.validate_order()`
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_validate_catalog_and_quantities_success`

### Tool 1.3: `validate_shipping_and_payment`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Validates shipping destination completeness (street, city, state, postal code regex, country) and payment token presence and status (`AUTHORIZED` vs `FAILED`).
- **Input Schema:** `address: Optional[AddressState]`, `payment: Optional[PaymentState]`
- **Output Schema:**
  ```python
  {
      "valid": bool,
      "errors": List[str],
      "warnings": List[str],
  }
  ```
- **Where Invoked:** `ValidationAgent.validate_order()`
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_validate_shipping_and_payment_valid`

---

## 2. Agent 2: Inventory Agent (`agt-inventory-002`)

### Tool 2.1: `check_stock_availability`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Inspects real-time catalog stock levels without placing holds. Identifies shortfalls, detects linked substitute SKUs (`substitute_sku`), and generates backorder proposals.
- **Input Schema:** `db: Any`, `items: List[OrderItemState]`
- **Output Schema:**
  ```python
  {
      "all_available": bool,
      "insufficient_items": List[str],
      "substitutes": List[Dict[str, Any]],
      "backorders": List[Dict[str, Any]],
  }
  ```
- **Where Invoked:** `InventoryAgent.process_inventory()` (`backend/app/agents/inventory_agent.py`)
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_check_stock_availability`

### Tool 2.2: `reserve_stock_atomic`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Atomically decrements catalog `stock_quantity` within a transactional lock and creates persistent `InventoryReservation` records with expiry timeout.
- **Input Schema:** `db: Any`, `order_id: str`, `items: List[OrderItemState]`, `timeout_minutes: int = 15`
- **Output Schema:**
  ```python
  {
      "success": bool,
      "message": str,
      "substitutes": list,
      "backorders": list,
      "reservation_ids": List[str],
      "expires_at": str,
  }
  ```
- **Where Invoked:** `InventoryAgent.process_inventory()`
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_reserve_and_release_stock_atomic`

### Tool 2.3: `release_stock_reservation`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Rollback / compensation function that restores decremented stock quantities and updates reservation status to `RELEASED` on order hold, failure, or cancellation.
- **Input Schema:** `db: Any`, `order_id: str`
- **Output Schema:**
  ```python
  {
      "success": bool,
      "released_count": int,
      "message": str,
  }
  ```
- **Where Invoked:** `InventoryAgent.release_reservations()` and `OrderFulfillmentOrchestrator._route_to_hold()`
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_reserve_and_release_stock_atomic`

---

## 3. Agent 3: Fraud Check Agent (`agt-fraud-003`)

### Tool 3.1: `retrieve_customer_history`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Reads committed historical records from `order_history` to calculate prior order volume, successful completions, disputes/chargebacks, average order value, and suspicion rate.
- **Input Schema:** `db: Any`, `customer_id: str`
- **Output Schema:**
  ```python
  {
      "customer_id": str,
      "total_orders": int,
      "successful_orders": int,
      "suspicious_orders": int,
      "failed_payment_attempts": int,
      "total_spent": str,
      "average_order_value": str,
      "suspicion_rate": float,
      "risk_tier": str,  # LOW, MEDIUM, HIGH
  }
  ```
- **Where Invoked:** `FraudCheckAgent.evaluate_fraud()` (`backend/app/agents/fraud_check_agent.py`)
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_retrieve_customer_history`

### Tool 3.2: `calculate_fraud_risk_score`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Calculates deterministic multi-factor risk score (0 to 100) evaluating customer historical disputes, payment retry velocity, order value anomalies, and shipping/billing mismatches.
- **Input Schema:** `order_state: OrderState`, `history_stats: Dict[str, Any]`, `simulated_failed_attempts: int = 0`
- **Output Schema:**
  ```python
  {
      "score": float,  # 0.0 to 100.0
      "risk_tier": str,  # LOW, MEDIUM, HIGH
      "decision": str,  # APPROVED, FLAGGED, HELD
      "risk_factors": List[str],
      "ai_explanation": str,
  }
  ```
- **Where Invoked:** `FraudCheckAgent.evaluate_fraud()`
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_calculate_fraud_risk_score`

### Tool 3.3: `persist_fraud_review`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Persists formal `FraudReview` entity to the database with score, decision, trigger factors, AI reasoning, and audit attribution.
- **Input Schema:** `db: Any`, `order_id: str`, `customer_id: str`, `score: float`, `risk_tier: str`, `risk_factors: List[str]`, `ai_explanation: str`, `decision: str`
- **Output Schema:** `{"review_id": str, "recorded": bool}`
- **Where Invoked:** `FraudCheckAgent.evaluate_fraud()`
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_persist_fraud_review`

---

## 4. Agent 4: Pricing Agent (`agt-pricing-004`)

### Tool 4.1: `calculate_subtotal_and_discounts`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Computes item subtotals using exact `Decimal` arithmetic, applies bulk volume discounts (>= 5 units = 5% off), and applies promotional coupon codes (`WELCOME10`, `SAVE20`, `FREESHIP`).
- **Input Schema:** `items: List[OrderItemState]`, `coupon_code: Optional[str] = None`
- **Output Schema:**
  ```python
  {
      "subtotal": Decimal,
      "discount_amount": Decimal,
      "applied_rules": List[str],
      "coupon_free_shipping": bool,
  }
  ```
- **Where Invoked:** `PricingAgent.calculate_pricing()` (`backend/app/agents/pricing_agent.py`)
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_calculate_subtotal_and_discounts`

### Tool 4.2: `calculate_tax_and_shipping`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Computes regional sales tax (8% on post-discount taxable subtotal) and dynamic shipping cost ($5 standard, $15 express, $0 if subtotal >= $100 or `FREESHIP`).
- **Input Schema:** `subtotal: Decimal`, `discount_amount: Decimal`, `shipping_method: Optional[str]`, `coupon_free_shipping: bool`
- **Output Schema:** `{"tax_amount": Decimal, "shipping_cost": Decimal}`
- **Where Invoked:** `PricingAgent.calculate_pricing()`
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_calculate_tax_and_shipping`

### Tool 4.3: `finalize_order_total`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Computes final payable amount (`subtotal - discount + tax + shipping`), enforces non-negative boundary, and quantizes strictly to 2 decimal places using `ROUND_HALF_UP`.
- **Input Schema:** `subtotal: Decimal`, `discount_amount: Decimal`, `tax_amount: Decimal`, `shipping_cost: Decimal`
- **Output Schema:** `Decimal`
- **Where Invoked:** `PricingAgent.calculate_pricing()`
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_finalize_order_total`

---

## 5. Agent 5: Dispatch Coordinator (`agt-dispatch-005`)

### Tool 5.1: `select_optimal_carrier`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Evaluates order destination and service level to assign optimal freight logistics carrier (FedEx Priority Express, UPS Ground Logistics, USPS Priority Commerce, DHL Express Worldwide).
- **Input Schema:** `shipping_method: Optional[str]`, `destination_state: Optional[str]`, `item_count: int = 1`
- **Output Schema:** `{"carrier": str, "shipping_method": str, "service_level": str}`
- **Where Invoked:** `DispatchCoordinator.coordinate_dispatch()` (`backend/app/agents/dispatch_coordinator.py`)
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_select_optimal_carrier`

### Tool 5.2: `generate_tracking_and_manifest`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Generates unique carrier tracking number (`TRK-XXX-XXXXXXXX`) and packaging manifest with weight, estimated pickup, and estimated delivery dates.
- **Input Schema:** `carrier: str`, `method: str`, `item_count: int = 1`
- **Output Schema:** `{"tracking_id": str, "manifest": dict, "estimated_delivery": datetime}`
- **Where Invoked:** `DispatchCoordinator.coordinate_dispatch()`
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_generate_tracking_and_manifest`

### Tool 5.3: `create_shipment_record`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Persists formal `Shipment` entity to database, updates courier transit status, and transitions active `InventoryReservation` rows from `RESERVED` to `COMMITTED`.
- **Input Schema:** `db: Any`, `order_id: str`, `tracking_id: str`, `carrier: str`, `shipping_method: str`, `estimated_delivery: Any`
- **Output Schema:** `{"shipment_id": str, "status": "DISPATCHED", "committed_reservations": int}`
- **Where Invoked:** `DispatchCoordinator.coordinate_dispatch()`
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_create_shipment_record`

---

## 6. Agent 6: Notification Agent (`agt-notification-006`)

### Tool 6.1: `draft_customer_notification`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Drafts personalized customer communications across Email and SMS channels tailored to the order outcome:
  - `CONFIRMED`: Dispatched confirmation with tracking ID and delivery estimate.
  - `SUBSTITUTED`: Out of stock notification proposing substitute SKU / backorder restock and requesting approval.
  - `HELD_FRAUD`: Neutral security review notification informing the customer of standard verification without exposing internal fraud heuristics.
  - `HELD_VALIDATION`: Actionable notice detailing missing fields or failed payment.
- **Input Schema:** `order_state: OrderState`
- **Output Schema:** `NotificationDraft`
- **Where Invoked:** `NotificationAgent.process_notification()` (`backend/app/agents/notification_agent.py`)
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_draft_customer_notification_confirmed`

### Tool 6.2: `record_notification_log`
- **File:** `backend/app/agents/tools.py`
- **Purpose:** Attaches the drafted notification to the shared `OrderState` and records the notification audit event.
- **Input Schema:** `order_state: OrderState`, `draft: NotificationDraft`
- **Output Schema:** `{"notification_id": str, "channel": str, "intent": str, "subject": str, "status": "DRAFTED_PREVIEW"}`
- **Where Invoked:** `NotificationAgent.process_notification()`
- **How Tested:** `backend/tests/test_agent_tools.py::test_tool_record_notification_log`
