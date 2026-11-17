import React, { useState, useEffect } from "react";
import { ShieldAlert, CheckCircle, RefreshCw } from "lucide-react";
import { fetchHeldOrders, overrideHeldOrder } from "../api";

export const FraudQueueView: React.FC = () => {
  const [heldOrders, setHeldOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadQueue = async () => {
    setLoading(true);
    try {
      const data = await fetchHeldOrders();
      setHeldOrders(data);
    } catch (e: any) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const handleOverride = async (orderId: string) => {
    try {
      await overrideHeldOrder(orderId);
      setMessage(`Order ${orderId} successfully released from hold and dispatched.`);
      loadQueue();
    } catch (e: any) {
      alert(`Error overriding order: ${e.message}`);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-rose-400" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
            Fraud Escalation Hold Queue & Audit Management
          </h2>
        </div>
        <button
          onClick={loadQueue}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Queue
        </button>
      </div>

      {message && (
        <div className="mb-4 p-3 bg-emerald-950/60 border border-emerald-800 rounded-lg text-emerald-300 text-xs flex items-center justify-between">
          <span>{message}</span>
          <button onClick={() => setMessage(null)} className="text-emerald-400 font-bold hover:text-emerald-200">
            ×
          </button>
        </div>
      )}

      {heldOrders.length === 0 ? (
        <div className="text-center py-8 text-slate-500 text-xs">
          No orders currently held in the escalation review queue.
        </div>
      ) : (
        <div className="space-y-4">
          {heldOrders.map((order) => (
            <div
              key={order.order_id}
              className="bg-slate-950 border border-rose-900/40 rounded-lg p-4 shadow"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-sm text-slate-200">
                      {order.order_id}
                    </span>
                    <span className="bg-rose-950 text-rose-400 border border-rose-800 text-[10px] px-2 py-0.5 rounded font-bold uppercase">
                      HELD (Score: {order.fraud_score}/100)
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    Customer: <span className="text-slate-300 font-mono">{order.customer_id}</span>
                  </div>
                </div>

                <button
                  onClick={() => handleOverride(order.order_id)}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold shadow flex items-center gap-1.5 transition"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  Auditor Manual Approval
                </button>
              </div>

              {/* Hold Reason */}
              <div className="mt-3 p-2.5 rounded bg-rose-950/30 border border-rose-900/30 text-xs text-rose-200">
                <span className="font-bold uppercase tracking-wider text-[10px] text-rose-400 block mb-0.5">
                  Escalation Trigger
                </span>
                {order.hold_reason}
              </div>

              {/* AI Explanation */}
              {order.fraud_reviews && order.fraud_reviews.length > 0 && order.fraud_reviews[0].ai_explanation && (
                <div className="mt-2.5 p-2.5 rounded bg-slate-900 border border-slate-800 text-xs text-slate-300">
                  <span className="font-bold uppercase tracking-wider text-[10px] text-indigo-400 block mb-0.5">
                    Contextual AI Reasoning Explanation (Audit Trail)
                  </span>
                  {order.fraud_reviews[0].ai_explanation}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
