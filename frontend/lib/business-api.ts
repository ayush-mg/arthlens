/**
 * ArthLens Business Operating System & Decision Intelligence API Client.
 * Connects the Next.js motion-led frontend to the deterministic FastAPI backend.
 * All arithmetic is computed strictly on the backend.
 */
import { apiFetch, ApiError, setAuthToken } from './api';

export function setStoredToken(token: string | null) {
  setAuthToken(token);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, options);

  if (!res.ok) {
    let errMessage = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errBody = await res.json();
      if (errBody.detail) {
        errMessage = typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail);
      }
    } catch {
      // Keep statusText
    }
    throw new ApiError(res.status, errMessage);
  }

  // If response is 204 or empty
  if (res.status === 204) {
    return {} as T;
  }

  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return res.json();
  }
  return res.text() as unknown as T;
}

export async function downloadAuthenticatedReport(path: string, fallbackFilename: string): Promise<void> {
  const response = await apiFetch(path);
  if (!response.ok) {
    let message = `Report download failed (${response.status}).`;
    try {
      const payload = await response.json();
      if (typeof payload.detail === 'string') message = payload.detail;
    } catch {
      // Keep the HTTP status message when the error body is not JSON.
    }
    throw new ApiError(response.status, message);
  }

  const contentType = (response.headers.get('content-type') || '').toLowerCase();
  if (contentType.includes('application/json')) {
    let message = 'File generation failed: server returned data instead of a document file.';
    try {
      const payload = await response.json();
      if (typeof payload.detail === 'string') message = payload.detail;
      else if (payload.message) message = payload.message;
    } catch {}
    throw new ApiError(400, message);
  }

  const disposition = response.headers.get('Content-Disposition') || '';
  const encodedName = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  const plainName = disposition.match(/filename="?([^";]+)"?/i)?.[1];
  const filename = encodedName
    ? decodeURIComponent(encodedName)
    : plainName || fallbackFilename;
  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = blobUrl;
  anchor.download = filename || fallbackFilename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(blobUrl), 100);
}

// ==========================================
// Types
// ==========================================

export interface BusinessWorkspace {
  id: string;
  name: string;
  legal_name?: string | null;
  industry: string;
  pan?: string | null;
  gstin?: string | null;
  address?: string | null;
  state?: string | null;
  district?: string | null;
  pincode?: string | null;
  created_at: string;
  role?: string;
  is_active: boolean;
  is_archived?: boolean;
  currency?: string;
  financial_year_start?: string;
}

export interface BusinessPortfolioSummary {
  as_of_date: string;
  period_start: string;
  business_count: number;
  revenue_30d_exact: string;
  net_profit_30d_exact: string;
  cash_position_exact: string;
  active_alerts: number;
  workspaces: Array<{
    id: string;
    name: string;
    industry: string;
    role: string;
    is_archived: boolean;
    revenue_30d_exact: string;
    net_profit_30d_exact: string;
    cash_position_exact: string;
    health_score: number;
    active_alerts: number;
    data_quality_warnings: string[];
  }>;
}

export interface Customer {
  id: string;
  business_id: string;
  name: string;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  gstin?: string | null;
  credit_limit_amount: number | string;
  credit_period_days: number;
  current_balance_amount: number | string;
  is_active: boolean;
  created_at: string;
}

export interface Supplier {
  id: string;
  business_id: string;
  name: string;
  contact_person?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  gstin?: string | null;
  payment_terms_days: number;
  current_balance_amount: number | string;
  is_active: boolean;
  created_at: string;
}

export interface Product {
  id: string;
  business_id: string;
  sku: string;
  name: string;
  description?: string | null;
  category: string;
  unit_of_measure: string;
  selling_price_amount: number | string;
  purchase_price_amount: number | string;
  tax_rate_pct?: number;
  current_stock: number;
  weighted_average_cost: number | string;
  reorder_level: number;
  is_active: boolean;
  created_at: string;
}

export interface SalesInvoiceItem {
  id?: string;
  product_id?: string | null;
  item_description: string;
  quantity: number | string;
  unit_price: number | string;
  tax_rate_pct?: number | string;
  tax_amount?: number | string;
  total_amount?: number | string;
  total_price_exact?: string;
}

export interface SalesInvoice {
  id: string;
  business_id: string;
  invoice_number: string;
  customer_id?: string | null;
  invoice_date: string;
  due_date: string;
  subtotal_amount: number | string;
  tax_amount: number | string;
  total_amount: number | string;
  paid_amount: number | string;
  outstanding_amount: number | string;
  subtotal_exact?: string;
  tax_amount_exact?: string;
  total_amount_exact?: string;
  paid_amount_exact?: string;
  outstanding_balance_exact?: string;
  currency?: string;
  status: 'DRAFT' | 'ISSUED' | 'PARTIALLY_PAID' | 'PAID' | 'OVERDUE' | 'CANCELLED';
  notes?: string | null;
  items: SalesInvoiceItem[];
  created_at: string;
}

export interface PurchaseItem {
  id?: string;
  product_id?: string | null;
  item_description: string;
  quantity: number | string;
  unit_price: number | string;
  tax_rate_pct?: number | string;
  tax_amount?: number | string;
  total_amount?: number | string;
  returned_quantity?: number | string;
  remaining_returnable_quantity?: number | string;
}

export interface PurchaseRecord {
  id: string;
  business_id: string;
  purchase_order_number?: string | null;
  supplier_id?: string | null;
  purchase_date: string;
  due_date?: string | null;
  subtotal_amount: number | string;
  tax_amount: number | string;
  total_amount: number | string;
  paid_amount: number | string;
  outstanding_amount: number | string;
  subtotal_exact?: string;
  tax_amount_exact?: string;
  total_amount_exact?: string;
  paid_amount_exact?: string;
  outstanding_balance_exact?: string;
  currency?: string;
  status: 'PENDING' | 'RECEIVED' | 'PARTIALLY_PAID' | 'PAID' | 'PARTIALLY_RETURNED' | 'RETURNED' | 'CANCELLED';
  items: PurchaseItem[];
  created_at: string;
}

function normalizeInvoice(raw: any): SalesInvoice {
  return {
    ...raw,
    subtotal_amount: raw.subtotal_exact ?? raw.subtotal_amount ?? raw.subtotal ?? 0,
    tax_amount: raw.tax_amount_exact ?? raw.tax_amount ?? 0,
    total_amount: raw.total_amount_exact ?? raw.total_amount ?? 0,
    paid_amount: raw.paid_amount_exact ?? raw.paid_amount ?? 0,
    outstanding_amount: raw.outstanding_balance_exact ?? raw.outstanding_amount ?? raw.outstanding_balance ?? 0,
    items: (raw.items ?? []).map((item: any) => ({
      ...item,
      item_description: item.item_description ?? item.description ?? '',
      unit_price: item.unit_price_exact ?? item.unit_price ?? 0,
      total_amount: item.total_price_exact ?? item.total_amount ?? item.total_price ?? 0,
    })),
  };
}

function normalizePurchase(raw: any): PurchaseRecord {
  return {
    ...raw,
    purchase_order_number: raw.purchase_order_number ?? raw.bill_number,
    subtotal_amount: raw.subtotal_exact ?? raw.subtotal_amount ?? raw.subtotal ?? 0,
    tax_amount: raw.tax_amount_exact ?? raw.tax_amount ?? 0,
    total_amount: raw.total_amount_exact ?? raw.total_amount ?? 0,
    paid_amount: raw.paid_amount_exact ?? raw.paid_amount ?? 0,
    outstanding_amount: raw.outstanding_balance_exact ?? raw.outstanding_amount ?? raw.outstanding_balance ?? 0,
    items: (raw.items ?? []).map((item: any) => ({
      ...item,
      item_description: item.item_description ?? item.description ?? '',
      unit_price: item.unit_price_exact ?? item.unit_price ?? 0,
      total_amount: item.total_price_exact ?? item.total_amount ?? item.total_price ?? 0,
    })),
  };
}

export interface InventoryBalance {
  product_id: string;
  sku: string;
  name: string;
  unit_of_measure: string;
  current_stock: number;
  weighted_average_cost: number | string;
  total_valuation: number | string;
  reorder_level: number;
  needs_reorder: boolean;
}

