import React, { useState } from "react";
import { History } from "lucide-react";
import type { Customer } from "../types";

interface CustomerMemoryViewProps {
  customers: Customer[];
  onSelectCustomerForOrder?: (customer: Customer) => void;
}

export const CustomerMemoryView: React.FC<CustomerMemoryViewProps> = ({
  customers,
  onSelectCustomerForOrder,
}) => {
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(
    customers.length > 0 ? customers[0] : null
  );

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-indigo-400" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
            Prior-Order Customer Memory & Historical Risk Profiler
          </h2>
        </div>
        <span className="text-xs text-slate-400">Isolated from current order in flight</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Customer List */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Select Customer
          </div>
          {customers.map((c) => {
            const isSelected = selectedCustomer?.id === c.id;
            const tier = c.history_stats?.risk_tier || "LOW";
            const badgeColor =
              tier === "HIGH"
                ? "bg-rose-950 text-rose-400 border-rose-800"
                : tier === "MEDIUM"
                ? "bg-amber-950 text-amber-400 border-amber-800"
                : "bg-emerald-950 text-emerald-400 border-emerald-800";

            return (
              <div
                key={c.id}
                onClick={() => setSelectedCustomer(c)}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  isSelected
                    ? "bg-indigo-950/40 border-indigo-500/60 shadow"
                    : "bg-slate-950 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-slate-200">{c.name}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border uppercase font-mono font-bold ${badgeColor}`}>
                    {tier}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">{c.id}</div>
                <div className="text-[11px] text-slate-500 truncate">{c.email}</div>
              </div>
            );
          })}
        </div>

        {/* Selected Customer Detailed Memory */}
        {selectedCustomer && selectedCustomer.history_stats && (
          <div className="md:col-span-3 bg-slate-950 border border-slate-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4 border-b border-slate-800/80 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-200">{selectedCustomer.name}</h3>
                <div className="text-xs text-slate-400 mt-0.5">
                  ID: <span className="font-mono text-slate-300">{selectedCustomer.id}</span> | Status:{" "}
                  <span className="font-semibold text-slate-300">{selectedCustomer.status}</span>
                </div>
                <div className="text-xs text-slate-400 mt-0.5">
                  Address: <span className="text-slate-300">{selectedCustomer.address}</span>
                </div>
              </div>

              {onSelectCustomerForOrder && (
                <button
                  onClick={() => onSelectCustomerForOrder(selectedCustomer)}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-semibold shadow transition-all"
                >
                  Use for New Order
                </button>
              )}
            </div>

            {/* Memory Statistics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <div className="bg-slate-900 border border-slate-800 rounded p-2.5">
                <span className="text-[10px] text-slate-400 uppercase">Total Past Orders</span>
                <div className="text-base font-bold text-slate-200 mt-0.5">
                  {selectedCustomer.history_stats.total_orders}
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded p-2.5">
                <span className="text-[10px] text-slate-400 uppercase">Successful Orders</span>
                <div className="text-base font-bold text-emerald-400 mt-0.5">
                  {selectedCustomer.history_stats.successful_orders}
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded p-2.5">
                <span className="text-[10px] text-slate-400 uppercase">Suspicious / Disputes</span>
                <div className="text-base font-bold text-rose-400 mt-0.5">
                  {selectedCustomer.history_stats.suspicious_orders}
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded p-2.5">
                <span className="text-[10px] text-slate-400 uppercase">Avg Order Value</span>
                <div className="text-base font-bold text-indigo-300 mt-0.5">
                  ${Number(selectedCustomer.history_stats.average_order_value || 0).toFixed(2)}
                </div>
              </div>
            </div>

            {/* Prior Transactions Table */}
            <div>
              <div className="text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wide">
                Prior Order Memory Log ({selectedCustomer.history_stats.prior_orders.length} entries)
              </div>

              {selectedCustomer.history_stats.prior_orders.length === 0 ? (
                <div className="text-xs text-slate-500 py-3 text-center bg-slate-900/60 rounded border border-slate-800">
                  No previous order history for this customer. Evaluated as new customer.
                </div>
              ) : (
                <div className="border border-slate-800 rounded overflow-hidden">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-900 text-slate-400 text-[11px] uppercase">
                      <tr>
                        <th className="py-2 px-3">Order ID</th>
                        <th className="py-2 px-3">Status</th>
                        <th className="py-2 px-3">Amount</th>
                        <th className="py-2 px-3">Suspicious</th>
                        <th className="py-2 px-3">Failed Retries</th>
                        <th className="py-2 px-3">Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {selectedCustomer.history_stats.prior_orders.map((order) => (
                        <tr
                          key={order.id}
                          className={order.is_suspicious ? "bg-rose-950/20" : "bg-slate-950/40"}
                        >
                          <td className="py-2 px-3 text-slate-300">{order.order_id}</td>
                          <td className="py-2 px-3">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                order.status === "DELIVERED"
                                  ? "bg-emerald-950 text-emerald-400"
                                  : "bg-rose-950 text-rose-400"
                              }`}
                            >
                              {order.status}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-slate-300">${Number(order.amount || 0).toFixed(2)}</td>
                          <td className="py-2 px-3">
                            {order.is_suspicious ? (
                              <span className="text-rose-400 font-bold">YES</span>
                            ) : (
                              <span className="text-slate-500">No</span>
                            )}
                          </td>
                          <td className="py-2 px-3 text-slate-300">{order.failed_payment_attempts}</td>
                          <td className="py-2 px-3 text-slate-400 font-sans text-[11px]">{order.notes || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
