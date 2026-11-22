import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.agents.base import BaseOrchestratorAgent
from backend.app.schemas.order_state import OrderState
from backend.app.config import settings
from backend.app.agents.tools import (
    retrieve_customer_history,
    calculate_fraud_risk_score,
    persist_fraud_review,
)


class FraudCheckAgent(BaseOrchestratorAgent):
    """
    Agent 3: Fraud Check Agent
    Implements:
    - Deterministic risk scoring from 0 to 100
    - Prior-order customer memory analysis
    - Address mismatch & velocity detection
    - Threshold evaluation:
        * 0-29: Low risk (Approved)
        * 30-69: Medium risk (Flagged for review)
        * 70-100: High risk (Routed to Escalation Hold Queue)
    - Deterministic decisioning with contextual AI reasoning explanation

    Microsoft Agent Framework Integration:
    Calls 3 plain Python tools decorated with @tool:
      1. retrieve_customer_history
      2. calculate_fraud_risk_score
      3. persist_fraud_review
    """

    def __init__(self) -> None:
        tools = [
            retrieve_customer_history,
            calculate_fraud_risk_score,
            persist_fraud_review,
        ]
        super().__init__(
            name="FraudCheckAgent",
            description="Evaluates order risk factors, historical transaction anomalies, and routes high-risk orders to hold.",
            agent_id="agt-fraud-003",
            tools=tools,
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

        # TOOL 1: Retrieve Customer Historical Memory
        t1_start = time.time()
        history_stats = retrieve_customer_history(db, order_state.customer_id)
        self.record_tool_call(
            order_state=order_state,
            tool_name="retrieve_customer_history",
            action="CustomerMemoryRetrieval",
            status="SUCCESS",
            message=f"Retrieved {history_stats['total_orders']} historical orders (Suspicious: {history_stats['suspicious_orders']}).",
            start_time=t1_start,
            details=history_stats,
        )

        # TOOL 2: Calculate Deterministic Fraud Risk Score
        t2_start = time.time()
        eval_res = calculate_fraud_risk_score(
            order_state=order_state,
            history_stats=history_stats,
            simulated_failed_attempts=simulated_failed_attempts,
        )
        score = eval_res["score"]
        risk_tier = eval_res["risk_tier"]
        decision = eval_res["decision"]
        risk_factors = eval_res["risk_factors"]
        ai_explanation = eval_res["ai_explanation"]

        order_state.fraud_score = score
        order_state.fraud_risk_factors = risk_factors
        order_state.fraud_ai_reasoning = ai_explanation

        self.record_tool_call(
            order_state=order_state,
            tool_name="calculate_fraud_risk_score",
            action="RiskScoreCalculation",
            status="WARNING" if risk_tier == "HIGH" else "SUCCESS",
            message=f"Score: {score}/100, Tier: {risk_tier}, Decision: {decision}.",
            start_time=t2_start,
            details=eval_res,
        )

        # Classify OrderState
        if score <= settings.FRAUD_LOW_THRESHOLD:
            order_state.fraud_status = "LOW_RISK"
            order_state.review_status = "APPROVED"
        elif score <= settings.FRAUD_MEDIUM_THRESHOLD:
            order_state.fraud_status = "MEDIUM_RISK"
            order_state.review_status = "FLAGGED_REVIEW"
        else:
            order_state.fraud_status = "HIGH_RISK_HELD"
            order_state.review_status = "HELD_ESCALATED"
            order_state.hold_reason = (
                f"Fraud Escalation Hold: Risk score of {score}/100 exceeds critical threshold ({settings.FRAUD_HIGH_THRESHOLD}). "
                f"Triggers: {'; '.join(risk_factors)}"
            )

        # TOOL 3: Persist Fraud Review Record in Database
        t3_start = time.time()
        persist_res = persist_fraud_review(
            db=db,
            order_id=order_state.order_id,
            customer_id=order_state.customer_id,
            score=score,
            risk_tier=risk_tier,
            risk_factors=risk_factors,
            ai_explanation=ai_explanation,
            decision=decision,
        )
        self.record_tool_call(
            order_state=order_state,
            tool_name="persist_fraud_review",
            action="AuditPersistence",
            status="SUCCESS",
            message=f"Persisted fraud audit review record {persist_res['review_id']}.",
            start_time=t3_start,
            details=persist_res,
        )

        # Agent Summary Log
        log_status = "HELD" if risk_tier == "HIGH" else ("WARNING" if risk_tier == "MEDIUM" else "SUCCESS")
        self.record_agent_log(
            order_state,
            action="FraudEvaluationSummary",
            status=log_status,
            message=f"Fraud evaluation completed with score {score}/100 (Tier: {risk_tier}). Decision: {decision}.",
            start_time=start_time,
            details={
                "fraud_score": score,
                "risk_tier": risk_tier,
                "decision": decision,
                "risk_factors_count": len(risk_factors),
            },
        )

        # Return False if escalated to hold
        return risk_tier != "HIGH"
