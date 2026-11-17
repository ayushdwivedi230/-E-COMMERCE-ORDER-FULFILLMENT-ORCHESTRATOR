import React, { useState, useEffect } from "react";
import {
  Sparkles,
  Send,
  RefreshCw,
  CheckCircle,
  AlertOctagon,
  Truck,
  ShieldAlert,
  ArrowRight,
  Shield,
  Layers,
} from "lucide-react";
import { fetchProducts, fetchCustomers, processOrder } from "../api";
import type { Product, Customer, OrderState } from "../types";
import { PipelineStepper } from "../components/PipelineStepper";
import { AgentLogViewer } from "../components/AgentLogViewer";

interface CreateOrderPageProps {
  onOrderCreated?: (orderId: string) => void;
  onViewOrderDetails?: (orderId: string) => void;
}

export const CreateOrderPage: React.FC<CreateOrderPageProps> = ({
  onOrderCreated,
  onViewOrderDetails,
}) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loadingInitial, setLoadingInitial] = useState<boolean>(true);

  // Form State
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

  // Execution State
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [orderResult, setOrderResult] = useState<OrderState | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoadingInitial(true);
      const [prods, custs] = await Promise.all([fetchProducts(), fetchCustomers()]);
      setProducts(prods);
      setCustomers(custs);
      if (custs.length > 0) setSelectedCustomerId(custs[0].id);
      if (prods.length > 0) setSelectedSku(prods[0].sku);
    } catch (e: any) {
      console.error("Failed to load initial catalog data:", e);
    } finally {
      setLoadingInitial(false);
    }
  };

  const selectedCustomer = customers.find((c) => c.id === selectedCustomerId);
  const selectedProduct = products.find((p) => p.sku === selectedSku);

  // 6 Required Test Demonstrations from Prompt 4
  const applyScenario = (
    type: "success" | "invalid" | "fraud" | "inventory" | "verified_cust" | "suspicious_cust"
  ) => {
    setErrorMsg(null);
    if (type === "success") {
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
      setSelectedCustomerId("CUST-001");
      setSelectedSku("NON-EXISTENT-SKU");
      setQuantity(1);
      setCouponCode("");
      setShippingStreet("");
      setShippingCity("Springfield");
      setShippingState("OR");
      setShippingZip("97477");
      setBillingMismatch(false);
      setSimulatedFailedAttempts(0);
    } else if (type === "fraud") {
      setSelectedCustomerId("CUST-003");
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
      setSelectedCustomerId("CUST-001");
      setSelectedSku("MON-CRV-32"); // Zero stock
      setQuantity(1);
      setCouponCode("");
      setShippingStreet("742 Evergreen Terrace");
      setShippingCity("Springfield");
      setShippingState("OR");
      setShippingZip("97477");
      setBillingMismatch(false);
      setSimulatedFailedAttempts(0);
    } else if (type === "verified_cust") {
      setSelectedCustomerId("CUST-001");
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
      setSelectedCustomerId("CUST-002");
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
        transaction_token: isInvalidDemo ? "" : "tok_live_dashboard",
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
      if (onOrderCreated) {
        onOrderCreated(result.order_id);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Pipeline execution failed");
    } finally {
      setIsProcessing(false);
    }
  };

  if (loadingInitial) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mb-3" />
        <p className="text-sm font-medium">Loading catalog items and customer profiles...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Visual 5-Agent Stepper */}
      <PipelineStepper orderState={orderResult} isProcessing={isProcessing} />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Preset Test Scenarios & Order Form */}
        <div className="lg:col-span-5 space-y-4">
          {/* Preset Demonstrations Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300 uppercase tracking-wide mb-2.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Automated Pipeline Test Demonstrations
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
                <div className="text-[10px] text-slate-400 mt-0.5">Validation stops at Agent 1</div>
              </button>
              <button
                type="button"
                onClick={() => applyScenario("fraud")}
                className="p-2 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-left transition"
              >
                <div className="text-[11px] font-bold text-rose-500">3. High-Risk Fraud</div>
                <div className="text-[10px] text-slate-400 mt-0.5">Score &ge; 70 &rarr; Hold Queue</div>
              </button>
              <button
                type="button"
                onClick={() => applyScenario("inventory")}
                className="p-2 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-left transition"
              >
                <div className="text-[11px] font-bold text-amber-400">4. Low Inventory</div>
                <div className="text-[10px] text-slate-400 mt-0.5">Backorder / Substitute</div>
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
                <div className="text-[10px] text-slate-400 mt-0.5">Past chargeback impact</div>
              </button>
            </div>
          </div>

          {/* Order Submission Form */}
          <form
            onSubmit={handleRunPipeline}
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4"
          >
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 border-b border-slate-800 pb-2 flex items-center justify-between">
              <span>Order Parameters</span>
              <span className="text-[10px] text-slate-400 font-mono">POST /api/orders/process</span>
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

              {/* Memory Indicator Card */}
              {selectedCustomer?.history_stats && (
                <div className="mt-1.5 p-2 bg-slate-950 rounded border border-slate-800/80 text-[10px] flex items-center justify-between text-slate-400">
                  <span className="flex items-center gap-1 text-slate-300 font-medium">
                    <Shield className="w-3 h-3 text-indigo-400" />
                    Memory: {selectedCustomer.history_stats.successful_orders} Delivered / {selectedCustomer.history_stats.suspicious_orders} Suspicious
                  </span>
                  <span
                    className={`font-mono font-bold px-1.5 py-0.5 rounded ${
                      selectedCustomer.history_stats.risk_tier === "HIGH"
                        ? "bg-rose-950 text-rose-400 border border-rose-800"
                        : selectedCustomer.history_stats.risk_tier === "MEDIUM"
                        ? "bg-amber-950 text-amber-400 border border-amber-800"
                        : "bg-emerald-950 text-emerald-400 border border-emerald-800"
                    }`}
                  >
                    Tier: {selectedCustomer.history_stats.risk_tier}
                  </span>
                </div>
              )}
            </div>

            {/* Product & Quantity */}
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                  Catalog Product SKU
                </label>
                <select
                  value={selectedSku}
                  onChange={(e) => setSelectedSku(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  {products.map((p) => (
                    <option key={p.sku} value={p.sku}>
                      {p.sku} (${Number(p.price || 0).toFixed(2)}) — Stock: {p.stock_quantity}
                    </option>
                  ))}
                </select>
                {selectedProduct && (
                  <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
                    <span>{selectedProduct.name}</span>
                    <span className={selectedProduct.stock_quantity === 0 ? "text-rose-400 font-bold" : "text-emerald-400"}>
                      {selectedProduct.stock_quantity} available
                    </span>
                  </div>
                )}
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
                {selectedProduct && (
                  <div className="text-[10px] text-slate-400 mt-1 font-mono text-right">
                    Sub: ${(Number(selectedProduct.price || 0) * quantity).toFixed(2)}
                  </div>
                )}
              </div>
            </div>

            {/* Coupon & Failed Retries */}
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
                  Failed Payment Attempts
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

            {/* Shipping Address */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                Shipping Destination
              </label>
              <div className="grid grid-cols-2 gap-2 mb-2">
                <input
                  type="text"
                  value={shippingStreet}
                  onChange={(e) => setShippingStreet(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  placeholder="Street Address"
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
                  placeholder="Postal Code"
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
                Simulate Billing Address Mismatch (+20 risk points)
              </label>
            </div>

            {/* Submit Pipeline Trigger Button */}
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

        {/* Right Column: Execution Output, Financial Breakdown & Audit Logs */}
        <div className="lg:col-span-7 space-y-4">
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
                        ? "Order Escalated & Held (Fraud Review Queue)"
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
                    ${Number(orderResult.final_amount || 0).toFixed(2)}
                  </span>
                </div>
              </div>

              {/* PROMPT 4 & 5 HIGHLIGHT CARD */}
              {orderResult.dispatch_status === "DISPATCHED" ? (
                <div className="mb-4 p-4 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-xs">
                  <div className="font-bold text-emerald-300 uppercase tracking-wide text-[11px] mb-2 flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <Truck className="w-4 h-4 text-emerald-400" />
                      Fulfillment Output — Order Confirmed
                    </span>
                    {onViewOrderDetails && (
                      <button
                        onClick={() => onViewOrderDetails(orderResult.order_id)}
                        className="text-emerald-400 hover:text-emerald-200 underline text-[11px] font-sans flex items-center gap-1"
                      >
                        Deep Audit View <ArrowRight className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
                    <div className="bg-slate-950/60 p-2 rounded border border-emerald-900/40">
                      <span className="text-[10px] font-sans text-slate-400 block">Status</span>
                      <span className="text-emerald-400 font-bold">CONFIRMED</span>
                    </div>
                    <div className="bg-slate-950/60 p-2 rounded border border-emerald-900/40">
                      <span className="text-[10px] font-sans text-slate-400 block">Final Payable</span>
                      <span className="text-emerald-300 font-bold">${Number(orderResult.final_amount || 0).toFixed(2)}</span>
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
                  <div className="font-bold text-rose-300 uppercase tracking-wide text-[11px] mb-2 flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <ShieldAlert className="w-4 h-4 text-rose-400" />
                      Fraud Escalation Route — Order Held
                    </span>
                    {onViewOrderDetails && (
                      <button
                        onClick={() => onViewOrderDetails(orderResult.order_id)}
                        className="text-rose-400 hover:text-rose-200 underline text-[11px] font-sans flex items-center gap-1"
                      >
                        Deep Audit View <ArrowRight className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-3 font-mono mb-3">
                    <div className="bg-slate-950/60 p-2 rounded border border-rose-900/40">
                      <span className="text-[10px] font-sans text-slate-400 block">Order Result</span>
                      <span className="text-rose-400 font-bold">HELD</span>
                    </div>
                    <div className="bg-slate-950/60 p-2 rounded border border-rose-900/40">
                      <span className="text-[10px] font-sans text-slate-400 block">Fraud Score</span>
                      <span className="text-rose-400 font-bold">{orderResult.fraud_score} / 100</span>
                    </div>
                    <div className="bg-slate-950/60 p-2 rounded border border-rose-900/40">
                      <span className="text-[10px] font-sans text-slate-400 block">Review Status</span>
                      <span className="text-amber-400 font-bold">{orderResult.review_status}</span>
                    </div>
                  </div>
                  <div className="bg-slate-950/80 p-2.5 rounded border border-rose-900/30 font-sans text-rose-200">
                    <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider block mb-0.5">
                      Audit Justification & AI Explanation
                    </span>
                    {orderResult.fraud_ai_reasoning || orderResult.hold_reason}
                  </div>
                </div>
              )}

              {/* Financial Calculation Breakdown */}
              <div className="grid grid-cols-4 gap-2 mb-4 bg-slate-950 p-3 rounded-lg border border-slate-800/80 text-xs font-mono">
                <div>
                  <span className="text-[10px] text-slate-400 font-sans block">Subtotal</span>
                  ${Number(orderResult.subtotal || 0).toFixed(2)}
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-sans block">Discounts</span>
                  -${Number(orderResult.discount_amount || 0).toFixed(2)}
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-sans block">Tax (8%)</span>
                  +${Number(orderResult.tax_amount || 0).toFixed(2)}
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-sans block">Shipping</span>
                  +${Number(orderResult.shipping_cost || 0).toFixed(2)}
                </div>
              </div>

              {/* Agent Log Viewer */}
              <AgentLogViewer logs={orderResult.agent_execution_logs} />
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-500 shadow-sm">
              <Layers className="w-10 h-10 mx-auto text-slate-600 mb-3" />
              <h3 className="text-sm font-bold text-slate-400">Pipeline Ready</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Select any test demonstration on the left or customize inputs, then click Trigger Multi-Agent Fulfillment Pipeline.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
