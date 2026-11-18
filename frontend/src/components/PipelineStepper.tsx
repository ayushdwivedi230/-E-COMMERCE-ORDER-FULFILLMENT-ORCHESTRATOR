import React from "react";
import { CheckCircle2, AlertOctagon, Clock, ShieldAlert, Cpu } from "lucide-react";
import type { OrderState } from "../types";

interface PipelineStepperProps {
  orderState: OrderState | null;
  isProcessing: boolean;
}

export const PipelineStepper: React.FC<PipelineStepperProps> = ({ orderState, isProcessing }) => {
  const getAgentStepTime = (agentName: string): number => {
    if (!orderState) return 0;
    const log = orderState.agent_execution_logs.find((l) => l.agent_name === agentName);
    return log ? log.execution_time_ms : 0;
  };

  const steps = [
    {
      id: "validation",
      name: "1. Validation Agent",
      role: "Input & Catalog Verification",
      status: orderState
        ? orderState.validation_status === "PASSED"
          ? "success"
          : "error"
        : isProcessing
        ? "active"
        : "idle",
      timeMs: getAgentStepTime("ValidationAgent"),
    },
    {
      id: "inventory",
      name: "2. Inventory Agent",
      role: "Atomic Stock Reservation",
      status: orderState
        ? orderState.inventory_status === "RESERVED"
          ? "success"
          : orderState.inventory_status === "SKIPPED"
          ? "skipped"
          : "error"
        : "idle",
      timeMs: getAgentStepTime("InventoryAgent"),
    },
    {
      id: "fraud",
      name: "3. Fraud Check Agent",
      role: "Deterministic Scoring & Memory",
      status: orderState
        ? orderState.fraud_status === "HIGH_RISK_HELD"
          ? "error"
          : orderState.fraud_status === "MEDIUM_RISK"
          ? "warning"
          : orderState.fraud_status === "LOW_RISK"
          ? "success"
          : "skipped"
        : "idle",
      timeMs: getAgentStepTime("FraudCheckAgent"),
      score: orderState ? orderState.fraud_score : null,
    },
    {
      id: "pricing",
      name: "4. Pricing Agent",
      role: "Decimal Financial Arithmetic",
      status: orderState
        ? orderState.pricing_status === "CALCULATED"
          ? "success"
          : "skipped"
        : "idle",
      timeMs: getAgentStepTime("PricingAgent"),
    },
    {
      id: "dispatch",
      name: "5. Dispatch Coordinator",
      role: "Carrier Logistics & Tracking",
      status: orderState
        ? orderState.dispatch_status === "DISPATCHED"
          ? "success"
          : orderState.dispatch_status === "HELD"
          ? "held"
          : "idle"
        : "idle",
      timeMs: getAgentStepTime("DispatchCoordinator"),
    },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Cpu className="w-5 h-5 text-indigo-400" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
            Microsoft Agent Framework — 5-Agent Fulfillment Pipeline
          </h2>
        </div>
        {orderState && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Order ID:</span>
            <span className="text-xs font-mono font-bold bg-slate-800 text-indigo-300 px-2 py-0.5 rounded">
              {orderState.order_id}
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {steps.map((step) => {
          let badgeColor = "border-slate-800 bg-slate-950/60 text-slate-400";
          let icon = <Clock className="w-4 h-4 text-slate-500" />;

          if (step.status === "success") {
            badgeColor = "border-emerald-500/30 bg-emerald-950/30 text-emerald-300";
            icon = <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
          } else if (step.status === "error" || step.status === "held") {
            badgeColor = "border-rose-500/40 bg-rose-950/40 text-rose-300";
            icon = <AlertOctagon className="w-4 h-4 text-rose-400" />;
          } else if (step.status === "warning") {
            badgeColor = "border-amber-500/40 bg-amber-950/40 text-amber-300";
            icon = <ShieldAlert className="w-4 h-4 text-amber-400" />;
          } else if (step.status === "active") {
            badgeColor = "border-indigo-500/50 bg-indigo-950/40 text-indigo-300 animate-pulse";
            icon = <Clock className="w-4 h-4 text-indigo-400 animate-spin" />;
          }

          return (
            <div
              key={step.id}
              className={`relative border rounded-xl p-4 transition-all shadow-sm ${badgeColor}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold truncate">{step.name}</span>
                {icon}
              </div>
              <div className="text-xs text-slate-400 line-clamp-1">{step.role}</div>

              <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <span className="text-slate-400">Status:</span>
                <span className="font-semibold uppercase tracking-wider">{step.status}</span>
              </div>

              {step.timeMs > 0 && (
                <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
                  <span>Latency:</span>
                  <span className="font-mono text-slate-300 font-semibold">{step.timeMs}ms</span>
                </div>
              )}

              {step.score !== null && (
                <div className="flex items-center justify-between text-xs mt-1">
                  <span className="text-slate-400">Risk Score:</span>
                  <span className="font-mono font-bold text-amber-300">{step.score}/100</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {orderState && orderState.hold_reason && (
        <div className="mt-4 p-4 rounded-xl bg-rose-950/40 border border-rose-800/50 flex items-start gap-3">
          <ShieldAlert className="w-6 h-6 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <div className="text-sm font-bold text-rose-300 uppercase tracking-wide">
              Pipeline Escalation — Order Held
            </div>
            <div className="text-sm text-rose-200 mt-1 leading-relaxed">{orderState.hold_reason}</div>
          </div>
        </div>
      )}

      {orderState && orderState.dispatch_status === "DISPATCHED" && (
        <div className="mt-4 p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
            <div>
              <div className="text-sm font-bold text-emerald-300 uppercase tracking-wide">
                Order Dispatched Successfully
              </div>
              <div className="text-xs text-emerald-200 mt-1">
                Carrier: {orderState.carrier} | Method: {orderState.shipping_method}
              </div>
            </div>
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-400 font-medium">Tracking Number</span>
            <div className="font-mono font-bold text-base text-emerald-400 mt-0.5">{orderState.tracking_id}</div>
          </div>
        </div>
      )}
    </div>
  );
};
