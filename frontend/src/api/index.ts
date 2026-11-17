import type {
  OrderState,
  Product,
  Customer,
  CustomerHistoryStats,
  OrderSummary,
  DashboardAnalytics,
  AgentsTelemetryResponse,
  FullOrderDetails,
  HeldOrder,
} from "../types";

const API_BASE = "http://localhost:8000/api";

export async function fetchProducts(): Promise<Product[]> {
  const res = await fetch(`${API_BASE}/products`);
  if (!res.ok) throw new Error("Failed to load products");
  return res.json();
}

export async function fetchCustomers(): Promise<Customer[]> {
  const res = await fetch(`${API_BASE}/customers`);
  if (!res.ok) throw new Error("Failed to load customers");
  return res.json();
}

export async function fetchCustomerMemory(customerId: string): Promise<CustomerHistoryStats> {
  const res = await fetch(`${API_BASE}/customers/${customerId}/memory`);
  if (!res.ok) throw new Error("Failed to load customer memory");
  return res.json();
}

export async function processOrder(payload: any): Promise<OrderState> {
  const res = await fetch(`${API_BASE}/orders/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to process order pipeline");
  }
  return res.json();
}

export async function fetchOrders(): Promise<OrderSummary[]> {
  const res = await fetch(`${API_BASE}/orders`);
  if (!res.ok) throw new Error("Failed to load orders");
  return res.json();
}

export async function fetchOrderDetails(orderId: string): Promise<FullOrderDetails> {
  const res = await fetch(`${API_BASE}/orders/${orderId}`);
  if (!res.ok) throw new Error(`Failed to load order details for ${orderId}`);
  return res.json();
}

export async function fetchHeldOrders(): Promise<HeldOrder[]> {
  const res = await fetch(`${API_BASE}/orders/queue/held`);
  if (!res.ok) throw new Error("Failed to load held orders");
  return res.json();
}

export async function overrideHeldOrder(orderId: string, notes?: string): Promise<any> {
  const params = notes ? `?auditor_notes=${encodeURIComponent(notes)}` : "";
  const res = await fetch(`${API_BASE}/orders/${orderId}/override-hold${params}`, {
    method: "POST",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to override held order");
  }
  return res.json();
}

export async function rejectHeldOrder(orderId: string, reason?: string): Promise<any> {
  const params = reason ? `?rejection_reason=${encodeURIComponent(reason)}` : "";
  const res = await fetch(`${API_BASE}/orders/${orderId}/reject${params}`, {
    method: "POST",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to reject held order");
  }
  return res.json();
}

export async function fetchDashboardAnalytics(): Promise<DashboardAnalytics> {
  const res = await fetch(`${API_BASE}/dashboard/analytics`);
  if (!res.ok) throw new Error("Failed to load dashboard analytics");
  return res.json();
}

export async function fetchAgentsInfo(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/info`);
  if (!res.ok) throw new Error("Failed to load agent info");
  return res.json();
}

export async function fetchAgentsTelemetry(): Promise<AgentsTelemetryResponse> {
  const res = await fetch(`${API_BASE}/agents/telemetry`);
  if (!res.ok) throw new Error("Failed to load agent telemetry");
  return res.json();
}

export async function reseedDatabase(): Promise<any> {
  const res = await fetch(`${API_BASE}/seed`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to reset sample data");
  return res.json();
}
