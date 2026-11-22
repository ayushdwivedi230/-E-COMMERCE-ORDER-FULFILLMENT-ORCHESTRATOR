import React, { useState, useEffect } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  ShieldAlert,
  Clock,
  Truck,
  DollarSign,
  Package,
  Layers,
  MapPin,
  CreditCard,
  RefreshCw,
  Mail,
  MessageSquare,
} from "lucide-react";
import { fetchOrderDetails, fetchOrders } from "../api";
import type { FullOrderDetails, OrderSummary } from "../types";

interface OrderDetailsPageProps {
  orderId: string | null;
  onBack: () => void;
  onSelectOrder: (orderId: string) => void;
}

export const OrderDetailsPage: React.FC<OrderDetailsPageProps> = ({
  orderId,
  onBack,
  onSelectOrder,
}) => {
  const [orderDetails, setOrderDetails] = useState<FullOrderDetails | null>(null);
  const [ordersList, setOrdersList] = useState<OrderSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // If no orderId is provided, fetch list of recent orders for quick selection
    if (!orderId) {
      fetchOrders().then((list) => {
        setOrdersList(list);
        if (list.length > 0) {
          onSelectOrder(list[0].order_id);
        }
      });
    } else {
      loadDetails(orderId);
    }
  }, [orderId]);

  const loadDetails = async (id: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchOrderDetails(id);
      setOrderDetails(data);
    } catch (e: any) {
      setError(e.message || "Failed to load order details");
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (st: string) => {
    switch (st) {
      case "DISPATCHED":
        return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
      case "HELD":
        return "bg-rose-500/15 text-rose-400 border-rose-500/30";
      case "REJECTED_FRAUD":
        return "bg-red-500/15 text-red-400 border-red-500/30";
      default:
        return "bg-amber-500/15 text-amber-400 border-amber-500/30";
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mb-3" />
        <p className="text-sm font-medium">Retrieving full order ledger and agent audit trail...</p>
      </div>
    );
  }

  if (error || !orderDetails) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-4">
        <p className="text-sm text-slate-300 font-semibold">{error || "No order selected"}</p>
        {ordersList.length > 0 && (
          <div className="max-w-md mx-auto space-y-2">
            <span className="text-xs text-slate-400 block">Select an order to inspect:</span>
            <div className="grid grid-cols-2 gap-2">
              {ordersList.slice(0, 4).map((o) => (
                <button
                  key={o.order_id}
                  onClick={() => onSelectOrder(o.order_id)}
                  className="p-2 rounded bg-slate-950 border border-slate-800 hover:border-indigo-500 text-xs font-mono text-left"
                >
                  <div className="font-bold text-slate-200">{o.order_id}</div>
                  <div className="text-[10px] text-slate-400">{o.status}</div>
                </button>
              ))}
            </div>
          </div>
        )}
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Orders
        </button>
      </div>
    );
  }

  const createdDate = orderDetails.created_at
    ? new Date(orderDetails.created_at).toLocaleString([], {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "—";

  return (
    <div className="space-y-6">
      {/* Top Bar with Back Button & Status Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <button
            onClick={onBack}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition shadow-sm"
            title="Back to Order Management"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-xl font-bold text-slate-100 font-mono">
                {orderDetails.order_id}
              </h2>
              <span
                className={`px-3 py-1 rounded-full text-xs font-mono font-bold border ${getStatusColor(
                  orderDetails.status
                )}`}
              >
                {orderDetails.status}
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1 font-medium">
              Placed on {createdDate} &bull; Customer ID: <span className="font-mono text-slate-300">{orderDetails.customer_id}</span>
            </p>
          </div>
        </div>

        <div className="text-right">
          <span className="text-xs uppercase font-bold tracking-wider text-slate-400 block mb-1">
            Final Payable Amount
          </span>
          <span className="text-3xl font-black font-mono text-emerald-400">
            ${Number(orderDetails.total_amount || 0).toFixed(2)}
          </span>
        </div>
      </div>

      {/* Grid: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Items, Pricing Breakdown & Addresses */}
        <div className="lg:col-span-7 space-y-6">
          {/* Purchased Items Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
              <Package className="w-5 h-5 text-indigo-400" />
              Line Items & Inventory Reservation
            </h3>

            <div className="divide-y divide-slate-800/80">
              {orderDetails.items.map((item, idx) => (
                <div key={idx} className="py-3.5 flex items-center justify-between text-sm">
                  <div>
                    <div className="font-bold text-slate-100 text-sm">{item.name}</div>
                    <div className="text-xs font-mono text-slate-400 mt-0.5">
                      SKU: {item.sku} &bull; Qty: {item.quantity} &times; ${Number(item.unit_price || 0).toFixed(2)}
                    </div>
                  </div>
                  <div className="font-mono font-bold text-slate-100 text-sm">
                    ${Number(item.total_price || 0).toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Deterministic Financial Pricing Breakdown Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
              <DollarSign className="w-5 h-5 text-emerald-400" />
              Pricing Agent Deterministic Decimal Ledger
            </h3>

            <div className="space-y-3 text-sm font-mono">
              <div className="flex justify-between text-slate-200">
                <span className="font-sans text-slate-400">Subtotal</span>
                <span>${Number(orderDetails.subtotal || 0).toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-emerald-400 font-semibold">
                <span className="font-sans text-slate-400">Discounts Applied</span>
                <span>-${Number(orderDetails.discount_amount || 0).toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-slate-200">
                <span className="font-sans text-slate-400">Sales Tax (8%)</span>
                <span>+${Number(orderDetails.tax_amount || 0).toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-slate-200">
                <span className="font-sans text-slate-400">Shipping Charges</span>
                <span>+${Number(orderDetails.shipping_cost || 0).toFixed(2)}</span>
              </div>
              <div className="border-t border-slate-800 pt-3 flex justify-between text-base font-bold text-slate-100">
                <span className="font-sans">Total Payable</span>
                <span className="text-emerald-400 text-lg">${Number(orderDetails.total_amount || 0).toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* Addresses & Payment Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm text-sm space-y-2">
              <div className="font-bold text-xs uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <MapPin className="w-4 h-4 text-indigo-400" /> Shipping Destination
              </div>
              <div className="text-slate-200 leading-relaxed font-medium">
                {orderDetails.shipping_address || "Standard Ground Destination"}
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm text-sm space-y-2">
              <div className="font-bold text-xs uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <CreditCard className="w-4 h-4 text-indigo-400" /> Payment & Billing
              </div>
              <div className="text-slate-200 font-mono font-medium">
                Method: {orderDetails.payment_method}
              </div>
              {orderDetails.billing_address && (
                <div className="text-xs text-slate-400 truncate mt-1">
                  Billing: {orderDetails.billing_address}
                </div>
              )}
            </div>
          </div>

          {/* Carrier Dispatch & Tracking Stepper */}
          {orderDetails.shipment && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5 border-b border-slate-800 pb-2.5">
                <Truck className="w-4 h-4 text-cyan-400" />
                Dispatch Coordinator Courier Logistics
              </h3>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono mb-4">
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-sans block">Carrier</span>
                  <span className="font-bold text-slate-200">{orderDetails.shipment.carrier}</span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-sans block">Method</span>
                  <span className="font-bold text-slate-200">{orderDetails.shipment.shipping_method}</span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-sans block">Tracking ID</span>
                  <span className="font-bold text-emerald-400">{orderDetails.shipment.tracking_id}</span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-400 font-sans block">Est. Delivery</span>
                  <span className="font-bold text-slate-200">
                    {orderDetails.shipment.estimated_delivery
                      ? new Date(orderDetails.shipment.estimated_delivery).toLocaleDateString()
                      : "2-3 Business Days"}
                  </span>
                </div>
              </div>

              {/* Transit Stepper Simulation */}
              <div className="flex items-center justify-between text-[11px] text-slate-400 px-2 pt-2">
                <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Manifest Created</span>
                </div>
                <div className="h-0.5 flex-1 mx-2 bg-emerald-500/40" />
                <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Carrier Dispatched</span>
                </div>
                <div className="h-0.5 flex-1 mx-2 bg-slate-800" />
                <div className="flex items-center gap-1.5 text-slate-500">
                  <Clock className="w-4 h-4" />
                  <span>In Transit</span>
                </div>
                <div className="h-0.5 flex-1 mx-2 bg-slate-800" />
                <div className="flex items-center gap-1.5 text-slate-500">
                  <Package className="w-4 h-4" />
                  <span>Delivered</span>
                </div>
              </div>
            </div>
          )}

          {/* Customer Notification Preview (Drafted by NotificationAgent) */}
          {orderDetails.notification_draft && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                  <Mail className="w-4 h-4 text-emerald-400" />
                  Customer Notification Draft
                </h3>
                <span className="text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                  NotificationAgent &bull; Preview Mode
                </span>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between text-slate-400 bg-slate-950 p-2 rounded border border-slate-800/80">
                  <span className="font-semibold text-slate-300">Recipient:</span>
                  <span className="font-mono text-slate-400">{orderDetails.notification_draft.recipient_email || "customer@example.com"}</span>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                  <div className="font-bold text-slate-200 border-b border-slate-800/60 pb-1.5 flex items-center justify-between">
                    <span>Subject: {orderDetails.notification_draft.subject}</span>
                    <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/20">
                      {orderDetails.notification_draft.intent}
                    </span>
                  </div>
                  <p className="text-slate-300 whitespace-pre-wrap leading-relaxed text-[11px] font-sans">
                    {orderDetails.notification_draft.body}
                  </p>
                </div>

                {orderDetails.notification_draft.sms_summary && (
                  <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80 flex items-start gap-2">
                    <MessageSquare className="w-3.5 h-3.5 text-cyan-400 mt-0.5 shrink-0" />
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide block">SMS Summary Preview:</span>
                      <span className="text-slate-300 font-mono text-[11px]">{orderDetails.notification_draft.sms_summary}</span>
                    </div>
                  </div>
                )}

                <div className="text-[10px] text-slate-500 italic flex items-center gap-1 pt-1">
                  <span>* Simulated preview drafted by NotificationAgent. External transmission disabled to prevent unconfigured gateway charges.</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Chronological Agent Execution Timeline & Audit Trail */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center justify-between border-b border-slate-800 pb-2.5">
              <span className="flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-indigo-400" />
                Agent Execution Timeline
              </span>
              <span className="text-[10px] font-mono text-slate-400">
                {orderDetails.agent_logs.length} step(s)
              </span>
            </h3>

            {orderDetails.agent_logs.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-4">No execution logs recorded.</p>
            ) : (
              <div className="relative pl-6 space-y-4 border-l-2 border-slate-800 ml-2">
                {orderDetails.agent_logs.map((log, index) => {
                  const isSuccess = log.status === "SUCCESS";
                  const isHeld = log.status === "HELD" || log.status === "FAILED";
                  const dateStr = log.created_at
                    ? new Date(log.created_at).toLocaleTimeString()
                    : "";

                  return (
                    <div key={index} className="relative group">
                      {/* Timeline Dot */}
                      <span
                        className={`absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full border-2 ${
                          isSuccess
                            ? "bg-emerald-500 border-slate-900"
                            : isHeld
                            ? "bg-rose-500 border-slate-900"
                            : "bg-amber-500 border-slate-900"
                        }`}
                      />

                      <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-slate-200">
                            {log.agent_name}
                          </span>
                          <span className="text-[10px] font-mono text-slate-400">
                            {log.execution_time_ms} ms &bull; {dateStr}
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5">
                          <span
                            className={`px-1.5 py-0.2 rounded text-[9px] font-mono font-bold border ${
                              isSuccess
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : isHeld
                                ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                                : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            }`}
                          >
                            {log.status}
                          </span>
                          <span className="text-[11px] font-mono text-slate-400">
                            {log.action}
                          </span>
                        </div>

                        <div className="text-[11px] text-slate-300 font-sans leading-relaxed pt-1">
                          {log.message}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Fraud Review Audit Section (if flagged or held) */}
          {orderDetails.fraud_reviews && orderDetails.fraud_reviews.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5 border-b border-slate-800 pb-2.5">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                Fraud Agent Audit Assessment
              </h3>

              {orderDetails.fraud_reviews.map((rev, idx) => (
                <div key={idx} className="space-y-2 text-xs">
                  <div className="flex items-center justify-between font-mono">
                    <span className="text-slate-400">Risk Score:</span>
                    <span className="font-bold text-rose-400">{rev.fraud_score} / 100</span>
                  </div>
                  <div className="flex items-center justify-between font-mono">
                    <span className="text-slate-400">Decision:</span>
                    <span className="font-bold text-amber-400">{rev.decision}</span>
                  </div>

                  {(() => {
                    const parsed = Array.isArray(rev.reasons)
                      ? rev.reasons
                      : typeof rev.reasons === "string"
                      ? (() => {
                          try {
                            const p = JSON.parse(rev.reasons);
                            return Array.isArray(p) ? p : [rev.reasons];
                          } catch {
                            return [rev.reasons];
                          }
                        })()
                      : [];
                    return parsed.length > 0 && parsed[0] !== "None" ? (
                      <div className="pt-1">
                        <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                          Trigger Reasons:
                        </span>
                        <ul className="list-disc pl-4 text-rose-300 space-y-0.5 text-[11px]">
                          {parsed.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null;
                  })()}

                  {rev.ai_explanation && (
                    <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-[11px] text-slate-300">
                      {rev.ai_explanation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
