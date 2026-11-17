import React, { useEffect, useState } from "react";
import {
  ShoppingBag,
  CheckCircle2,
  AlertTriangle,
  Clock,
  DollarSign,
  ShieldAlert,
  TrendingUp,
  Activity,
  ArrowUpRight,
  RefreshCw,
  Eye,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { fetchDashboardAnalytics } from "../api";
import type { DashboardAnalytics } from "../types";

interface DashboardPageProps {
  onViewOrder: (orderId: string) => void;
  onNavigateToFraud: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onViewOrder,
  onNavigateToFraud,
}) => {
  const [data, setData] = useState<DashboardAnalytics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchDashboardAnalytics();
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mb-3" />
        <p className="text-sm font-medium">Aggregating live multi-agent metrics...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-rose-950/40 border border-rose-800 rounded-xl text-rose-300">
        <div className="flex items-center gap-2 font-bold mb-2">
          <AlertTriangle className="w-5 h-5 text-rose-400" />
          <span>Failed to load live dashboard metrics</span>
        </div>
        <p className="text-xs mb-4">{error}</p>
        <button
          onClick={loadData}
          className="px-3 py-1.5 bg-rose-800 hover:bg-rose-700 text-white rounded text-xs font-semibold"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        {/* Total Orders */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Total Orders</span>
            <div className="w-7 h-7 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
              <ShoppingBag className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black font-mono text-slate-100">
            {data.total_orders}
          </div>
          <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
            <span>Throughput count</span>
          </div>
        </div>

        {/* Completed Orders */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Completed</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black font-mono text-emerald-400">
            {data.completed_orders}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            Dispatched & Tracking Generated
          </div>
        </div>

        {/* Held Orders */}
        <div
          onClick={data.held_orders > 0 ? onNavigateToFraud : undefined}
          className={`bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm transition ${
            data.held_orders > 0
              ? "hover:border-rose-600/60 cursor-pointer group"
              : ""
          }`}
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-rose-300">
              Held Orders
            </span>
            <div className="w-7 h-7 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-400">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black font-mono text-rose-400 flex items-center justify-between">
            <span>{data.held_orders}</span>
            {data.held_orders > 0 && (
              <span className="text-[10px] font-sans font-medium text-rose-400 group-hover:underline flex items-center gap-0.5">
                Review <ArrowUpRight className="w-3 h-3" />
              </span>
            )}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            In Escalation Audit Queue
          </div>
        </div>

        {/* Pending Orders */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Pending</span>
            <div className="w-7 h-7 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black font-mono text-amber-400">
            {data.pending_orders}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            In Validation / Reservation
          </div>
        </div>

        {/* Total Revenue */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Revenue</span>
            <div className="w-7 h-7 rounded-lg bg-cyan-500/10 flex items-center justify-center text-cyan-400">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black font-mono text-cyan-300">
            ${Number(data.total_revenue || 0).toFixed(2)}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            Dispatched gross revenue
          </div>
        </div>

        {/* Average Order Value */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Avg Order</span>
            <div className="w-7 h-7 rounded-lg bg-violet-500/10 flex items-center justify-center text-violet-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black font-mono text-violet-300">
            ${Number(data.average_order_value || 0).toFixed(2)}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            Per fulfilled basket
          </div>
        </div>
      </div>

      {/* Fraud Intelligence & Real Visual Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Fraud Summary Banner */}
        <div className="lg:col-span-12 bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Automated Multi-Agent Fraud Analytics
                </h3>
                <p className="text-[11px] text-slate-400">
                  Dual-tier deterministic rule engine + contextual AI reasoning
                </p>
              </div>
            </div>

            <div className="flex items-center gap-6 text-xs font-mono">
              <div>
                <span className="text-[10px] text-slate-400 block font-sans">Total Evaluated</span>
                <span className="text-sm font-bold text-slate-200">
                  {data.fraud_stats.total_evaluated}
                </span>
              </div>
              <div className="border-l border-slate-800 pl-6">
                <span className="text-[10px] text-slate-400 block font-sans">Avg Risk Score</span>
                <span className="text-sm font-bold text-amber-400">
                  {data.fraud_stats.average_fraud_score} / 100
                </span>
              </div>
              <div className="border-l border-slate-800 pl-6">
                <span className="text-[10px] text-slate-400 block font-sans">Escalation Rate</span>
                <span className="text-sm font-bold text-rose-400">
                  {data.fraud_stats.escalation_rate}%
                </span>
              </div>
              <div className="border-l border-slate-800 pl-6">
                <span className="text-[10px] text-slate-400 block font-sans">High Risk Flags</span>
                <span className="text-sm font-bold text-rose-400">
                  {data.fraud_stats.high_risk_count}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Chart 1: Order Status Distribution (Donut Chart) */}
        <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Order Fulfillment Status
              </h3>
              <p className="text-[11px] text-slate-400">Distribution across pipeline stages</p>
            </div>
          </div>

          <div className="h-60 w-full flex items-center justify-center">
            {data.total_orders === 0 ? (
              <p className="text-xs text-slate-500">No orders placed yet</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.status_distribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {data.status_distribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      borderRadius: "8px",
                      fontSize: "12px",
                      color: "#f8fafc",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="flex justify-center gap-4 mt-2">
            {data.status_distribution.map((item) => (
              <div key={item.name} className="flex items-center gap-1.5 text-xs text-slate-300">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span>{item.name}:</span>
                <span className="font-mono font-bold">{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Chart 2: Fraud Risk Tier Breakdown (Bar Chart) */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Fraud Risk Classification
              </h3>
              <p className="text-[11px] text-slate-400">
                Low (0-29), Medium (30-69), High Escalation (70-100)
              </p>
            </div>
          </div>

          <div className="h-60 w-full">
            {data.fraud_stats.total_evaluated === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-500">
                No orders evaluated by Fraud Check Agent yet
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.risk_distribution}>
                  <XAxis dataKey="tier" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      borderRadius: "8px",
                      fontSize: "12px",
                      color: "#f8fafc",
                    }}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {data.risk_distribution.map((entry, index) => (
                      <Cell key={`bar-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="flex justify-around text-xs text-slate-400 mt-2 font-mono">
            <div>
              Low Risk: <span className="text-emerald-400 font-bold">{data.fraud_stats.low_risk_count}</span>
            </div>
            <div>
              Medium Risk: <span className="text-amber-400 font-bold">{data.fraud_stats.medium_risk_count}</span>
            </div>
            <div>
              High Risk Held: <span className="text-rose-400 font-bold">{data.fraud_stats.high_risk_count}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity Feed */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Live Multi-Agent Activity Stream
            </h3>
          </div>
          <button
            onClick={loadData}
            className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1 transition"
          >
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>

        {data.recent_activity.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No agent execution logs recorded yet. Place an order in Create Order tab to start the pipeline!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800/80 text-[11px] font-semibold text-slate-400">
                  <th className="pb-2.5">Agent</th>
                  <th className="pb-2.5">Order ID</th>
                  <th className="pb-2.5">Action</th>
                  <th className="pb-2.5">Status</th>
                  <th className="pb-2.5">Latency</th>
                  <th className="pb-2.5">Message</th>
                  <th className="pb-2.5 text-right">View</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {data.recent_activity.map((act) => {
                  const getStatusBadge = (st: string) => {
                    switch (st) {
                      case "SUCCESS":
                        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
                      case "HELD":
                      case "FAILED":
                        return "bg-rose-500/10 text-rose-400 border-rose-500/20";
                      case "WARNING":
                        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
                      default:
                        return "bg-indigo-500/10 text-indigo-400 border-indigo-500/20";
                    }
                  };

                  return (
                    <tr key={act.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-2.5 font-semibold text-slate-200">
                        {act.agent_name}
                      </td>
                      <td className="py-2.5 font-mono text-slate-400">
                        {act.order_id}
                      </td>
                      <td className="py-2.5 text-slate-300 font-mono text-[11px]">
                        {act.action}
                      </td>
                      <td className="py-2.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${getStatusBadge(
                            act.status
                          )}`}
                        >
                          {act.status}
                        </span>
                      </td>
                      <td className="py-2.5 font-mono text-slate-400 text-[11px]">
                        {act.execution_time_ms} ms
                      </td>
                      <td className="py-2.5 text-slate-300 max-w-xs truncate" title={act.message}>
                        {act.message}
                      </td>
                      <td className="py-2.5 text-right">
                        <button
                          onClick={() => onViewOrder(act.order_id)}
                          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-indigo-400 transition"
                          title="View Order Details"
                        >
                          <Eye className="w-3.5 h-3.5" />
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
