import React from "react";
import {
  LayoutDashboard,
  PlusCircle,
  PackageSearch,
  Bot,
  ShieldAlert,
  FileText,
  Boxes,
  Activity,
  Sparkles,
} from "lucide-react";

export type NavPage =
  | "dashboard"
  | "create-order"
  | "orders"
  | "agents"
  | "fraud-review"
  | "order-details";

interface SidebarProps {
  currentPage: NavPage;
  onNavigate: (page: NavPage) => void;
  heldCount?: number;
  isConnected: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onNavigate,
  heldCount = 0,
  isConnected,
}) => {
  const navItems = [
    {
      id: "dashboard" as NavPage,
      label: "Dashboard",
      icon: LayoutDashboard,
      description: "Metrics & SaaS Analytics",
    },
    {
      id: "create-order" as NavPage,
      label: "Create Order",
      icon: PlusCircle,
      description: "Pipeline Trigger & Demos",
    },
    {
      id: "orders" as NavPage,
      label: "Order Management",
      icon: PackageSearch,
      description: "All Orders & Statuses",
    },
    {
      id: "agents" as NavPage,
      label: "Agent Monitoring",
      icon: Bot,
      description: "5-Agent Telemetry & Logs",
    },
    {
      id: "fraud-review" as NavPage,
      label: "Fraud Review",
      icon: ShieldAlert,
      description: "Escalation Queue & Audit",
      badge: heldCount > 0 ? heldCount : undefined,
      badgeColor: "bg-rose-500 text-white",
    },
    {
      id: "order-details" as NavPage,
      label: "Order Details",
      icon: FileText,
      description: "Timeline, Pricing & Dispatch",
    },
  ];

  return (
    <aside className="w-64 flex-shrink-0 flex flex-col bg-slate-900 border-r border-slate-800 transition-colors duration-200">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-600/30 text-white font-black text-sm tracking-wider">
            AG
          </div>
          <div>
            <div className="font-bold text-sm text-slate-100 flex items-center gap-1.5 tracking-tight">
              <span>Antigravity</span>
              <span className="text-[9px] font-mono font-medium px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                SaaS
              </span>
            </div>
            <div className="text-[10px] text-slate-400 font-medium">
              Order Fulfillment Engine
            </div>
          </div>
        </div>
      </div>

      {/* System Status Pill */}
      <div className="px-4 py-2.5 bg-slate-950/60 border-b border-slate-800/60 flex items-center justify-between text-[11px]">
        <span className="text-slate-400 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-indigo-400" />
          Live WebSocket
        </span>
        <span
          className={`flex items-center gap-1 font-mono font-semibold px-2 py-0.5 rounded-full text-[10px] ${
            isConnected
              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
              : "bg-amber-500/15 text-amber-400 border border-amber-500/30"
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isConnected ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
            }`}
          />
          {isConnected ? "ONLINE" : "RECONNECTING"}
        </span>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Core Operations
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-left text-xs font-medium transition-all group ${
                isActive
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-semibold"
                  : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Icon
                  className={`w-4 h-4 flex-shrink-0 transition ${
                    isActive
                      ? "text-white"
                      : "text-slate-400 group-hover:text-indigo-400"
                  }`}
                />
                <div className="truncate">
                  <div className="leading-tight">{item.label}</div>
                  <div
                    className={`text-[10px] font-normal truncate ${
                      isActive ? "text-indigo-200" : "text-slate-400"
                    }`}
                  >
                    {item.description}
                  </div>
                </div>
              </div>

              {item.badge !== undefined && (
                <span
                  className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold font-mono ${item.badgeColor}`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/40 text-[10px] space-y-1">
        <div className="flex items-center justify-between text-slate-400">
          <span className="flex items-center gap-1 font-medium">
            <Boxes className="w-3 h-3 text-indigo-400" />
            Framework
          </span>
          <span className="font-mono text-slate-300">MSFT Agent v1.26</span>
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span className="flex items-center gap-1 font-medium">
            <Sparkles className="w-3 h-3 text-amber-400" />
            Course
          </span>
          <span className="font-mono text-slate-300">CSE476 Agentic AI</span>
        </div>
      </div>
    </aside>
  );
};
