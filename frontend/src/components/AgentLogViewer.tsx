import React from "react";
import { Terminal, CheckCircle, AlertTriangle, XCircle, Clock } from "lucide-react";
import type { AgentLogEntry } from "../types";

interface AgentLogViewerProps {
  logs: AgentLogEntry[];
}

export const AgentLogViewer: React.FC<AgentLogViewerProps> = ({ logs }) => {
  if (!logs || logs.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 text-center text-slate-500 text-xs">
        No agent telemetry recorded yet. Submit an order to trigger the multi-agent pipeline.
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Real-Time Agent Execution Telemetry ({logs.length} events)
          </h3>
        </div>
        <span className="text-[10px] text-slate-400 font-mono">Shared OrderState Log Bus</span>
      </div>

      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {logs.map((log, index) => {
          let statusBadge = "bg-emerald-950/80 text-emerald-400 border-emerald-800/60";
          let StatusIcon = CheckCircle;

          if (log.status === "FAILED" || log.status === "HELD") {
            statusBadge = "bg-rose-950/80 text-rose-400 border-rose-800/60";
            StatusIcon = XCircle;
          } else if (log.status === "WARNING") {
            statusBadge = "bg-amber-950/80 text-amber-400 border-amber-800/60";
            StatusIcon = AlertTriangle;
          } else if (log.status === "SKIPPED") {
            statusBadge = "bg-slate-800 text-slate-400 border-slate-700";
            StatusIcon = Clock;
          }

          return (
            <div
              key={index}
              className="bg-slate-950/70 border border-slate-800/90 rounded-lg p-3 text-xs font-mono transition-all hover:border-slate-700"
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-indigo-400 font-bold font-sans">[{log.agent_name}]</span>
                  <span className="text-slate-400 font-sans">{log.action}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500">{log.execution_time_ms}ms</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border uppercase flex items-center gap-1 ${statusBadge}`}>
                    <StatusIcon className="w-3 h-3" />
                    {log.status}
                  </span>
                </div>
              </div>
              <div className="text-slate-300 text-[11px] mt-1">{log.message}</div>

              {log.details && Object.keys(log.details).length > 0 && (
                <details className="mt-2 text-[10px] text-slate-400">
                  <summary className="cursor-pointer hover:text-slate-300 select-none">
                    View Execution Payload
                  </summary>
                  <pre className="mt-1 p-2 bg-slate-900/90 rounded text-slate-300 overflow-x-auto border border-slate-800">
                    {JSON.stringify(log.details, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