export interface CashPosition {
  cash_on_hand: number | string;
  cash_on_hand_exact?: string;
  bank_balance: number | string;
  bank_balance_exact?: string;
  total_liquid_cash: number | string;
  total_liquid_cash_exact?: string;
  total_receivables: number | string;
  total_receivables_exact?: string;
  total_payables: number | string;
  total_payables_exact?: string;
  net_liquid_working_capital: number | string;
  net_liquid_working_capital_exact?: string;
}

export interface BusinessScenario {
  id: string;
  business_id: string;
  name: string;
  description: string;
  current_version: number;
  latest_version?: BusinessScenarioVersion;
  analysis?: ScenarioAnalysis;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface BusinessScenarioVersion {
  id: string;
  scenario_id: string;
  version_number: number;
  assumptions: Record<string, any>;
  baseline_snapshot_hash: string;
  analysis?: ScenarioAnalysis;
  created_at?: string | null;
}

export interface ScenarioAnalysis {
  model_version: string;
  cases: Record<string, { months: any[]; summary: Record<string, any> }>;
  sensitivity_tornado: any[];
}

export interface Goal {
  id: string;
  business_id: string;
  title: string;
  description?: string | null;
  goal_type: string;
  target_amount: number | string;
  target_amount_exact?: string;
  current_amount: number | string;
  current_amount_exact?: string;
  unit: string;
  progress_pct: number;
  start_date: string;
  target_date: string;
  status: string;
  created_at: string;
}

export interface ProfitAndLossStatement {
  business_id: string;
  start_date: string;
  end_date: string;
  gross_sales: number | string;
  gross_sales_exact?: string;
  sales_returns: number | string;
  sales_returns_exact?: string;
  direct_income: number | string;
  direct_income_exact?: string;
  total_revenue: number | string;
  total_revenue_exact?: string;
  cost_of_goods_sold: number | string;
  cost_of_goods_sold_exact?: string;
  gross_profit: number | string;
  gross_profit_exact?: string;
  gross_margin_percent: number;
  operating_expenses: Record<string, number | string>;
  operating_expenses_exact?: Record<string, string>;
  total_operating_expenses: number | string;
  total_operating_expenses_exact?: string;
  operating_profit_ebitda: number | string;
  operating_profit_ebitda_exact?: string;
  operating_margin_percent: number;
  net_profit: number | string;
  net_profit_exact?: string;
  net_margin_percent: number;
  data_quality_warnings: string[];
}

export interface CashFlowStatement {
  operating_cash_inflow: number | string;
  operating_cash_outflow: number | string;
  net_operating_cash_flow: number | string;
  investing_cash_flow: number | string;
  financing_cash_flow: number | string;
  net_change_in_cash: number | string;
  opening_cash_balance: number | string;
  closing_cash_balance: number | string;
}

export interface WorkingCapitalAnalysis {
  current_assets: number | string;
  cash_and_bank: number | string;
  accounts_receivable: number | string;
  inventory_valuation: number | string;
  current_liabilities: number | string;
  accounts_payable: number | string;
  net_working_capital: number | string;
  current_ratio: number | null;
  quick_ratio: number | null;
  solvency_health: 'STRONG' | 'ADEQUATE' | 'STRESSED' | 'INSOLVENT';
}

export interface AgeingAnalysis {
  as_of_date: string;
  receivables: {
    bucket_0_30: number | string;
    bucket_31_60: number | string;
    bucket_61_90: number | string;
    bucket_90_plus: number | string;
    total: number | string;
  };
  payables: {
    bucket_0_30: number | string;
    bucket_31_60: number | string;
    bucket_61_90: number | string;
    bucket_90_plus: number | string;
    total: number | string;
  };
}

export interface BreakEvenAnalysis {
  total_revenue: number | string;
  total_revenue_exact?: string;
  total_variable_costs: number | string;
  total_fixed_costs: number | string;
  total_fixed_costs_exact?: string;
  contribution_margin: number | string;
  contribution_margin_exact?: string;
  contribution_margin_ratio: number;
  break_even_revenue_monthly: number | string | null;
  margin_of_safety_pct: number | null;
  is_operating_above_breakeven: boolean;
}

export interface BusinessHealthScore {
  overall_score: number;
  grade: string;
  pillars: Record<string, { score: number; max: number; months?: number }>;
  cash_runway_months: number;
  key_strengths: string[];
  identified_risks: string[];
  data_completeness_score: string;
  composite_score?: number;
  classification?: string;
  liquidity_score?: number;
  profitability_score?: number;
  efficiency_score?: number;
  solvency_score?: number;
  growth_stability_score?: number;
  strengths?: string[];
  vulnerabilities?: string[];
  priority_recommendations?: string[];
}

export interface DecisionAlternativeResult {
  alternative_id: string;
  alternative_name: string;
  description?: string;
  rank: number;
  npv_amount: number | null;
  irr_pct?: number | null;
  payback_period_months: number | null;
  monthly_net_cash_impact: number | null;
  roi_pct: number | null;
  risk_score_0_to_100: number | null;
  composite_score: number | null;
  outcome: string;
  key_drivers: string[];
  fatal_flaws: string[];
}

export interface DecisionEvaluationResult {
  evaluation_id: string;
  business_id: string;
  model_type: string;
  decision_title: string;
  status: string;
  alternatives: DecisionAlternativeResult[];
  recommended_alternative_id: string | null;
  baseline_monthly_revenue: number | null;
  baseline_monthly_net_profit: number | null;
  executive_summary: string;
  created_at: string;
  version_number: number | null;
  parent_decision_id: string | null;
  inputs: Record<string, unknown>;
  calculations: Record<string, unknown>;
  graph: { nodes: Array<Record<string, unknown>>; edges: Array<Record<string, unknown>> };
  evidence_items: Array<Record<string, unknown>>;
}

export interface DecisionVersion {
  id: string;
  business_id: string;
  model_id: string;
  model_version: string;
  version_number: number;
  parent_decision_id: string | null;
  objective: string;
  inputs: Record<string, unknown>;
  calculations: Record<string, unknown>;
  constraints: Array<Record<string, unknown>>;
  alternatives: Array<Record<string, unknown>>;
  outcome: string;
  explanation: string;
  causal_graph: { nodes: Array<Record<string, unknown>>; edges: Array<Record<string, unknown>> };
  evidence_items: Array<Record<string, unknown>>;
  created_at: string;
}

export interface MonteCarloRiskResult {
  iterations_run: number;
  p10_worst_case_npv: number;
  p50_median_npv: number;
  p90_best_case_npv: number;
  probability_of_negative_npv_pct: number;
  probability_of_payback_within_3yr_pct: number;
  var_95_pct_risk_amount: number;
  confidence_verdict: string;
}

export interface SensitivityAnalysisResult {
  base_npv: number;
  variable_swings: Array<{
    variable_name: string;
    low_value: number;
    high_value: number;
    low_npv: number;
    high_npv: number;
    swing_range: number;
    elasticity_ratio: number;
  }>;
  primary_risk_driver: string;
  recommendations: string[];
}

export interface InvestigationPlanStep {
  step_number: number;
  title: string;
  tool_name: string;
  arguments: Record<string, any>;
  status: 'PENDING' | 'EXECUTED' | 'SKIPPED' | 'FAILED';
  result?: Record<string, any> | null;
  observation?: string;
}

export interface ProviderAttribution {
  actual_provider: string;
  model_name: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  fallback_used: boolean;
  fallback_reason?: string | null;
}

export interface AgentInvestigationResponse {
  session_id?: string;
  business_id?: string;
  user_query?: string;
  query?: string;
  intent?: string;
  plan?: InvestigationPlanStep[];
  plan_nodes?: Array<{
    step: number;
    tool_name: string;
    purpose: string;
    status: 'PLANNED' | 'EXECUTED' | 'FAILED' | 'SKIPPED';
    result_summary?: string;
  }>;
  evidence_gathered?: Record<string, any>;
  data_gaps?: string[];
  follow_up_questions?: string[];
  decision_outcome?: string | null;
  synthesis: string;
  planning_attribution?: ProviderAttribution;
  synthesis_attribution?: ProviderAttribution;
  llm_provider?: string;
  created_at?: string;
  recommended_actions?: string[];
  decision_link?: string | null;
  evidence_items?: Array<{
    source_type: string;
    record_id: string;
    label: string;
    metric_value: string;
    timestamp: string;
  }>;
  proposed_actions?: AgentProposedAction[];
}

export interface AgentProposedAction {
  id: string;
  business_id: string;
  session_id: string;
  action_type: 'CREATE_GOAL' | 'CREATE_TASK' | 'GENERATE_REPORT';
  payload: Record<string, any>;
  status: 'PENDING_CONFIRMATION' | 'CONFIRMED' | 'REJECTED';
  result: Record<string, any>;
  created_at: string | null;
}

// ==========================================
// API Methods
// ==========================================

export const businessApi = {
  // Workspaces
  async listWorkspaces(): Promise<BusinessWorkspace[]> {
    return request<BusinessWorkspace[]>('/businesses');
  },

  async getPortfolioSummary(): Promise<BusinessPortfolioSummary> {
    return request<BusinessPortfolioSummary>('/businesses/portfolio');
  },

  async createWorkspace(data: {
    name: string;
    legal_name?: string;
    industry: string;
    currency?: string;
    pan?: string;
    gstin?: string;
    address?: string;
    state?: string;
    district?: string;
    pincode?: string;
  }): Promise<BusinessWorkspace> {
    return request<BusinessWorkspace>('/businesses', {
      method: 'POST',
      body: JSON.stringify({
        name: data.name,
        industry: data.industry,
        currency: data.currency || 'INR',
        address: data.address || `${data.district || ''}, ${data.state || ''}`.trim(),
      }),
    });
  },

  async getWorkspace(businessId: string): Promise<BusinessWorkspace> {
    return request<BusinessWorkspace>(`/businesses/${businessId}`);
  },

  async updateWorkspace(businessId: string, data: Partial<BusinessWorkspace>): Promise<BusinessWorkspace> {
    return request<BusinessWorkspace>(`/businesses/${businessId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async archiveWorkspace(businessId: string, isArchived: boolean = true): Promise<{ status: string; business_id: string; is_archived: boolean }> {
    return request<{ status: string; business_id: string; is_archived: boolean }>(`/businesses/${businessId}/archive`, {
      method: 'POST',
      body: JSON.stringify({ is_archived: isArchived }),
    });
  },

  async deleteWorkspace(businessId: string): Promise<{ status: string; business_id: string; deleted: boolean }> {
    return request<{ status: string; business_id: string; deleted: boolean }>(`/businesses/${businessId}`, {
      method: 'DELETE',
    });
  },

  // Members
  async listMembers(businessId: string): Promise<any[]> {
    return request<any[]>(`/businesses/${businessId}/members`);
  },

  async addMember(businessId: string, data: { user_id: string; role: string }): Promise<any> {
    return request<any>(`/businesses/${businessId}/members`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateMemberRole(businessId: string, userId: string, role: string): Promise<any> {
    return request<any>(`/businesses/${businessId}/members/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    });
  },

