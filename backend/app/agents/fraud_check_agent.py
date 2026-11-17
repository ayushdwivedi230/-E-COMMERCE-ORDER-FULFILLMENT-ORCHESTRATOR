import time
import uuid
from decimal import Decimal
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseOrchestratorAgent
from backend.app.schemas.order_state import OrderState
from backend.app.services.customer_memory import CustomerMemoryService
from backend.app.models.fraud import FraudReview
from backend.app.config import settings


class FraudCheckAgent(BaseOrchestratorAgent):
    """
    Agent 3: Fraud Check Agent
    Implements:
    - Deterministic risk scoring from 0 to 100
    - Prior-order customer memory analysis
    - Address mismatch & velocity detection
    - Threshold evaluation:
        * 0-29: Low risk
        * 30-69: Medium risk
        * 70-100: High risk (routed to hold queue)
    - Deterministic decisioning with contextual AI reasoning explanation
    """

    def __init__(self) -> None:
        super().__init__(
            name="FraudCheckAgent",
            description="Evaluates order risk factors, historical transaction anomalies, and routes high-risk orders to hold.",
            agent_id="agt-fraud-003",
        )

    def evaluate_fraud(
        self,
        order_state: OrderState,
        db: Session,
        simulated_failed_attempts: int = 0,
    ) -> bool:
        start_time = time.time()

        if order_state.inventory_status != "RESERVED":
            order_state.fraud_status = "SKIPPED"
            self.record_agent_log(
                order_state,
                action="FraudEvaluation",
                status="SKIPPED",
                message="Skipping fraud check because inventory reservation was not completed.",
                start_time=start_time,
            )
            return False

        # 1. Retrieve customer memory
        history = CustomerMemoryService.get_customer_history(db, order_state.customer_id)

        # 2. Compute Deterministic Risk Score
        score, risk_factors = self._calculate_deterministic_risk_score(
            order_state=order_state,
            history=history,
            simulated_failed_attempts=simulated_failed_attempts,
        )

        order_state.fraud_score = score
        order_state.fraud_risk_factors = risk_factors

        # 3. Classify Risk Tier
        if score <= settings.FRAUD_LOW_THRESHOLD:
            risk_tier = "LOW"
            decision = "APPROVED"
            order_state.fraud_status = "LOW_RISK"
        elif score <= settings.FRAUD_MEDIUM_THRESHOLD:
            risk_tier = "MEDIUM"
            decision = "FLAGGED"
            order_state.fraud_status = "MEDIUM_RISK"
        else:
            risk_tier = "HIGH"
            decision = "HELD"
            order_state.fraud_status = "HIGH_RISK_HELD"
            order_state.hold_reason = (
                f"Fraud Escalation Hold: Risk score of {score}/100 exceeds critical threshold ({settings.FRAUD_HIGH_THRESHOLD}). "
                f"Triggers: {'; '.join(risk_factors)}"
            )

        # 4. Generate AI Contextual Reasoning Explanation
        ai_explanation = self._generate_contextual_explanation(
            score=score,
            risk_tier=risk_tier,
            risk_factors=risk_factors,
            history=history,
            order_state=order_state,
        )
        order_state.fraud_ai_reasoning = ai_explanation

        # 5. Persist to FraudReview table in database
        fraud_record = FraudReview(
            id=f"FRD-{uuid.uuid4().hex[:8].upper()}",
            order_id=order_state.order_id,
            customer_id=order_state.customer_id,
            fraud_score=score,
            risk_level=risk_tier,
            reasons="; ".join(risk_factors) if risk_factors else "None",
            ai_explanation=ai_explanation,
            decision=decision,
            reviewed_by="FraudCheckAgent",
        )
        db.add(fraud_record)
        db.commit()

        # 6. Log Agent Result
        log_status = "HELD" if risk_tier == "HIGH" else ("WARNING" if risk_tier == "MEDIUM" else "SUCCESS")
        self.record_agent_log(
            order_state,
            action="FraudEvaluation",
            status=log_status,
            message=f"Fraud evaluation completed with score {score}/100 (Tier: {risk_tier}). Decision: {decision}.",
            start_time=start_time,
            details={
                "fraud_score": score,
                "risk_tier": risk_tier,
                "decision": decision,
                "risk_factors": risk_factors,
                "ai_explanation": ai_explanation,
            },
        )

        return decision != "HELD"

    def _calculate_deterministic_risk_score(
        self,
        order_state: OrderState,
        history,
        simulated_failed_attempts: int = 0,
    ) -> Tuple[float, List[str]]:
        """
        Pure deterministic risk scoring function using strict mathematical weights:
        Base score: 5
        + History of prior suspicious/chargeback orders (+35 pts each, max 70)
        + Failed payment attempts (+15 pts each)
        + Shipping vs Billing Address mismatch (+20 pts)
        + Unusually high order value (> $1000 or > 3x historical avg) (+25 pts)
        + Brand new customer with large initial cart (> $500) (+20 pts)
        + Disposable or suspicious email domain (+15 pts)
        Clamped to [0, 100].
        """
        score = 5.0
        factors: List[str] = []

        # Factor A: Prior Suspicious Orders from Customer Memory
        if history.suspicious_orders > 0:
            pts = min(history.suspicious_orders * 35.0, 70.0)
            score += pts
            factors.append(
                f"Customer has {history.suspicious_orders} prior suspicious/chargeback transactions (+{int(pts)} pts)"
            )

        # Factor B: Failed Payment Attempts
        total_failed_attempts = history.failed_payment_attempts + simulated_failed_attempts
        if total_failed_attempts >= 2:
            pts = min(total_failed_attempts * 15.0, 30.0)
            score += pts
            factors.append(
                f"Multiple failed payment attempts detected ({total_failed_attempts} attempts) (+{int(pts)} pts)"
            )

        # Factor C: Address Inconsistency
        ship_addr = order_state.shipping_address
        bill_addr = order_state.payment_information.billing_address
        if bill_addr:
            if (
                ship_addr.postal_code != bill_addr.postal_code
                or ship_addr.state != bill_addr.state
            ):
                score += 20.0
                factors.append(
                    f"Address mismatch: Shipping ({ship_addr.state} {ship_addr.postal_code}) "
                    f"does not match Billing ({bill_addr.state} {bill_addr.postal_code}) (+20 pts)"
                )

        # Estimate order total before pricing agent
        estimated_subtotal = sum(item.total_price for item in order_state.items)

        # Factor D: Unusually High Order Value
        if history.successful_orders > 0 and history.average_order_value > Decimal("0.00"):
            if estimated_subtotal > (history.average_order_value * Decimal("3.0")):
                score += 25.0
                factors.append(
                    f"Order value (${estimated_subtotal}) is >3x higher than historical average (${history.average_order_value}) (+25 pts)"
                )
        elif estimated_subtotal > Decimal("1000.00"):
            score += 25.0
            factors.append(
                f"Order value (${estimated_subtotal}) exceeds high-value threshold of $1,000.00 (+25 pts)"
            )

        # Factor E: New customer with high first order
        if history.total_orders == 0 and estimated_subtotal > Decimal("500.00"):
            score += 20.0
            factors.append(
                f"New customer first-order value (${estimated_subtotal}) exceeds $500.00 threshold (+20 pts)"
            )

        # Factor F: Suspicious Email Domain
        if order_state.customer_email and any(
            domain in order_state.customer_email.lower()
            for domain in ["disposable", "tempmail", "sharklasers", "mailinator"]
        ):
            score += 15.0
            factors.append(
                f"Customer email domain appears disposable ({order_state.customer_email}) (+15 pts)"
            )

        final_score = min(max(score, 0.0), 100.0)
        return round(final_score, 1), factors

    def _generate_contextual_explanation(
        self,
        score: float,
        risk_tier: str,
        risk_factors: List[str],
        history,
        order_state: OrderState,
    ) -> str:
        """
        AI Contextual Reasoning Explanation synthesized for human compliance auditors.
        Provides transparent audit trail justification.
        """
        reasons_summary = "; ".join(risk_factors) if risk_factors else "No abnormal risk indicators observed."
        if risk_tier == "HIGH":
            return (
                f"CRITICAL ESCALATION: The order presents an acute risk profile (Score: {score}/100, Tier: HIGH). "
                f"Audit analysis reveals {len(risk_factors)} risk factor(s): {reasons_summary}. "
                f"Customer prior history indicates {history.suspicious_orders} suspicious transactions and "
                f"{history.failed_payment_attempts} failed payment attempts. "
                f"In accordance with fraud policy, automated dispatch is blocked and the transaction has been routed "
                f"to the Fraud Escalation Hold Queue for mandatory human review."
            )
        elif risk_tier == "MEDIUM":
            return (
                f"CAUTIONARY WARNING: The order exhibits moderate risk anomalies (Score: {score}/100, Tier: MEDIUM). "
                f"Identified signals: {reasons_summary}. "
                f"Transaction is cleared for automated fulfillment but flagged for post-fulfillment audit review."
            )
        else:
            return (
                f"TRANSACTION APPROVED: Clean transaction profile (Score: {score}/100, Tier: LOW). "
                f"Customer has a verified profile with {history.successful_orders} successful prior orders and 0 disputes. "
                f"Payment and address verification criteria satisfied."
            )
