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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-5">
        {/* Total Orders */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 mb-2.5">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">Total Orders</span>
            <div className="w-9 h-9 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-400">
              <ShoppingBag className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black font-mono text-slate-100">
            {data.total_orders}
          </div>
          <div className="text-xs text-slate-400 mt-1.5 flex items-center gap-1 font-medium">
            <span>Throughput count</span>
          </div>
        </div>

        {/* Completed Orders */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 mb-2.5">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-300">Completed</span>
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black font-mono text-emerald-400">
            {data.completed_orders}
          </div>
          <div className="text-xs text-slate-400 mt-1.5 font-medium">
            Dispatched & Tracking
          </div>
        </div>

        {/* Held Orders */}
        <div
          onClick={data.held_orders > 0 ? onNavigateToFraud : undefined}
          className={`bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm transition ${
            data.held_orders > 0
              ? "hover:border-rose-600/60 cursor-pointer group"
              : ""
          }`}
        >
          <div className="flex items-center justify-between text-slate-400 mb-2.5">
            <span className="text-xs font-bold uppercase tracking-wider text-rose-300">
              Held Orders
            </span>
            <div className="w-9 h-9 rounded-xl bg-rose-500/10 flex items-center justify-center text-rose-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black font-mono text-rose-400 flex items-center justify-between">
            <span>{data.held_orders}</span>
            {data.held_orders > 0 && (
              <span className="text-xs font-sans font-semibold text-rose-400 group-hover:underline flex items-center gap-1">
                Review <ArrowUpRight className="w-3.5 h-3.5" />
              </span>
            )}
          </div>
          <div className="text-xs text-slate-400 mt-1.5 font-medium">
            In Escalation Audit Queue
          </div>
        </div>

        {/* Pending Orders */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 mb-2.5">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-300">Pending</span>
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black font-mono text-amber-400">
            {data.pending_orders}
          </div>
          <div className="text-xs text-slate-400 mt-1.5 font-medium">
            In Validation / Pipeline
          </div>
        </div>

        {/* Total Revenue */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 mb-2.5">
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-300">Revenue</span>
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 flex items-center justify-center text-cyan-400">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black font-mono text-cyan-300">
            ${Number(data.total_revenue || 0).toFixed(2)}
          </div>
          <div className="text-xs text-slate-400 mt-1.5 font-medium">
            Dispatched gross revenue
          </div>
        </div>

        {/* Average Order Value */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 mb-2.5">
            <span className="text-xs font-bold uppercase tracking-wider text-violet-300">Avg Order</span>
            <div className="w-9 h-9 rounded-xl bg-violet-500/10 flex items-center justify-center text-violet-400">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black font-mono text-violet-300">
            ${Number(data.average_order_value || 0).toFixed(2)}
          </div>
          <div className="text-xs text-slate-400 mt-1.5 font-medium">
            Per fulfilled basket
          </div>
        </div>
      </div>

      {/* Fraud Intelligence & Real Visual Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Fraud Summary Banner */}
        <div className="lg:col-span-12 bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-5">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 shadow-md">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold uppercase tracking-wider text-slate-100">
                  Automated Multi-Agent Fraud Analytics
                </h3>
                <p className="text-sm text-slate-400 mt-0.5">
                  Dual-tier deterministic rule engine + contextual AI reasoning
                </p>
              </div>
            </div>

            <div className="flex items-center gap-8 text-sm font-mono">
              <div>
                <span className="text-xs text-slate-400 block font-sans font-medium">Total Evaluated</span>
                <span className="text-base font-bold text-slate-100">
                  {data.fraud_stats.total_evaluated}
                </span>
              </div>
              <div className="border-l border-slate-800 pl-8">
                <span className="text-xs text-slate-400 block font-sans font-medium">Avg Risk Score</span>
                <span className="text-base font-bold text-amber-400">
                  {data.fraud_stats.average_fraud_score} / 100
                </span>
              </div>
              <div className="border-l border-slate-800 pl-8">
                <span className="text-xs text-slate-400 block font-sans font-medium">Escalation Rate</span>
                <span className="text-base font-bold text-rose-400">
                  {data.fraud_stats.escalation_rate}%
                </span>
              </div>
              <div className="border-l border-slate-800 pl-8">
                <span className="text-xs text-slate-400 block font-sans font-medium">High Risk Flags</span>
                <span className="text-base font-bold text-rose-400">
                  {data.fraud_stats.high_risk_count}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Chart 1: Order Status Distribution (Donut Chart) */}
        <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-100">
                Order Fulfillment Status
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Distribution across pipeline stages</p>
            </div>
          </div>

          <div className="h-72 w-full flex items-center justify-center">
            {data.total_orders === 0 ? (
              <p className="text-sm text-slate-500">No orders placed yet</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.status_distribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={65}
                    outerRadius={95}
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
                      borderRadius: "10px",
                      fontSize: "14px",
                      color: "#f8fafc",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="flex justify-center gap-5 mt-3">
            {data.status_distribution.map((item) => (
              <div key={item.name} className="flex items-center gap-2 text-sm text-slate-300">
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="font-medium">{item.name}:</span>
                <span className="font-mono font-bold text-white">{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Chart 2: Fraud Risk Tier Breakdown (Bar Chart) */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-100">
                Fraud Risk Classification
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Low (0-29), Medium (30-69), High Escalation (70-100)
              </p>
            </div>
          </div>

          <div className="h-72 w-full">
            {data.fraud_stats.total_evaluated === 0 ? (
              <div className="h-full flex items-center justify-center text-sm text-slate-500">
                No orders evaluated by Fraud Check Agent yet
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.risk_distribution}>
                  <XAxis dataKey="tier" stroke="#94a3b8" fontSize={13} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={13} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      borderRadius: "10px",
                      fontSize: "14px",
                      color: "#f8fafc",
                    }}
                  />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {data.risk_distribution.map((entry, index) => (
                      <Cell key={`bar-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="flex justify-around text-sm text-slate-300 mt-3 font-mono">
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
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
          <div className="flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-indigo-400" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-100">
              Live Multi-Agent Activity Stream
            </h3>
          </div>
          <button
            onClick={loadData}
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh Stream
          </button>
        </div>

        {data.recent_activity.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-sm">
            No agent execution logs recorded yet. Place an order in Create Order tab to start the pipeline!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800/80 text-xs font-bold uppercase tracking-wider text-slate-400">
                  <th className="pb-3 px-3">Agent</th>
                  <th className="pb-3 px-3">Order ID</th>
                  <th className="pb-3 px-3">Action</th>
                  <th className="pb-3 px-3">Status</th>
                  <th className="pb-3 px-3">Latency</th>
                  <th className="pb-3 px-3">Message</th>
                  <th className="pb-3 px-3 text-right">View</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {data.recent_activity.map((act) => {
                  const getStatusBadge = (st: string) => {
                    switch (st) {
                      case "SUCCESS":
                        return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
                      case "HELD":
                      case "FAILED":
                        return "bg-rose-500/15 text-rose-400 border-rose-500/30";
                      case "WARNING":
                        return "bg-amber-500/15 text-amber-400 border-amber-500/30";
                      default:
                        return "bg-indigo-500/15 text-indigo-400 border-indigo-500/30";
                    }
                  };

                  return (
                    <tr key={act.id} className="hover:bg-slate-800/50 transition">
                      <td className="py-3 px-3 font-semibold text-slate-100">
                        {act.agent_name}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-300 font-medium">
                        {act.order_id}
                      </td>
                      <td className="py-3 px-3 text-slate-300 font-mono text-xs">
                        {act.action}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2.5 py-1 rounded-full text-xs font-mono font-bold border ${getStatusBadge(
                            act.status
                          )}`}
                        >
                          {act.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-300 text-xs">
                        {act.execution_time_ms} ms
                      </td>
                      <td className="py-3 px-3 text-slate-200 max-w-sm truncate" title={act.message}>
                        {act.message}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={() => onViewOrder(act.order_id)}
                          className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-indigo-400 transition"
                          title="View Order Details"
                        >
                          <Eye className="w-4 h-4" />
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
