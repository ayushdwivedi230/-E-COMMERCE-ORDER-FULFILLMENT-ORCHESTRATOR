import React, { useState, useEffect, useMemo } from "react";
import {
  Search,
  RefreshCw,
  Filter,
  Eye,
  CheckCircle2,
  ShieldAlert,
  Clock,
  XCircle,
  Truck,
} from "lucide-react";
import { fetchOrders } from "../api";
import type { OrderSummary } from "../types";

interface OrderManagementPageProps {
  onViewOrder: (orderId: string) => void;
  onNavigateToCreate: () => void;
}

export const OrderManagementPage: React.FC<OrderManagementPageProps> = ({
  onViewOrder,
  onNavigateToCreate,
}) => {
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const loadOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchOrders();
      setOrders(data);
    } catch (e: any) {
      setError(e.message || "Failed to load orders");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();
  }, []);

  const filteredOrders = useMemo(() => {
    return orders.filter((o) => {
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        o.order_id.toLowerCase().includes(q) ||
        o.customer_id.toLowerCase().includes(q) ||
        (o.customer_name && o.customer_name.toLowerCase().includes(q)) ||
        (o.tracking_id && o.tracking_id.toLowerCase().includes(q));

      const matchesStatus =
        statusFilter === "ALL" ||
        (statusFilter === "DISPATCHED" && o.status === "DISPATCHED") ||
        (statusFilter === "HELD" && o.status === "HELD") ||
        (statusFilter === "PROCESSING" && (o.status === "PENDING" || o.status === "PROCESSING")) ||
        (statusFilter === "REJECTED" && (o.status.includes("REJECT") || o.status === "CANCELLED"));

      return matchesSearch && matchesStatus;
    });
  }, [orders, searchQuery, statusFilter]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "DISPATCHED":
        return {
          icon: CheckCircle2,
          bg: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
          label: "DISPATCHED",
        };
      case "HELD":
        return {
          icon: ShieldAlert,
          bg: "bg-rose-500/15 text-rose-400 border-rose-500/30",
          label: "HELD (FRAUD)",
        };
      case "REJECTED_FRAUD":
      case "CANCELLED":
        return {
          icon: XCircle,
          bg: "bg-red-500/15 text-red-400 border-red-500/30",
          label: "REJECTED",
        };
      default:
        return {
          icon: Clock,
          bg: "bg-amber-500/15 text-amber-400 border-amber-500/30",
          label: status,
        };
    }
  };

  const getFraudScoreBadge = (score: number) => {
    if (score >= 70) {
      return "bg-rose-500/15 text-rose-400 border-rose-500/30";
    }
    if (score >= 30) {
      return "bg-amber-500/15 text-amber-400 border-amber-500/30";
    }
    return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
  };

  return (
    <div className="space-y-4">
      {/* Search and Filters Toolbar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search Order ID, Customer, Tracking..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Filter Tabs & Refresh */}
        <div className="flex items-center gap-2 w-full md:w-auto justify-between md:justify-end">
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400 ml-1.5 mr-0.5" />
            {(["ALL", "DISPATCHED", "HELD", "PROCESSING", "REJECTED"] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setStatusFilter(filter)}
                className={`px-2.5 py-1 rounded text-[11px] font-semibold transition ${
                  statusFilter === filter
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {filter}
              </button>
            ))}
          </div>

          <button
            onClick={loadOrders}
            disabled={loading}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            title="Refresh order database"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Orders Data Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-sm overflow-hidden">
        {loading && orders.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <RefreshCw className="w-6 h-6 animate-spin text-indigo-500 mx-auto mb-2" />
            Loading live orders...
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-400 text-xs">
            <p className="font-semibold mb-2">{error}</p>
            <button
              onClick={loadOrders}
              className="px-3 py-1 bg-rose-900/50 hover:bg-rose-900 border border-rose-700 text-white rounded text-xs"
            >
              Retry
            </button>
          </div>
        ) : filteredOrders.length === 0 ? (
          <div className="p-12 text-center text-slate-400 space-y-3">
            <p className="text-sm">No orders matching current search & filter criteria.</p>
            <button
              onClick={onNavigateToCreate}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded text-xs"
            >
              Place an Order in Create Order Tab
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 border-b border-slate-800 text-[11px] font-semibold text-slate-400">
                <tr>
                  <th className="py-3 px-4">Order ID</th>
                  <th className="py-3 px-4">Customer</th>
                  <th className="py-3 px-4">Date & Time</th>
                  <th className="py-3 px-4">Items</th>
                  <th className="py-3 px-4">Total Amount</th>
                  <th className="py-3 px-4">Fraud Risk</th>
                  <th className="py-3 px-4">Fulfillment Status</th>
                  <th className="py-3 px-4">Tracking ID</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredOrders.map((order) => {
                  const statusInfo = getStatusBadge(order.status);
                  const StatusIcon = statusInfo.icon;
                  const dateStr = order.created_at
                    ? new Date(order.created_at).toLocaleString([], {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "—";

                  return (
                    <tr
                      key={order.order_id}
                      className="hover:bg-slate-800/40 transition cursor-pointer"
                      onClick={() => onViewOrder(order.order_id)}
                    >
                      {/* Order ID */}
                      <td className="py-3 px-4 font-mono font-bold text-slate-100">
                        {order.order_id}
                      </td>

                      {/* Customer */}
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-200">
                          {order.customer_name || order.customer_id}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {order.customer_id}
                        </div>
                      </td>

                      {/* Date */}
                      <td className="py-3 px-4 text-slate-400 text-[11px]">
                        {dateStr}
                      </td>

                      {/* Items */}
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {order.item_count || 1} item(s)
                      </td>

                      {/* Total Amount */}
                      <td className="py-3 px-4 font-mono font-bold text-emerald-400">
                        ${Number(order.final_amount).toFixed(2)}
                      </td>

                      {/* Fraud Score */}
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getFraudScoreBadge(
                            order.fraud_score
                          )}`}
                        >
                          {order.fraud_score} / 100
                        </span>
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${statusInfo.bg}`}
                        >
                          <StatusIcon className="w-3 h-3" />
                          {statusInfo.label}
                        </span>
                      </td>

                      {/* Tracking ID */}
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {order.tracking_id ? (
                          <span className="flex items-center gap-1 text-emerald-400">
                            <Truck className="w-3 h-3" />
                            {order.tracking_id}
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onViewOrder(order.order_id);
                          }}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-indigo-600 text-slate-300 hover:text-white transition font-medium text-[11px] flex items-center gap-1 ml-auto"
                        >
                          <Eye className="w-3 h-3" />
                          Details
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