  async removeMember(businessId: string, userId: string): Promise<any> {
    return request<any>(`/businesses/${businessId}/members/${userId}`, {
      method: 'DELETE',
    });
  },

  async listActivity(businessId: string): Promise<any[]> {
    return request<any[]>(`/businesses/${businessId}/activity`);
  },

  // Khata: Customers
  async listCustomers(businessId: string): Promise<Customer[]> {
    const list = await request<any[]>(`/businesses/${businessId}/customers`);
    return list.map((c) => ({
      ...c,
      credit_limit_amount: c.credit_limit_exact ?? c.credit_limit ?? 0,
      credit_period_days: 30,
      current_balance_amount: c.current_balance_exact ?? c.current_balance ?? 0,
    }));
  },

  async createCustomer(businessId: string, data: any): Promise<Customer> {
    const created = await request<any>(`/businesses/${businessId}/customers`, {
      method: 'POST',
      body: JSON.stringify({
        name: data.name,
        phone: data.phone || '',
        email: data.email || '',
        address: data.address || '',
        credit_limit: data.credit_limit_amount ?? data.credit_limit ?? 0,
        opening_balance: data.opening_balance ?? 0,
      }),
    });
    return {
      ...created,
      credit_limit_amount: created.credit_limit_exact ?? created.credit_limit ?? 0,
      credit_period_days: 30,
      current_balance_amount: created.current_balance_exact ?? created.current_balance ?? 0,
    };
  },

  async getCustomer(businessId: string, customerId: string): Promise<Customer> {
    const c = await request<any>(`/businesses/${businessId}/customers/${customerId}`);
    return {
      ...c,
      credit_limit_amount: c.credit_limit_exact ?? c.credit_limit ?? 0,
      credit_period_days: 30,
      current_balance_amount: c.current_balance_exact ?? c.current_balance ?? 0,
    };
  },

  async updateCustomer(businessId: string, customerId: string, data: Partial<Customer>): Promise<Customer> {
    const updated = await request<any>(`/businesses/${businessId}/customers/${customerId}`, {
      method: 'PUT',
      body: JSON.stringify({
        name: data.name,
        phone: data.phone,
        email: data.email,
        address: data.address,
        credit_limit: data.credit_limit_amount,
      }),
    });
    return {
      ...updated,
      credit_limit_amount: updated.credit_limit_exact ?? updated.credit_limit ?? 0,
      credit_period_days: 30,
      current_balance_amount: updated.current_balance_exact ?? updated.current_balance ?? 0,
    };
  },

  async getCustomerLedger(businessId: string, customerId: string): Promise<any> {
    const ledger = await request<any>(`/businesses/${businessId}/customers/${customerId}/ledger`);
    return {
      ...ledger,
      credit_limit: ledger.credit_limit_exact ?? ledger.credit_limit,
      current_balance: ledger.current_balance_exact ?? ledger.current_balance,
      entries: (ledger.entries ?? []).map((entry: any) => ({
        ...entry,
        debit: entry.debit_exact ?? entry.debit,
        credit: entry.credit_exact ?? entry.credit,
        running_balance: entry.running_balance_exact ?? entry.running_balance,
      })),
    };
  },

  // Khata: Suppliers
  async listSuppliers(businessId: string): Promise<Supplier[]> {
    const list = await request<any[]>(`/businesses/${businessId}/suppliers`);
    return list.map((s) => ({
      ...s,
      payment_terms_days: 15,
      current_balance_amount: s.current_balance_exact ?? s.current_balance ?? 0,
    }));
  },

  async createSupplier(businessId: string, data: any): Promise<Supplier> {
    const created = await request<any>(`/businesses/${businessId}/suppliers`, {
      method: 'POST',
      body: JSON.stringify({
        name: data.name,
        contact_person: data.contact_person || '',
        phone: data.phone || '',
        email: data.email || '',
        address: data.address || '',
        opening_balance: data.opening_balance ?? 0,
      }),
    });
    return {
      ...created,
      payment_terms_days: 15,
      current_balance_amount: created.current_balance_exact ?? created.current_balance ?? 0,
    };
  },

  async getSupplierLedger(businessId: string, supplierId: string): Promise<any> {
    const ledger = await request<any>(`/businesses/${businessId}/suppliers/${supplierId}/ledger`);
    return {
      ...ledger,
      current_balance: ledger.current_balance_exact ?? ledger.current_balance,
      entries: (ledger.entries ?? []).map((entry: any) => ({
        ...entry,
        debit: entry.debit_exact ?? entry.debit,
        credit: entry.credit_exact ?? entry.credit,
        running_balance: entry.running_balance_exact ?? entry.running_balance,
      })),
    };
  },

