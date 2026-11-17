export interface OrderItemState {
  product_id: string;
  sku: string;
  name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface AddressState {
  street: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface PaymentState {
  payment_method: string;
  payment_status: string;
  card_last4?: string;
  transaction_token?: string;
  billing_address?: AddressState;
}

export interface AgentLogEntry {
  agent_name: string;
  action: string;
  status: string;
  message: string;
  execution_time_ms: number;
  timestamp: string;
  details?: Record<string, any>;
}

export interface SubstituteRecommendation {
  original_sku: string;
  substitute_sku: string;
  substitute_name: string;
  substitute_price: number;
  reason: string;
}

export interface BackorderProposal {
  sku: string;
  product_name: string;
  requested_quantity: number;
  available_quantity: number;
  estimated_restock_days: number;
}

export interface OrderState {
  order_id: string;
  customer_id: string;
  customer_name?: string;
  customer_email?: string;
  customer_phone?: string;
  items: OrderItemState[];
  shipping_address: AddressState;
  payment_information: PaymentState;
  coupon_code?: string;
  validation_status: string;
  inventory_status: string;
  fraud_status: string;
  pricing_status: string;
  dispatch_status: string;
  fraud_score: number;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  shipping_cost: number;
  final_amount: number;
  hold_reason?: string;
  tracking_id?: string;
  carrier?: string;
  shipping_method?: string;
  review_status?: string;
  substitute_recommendations: SubstituteRecommendation[];
  backorder_proposals: BackorderProposal[];
  fraud_risk_factors: string[];
  fraud_ai_reasoning?: string;
  agent_execution_logs: AgentLogEntry[];
}

export interface CustomerHistoryStats {
  customer_id: string;
  total_orders: number;
  successful_orders: number;
  suspicious_orders: number;
  failed_payment_attempts: number;
  total_spent: number;
  average_order_value: number;
  suspicion_rate: number;
  risk_tier: string;
  prior_orders: Array<{
    id: string;
    order_id: string;
    status: string;
    amount: number;
    is_suspicious: boolean;
    failed_payment_attempts: number;
    notes?: string;
    created_at: string;
  }>;
}

export interface Customer {
  id: string;
  name: string;
  email: string;
  phone?: string;
  address: string;
  billing_address?: string;
  status: string;
  created_at: string;
  history_stats?: CustomerHistoryStats;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  description?: string;
  price: number;
  stock_quantity: number;
  substitute_sku?: string;
  category?: string;
  is_active: boolean;
}
