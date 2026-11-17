import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  RefreshCw,
  AlertTriangle,
  History,
  Info,
} from "lucide-react";
import { fetchHeldOrders, overrideHeldOrder, rejectHeldOrder, fetchCustomerMemory } from "../api";
import type { HeldOrder, CustomerHistoryStats } from "../types";

interface FraudReviewPageProps {
  onViewOrderDetails?: (orderId: string) => void;
  onRefreshMetrics?: () => void;
}

export const FraudReviewPage: React.FC<FraudReviewPageProps> = ({
  onViewOrderDetails,
  onRefreshMetrics,
}) => {
  const [heldOrders, setHeldOrders] = useState<HeldOrder[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [customerStats, setCustomerStats] = useState<CustomerHistoryStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [auditorNotes, setAuditorNotes] = useState<string>("");
  const [statusMessage, setStatusMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadQueue = async () => {
    try {
      setLoading(true);
      const data = await fetchHeldOrders();
      setHeldOrders(data);
      if (data.length > 0 && !selectedOrderId) {
        setSelectedOrderId(data[0].order_id);
      } else if (data.length === 0) {
        setSelectedOrderId(null);
        setCustomerStats(null);
      }
    } catch (e: any) {
      console.error("Failed to load held orders queue:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const selectedOrder = heldOrders.find((o) => o.order_id === selectedOrderId);

  // Load customer memory whenever selected order changes
  useEffect(() => {
    if (selectedOrder?.customer_id) {
      fetchCustomerMemory(selectedOrder.customer_id)
        .then((stats) => setCustomerStats(stats))
        .catch(() => setCustomerStats(null));
    } else {
      setCustomerStats(null);
    }
  }, [selectedOrder?.customer_id]);

  const handleApprove = async () => {
    if (!selectedOrderId) return;
    setActionLoading(true);
    setStatusMessage(null);
    try {
      await overrideHeldOrder(selectedOrderId, auditorNotes || "Auditor manual verification passed");
      setStatusMessage({
        type: "success",
        text: `Order ${selectedOrderId} approved. Resumed pipeline: pricing applied & carrier tracking generated.`,
      });
      setAuditorNotes("");
      await loadQueue();
      if (onRefreshMetrics) onRefreshMetrics();
    } catch (e: any) {
      setStatusMessage({ type: "error", text: e.message || "Failed to approve held order" });
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedOrderId) return;
    if (!confirm(`Are you sure you want to permanently reject Order ${selectedOrderId}? Reserved inventory will be released.`)) return;
    setActionLoading(true);
    setStatusMessage(null);
    try {
      await rejectHeldOrder(selectedOrderId, auditorNotes || "Rejected by fraud compliance auditor");
      setStatusMessage({
        type: "success",
        text: `Order ${selectedOrderId} permanently rejected. Inventory reservation released.`,
      });
      setAuditorNotes("");
      await loadQueue();
      if (onRefreshMetrics) onRefreshMetrics();
    } catch (e: any) {
      setStatusMessage({ type: "error", text: e.message || "Failed to reject order" });
    } finally {
      setActionLoading(false);
    }
  };

  const activeReview = selectedOrder?.fraud_reviews?.[0];

  return (
    <div className="space-y-6">
      {/* Alert Message Banner */}
      {statusMessage && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center justify-between ${
            statusMessage.type === "success"
              ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
              : "bg-rose-950/60 border-rose-800 text-rose-300"
          }`}
        >
          <span>{statusMessage.text}</span>
          <button
            onClick={() => setStatusMessage(null)}
            className="text-sm font-bold opacity-80 hover:opacity-100"
          >
            &times;
          </button>
        </div>
      )}

      {/* Main Grid: Queue on Left, Audit Console on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Held Orders Queue */}
        <div className="lg:col-span-4 space-y-3">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Escalation Queue ({heldOrders.length})
              </h3>
            </div>
            <button
              onClick={loadQueue}
              disabled={loading}
              className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition"
              title="Refresh queue"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>

          {loading && heldOrders.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-xs">
              <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-indigo-500" />
              Loading held orders queue...
            </div>
          ) : heldOrders.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-xs space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
              <p className="font-bold text-slate-200">Queue is Clear</p>
              <p className="text-[11px] text-slate-400">
                All incoming transactions have passed automated risk validation or have been resolved.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {heldOrders.map((order) => {
                const isSelected = order.order_id === selectedOrderId;
                const review = order.fraud_reviews?.[0];

                return (
                  <div
                    key={order.order_id}
                    onClick={() => setSelectedOrderId(order.order_id)}
                    className={`p-3.5 rounded-xl border transition cursor-pointer ${
                      isSelected
                        ? "bg-slate-800/90 border-indigo-500 shadow-md shadow-indigo-500/10"
                        : "bg-slate-900 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono font-bold text-xs text-slate-200">
                        {order.order_id}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                        Score: {order.fraud_score}
                      </span>
                    </div>

                    <div className="text-xs text-slate-300 font-medium">
                      {order.customer_name || order.customer_id}
                    </div>

                    <div className="text-[11px] text-slate-400 truncate mt-1">
                      {order.hold_reason || review?.ai_explanation || "Held for manual compliance review"}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Selected Order Audit Console */}
        <div className="lg:col-span-8">
          {selectedOrder ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm space-y-6">
              {/* Header */}
              <div className="flex flex-wrap items-center justify-between border-b border-slate-800 pb-4 gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-slate-100">
                      Audit Investigation: {selectedOrder.order_id}
                    </h3>
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                      STATUS: HELD
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Customer: {selectedOrder.customer_name} ({selectedOrder.customer_id})
                  </p>
                </div>

                {onViewOrderDetails && (
                  <button
                    onClick={() => onViewOrderDetails(selectedOrder.order_id)}
                    className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 underline"
                  >
                    View Full Order Breakdown &rarr;
                  </button>
                )}
              </div>

              {/* Fraud Score Gauge Card */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-950 p-4 rounded-xl border border-slate-800/80">
                {/* Score Gauge */}
                <div className="text-center p-3 border-b md:border-b-0 md:border-r border-slate-800">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                    Calculated Risk Score
                  </span>
                  <div className="text-4xl font-black font-mono text-rose-400">
                    {selectedOrder.fraud_score}
                    <span className="text-xs font-normal text-slate-500"> / 100</span>
                  </div>
                  <span className="inline-block mt-2 px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-rose-950 text-rose-400 border border-rose-800">
                    HIGH RISK ESCALATION
                  </span>
                </div>

                {/* Risk Level & Policy */}
                <div className="p-3 border-b md:border-b-0 md:border-r border-slate-800 flex flex-col justify-center text-xs">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                    Risk Classification
                  </span>
                  <div className="font-semibold text-slate-200">
                    Tier: {activeReview?.risk_level || "HIGH"} (Score &ge; 70)
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Orchestrator Policy: Pipeline immediately halted at Agent 3. Pricing and dispatch blocked.
                  </p>
                </div>

                {/* Financial Value at Risk */}
                <div className="p-3 flex flex-col justify-center text-xs">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                    Cart Value at Risk
                  </span>
                  <div className="text-2xl font-black font-mono text-emerald-400">
                    ${(selectedOrder.total_amount || 0).toFixed(2)}
                  </div>
                  <span className="text-[11px] text-slate-400 mt-1">
                    Items reserved pending compliance decision
                  </span>
                </div>
              </div>

              {/* Detection Trigger Reasons & AI Justification */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  Deterministic Risk Factors Detected
                </h4>
                {activeReview?.reasons && activeReview.reasons.length > 0 ? (
                  <ul className="space-y-1.5">
                    {activeReview.reasons.map((reason, idx) => (
                      <li
                        key={idx}
                        className="p-2.5 rounded bg-rose-950/40 border border-rose-900/60 text-xs text-rose-200 flex items-start gap-2"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-1.5 flex-shrink-0" />
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-400">
                    {selectedOrder.hold_reason || "Escalated by rule threshold."}
                  </div>
                )}

                {/* AI Reasoning Text */}
                {activeReview?.ai_explanation && (
                  <div className="p-3 rounded-lg bg-slate-950 border border-indigo-900/40 text-xs space-y-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 block">
                      Contextual AI Reasoning & Audit Trail
                    </span>
                    <p className="text-slate-300 leading-relaxed font-sans">
                      {activeReview.ai_explanation}
                    </p>
                  </div>
                )}
              </div>

              {/* Customer Prior History & Isolation Memory */}
              {customerStats && (
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                      <History className="w-3.5 h-3.5 text-indigo-400" />
                      Isolated Customer Memory Record
                    </h4>
                    <span className="text-[10px] font-mono text-slate-400">
                      ID: {customerStats.customer_id}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono">
                    <div className="bg-slate-900 p-2 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-400 block font-sans">Delivered Orders</span>
                      <span className="font-bold text-emerald-400">{customerStats.successful_orders}</span>
                    </div>
                    <div className="bg-slate-900 p-2 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-400 block font-sans">Suspicious Past Orders</span>
                      <span className="font-bold text-rose-400">{customerStats.suspicious_orders}</span>
                    </div>
                    <div className="bg-slate-900 p-2 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-400 block font-sans">Historical Spend</span>
                      <span className="font-bold text-slate-200">${customerStats.total_spent.toFixed(2)}</span>
                    </div>
                    <div className="bg-slate-900 p-2 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-400 block font-sans">Suspicion Rate</span>
                      <span className="font-bold text-amber-400">{customerStats.suspicion_rate}%</span>
                    </div>
                  </div>

                  {/* Prior Orders Mini-Table */}
                  {customerStats.prior_orders && customerStats.prior_orders.length > 0 && (
                    <div className="text-[11px] text-slate-400 space-y-1">
                      <span className="text-[10px] font-semibold text-slate-400 block">
                        Prior Historical Transactions (Independent of Current Order):
                      </span>
                      <div className="space-y-1 max-h-32 overflow-y-auto">
                        {customerStats.prior_orders.map((po) => (
                          <div
                            key={po.id}
                            className="flex items-center justify-between p-1.5 rounded bg-slate-900/80 border border-slate-800 text-[10px]"
                          >
                            <span className="font-mono text-slate-300">{po.order_id}</span>
                            <span className="text-slate-400">${Number(po.amount).toFixed(2)}</span>
                            <span
                              className={`px-1.5 py-0.2 rounded font-mono font-bold ${
                                po.is_suspicious ? "text-rose-400" : "text-emerald-400"
                              }`}
                            >
                              {po.status}
                            </span>
                            <span className="text-slate-500 truncate max-w-[150px]">
                              {po.notes || "Clean"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Auditor Controls & Decision Actions */}
              <div className="border-t border-slate-800 pt-4 space-y-3">
                <label className="block text-[11px] font-semibold text-slate-300">
                  Auditor Verification Notes (Persisted to Order Audit Trail)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Identity verified via phone confirmation; payment approved."
                  value={auditorNotes}
                  onChange={(e) => setAuditorNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />

                <div className="flex items-center gap-3 pt-1">
                  {/* Approve Button */}
                  <button
                    onClick={handleApprove}
                    disabled={actionLoading}
                    className="flex-1 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg shadow text-xs flex items-center justify-center gap-2 transition disabled:opacity-50"
                  >
                    {actionLoading ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-4 h-4" />
                    )}
                    <span>Approve & Resume Fulfillment</span>
                  </button>

                  {/* Reject Button */}
                  <button
                    onClick={handleReject}
                    disabled={actionLoading}
                    className="flex-1 py-2.5 px-4 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-lg shadow text-xs flex items-center justify-center gap-2 transition disabled:opacity-50"
                  >
                    {actionLoading ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <XCircle className="w-4 h-4" />
                    )}
                    <span>Reject & Release Stock</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-500 shadow-sm">
              <Info className="w-10 h-10 mx-auto text-slate-600 mb-2" />
              <p className="text-sm font-semibold text-slate-400">No Order Selected</p>
              <p className="text-xs text-slate-500 mt-1">
                Select an order from the escalation queue on the left to review its risk factors and audit history.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
