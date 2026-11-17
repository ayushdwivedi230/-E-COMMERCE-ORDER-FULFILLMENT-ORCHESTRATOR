import React, { useState, useEffect } from "react";
import {
  ShoppingCart,
  ShieldAlert,
  History,
  Package,
  Layers,
  Sparkles,
  CheckCircle,
  AlertOctagon,
  RefreshCw,
  Send,
  Truck,
} from "lucide-react";
import { fetchProducts, fetchCustomers, processOrder } from "./api";
import type { Product, Customer, OrderState } from "./types";
import { PipelineStepper } from "./components/PipelineStepper";
import { AgentLogViewer } from "./components/AgentLogViewer";
import { CustomerMemoryView } from "./components/CustomerMemoryView";
import { FraudQueueView } from "./components/FraudQueueView";
import { InventoryView } from "./components/InventoryView";

export function App() {
  const [activeTab, setActiveTab] = useState<"pipeline" | "memory" | "fraud" | "inventory">("pipeline");
  const [products, setProducts] = useState<Product[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);

  // Form state
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>("CUST-001");
  const [selectedSku, setSelectedSku] = useState<string>("KB-MECH-RGB");
  const [quantity, setQuantity] = useState<number>(1);
  const [couponCode, setCouponCode] = useState<string>("WELCOME10");
  const [shippingStreet, setShippingStreet] = useState<string>("742 Evergreen Terrace");
  const [shippingCity, setShippingCity] = useState<string>("Springfield");
  const [shippingState, setShippingState] = useState<string>("OR");
  const [shippingZip, setShippingZip] = useState<string>("97477");
  const [billingMismatch, setBillingMismatch] = useState<boolean>(false);
  const [simulatedFailedAttempts, setSimulatedFailedAttempts] = useState<number>(0);

  // Execution state
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [orderResult, setOrderResult] = useState<OrderState | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [prods, custs] = await Promise.all([fetchProducts(), fetchCustomers()]);
      setProducts(prods);
      setCustomers(custs);
      if (custs.length > 0) setSelectedCustomerId(custs[0].id);
      if (prods.length > 0) setSelectedSku(prods[0].sku);
    } catch (e: any) {
      console.error(e);
    }
  };

  // Prompt 4 Required Demonstration Scenarios
  const applyScenario = (
    type: "success" | "invalid" | "fraud" | "inventory" | "verified_cust" | "suspicious_cust"
  ) => {
    setErrorMsg(null);
    if (type === "success") {
      // Demo 1: Successful Order (Confirmed + Amount + Method + Tracking ID)
      setSelectedCustomerId("CUST-001");
      setSelectedSku("KB-MECH-RGB");
      setQuantity(1);
      setCouponCode("WELCOME10");
      setShippingStreet("742 Evergreen Terrace");
      setShippingCity("Springfield");
      setShippingState("OR");
      setShippingZip("97477");
      setBillingMismatch(false);
      setSimulatedFailedAttempts(0);
    } else if (type === "invalid") {
      // Demo 2: Invalid Order (Validation stops immediately)
      setSelectedCustomerId("CUST-001");
      setSelectedSku("NON-EXISTENT-SKU");
      setQuantity(1);
      setCouponCode("");
      setShippingStreet(""); // Missing street
      setShippingCity("Springfield");
      setShippingState("OR");
      setShippingZip("97477");
      setBillingMismatch(false);
      setSimulatedFailedAttempts(0);
    } else if (type === "fraud") {
      // Demo 3: High-Risk Fraudulent Order (Fraud Escalation Route to Hold Queue)
      setSelectedCustomerId("CUST-003"); // High-risk customer with prior disputes
      setSelectedSku("MON-4K-27");
      setQuantity(3);
      setCouponCode("");
      setShippingStreet("PO Box 9999");
      setShippingCity("Unknown Island");
      setShippingState("FL");
      setShippingZip("33040");
      setBillingMismatch(true);
      setSimulatedFailedAttempts(2);
    } else if (type === "inventory") {
      // Demo 4: Insufficient Inventory (Substitute / Backorder Proposal)
      setSelectedCustomerId("CUST-001");
      setSelectedSku("MON-CRV-32"); // 0 stock
      setQuantity(1);
      setCouponCode("");
      setShippingStreet("742 Evergreen Terrace");
      setShippingCity("Springfield");
      setShippingState("OR");
      setShippingZip("97477");
      setBillingMismatch(false);
      setSimulatedFailedAttempts(0);
    } else if (type === "verified_cust") {
      // Demo 5: Customer with Previous Successful Transactions
      setSelectedCustomerId("CUST-001"); // Verified clean history
      setSelectedSku("HUB-USBC-8P");
      setQuantity(2);
      setCouponCode("WELCOME10");
      setShippingStreet("742 Evergreen Terrace");
      setShippingCity("Springfield");
      setShippingState("OR");
      setShippingZip("97477");
      setBillingMismatch(false);
      setSimulatedFailedAttempts(0);
    } else if (type === "suspicious_cust") {
      // Demo 6: Customer with Suspicious Historical Transactions
      setSelectedCustomerId("CUST-002"); // Medium-risk with past chargeback
      setSelectedSku("KB-MECH-RGB");
      setQuantity(1);
      setCouponCode("");
      setShippingStreet("1200 Market Street");
      setShippingCity("San Francisco");
      setShippingState("CA");
      setShippingZip("94102");
      setBillingMismatch(false);
      setSimulatedFailedAttempts(0);
    }
  };

  const handleRunPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    setErrorMsg(null);
    setOrderResult(null);

    const isInvalidDemo = shippingStreet.trim() === "";
    const payload = {
      customer_id: selectedCustomerId,
      items: [{ sku: selectedSku, quantity }],
      shipping_address: {
        street: shippingStreet,
        city: shippingCity,
        state: shippingState,
        postal_code: shippingZip,
        country: "USA",
      },
      payment_information: {
        payment_method: "CREDIT_CARD",
        payment_status: isInvalidDemo ? "FAILED" : "AUTHORIZED",
        card_last4: "4242",
        transaction_token: isInvalidDemo ? "" : "tok_simulated_live",
        billing_address: billingMismatch
          ? {
              street: "PO Box 111",
              city: "Anchorage",
              state: "AK",
              postal_code: "99501",
              country: "USA",
            }
          : {
              street: shippingStreet || "742 Evergreen Terrace",
              city: shippingCity || "Springfield",
              state: shippingState || "OR",
              postal_code: shippingZip || "97477",
              country: "USA",
            },
      },
      coupon_code: couponCode.trim() || undefined,
      simulate_recent_failed_attempts: simulatedFailedAttempts,
    };

    try {
      const result = await processOrder(payload);
      setOrderResult(result);
    } catch (err: any) {
      setErrorMsg(err.message || "Pipeline execution failed");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-30 px-6 py-3.5 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center font-bold text-white shadow-lg">
            AG
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
              E-Commerce Order Fulfillment Orchestrator
              <span className="text-[10px] font-mono bg-indigo-950 text-indigo-300 border border-indigo-800 px-2 py-0.5 rounded-full font-normal">
                CSE476 Prompt 4
              </span>
            </h1>
            <p className="text-[11px] text-slate-400">
              Multi-Agent Orchestration & Fraud Escalation Engine | Microsoft Agent Framework v1.26.0
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setActiveTab("pipeline")}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition ${
              activeTab === "pipeline"
                ? "bg-indigo-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <ShoppingCart className="w-3.5 h-3.5" />
            Order Pipeline
          </button>
          <button
            onClick={() => setActiveTab("fraud")}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition ${
              activeTab === "fraud"
                ? "bg-indigo-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            Fraud Hold Queue
          </button>
          <button
            onClick={() => setActiveTab("memory")}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition ${
              activeTab === "memory"
                ? "bg-indigo-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <History className="w-3.5 h-3.5" />
            Customer Memory
          </button>
          <button
            onClick={() => setActiveTab("inventory")}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition ${
              activeTab === "inventory"
                ? "bg-indigo-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Package className="w-3.5 h-3.5" />
            Live Catalog & Stock
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {activeTab === "memory" && (
          <CustomerMemoryView
            customers={customers}
            onSelectCustomerForOrder={(c) => {
              setSelectedCustomerId(c.id);
              setActiveTab("pipeline");
            }}
          />
        )}

        {activeTab === "fraud" && <FraudQueueView />}

        {activeTab === "inventory" && (
          <InventoryView
            products={products}
            onSelectProductForOrder={(p) => {
              setSelectedSku(p.sku);
              setActiveTab("pipeline");
            }}
          />
        )}

        {activeTab === "pipeline" && (
          <div>
            {/* Visual 5-Agent Stepper */}
            <PipelineStepper orderState={orderResult} isProcessing={isProcessing} />

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Preset Scenarios & Order Submission Form */}
              <div className="lg:col-span-5 space-y-4">
                {/* 6 Required Demonstrations */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300 uppercase tracking-wide mb-2.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    Prompt 4 Required Test Demonstrations
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => applyScenario("success")}
                      className="p-2 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-left transition"
                    >
                      <div className="text-[11px] font-bold text-emerald-400">1. Successful Order</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Dispatched + Tracking ID</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => applyScenario("invalid")}
                      className="p-2 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-left transition"
                    >
                      <div className="text-[11px] font-bold text-rose-400">2. Invalid Order</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Stops at validation</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => applyScenario("fraud")}
                      className="p-2 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-left transition"
                    >
                      <div className="text-[11px] font-bold text-rose-500">3. High-Risk Fraud</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Score &gt;= 70, hold queue</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => applyScenario("inventory")}
                      className="p-2 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-left transition"
                    >
                      <div className="text-[11px] font-bold text-amber-400">4. Low Inventory</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Requires user approval</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => applyScenario("verified_cust")}
                      className="p-2 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-left transition"
                    >
                      <div className="text-[11px] font-bold text-cyan-400">5. Verified History</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Clean customer memory</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => applyScenario("suspicious_cust")}
                      className="p-2 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-left transition"
                    >
                      <div className="text-[11px] font-bold text-orange-400">6. Suspicious History</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">Prior chargeback impact</div>
                    </button>
                  </div>
                </div>

                {/* Form */}
                <form
                  onSubmit={handleRunPipeline}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow space-y-4"
                >
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 border-b border-slate-800 pb-2 flex items-center justify-between">
                    <span>Order Pipeline Trigger</span>
                    <span className="text-[10px] text-slate-500 font-mono">POST /api/orders/process</span>
                  </h3>

                  {/* Customer Select */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                      Customer Profile & Prior Memory
                    </label>
                    <select
                      value={selectedCustomerId}
                      onChange={(e) => setSelectedCustomerId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                    >
                      {customers.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name} ({c.id}) — Standing: {c.status} | Tier: {c.history_stats?.risk_tier || "LOW"}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Product & Qty */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="col-span-2">
                      <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                        Catalog Item SKU
                      </label>
                      <select
                        value={selectedSku}
                        onChange={(e) => setSelectedSku(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                      >
                        {products.map((p) => (
                          <option key={p.sku} value={p.sku}>
                            {p.sku} (${p.price.toFixed(2)}) — Stock: {p.stock_quantity}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                        Quantity
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="99"
                        value={quantity}
                        onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
                      />
                    </div>
                  </div>

                  {/* Coupon & Failed Attempts */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                        Coupon Code
                      </label>
                      <input
                        type="text"
                        placeholder="WELCOME10, SAVE20"
                        value={couponCode}
                        onChange={(e) => setCouponCode(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 uppercase font-mono focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                        Failed Payment Retries
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="5"
                        value={simulatedFailedAttempts}
                        onChange={(e) => setSimulatedFailedAttempts(parseInt(e.target.value) || 0)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                  </div>

                  {/* Address */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                      Shipping Street & City
                    </label>
                    <div className="grid grid-cols-2 gap-2 mb-2">
                      <input
                        type="text"
                        value={shippingStreet}
                        onChange={(e) => setShippingStreet(e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                        placeholder="Street"
                      />
                      <input
                        type="text"
                        value={shippingCity}
                        onChange={(e) => setShippingCity(e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                        placeholder="City"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        value={shippingState}
                        onChange={(e) => setShippingState(e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                        placeholder="State"
                      />
                      <input
                        type="text"
                        value={shippingZip}
                        onChange={(e) => setShippingZip(e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                        placeholder="Zip"
                      />
                    </div>
                  </div>

                  {/* Billing Mismatch Toggle */}
                  <div className="flex items-center gap-2 pt-1">
                    <input
                      type="checkbox"
                      id="mismatchCheck"
                      checked={billingMismatch}
                      onChange={(e) => setBillingMismatch(e.target.checked)}
                      className="rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-0"
                    />
                    <label htmlFor="mismatchCheck" className="text-xs text-slate-300 cursor-pointer">
                      Simulate Billing Address Mismatch (+20 risk pts)
                    </label>
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={isProcessing}
                    className="w-full py-2.5 px-4 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold rounded-lg shadow-lg flex items-center justify-center gap-2 transition-all disabled:opacity-50 text-xs uppercase tracking-wider"
                  >
                    {isProcessing ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Orchestrating 5 Agents...
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        Trigger Multi-Agent Fulfillment Pipeline
                      </>
                    )}
                  </button>
                </form>

                {errorMsg && (
                  <div className="p-3 bg-rose-950/80 border border-rose-800 rounded-lg text-rose-300 text-xs">
                    {errorMsg}
                  </div>
                )}
              </div>

              {/* Right Column: Execution Output, Financial Breakdown & Trace Logs */}
              <div className="lg:col-span-7 space-y-4">
                {/* Result Card */}
                {orderResult ? (
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                      <div className="flex items-center gap-2">
                        {orderResult.dispatch_status === "DISPATCHED" ? (
                          <CheckCircle className="w-5 h-5 text-emerald-400" />
                        ) : (
                          <AlertOctagon className="w-5 h-5 text-rose-400" />
                        )}
                        <div>
                          <h3 className="text-sm font-bold text-slate-200">
                            {orderResult.dispatch_status === "DISPATCHED"
                              ? "Order Confirmed & Dispatched"
                              : orderResult.fraud_status === "HIGH_RISK_HELD"
                              ? "Order Escalated & Held (Fraud Review)"
                              : "Order Held by Orchestrator"}
                          </h3>
                          <div className="text-[11px] text-slate-400 font-mono">
                            Status: {orderResult.dispatch_status} | Order ID: {orderResult.order_id}
                          </div>
                        </div>
                      </div>

                      <div className="text-right">
                        <span className="text-[10px] uppercase text-slate-400 block">Final Amount</span>
                        <span className="text-lg font-bold font-mono text-emerald-400">
                          ${orderResult.final_amount.toFixed(2)}
                        </span>
                      </div>
                    </div>

                    {/* PROMPT 4 REQUIRED OUTPUT HIGHLIGHT CARD */}
                    {orderResult.dispatch_status === "DISPATCHED" ? (
                      <div className="mb-4 p-4 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-xs">
                        <div className="font-bold text-emerald-300 uppercase tracking-wide text-[11px] mb-2 flex items-center gap-1.5">
                          <Truck className="w-4 h-4 text-emerald-400" />
                          Prompt 4 Required Output — Successful Order
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
                          <div className="bg-slate-950/60 p-2 rounded border border-emerald-900/40">
                            <span className="text-[10px] font-sans text-slate-400 block">Status</span>
                            <span className="text-emerald-400 font-bold">CONFIRMED</span>
                          </div>
                          <div className="bg-slate-950/60 p-2 rounded border border-emerald-900/40">
                            <span className="text-[10px] font-sans text-slate-400 block">Final Payable</span>
                            <span className="text-emerald-300 font-bold">${orderResult.final_amount.toFixed(2)}</span>
                          </div>
                          <div className="bg-slate-950/60 p-2 rounded border border-emerald-900/40">
                            <span className="text-[10px] font-sans text-slate-400 block">Shipping Method</span>
                            <span className="text-slate-200 truncate block">{orderResult.shipping_method}</span>
                          </div>
                          <div className="bg-slate-950/60 p-2 rounded border border-emerald-900/40">
                            <span className="text-[10px] font-sans text-slate-400 block">Tracking ID</span>
                            <span className="text-emerald-400 font-bold">{orderResult.tracking_id}</span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="mb-4 p-4 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs">
                        <div className="font-bold text-rose-300 uppercase tracking-wide text-[11px] mb-2 flex items-center gap-1.5">
                          <ShieldAlert className="w-4 h-4 text-rose-400" />
                          Prompt 4 Required Output — Suspicious / Held Order
                        </div>
                        <div className="grid grid-cols-3 gap-3 font-mono mb-3">
                          <div className="bg-slate-950/60 p-2 rounded border border-rose-900/40">
                            <span className="text-[10px] font-sans text-slate-400 block">Order Result</span>
                            <span className="text-rose-400 font-bold">HELD</span>
                          </div>
                          <div className="bg-slate-950/60 p-2 rounded border border-rose-900/40">
                            <span className="text-[10px] font-sans text-slate-400 block">Fraud Score</span>
                            <span className="text-rose-400 font-bold">{orderResult.fraud_score}/100</span>
                          </div>
                          <div className="bg-slate-950/60 p-2 rounded border border-rose-900/40">
                            <span className="text-[10px] font-sans text-slate-400 block">Review Status</span>
                            <span className="text-amber-400 font-bold">{orderResult.review_status}</span>
                          </div>
                        </div>
                        <div className="bg-slate-950/80 p-2.5 rounded border border-rose-900/30 font-sans text-rose-200">
                          <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider block mb-0.5">
                            Audit Justification & Explanation
                          </span>
                          {orderResult.fraud_ai_reasoning || orderResult.hold_reason}
                        </div>
                      </div>
                    )}

                    {/* Financial Summary */}
                    <div className="grid grid-cols-4 gap-2 mb-4 bg-slate-950 p-3 rounded-lg border border-slate-800/80 text-xs font-mono">
                      <div>
                        <span className="text-[10px] text-slate-400 font-sans block">Subtotal</span>
                        ${orderResult.subtotal.toFixed(2)}
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-sans block">Discounts</span>
                        -${orderResult.discount_amount.toFixed(2)}
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-sans block">Tax (8%)</span>
                        +${orderResult.tax_amount.toFixed(2)}
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-sans block">Shipping</span>
                        +${orderResult.shipping_cost.toFixed(2)}
                      </div>
                    </div>

                    {/* Log Viewer Component */}
                    <AgentLogViewer logs={orderResult.agent_execution_logs} />
                  </div>
                ) : (
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-500 shadow-xl">
                    <Layers className="w-10 h-10 mx-auto text-slate-600 mb-3" />
                    <h3 className="text-sm font-bold text-slate-400">Pipeline Ready</h3>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                      Choose any of the 6 test demonstrations on the left, then click Trigger Multi-Agent Fulfillment Pipeline.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
