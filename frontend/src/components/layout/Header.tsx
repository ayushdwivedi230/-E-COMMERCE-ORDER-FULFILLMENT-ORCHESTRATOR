import React, { useState } from "react";
import {
  Sun,
  Moon,
  Plus,
  RotateCcw,
  ShieldCheck,
  Server,
} from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import { reseedDatabase } from "../../api";
import type { NavPage } from "./Sidebar";

interface HeaderProps {
  currentPage: NavPage;
  onNavigate: (page: NavPage) => void;
  onDataRefresh?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentPage,
  onNavigate,
  onDataRefresh,
}) => {
  const { theme, toggleTheme } = useTheme();
  const [isResetting, setIsResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);

  const getPageMeta = (page: NavPage) => {
    switch (page) {
      case "dashboard":
        return {
          title: "Executive Dashboard",
          subtitle: "Enterprise metrics, live fulfillment stream & automated fraud analytics",
        };
      case "create-order":
        return {
          title: "Create & Orchestrate Order",
          subtitle: "Trigger the 5-Agent sequential pipeline with deterministic rules & fraud escalation",
        };
      case "orders":
        return {
          title: "Order Management",
          subtitle: "Live database inventory of all processed orders, dispatch tracking & audit states",
        };
      case "agents":
        return {
          title: "Specialised Agent Monitoring",
          subtitle: "Real-time telemetry, latencies, and execution outputs for all 5 Microsoft Agent Framework agents",
        };
      case "fraud-review":
        return {
          title: "Fraud Escalation Review Queue",
          subtitle: "Auditor inspection console with AI reasoning, prior dispute history, and manual override controls",
        };
      case "order-details":
        return {
          title: "Order Fulfillment Details",
          subtitle: "Deep audit view with agent execution timeline, decimal pricing, and courier tracking",
        };
      default:
        return { title: "Operations Console", subtitle: "E-Commerce Fulfillment System" };
    }
  };

  const meta = getPageMeta(currentPage);

  const handleResetData = async () => {
    if (!confirm("Reset database to baseline sample customers, products, and historical memory?")) return;
    setIsResetting(true);
    try {
      await reseedDatabase();
      setResetMessage("Sample database refreshed successfully.");
      if (onDataRefresh) onDataRefresh();
      setTimeout(() => setResetMessage(null), 3500);
    } catch (e: any) {
      alert("Failed to reset seed data: " + e.message);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-20 px-6 py-3.5 flex items-center justify-between">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-base font-bold text-slate-100 tracking-tight">
            {meta.title}
          </h1>
          <span className="flex items-center gap-1 text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            FastAPI Connected
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-0.5">
          {meta.subtitle}
        </p>
      </div>

      <div className="flex items-center gap-2.5">
        {resetMessage && (
          <div className="text-xs font-medium text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2.5 py-1 rounded">
            {resetMessage}
          </div>
        )}

        {/* Reset Database Seed Button */}
        <button
          onClick={handleResetData}
          disabled={isResetting}
          title="Reset database to baseline sample customers, products, and order history"
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700/80 border border-slate-700/60 transition disabled:opacity-50"
        >
          <RotateCcw className={`w-3.5 h-3.5 text-slate-400 ${isResetting ? "animate-spin" : ""}`} />
          <span className="hidden sm:inline">Reset Baseline Data</span>
        </button>

        {/* New Order Button */}
        {currentPage !== "create-order" && (
          <button
            onClick={() => onNavigate("create-order")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 shadow-md shadow-indigo-600/30 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Order</span>
          </button>
        )}

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          className="p-2 rounded-lg text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700/80 border border-slate-700/60 transition"
        >
          {theme === "dark" ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-indigo-400" />
          )}
        </button>

        {/* System Endpoint Link */}
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          title="Open Swagger OpenAPI Documentation"
          className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-mono text-slate-400 hover:text-slate-200 bg-slate-950/80 border border-slate-800 transition"
        >
          <Server className="w-3 h-3 text-indigo-400" />
          <span>API Docs</span>
        </a>
      </div>
    </header>
  );
};
