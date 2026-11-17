import type { OrderState, Product, Customer, CustomerHistoryStats } from "../types";

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

export async function fetchHeldOrders(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/orders/queue/held`);
  if (!res.ok) throw new Error("Failed to load held orders");
  return res.json();
}

export async function overrideHeldOrder(orderId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/orders/${orderId}/override-hold`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to override held order");
  return res.json();
}

export async function fetchAgentsInfo(): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/info`);
  if (!res.ok) throw new Error("Failed to load agent info");
  return res.json();
}