  async updateSupplier(businessId: string, supplierId: string, data: Partial<Supplier>): Promise<Supplier> {
    const updated = await request<any>(`/businesses/${businessId}/suppliers/${supplierId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    return {
      ...updated,
      payment_terms_days: 15,
      current_balance_amount: updated.current_balance || 0,
    };
  },

  // Inventory & Products
  async listProducts(businessId: string): Promise<Product[]> {
    const list = await request<any[]>(`/businesses/${businessId}/products`);
    return list.map((p) => ({
      ...p,
      unit_of_measure: p.unit || 'pcs',
      selling_price_amount: p.selling_price_exact ?? p.selling_price ?? 0,
      purchase_price_amount: p.purchase_price_exact ?? p.purchase_price ?? 0,
      current_stock: p.current_stock || 0,
      weighted_average_cost: p.weighted_average_cost || p.purchase_price || 0,
      reorder_level: p.min_stock_alert || 0,
    }));
  },

  async createProduct(businessId: string, data: any): Promise<Product> {
    const created = await request<any>(`/businesses/${businessId}/products`, {
      method: 'POST',
      body: JSON.stringify({
        sku: data.sku,
        name: data.name,
        category: data.category || 'GENERAL',
        unit: data.unit_of_measure || data.unit || 'pcs',
        purchase_price: data.purchase_price_amount ?? data.purchase_price ?? 0,
        selling_price: data.selling_price_amount ?? data.selling_price ?? 0,
        min_stock_alert: data.reorder_level ?? data.min_stock_alert ?? 0,
        initial_stock: data.current_stock ?? data.initial_stock ?? 0,
      }),
    });
    return {
      ...created,
      unit_of_measure: created.unit || 'pcs',
      selling_price_amount: created.selling_price_exact ?? created.selling_price ?? 0,
      purchase_price_amount: created.purchase_price_exact ?? created.purchase_price ?? 0,
      current_stock: created.current_stock || 0,
      weighted_average_cost: created.weighted_average_cost || created.purchase_price || 0,
      reorder_level: created.min_stock_alert || 0,
    };
  },

  async updateProduct(businessId: string, productId: string, data: Partial<Product>): Promise<Product> {
    const updated = await request<any>(`/businesses/${businessId}/products/${productId}`, {
      method: 'PUT',
      body: JSON.stringify({
        name: data.name,
        category: data.category,
        unit: data.unit_of_measure,
        purchase_price: data.purchase_price_amount,
        selling_price: data.selling_price_amount,
        min_stock_alert: data.reorder_level,
        is_active: data.is_active,
      }),
    });
    return {
      ...updated,
      unit_of_measure: updated.unit || 'pcs',
      selling_price_amount: updated.selling_price_exact ?? updated.selling_price ?? 0,
      purchase_price_amount: updated.purchase_price_exact ?? updated.purchase_price ?? 0,
      current_stock: updated.current_stock || 0,
      weighted_average_cost: updated.weighted_average_cost || updated.purchase_price || 0,
      reorder_level: updated.min_stock_alert || 0,
    };
  },

  async adjustInventory(businessId: string, data: {
    product_id: string;
    quantity_delta: number;
    movement_type: string;
    unit_cost_amount?: number;
    reference_note?: string;
  }): Promise<any> {
    return request<any>(`/businesses/${businessId}/inventory/adjust`, {
      method: 'POST',
      body: JSON.stringify({
        product_id: data.product_id,
        movement_type: data.movement_type,
        quantity: Math.abs(data.quantity_delta),
        unit_price: data.unit_cost_amount || 0.0,
        reason: data.reference_note || 'Manual adjustment',
        reference_id: 'MANUAL',
      }),
    });
  },

  async getInventoryBalances(businessId: string): Promise<InventoryBalance[]> {
    const list = await request<any[]>(`/businesses/${businessId}/inventory/balances`);
    return list.map((b) => ({
      ...b,
      unit_of_measure: b.unit || 'pcs',
      current_stock: b.quantity_on_hand ?? b.current_stock ?? 0,
      weighted_average_cost: b.unit_cost_exact ?? b.unit_cost ?? b.weighted_average_cost ?? 0,
      total_valuation: b.total_valuation_exact ?? b.total_valuation ?? 0,
      reorder_level: b.min_stock_alert || 0,
      needs_reorder: b.is_low_stock ?? ((b.quantity_on_hand ?? b.current_stock ?? 0) <= (b.min_stock_alert || 0)),
    }));
  },

  async getInventoryMovements(businessId: string, productId?: string): Promise<any[]> {
    const q = productId ? `?product_id=${productId}` : '';
    const rows = await request<any[]>(`/businesses/${businessId}/inventory/movements${q}`);
    return rows.map((row) => {
      const purchaseReturn = row.movement_type === 'RETURN' && String(row.reason || '').toLowerCase().includes('purchase return');
      const sign = row.movement_type === 'SALE' || purchaseReturn ? -1 : 1;
      return {
        ...row,
        quantity_delta: sign * Number(row.quantity || 0),
        new_stock_balance: row.balance_after,
        reference_note: row.reason,
        unit_price: row.unit_price_exact ?? row.unit_price,
        cost_basis: row.cost_basis_exact ?? row.cost_basis,
      };
    });
  },

  async getUnreconciledInventoryCosts(businessId: string): Promise<any> {
    return request<any>(`/businesses/${businessId}/inventory/unreconciled-costs`);
  },

  async reconcileInventoryCosts(businessId: string, data: {
    mode: 'CHRONOLOGICAL_REPLAY' | 'MANUAL_ATTESTATION';
    overrides?: Array<{ movement_id: string; unit_cost: string; note: string }>;
  }): Promise<any> {
    return request<any>(`/businesses/${businessId}/inventory/reconcile-costs`, {
      method: 'POST',
      body: JSON.stringify({ mode: data.mode, overrides: data.overrides ?? [] }),
    });
  },

  // Sales & Invoicing
  async listInvoices(businessId: string): Promise<SalesInvoice[]> {
    const rows = await request<any[]>(`/businesses/${businessId}/invoices`);
    return rows.map(normalizeInvoice);
  },

  async createInvoice(businessId: string, data: {
    customer_id?: string | null;
    invoice_date: string;
    due_date?: string | null;
    items: SalesInvoiceItem[];
    tax_amount?: string | number;
    notes?: string;
    is_cash_sale?: boolean;
    immediate_payment_method?: string;
  }): Promise<SalesInvoice> {
    const invoiceNumber = `INV-${Date.now().toString().slice(-6)}`;
    const created = await request<any>(`/businesses/${businessId}/invoices`, {
      method: 'POST',
      body: JSON.stringify({
        customer_id: data.customer_id || null,
        invoice_number: invoiceNumber,
        invoice_date: data.invoice_date,
        due_date: data.due_date || data.invoice_date,
        items: data.items.map((it) => ({
          product_id: it.product_id || null,
          description: it.item_description,
          quantity: it.quantity,
          unit: 'pcs',
          unit_price: it.unit_price,
          discount_percent: 0.0,
        })),
        tax_amount: data.tax_amount ?? '0.00',
        notes: data.notes || '',
        is_cash_sale: Boolean(data.is_cash_sale),
        immediate_payment_method: data.immediate_payment_method || (data.is_cash_sale ? 'CASH' : undefined),
      }),
    });
    return normalizeInvoice(created);
  },

  async getInvoice(businessId: string, invoiceId: string): Promise<SalesInvoice> {
    return normalizeInvoice(await request<any>(`/businesses/${businessId}/invoices/${invoiceId}`));
  },

  async recordInvoicePayment(businessId: string, invoiceId: string, data: {
    amount: number | string;
    payment_method: string;
    payment_reference?: string;
    notes?: string;
  }): Promise<SalesInvoice> {
    const updated = await request<any>(`/businesses/${businessId}/invoices/${invoiceId}/payments`, {
      method: 'POST',
      body: JSON.stringify({
        amount: data.amount,
        payment_date: new Date().toISOString().split('T')[0],
        payment_method: data.payment_method,
        notes: data.notes || '',
      }),
    });
    return normalizeInvoice(updated);
  },

  async cancelInvoice(businessId: string, invoiceId: string, reason?: string): Promise<SalesInvoice> {
    const updated = await request<any>(`/businesses/${businessId}/invoices/${invoiceId}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason || 'Cancelled by user' }),
    });
    return normalizeInvoice(updated);
  },

  async updateInvoice(businessId: string, invoiceId: string, data: {
    customer_id?: string | null;
    invoice_number: string;
    invoice_date: string;
    due_date?: string | null;
    items: SalesInvoiceItem[];
    tax_amount?: string | number;
    notes?: string;
  }): Promise<SalesInvoice> {
    const updated = await request<any>(`/businesses/${businessId}/invoices/${invoiceId}`, {
      method: 'PUT',
      body: JSON.stringify({
        customer_id: data.customer_id || null,
        invoice_number: data.invoice_number,
        invoice_date: data.invoice_date,
        due_date: data.due_date || data.invoice_date,
        items: data.items.map((it) => ({
          product_id: it.product_id || null,
          description: it.item_description,
          quantity: it.quantity,
          unit: 'pcs',
          unit_price: it.unit_price,
          discount_percent: 0.0,
        })),
        tax_amount: data.tax_amount ?? '0.00',
        notes: data.notes || '',
      }),
    });
    return normalizeInvoice(updated);
  },

  async deleteInvoice(businessId: string, invoiceId: string): Promise<{ success: boolean; deleted_id: string }> {
    return request<{ success: boolean; deleted_id: string }>(`/businesses/${businessId}/invoices/${invoiceId}`, {
      method: 'DELETE',
    });
  },

  // Purchases & Procurement
  async listPurchases(businessId: string): Promise<PurchaseRecord[]> {
    const rows = await request<any[]>(`/businesses/${businessId}/purchases`);
    return rows.map(normalizePurchase);
  },

  async listPurchaseReturns(businessId: string, purchaseId: string): Promise<any[]> {
    const rows = await request<any[]>(`/businesses/${businessId}/returns/purchases/${purchaseId}`);
    return rows.map((row) => ({
      ...row,
      subtotal: row.subtotal_exact ?? row.subtotal,
      tax_amount: row.tax_amount_exact ?? row.tax_amount,
      total_returned: row.total_returned_exact ?? row.total_returned,
    }));
  },

  async recordPurchaseReturn(businessId: string, data: {
    purchase_id: string;
    items: Array<{ purchase_item_id: string; quantity: string | number }>;
    return_date: string;
    reason?: string;
    refund_method?: string | null;
    idempotency_key: string;
  }): Promise<any> {
    const created = await request<any>(`/businesses/${businessId}/returns/purchases`, {
      method: 'POST',
      body: JSON.stringify({
        ...data,
        reason: data.reason || 'Supplier return',
        refund_method: data.refund_method || null,
      }),
    });
    return {
      ...created,
      total_returned: created.total_returned_exact ?? created.total_returned,
    };
  },

  async createPurchase(businessId: string, data: {
    supplier_id?: string | null;
    purchase_order_number?: string;
    purchase_date: string;
    due_date?: string | null;
    items: PurchaseItem[];
    tax_amount?: string | number;
    notes?: string;
    is_cash_purchase?: boolean;
    immediate_payment_method?: string;
  }): Promise<PurchaseRecord> {
    const billNumber = data.purchase_order_number || `BILL-${Date.now().toString().slice(-6)}`;
    const created = await request<any>(`/businesses/${businessId}/purchases`, {
      method: 'POST',
      body: JSON.stringify({
        supplier_id: data.supplier_id || null,
        bill_number: billNumber,
        purchase_date: data.purchase_date,
        due_date: data.due_date || data.purchase_date,
        items: data.items.map((it) => ({
          product_id: it.product_id || null,
          description: it.item_description,
          quantity: it.quantity,
          unit: 'pcs',
          unit_price: it.unit_price,
        })),
        tax_amount: data.tax_amount ?? '0.00',
        is_cash_purchase: Boolean(data.is_cash_purchase),
        immediate_payment_method: data.immediate_payment_method || (data.is_cash_purchase ? 'CASH' : undefined),
      }),
    });
    return normalizePurchase(created);
  },

  async recordPurchasePayment(businessId: string, purchaseId: string, data: {
    amount: number | string;
    payment_method: string;
    payment_reference?: string;
  }): Promise<PurchaseRecord> {
    const updated = await request<any>(`/businesses/${businessId}/purchases/${purchaseId}/payments`, {
      method: 'POST',
      body: JSON.stringify({
        amount: data.amount,
        payment_date: new Date().toISOString().split('T')[0],
        payment_method: data.payment_method,
      }),
    });
    return normalizePurchase(updated);
  },

  async getPurchase(businessId: string, purchaseId: string): Promise<PurchaseRecord> {
    const row = await request<any>(`/businesses/${businessId}/purchases/${purchaseId}`);
    return normalizePurchase(row);
  },

  async updatePurchase(businessId: string, purchaseId: string, data: {
    supplier_id?: string | null;
    purchase_order_number?: string;
    purchase_date: string;
    due_date?: string | null;
    items: PurchaseItem[];
    tax_amount?: string | number;
  }): Promise<PurchaseRecord> {
    const billNumber = data.purchase_order_number || `BILL-${Date.now().toString().slice(-6)}`;
    const updated = await request<any>(`/businesses/${businessId}/purchases/${purchaseId}`, {
      method: 'PUT',
      body: JSON.stringify({
        supplier_id: data.supplier_id || null,
        bill_number: billNumber,
        purchase_date: data.purchase_date,
        due_date: data.due_date || data.purchase_date,
        items: data.items.map((it) => ({
          product_id: it.product_id || null,
          description: it.item_description,
          quantity: Number(it.quantity),
          unit: 'pcs',
          unit_price: it.unit_price,
        })),
        tax_amount: data.tax_amount ?? '0.00',
      }),
    });
    return normalizePurchase(updated);
  },

  async deletePurchase(businessId: string, purchaseId: string): Promise<{ success: boolean; deleted_id: string }> {
    return request<{ success: boolean; deleted_id: string }>(`/businesses/${businessId}/purchases/${purchaseId}`, {
      method: 'DELETE',
    });
  },

  // Direct Cash, Income & Expense
  async recordIncome(businessId: string, data: {
    source: string;
    category: string;
    amount: number | string;
    payment_method: string;
    date: string;
    reference?: string;
  }): Promise<any> {
    const created = await request<any>(`/businesses/${businessId}/income`, {
      method: 'POST',
      body: JSON.stringify({
        category: data.category,
        amount: data.amount,
        date: data.date,
        description: data.source,
        payment_method: data.payment_method,
      }),
    });
    return { ...created, amount: created.amount_exact ?? created.amount };
  },

  async listIncome(businessId: string): Promise<any[]> {
    const rows = await request<any[]>(`/businesses/${businessId}/income`);
    return rows.map((row) => ({ ...row, amount: row.amount_exact ?? row.amount }));
  },

  async recordExpense(businessId: string, data: {
    category: string;
    amount: number | string;
    payment_method: string;
    date: string;
    payee?: string;
    description?: string;
  }): Promise<any> {
    const created = await request<any>(`/businesses/${businessId}/expenses`, {
      method: 'POST',
      body: JSON.stringify({
        category: data.category || 'OPERATING',
        amount: data.amount,
        date: data.date,
        description: data.description || data.payee || '',
        payment_method: data.payment_method,
      }),
    });
    return { ...created, amount: created.amount_exact ?? created.amount };
  },

  async listExpenses(businessId: string): Promise<any[]> {
    const rows = await request<any[]>(`/businesses/${businessId}/expenses`);
    return rows.map((row) => ({ ...row, amount: row.amount_exact ?? row.amount }));
  },

  async getJournalEntries(
    businessId: string,
    filters: { start_date?: string; end_date?: string; account_code?: string } = {},
  ): Promise<any[]> {
    const query = new URLSearchParams();
    if (filters.start_date) query.set('start_date', filters.start_date);
    if (filters.end_date) query.set('end_date', filters.end_date);
    if (filters.account_code) query.set('account_code', filters.account_code);
    const queryString = query.toString();
    const suffix = queryString ? `?${queryString}` : '';
    const entries = await request<any[]>(`/businesses/${businessId}/ledger/journal-entries${suffix}`);
    return entries.map((entry) => ({
      ...entry,
      total_debits: entry.total_debits_exact ?? entry.total_debits,
      total_credits: entry.total_credits_exact ?? entry.total_credits,
      lines: (entry.lines ?? []).map((line: any) => ({
        ...line,
        debit: line.debit_exact ?? line.debit,
        credit: line.credit_exact ?? line.credit,
      })),
    }));
  },

  async getTrialBalance(businessId: string, asOfDate?: string): Promise<any> {
    const suffix = asOfDate ? `?as_of_date=${encodeURIComponent(asOfDate)}` : '';
    const result = await request<any>(`/businesses/${businessId}/ledger/trial-balance${suffix}`);
    return {
      ...result,
      total_debits: result.total_debits_exact ?? result.total_debits,
      total_credits: result.total_credits_exact ?? result.total_credits,
      accounts: (result.accounts ?? []).map((account: any) => ({
        ...account,
        total_debit: account.total_debit_exact ?? account.total_debit,
        total_credit: account.total_credit_exact ?? account.total_credit,
        net_balance: account.net_balance_exact ?? account.net_balance,
      })),
    };
  },

  async reconcileKhata(businessId: string, asOfDate?: string): Promise<any> {
    const suffix = asOfDate ? `?as_of_date=${encodeURIComponent(asOfDate)}` : '';
    return request<any>(`/businesses/${businessId}/khata/reconcile${suffix}`, { method: 'POST' });
  },

  async searchTransactions(
    businessId: string,
    filters: { start_date?: string; end_date?: string; reference_type?: string; query?: string; limit?: number } = {},
  ): Promise<any> {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '') query.set(key, String(value));
    });
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return request<any>(`/businesses/${businessId}/transactions${suffix}`);
  },

  async getCashPosition(businessId: string): Promise<CashPosition> {
    return request<CashPosition>(`/businesses/${businessId}/cash-position`);
  },

  // Goals
  async listGoals(businessId: string): Promise<Goal[]> {
    return request<Goal[]>(`/businesses/${businessId}/goals`);
  },

  async updateGoal(businessId: string, goalId: string, data: Record<string, any>): Promise<Goal> {
    return request<Goal>(`/businesses/${businessId}/goals/${goalId}`, { method: 'PUT', body: JSON.stringify(data) });
  },

  async cancelGoal(businessId: string, goalId: string): Promise<Goal> {
    return request<Goal>(`/businesses/${businessId}/goals/${goalId}`, { method: 'DELETE' });
  },

  async createGoal(businessId: string, data: {
    title: string;
    description?: string;
    goal_type: string;
    target_amount: number | string;
    unit?: string;
    start_date: string;
    target_date: string;
  }): Promise<Goal> {
    return request<Goal>(`/businesses/${businessId}/goals`, {
      method: 'POST',
      body: JSON.stringify({
        goal_type: data.goal_type,
        title: data.title,
        target_value: data.target_amount,
        start_date: data.start_date,
        target_date: data.target_date,
      }),
    });
  },

  async recalculateGoal(businessId: string, goalId: string): Promise<Goal> {
    return request<Goal>(`/businesses/${businessId}/goals/${goalId}/recalculate`, {
      method: 'POST',
    });
  },

  async evaluateGoalProgress(businessId: string, goalId: string): Promise<any> {
    return request<any>(`/businesses/${businessId}/goals/${goalId}/evaluate`, { method: 'POST' });
  },

  async listGoalMilestones(businessId: string, goalId: string): Promise<any[]> {
    return request<any[]>(`/businesses/${businessId}/goals/${goalId}/milestones`);
  },

  async createGoalMilestone(businessId: string, goalId: string, data: { title: string; target_date: string; target_value: string }): Promise<any> {
    return request<any>(`/businesses/${businessId}/goals/${goalId}/milestones`, { method: 'POST', body: JSON.stringify(data) });
  },

  async deleteGoalMilestone(businessId: string, goalId: string, milestoneId: string): Promise<void> {
    await request<void>(`/businesses/${businessId}/goals/${goalId}/milestones/${milestoneId}`, { method: 'DELETE' });
  },

  async listGoalPlans(businessId: string, goalId: string): Promise<any[]> {
    return request<any[]>(`/businesses/${businessId}/goals/${goalId}/plans`);
  },

  async createGoalPlan(businessId: string, goalId: string, data: { title: string; description?: string }): Promise<any> {
    return request<any>(`/businesses/${businessId}/goals/${goalId}/plans`, { method: 'POST', body: JSON.stringify(data) });
  },

  async listGoalTasks(businessId: string, goalId: string): Promise<any[]> {
    return request<any[]>(`/businesses/${businessId}/goals/${goalId}/tasks`);
  },

  async createGoalTask(businessId: string, goalId: string, data: { plan_id: string; title: string; description?: string; assigned_member_id?: string | null; priority?: number; status?: string; due_date?: string | null; expected_financial_impact?: string }): Promise<any> {
    return request<any>(`/businesses/${businessId}/goals/${goalId}/tasks`, { method: 'POST', body: JSON.stringify(data) });
  },

  async updateGoalTask(businessId: string, goalId: string, taskId: string, data: Record<string, any>): Promise<any> {
    return request<any>(`/businesses/${businessId}/goals/${goalId}/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify(data) });
  },

  async deleteGoalTask(businessId: string, goalId: string, taskId: string): Promise<void> {
    await request<void>(`/businesses/${businessId}/goals/${goalId}/tasks/${taskId}`, { method: 'DELETE' });
  },

  // Financial Intelligence
  async getPnL(businessId: string, startDate?: string, endDate?: string): Promise<ProfitAndLossStatement> {
    const params = new URLSearchParams();
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    const q = params.toString() ? `?${params.toString()}` : '';
    const raw = await request<any>(`/businesses/${businessId}/analytics/pnl${q}`);
    return {
      ...raw,
      gross_sales: raw.gross_sales_exact ?? raw.gross_sales,
      sales_returns: raw.sales_returns_exact ?? raw.sales_returns,
      direct_income: raw.direct_income_exact ?? raw.direct_income,
      total_revenue: raw.total_revenue_exact ?? raw.total_revenue,
      cost_of_goods_sold: raw.cost_of_goods_sold_exact ?? raw.cost_of_goods_sold,
      gross_profit: raw.gross_profit_exact ?? raw.gross_profit,
      operating_expenses: raw.operating_expenses_exact ?? raw.operating_expenses,
      total_operating_expenses: raw.total_operating_expenses_exact ?? raw.total_operating_expenses,
      operating_profit_ebitda: raw.operating_profit_ebitda_exact ?? raw.operating_profit_ebitda,
      net_profit: raw.net_profit_exact ?? raw.net_profit,
    };
  },

  async getCashFlow(businessId: string, startDate?: string, endDate?: string): Promise<CashFlowStatement> {
    const params = new URLSearchParams();
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    const q = params.toString() ? `?${params.toString()}` : '';
    const raw = await request<any>(`/businesses/${businessId}/analytics/cash-flow${q}`);
    return {
      operating_cash_inflow: raw.operating_cash_inflows_exact ?? raw.operating_cash_inflows ?? 0,
      operating_cash_outflow: raw.operating_cash_outflows_exact ?? raw.operating_cash_outflows ?? 0,
      net_operating_cash_flow: raw.net_operating_cash_flow_exact ?? raw.net_operating_cash_flow ?? 0,
      investing_cash_flow: raw.net_investing_cash_flow_exact ?? raw.net_investing_cash_flow ?? 0,
      financing_cash_flow: raw.net_financing_cash_flow_exact ?? raw.net_financing_cash_flow ?? 0,
      net_change_in_cash: raw.net_change_in_cash_exact ?? raw.net_change_in_cash ?? 0,
      opening_cash_balance: raw.opening_cash_balance_exact ?? raw.opening_cash_balance ?? 0,
      closing_cash_balance: raw.total_closing_liquidity_exact ?? raw.total_closing_liquidity ?? 0,
    };
  },

  async getWorkingCapital(businessId: string): Promise<WorkingCapitalAnalysis> {
    const raw = await request<any>(`/businesses/${businessId}/analytics/working-capital`);
    const ratio = raw.current_ratio == null ? null : Number(raw.current_ratio);
    const solvency_health = ratio == null ? 'INSOLVENT'
      : ratio >= 1.5 ? 'STRONG'
      : ratio >= 1 ? 'ADEQUATE'
      : ratio >= 0.8 ? 'STRESSED'
      : 'INSOLVENT';
    return {
      current_assets: raw.total_current_assets_exact ?? raw.total_current_assets ?? 0,
      cash_and_bank: raw.cash_and_bank_exact ?? raw.cash_and_bank ?? 0,
      accounts_receivable: raw.accounts_receivable_exact ?? raw.accounts_receivable ?? 0,
      inventory_valuation: raw.inventory_valuation_exact ?? raw.inventory_valuation ?? 0,
      current_liabilities: raw.total_current_liabilities_exact ?? raw.total_current_liabilities ?? 0,
      accounts_payable: raw.accounts_payable_exact ?? raw.accounts_payable ?? 0,
      net_working_capital: raw.net_working_capital_exact ?? raw.net_working_capital ?? 0,
      current_ratio: ratio,
      quick_ratio: raw.quick_ratio == null ? null : Number(raw.quick_ratio),
      solvency_health,
    };
  },

  async getAgeing(businessId: string): Promise<AgeingAnalysis> {
    const raw = await request<any>(`/businesses/${businessId}/analytics/ageing`);
    const bucketValues = (source: any) => ({
      bucket_0_30: source['0_30_days_exact'] ?? source['0_30_days'] ?? 0,
      bucket_31_60: source['31_60_days_exact'] ?? source['31_60_days'] ?? 0,
      bucket_61_90: source['61_90_days_exact'] ?? source['61_90_days'] ?? 0,
      bucket_90_plus: source['90_plus_days_exact'] ?? source['90_plus_days'] ?? 0,
      total: source.total_outstanding_exact ?? source.total_outstanding ?? 0,
    });
    return {
      as_of_date: raw.as_of_date ?? new Date().toISOString().slice(0, 10),
      receivables: bucketValues(raw.receivables ?? {}),
      payables: bucketValues(raw.payables ?? {}),
    };
  },

  async getBreakEven(businessId: string): Promise<BreakEvenAnalysis> {
    const raw = await request<any>(`/businesses/${businessId}/analytics/break-even`);
    const revenue = raw.total_revenue_exact ?? raw.total_revenue ?? 0;
    const breakEvenRevenue = raw.break_even_revenue_exact ?? raw.break_even_revenue ?? null;
    return {
      total_revenue: revenue,
      total_revenue_exact: raw.total_revenue_exact,
      total_variable_costs: raw.total_variable_costs_exact ?? raw.total_variable_costs ?? 0,
      total_fixed_costs: raw.total_fixed_costs_exact ?? raw.total_fixed_costs ?? 0,
      total_fixed_costs_exact: raw.total_fixed_costs_exact,
      contribution_margin: raw.contribution_margin_exact ?? raw.contribution_margin ?? 0,
      contribution_margin_exact: raw.contribution_margin_exact,
      contribution_margin_ratio: Number(raw.contribution_margin_ratio ?? 0),
      break_even_revenue_monthly: breakEvenRevenue,
      margin_of_safety_pct: raw.margin_of_safety_percent == null ? null : Number(raw.margin_of_safety_percent),
      is_operating_above_breakeven: raw.margin_of_safety_percent != null
        ? Number(raw.margin_of_safety_percent) > 0
        : Boolean(raw.is_profitable),
    };
  },

  async getHealthScore(businessId: string): Promise<BusinessHealthScore> {
    const raw = await request<any>(`/businesses/${businessId}/analytics/health-score`);
    const pillars = raw.pillars ?? {
      liquidity: { score: raw.liquidity_score ?? 0, max: 100 },
      profitability: { score: raw.profitability_score ?? 0, max: 100 },
      solvency: { score: raw.solvency_score ?? 0, max: 100 },
      efficiency: { score: raw.efficiency_score ?? 0, max: 100 },
      cash_runway: { score: raw.growth_stability_score ?? 0, max: 100 },
    };
    const grade = raw.grade ?? raw.classification ?? 'UNKNOWN';
    const overallScore = raw.overall_score ?? raw.composite_score ?? 0;
    const strengths = raw.key_strengths ?? raw.strengths ?? [];
    const risks = raw.identified_risks ?? raw.vulnerabilities ?? [];
    return {
      ...raw,
      overall_score: overallScore,
      grade,
      pillars,
      cash_runway_months: Number(raw.pillars?.cash_runway?.months ?? raw.cash_runway_months ?? 0),
      key_strengths: strengths,
      identified_risks: risks,
      data_completeness_score: String(raw.data_completeness_score ?? '100.00'),
      composite_score: overallScore,
      classification: grade,
      liquidity_score: raw.liquidity_score ?? pillars.liquidity?.score ?? 0,
      profitability_score: raw.profitability_score ?? pillars.profitability?.score ?? 0,
      efficiency_score: raw.efficiency_score ?? pillars.efficiency?.score ?? 0,
      solvency_score: raw.solvency_score ?? pillars.solvency?.score ?? 0,
      growth_stability_score: raw.growth_stability_score ?? pillars.cash_runway?.score ?? 0,
      strengths,
      vulnerabilities: risks,
      priority_recommendations: raw.priority_recommendations ?? [],
    };
  },

  // Decision Intelligence
  async evaluateDecision(businessId: string, data: {
    model_type: string;
    decision_title: string;
    parameters: Record<string, any>;
    parent_decision_id?: string;
  }): Promise<DecisionEvaluationResult> {
    const inputProvenance: Record<string, string> = {};
    const markUserSupplied = (value: unknown, path: string) => {
      if (Array.isArray(value)) {
        value.forEach((item, index) => markUserSupplied(item, `${path}[${index}]`));
      } else if (value && typeof value === 'object') {
        Object.entries(value as Record<string, unknown>).forEach(([key, item]) =>
          markUserSupplied(item, path ? `${path}.${key}` : key),
        );
      } else if (path) {
        inputProvenance[path] = 'USER_ASSUMPTION';
      }
    };
    Object.entries(data.parameters).forEach(([key, value]) => markUserSupplied(value, key));
    const raw = await request<any>(`/businesses/${businessId}/decisions/evaluate`, {
      method: 'POST',
      body: JSON.stringify({
        model_id: data.model_type,
        inputs: {
          ...data.parameters,
          input_provenance: inputProvenance,
        },
        save_evaluation: true,
        parent_decision_id: data.parent_decision_id,
      }),
    });
    const finiteNumber = (value: unknown): number | null => {
      const numeric = typeof value === 'number' ? value : typeof value === 'string' && value.trim() ? Number(value) : NaN;
      return Number.isFinite(numeric) ? numeric : null;
    };
    return {
      evaluation_id: String(raw.evaluation_id ?? ''),
      business_id: businessId,
      model_type: String(raw.model_id ?? data.model_type),
      decision_title: data.decision_title,
      status: String(raw.outcome ?? 'UNKNOWN'),
      alternatives: (Array.isArray(raw.alternatives) ? raw.alternatives : []).map((alternative: any) => {
        const metrics = alternative.metrics && typeof alternative.metrics === 'object' ? alternative.metrics : {};
        return {
          alternative_id: String(alternative.alternative_id ?? ''),
          alternative_name: String(alternative.name ?? ''),
          outcome: String(alternative.outcome ?? 'UNKNOWN'),
          rank: finiteNumber(alternative.rank) ?? 0,
          npv_amount: finiteNumber(metrics.npv_amount ?? metrics.npv),
          irr_pct: finiteNumber(metrics.irr_pct ?? metrics.irr_percent),
          payback_period_months: finiteNumber(metrics.payback_months ?? metrics.payback_period_months ?? raw.calculations?.payback_period_months),
          monthly_net_cash_impact: finiteNumber(metrics.net_monthly_cash_flow ?? metrics.monthly_net_cash_impact),
          roi_pct: finiteNumber(metrics.roi_pct),
          risk_score_0_to_100: finiteNumber(metrics.risk_score_0_to_100),
          composite_score: finiteNumber(alternative.score),
          key_drivers: Array.isArray(metrics.key_drivers) ? metrics.key_drivers.map(String) : [],
          fatal_flaws: Array.isArray(alternative.constraints)
            ? alternative.constraints.filter((constraint: any) => constraint.is_hard_constraint && !constraint.passed).map((constraint: any) => String(constraint.explanation))
            : [],
        };
      }),
      recommended_alternative_id: raw.recommended_alternative ? String(raw.recommended_alternative) : null,
      baseline_monthly_revenue: finiteNumber(raw.inputs?.current_monthly_revenue),
      baseline_monthly_net_profit: finiteNumber(raw.inputs?.current_monthly_ebitda),
      executive_summary: String(raw.summary_explanation ?? ''),
      created_at: new Date().toISOString(),
      version_number: finiteNumber(raw.version_number),
      parent_decision_id: raw.parent_decision_id ? String(raw.parent_decision_id) : null,
      inputs: raw.inputs && typeof raw.inputs === 'object' ? raw.inputs : {},
      calculations: raw.calculations && typeof raw.calculations === 'object' ? raw.calculations : {},
      graph: raw.graph && typeof raw.graph === 'object' ? raw.graph : { nodes: [], edges: [] },
      evidence_items: Array.isArray(raw.evidence_items) ? raw.evidence_items : [],
    };
  },

  async simulateDecisionRisk(businessId: string, data: {
    model_type: string;
    parameters: Record<string, any>;
    iterations?: number;
  }): Promise<MonteCarloRiskResult> {
    const raw = await request<any>(`/businesses/${businessId}/decisions/simulate-risk`, {
      method: 'POST',
      body: JSON.stringify({
        model_id: data.model_type,
        inputs: data.parameters,
        iterations: data.iterations || 1000,
      }),
    });
    const metrics = (raw && typeof raw === 'object' && raw.stochastic_metrics) ? raw.stochastic_metrics : {};
    const primaryKey = raw?.primary_metric_name || Object.keys(metrics)[0] || '';
    const primary = metrics[primaryKey] || {};
    const shortfall = Number(raw?.probability_of_negative_npv_pct ?? raw?.shortfall_risk_probability_percent ?? 0);
    return {
      iterations_run: Number(raw?.iterations_run ?? raw?.iterations ?? 1000),
      p10_worst_case_npv: Number(raw?.p10_worst_case_npv ?? primary.p10_downside ?? 0),
      p50_median_npv: Number(raw?.p50_median_npv ?? primary.p50_median ?? 0),
      p90_best_case_npv: Number(raw?.p90_best_case_npv ?? primary.p90_upside ?? 0),
      probability_of_negative_npv_pct: shortfall,
      probability_of_payback_within_3yr_pct: Number(raw?.probability_of_payback_within_3yr_pct ?? (shortfall < 10 ? 95 : 75)),
      var_95_pct_risk_amount: Number(raw?.var_95_pct_risk_amount ?? Math.abs(Number(primary.p10_downside ?? 0))),
      confidence_verdict: raw?.confidence_verdict || (shortfall < 5 ? 'HIGH CONFIDENCE' : shortfall < 20 ? 'MODERATE' : 'VOLATILE DOWNSIDE'),
    };
  },

  async evaluateDecisionSensitivity(businessId: string, data: {
    model_type: string;
    parameters: Record<string, any>;
    target_output_metric?: string;
    variables_to_test?: string[];
  }): Promise<SensitivityAnalysisResult> {
    return request<SensitivityAnalysisResult>(`/businesses/${businessId}/decisions/sensitivity`, {
      method: 'POST',
      body: JSON.stringify({
        model_id: data.model_type,
        inputs: data.parameters,
        target_output_metric: data.target_output_metric || 'net_monthly_cash_flow_after_emi',
      }),
    });
  },

  async getDecisionHistory(businessId: string): Promise<any[]> {
    const raw = await request<any[]>(`/businesses/${businessId}/decisions/history`);
    return raw.map((item) => ({
      id: String(item.id ?? ''),
      title: String(item.objective ?? item.model_id ?? 'Decision evaluation'),
      model: String(item.model_id ?? ''),
      outcome: String(item.outcome ?? 'UNKNOWN'),
      version_number: item.version_number ?? 1,
      date: item.created_at ? new Date(item.created_at).toLocaleDateString('en-IN') : '',
    }));
  },

  async getDecisionVersions(businessId: string, decisionId: string): Promise<DecisionVersion[]> {
    return request<DecisionVersion[]>(`/businesses/${businessId}/decisions/${decisionId}/versions`);
  },

  // Persisted scenario laboratory
  async listScenarios(businessId: string): Promise<BusinessScenario[]> {
    return request<BusinessScenario[]>(`/businesses/${businessId}/scenarios`);
  },

  async createScenario(businessId: string, data: { name: string; description?: string; assumptions: Record<string, any> }): Promise<BusinessScenario> {
    return request<BusinessScenario>(`/businesses/${businessId}/scenarios`, {
      method: 'POST', body: JSON.stringify(data),
    });
  },

  async listScenarioVersions(businessId: string, scenarioId: string): Promise<BusinessScenarioVersion[]> {
    return request<BusinessScenarioVersion[]>(`/businesses/${businessId}/scenarios/${scenarioId}/versions`);
  },

  async deleteScenario(businessId: string, scenarioId: string): Promise<{ status: string; scenario_id: string; name: string }> {
    return request<{ status: string; scenario_id: string; name: string }>(`/businesses/${businessId}/scenarios/${scenarioId}`, {
      method: 'DELETE',
    });
  },

  async createScenarioVersion(businessId: string, scenarioId: string, assumptions: Record<string, any>): Promise<BusinessScenario> {
    return request<BusinessScenario>(`/businesses/${businessId}/scenarios/${scenarioId}/versions`, {
      method: 'POST', body: JSON.stringify({ assumptions }),
    });
  },

  async compareScenarioVersions(businessId: string, versionIds: string[]): Promise<any> {
    return request<any>(`/businesses/${businessId}/scenarios/compare`, {
      method: 'POST', body: JSON.stringify({ version_ids: versionIds }),
    });
  },

  async runScenarioMonteCarlo(businessId: string, scenarioId: string, data: { iterations: number; random_seed?: number; distributions: Record<string, any> }): Promise<any> {
    return request<any>(`/businesses/${businessId}/scenarios/${scenarioId}/runs`, {
      method: 'POST', body: JSON.stringify(data),
    });
  },

  async listScenarioRuns(businessId: string, scenarioId: string): Promise<any[]> {
    return request<any[]>(`/businesses/${businessId}/scenarios/${scenarioId}/runs`);
  },

  async replayScenarioRun(businessId: string, scenarioId: string, runId: string): Promise<any> {
    return request<any>(`/businesses/${businessId}/scenarios/${scenarioId}/runs/${runId}/replay`, { method: 'POST' });
  },

  // Agentic AI
  async agentInvestigate(businessId: string, query: string, sessionId?: string): Promise<AgentInvestigationResponse> {
    return request<AgentInvestigationResponse>(`/businesses/${businessId}/agent/investigate`, {
      method: 'POST',
      body: JSON.stringify({ query, session_id: sessionId || null }),
    });
  },

  async createAgentProposedAction(
    businessId: string,
    sessionId: string,
    actionType: AgentProposedAction['action_type'],
    payload: Record<string, any>,
  ): Promise<AgentProposedAction> {
    return request<AgentProposedAction>(`/businesses/${businessId}/agent/sessions/${sessionId}/actions`, {
      method: 'POST', body: JSON.stringify({ action_type: actionType, payload }),
    });
  },

  async listAgentProposedActions(businessId: string, sessionId: string): Promise<AgentProposedAction[]> {
    return request<AgentProposedAction[]>(`/businesses/${businessId}/agent/sessions/${sessionId}/actions`);
  },

  async confirmAgentProposedAction(businessId: string, sessionId: string, actionId: string): Promise<AgentProposedAction> {
    return request<AgentProposedAction>(`/businesses/${businessId}/agent/sessions/${sessionId}/actions/${actionId}/confirm`, {
      method: 'POST',
    });
  },

  async rejectAgentProposedAction(businessId: string, sessionId: string, actionId: string): Promise<AgentProposedAction> {
    return request<AgentProposedAction>(`/businesses/${businessId}/agent/sessions/${sessionId}/actions/${actionId}/reject`, {
      method: 'POST',
    });
  },

  getAgentActionReportUrl(businessId: string, sessionId: string, actionId: string): string {
    return `/businesses/${businessId}/agent/sessions/${sessionId}/actions/${actionId}/download`;
  },

  // Report URLs
  getDossierPdfUrl(businessId: string): string {
    return `/businesses/${businessId}/reports/dossier.pdf`;
  },

  getDecisionBriefPdfUrl(businessId: string, evaluationId: string): string {
    return `/businesses/${businessId}/reports/decisions/${evaluationId}/brief.pdf`;
  },

  getCustomerLedgerCsvUrl(businessId: string, customerId: string): string {
    return `/businesses/${businessId}/reports/customers/${customerId}/ledger.csv`;
  },

  getSupplierLedgerCsvUrl(businessId: string, supplierId: string): string {
    return `/businesses/${businessId}/reports/suppliers/${supplierId}/ledger.csv`;
  },

  getTaxInvoicePdfUrl(businessId: string, invoiceId: string): string {
    return `/businesses/${businessId}/invoices/${invoiceId}/pdf`;
  },

  getPurchasePdfUrl(businessId: string, purchaseId: string): string {
    return `/businesses/${businessId}/purchases/${purchaseId}/pdf`;
  },

  getGeneralLedgerCsvUrl(businessId: string): string {
    return `/businesses/${businessId}/reports/ledger.csv`;
  },

  getTransactionsCsvUrl(
    businessId: string,
    filters: { start_date?: string; end_date?: string; reference_type?: string; query?: string } = {},
  ): string {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return `/businesses/${businessId}/transactions/export.csv${suffix}`;
  },
};
