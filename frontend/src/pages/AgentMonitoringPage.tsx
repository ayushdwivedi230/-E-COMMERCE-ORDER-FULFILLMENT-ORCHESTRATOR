import React, { useState, useEffect } from "react";
import {
  Bot,
  AlertTriangle,
  RefreshCw,
  Cpu,
  Layers,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { fetchAgentsTelemetry } from "../api";
import type { AgentsTelemetryResponse } from "../types";

export const AgentMonitoringPage: React.FC = () => {
  const [data, setData] = useState<AgentsTelemetryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedAgent, setExpandedAgent] = useState<string | null>("ValidationAgent");

  const loadTelemetry = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchAgentsTelemetry();
      setData(res);
    } catch (e: any) {
      setError(e.message || "Failed to load agent telemetry");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTelemetry();
  }, []);

  const getAgentRole = (name: string): { title: string; subtitle: string } => {
    switch (name) {
      case "ValidationAgent":
        return {
          title: "Agent 1: Validation Agent",
          subtitle: "Structural schema verification, catalog SKU validation, and payment presence",
        };
      case "InventoryAgent":
        return {
          title: "Agent 2: Inventory Agent",
          subtitle: "Atomic ACID stock reservations, substitute recommendations & backorders",
        };
      case "FraudCheckAgent":
        return {
          title: "Agent 3: Fraud Check Agent",
          subtitle: "Prior customer memory, risk scoring (0-100), and escalation hold queue routing",
        };
      case "PricingAgent":
        return {
          title: "Agent 4: Pricing Agent",
          subtitle: "Deterministic decimal financial calculations, coupon discounts, tax & shipping",
        };
      case "DispatchCoordinator":
        return {
          title: "Agent 5: Dispatch Coordinator",
          subtitle: "Carrier routing simulation, unique tracking number generation & dispatch record",
        };
      default:
        return { title: name, subtitle: "Specialised Microsoft Agent Framework Module" };
    }
  };

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mb-3" />
        <p className="text-sm font-medium">Gathering agent telemetry from database logs...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-rose-950/40 border border-rose-800 rounded-xl text-rose-300">
        <div className="flex items-center gap-2 font-bold mb-2">
          <AlertTriangle className="w-5 h-5 text-rose-400" />
          <span>Failed to query agent telemetry</span>
        </div>
        <p className="text-xs mb-4">{error}</p>
        <button
          onClick={loadTelemetry}
          className="px-3 py-1.5 bg-rose-800 hover:bg-rose-700 text-white rounded text-xs font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-indigo-400" />
            <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
              Microsoft Agent Framework Orchestration Roster
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Framework: <span className="font-mono text-indigo-300 font-semibold">{data.framework}</span> (v{data.version}) | 5 Specialized Core Agent Modules Active
          </p>
        </div>

        <button
          onClick={loadTelemetry}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 hover:text-white transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Telemetry
        </button>
      </div>

      {/* 5 Agent Cards */}
      <div className="space-y-4">
        {data.agents.map((agent) => {
          const role = getAgentRole(agent.agent_name);
          const isExpanded = expandedAgent === agent.agent_name;

          return (
            <div
              key={agent.agent_name}
              className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm hover:border-slate-700 transition"
            >
              {/* Agent Summary Header */}
              <div
                onClick={() => setExpandedAgent(isExpanded ? null : agent.agent_name)}
                className="p-5 cursor-pointer flex flex-col md:flex-row items-start md:items-center justify-between gap-5 bg-slate-900/90 hover:bg-slate-800/80 transition"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold shadow-md">
                    <Bot className="w-6 h-6" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h3 className="text-base font-bold text-slate-100">{role.title}</h3>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        {agent.status}
                      </span>
                    </div>
                    <p className="text-sm text-slate-400 mt-1">{role.subtitle}</p>
                  </div>
                </div>

                {/* Telemetry Metrics */}
                <div className="flex items-center gap-6 text-sm font-mono w-full md:w-auto justify-between md:justify-end border-t md:border-t-0 border-slate-800 pt-3 md:pt-0">
                  <div className="text-center md:text-right">
                    <span className="text-xs text-slate-400 block font-sans font-medium">Total Invocations</span>
                    <span className="font-bold text-slate-100 text-base">{agent.total_executions}</span>
                  </div>
                  <div className="text-center md:text-right">
                    <span className="text-xs text-slate-400 block font-sans font-medium">Success</span>
                    <span className="font-bold text-emerald-400 text-base">{agent.successful_executions}</span>
                  </div>
                  <div className="text-center md:text-right">
                    <span className="text-xs text-slate-400 block font-sans font-medium">Held / Warning</span>
                    <span className="font-bold text-amber-400 text-base">{agent.held_or_warning_executions}</span>
                  </div>
                  <div className="text-center md:text-right">
                    <span className="text-xs text-slate-400 block font-sans font-medium">Avg Latency</span>
                    <span className="font-bold text-indigo-300 text-base">{agent.average_latency_ms} ms</span>
                  </div>

                  <div className="text-slate-400 hover:text-white pl-2">
                    {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </div>
                </div>
              </div>

              {/* Expandable Execution History & Logs */}
              {isExpanded && (
                <div className="border-t border-slate-800 bg-slate-950/60 p-5">
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3.5 flex items-center gap-2">
                    <Layers className="w-4 h-4 text-indigo-400" />
                    Recent Execution Events & Outputs (From Database `agent_logs`)
                  </div>

                  {agent.recent_events.length === 0 ? (
                    <div className="text-sm text-slate-500 py-4 text-center">
                      No executions logged for this agent yet.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {agent.recent_events.map((evt, idx) => {
                        const dateStr = evt.timestamp
                          ? new Date(evt.timestamp).toLocaleTimeString()
                          : "—";

                        return (
                          <div
                            key={idx}
                            className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-sm font-mono space-y-2 shadow-sm"
                          >
                            <div className="flex items-center justify-between text-xs">
                              <div className="flex items-center gap-2.5">
                                <span
                                  className={`px-2 py-0.5 rounded-full text-xs font-bold border ${
                                    evt.status === "SUCCESS"
                                      ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                                      : evt.status === "HELD" || evt.status === "FAILED"
                                      ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
                                      : "bg-amber-500/15 text-amber-400 border-amber-500/30"
                                  }`}
                                >
                                  {evt.status}
                                </span>
                                <span className="font-bold text-slate-100">{evt.action}</span>
                                <span className="text-slate-400 font-medium">Order: {evt.order_id}</span>
                              </div>

                              <div className="flex items-center gap-4 text-slate-400 text-xs">
                                <span className="font-semibold text-slate-300">{evt.execution_time_ms} ms</span>
                                <span>{dateStr}</span>
                              </div>
                            </div>

                            <div className="text-slate-200 font-sans text-sm bg-slate-950 p-3 rounded-lg border border-slate-800/80 leading-relaxed">
                              {evt.message}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
