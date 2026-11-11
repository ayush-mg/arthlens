/**
 * ArthLens API Client for Geospatial Atlas, Indicators, and Epistemic Ledger (P2-4).
 * Handles authenticated API calls against backend epistemic endpoints.
 * Strictly avoids hardcoding or synthesizing demonstration economic numbers.
 */

import {
  GeoUnitDetail,
  GeoUnitSummary,
  IndicatorItem,
  IndicatorQuality,
  LedgerQuantityDetail,
  EvidenceGraphData,
} from './types';

const getApiBaseUrl = (): string => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined') {
    return '';
  }
  return (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
};

const API_BASE_URL = getApiBaseUrl();

function buildUrl(path: string): URL {
  const base = API_BASE_URL || (typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:8000');
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return new URL(`${base}${normalizedPath}`);
}

export interface UserProfile {
  id: string;
  email: string;
  roles: string[];
  full_name?: string;
}

/**
 * Authoritative Typed Error Hierarchy for Epistemic API Communications.
 * Distinguishes authentication, authorization, missing entities, and network states.
 * Prohibits masking failures with synthetic mock entities.
 */
export class ApiError extends Error {
  constructor(public status: number, message: string, public code?: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export class AuthenticationError extends ApiError {
  constructor(message = 'Authentication required. Session is invalid or absent.') {
    super(401, message, 'UNAUTHORIZED');
    this.name = 'AuthenticationError';
  }
}

export const AuthenticationRequiredError = AuthenticationError;
export type AuthenticationRequiredError = AuthenticationError;

export class ForbiddenError extends ApiError {
  constructor(message = 'Access forbidden. Insufficient RBAC privileges.') {
    super(403, message, 'FORBIDDEN');
    this.name = 'ForbiddenError';
  }
}

export class NotFoundError extends ApiError {
  constructor(message = 'The requested geographic or epistemic entity was not found.') {
    super(404, message, 'NOT_FOUND');
    this.name = 'NotFoundError';
  }
}

export class NetworkError extends ApiError {
  constructor(message = 'Network connection failed. Epistemic backend is unreachable.') {
    super(0, message, 'NETWORK_ERROR');
    this.name = 'NetworkError';
  }
}

// In-memory token carrier for programmatic CLI/SSR/testing sessions
let inMemoryToken: string | null = null;

/**
 * Security Gate: Dev auto-auth and test credentials are strictly disabled in production.
 */
export function isDevAutoAuthEnabled(): boolean {
  if (process.env.NODE_ENV === 'production') {
    return false;
  }
  return true;
}

/**
 * Sets the active in-memory token.
 * Note: Session persistence in browsers strictly relies on Secure HTTP-only cookies
 * in compliance with Handbook Part 10.1 (no JWT tokens stored in localStorage).
 */
export function setAuthToken(token: string | null) {
  inMemoryToken = token;
}

export function getAuthToken(): string | null {
  return inMemoryToken;
}

export function getAuthHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function loginUser(email: string, password: string): Promise<UserProfile> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Authentication failed');
  }
  const data = await res.json();
  if (data.access_token) {
    setAuthToken(data.access_token);
  }
  return {
    id: data.id,
    email: data.email,
    roles: data.roles || [],
    full_name: data.full_name,
  };
}

export async function registerUser(
  fullName: string,
  email: string,
  password: string,
): Promise<UserProfile> {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      full_name: fullName,
      email: email,
      password: password,
    }),
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Registration failed');
  }
  const data = await res.json();
  if (data.access_token) {
    setAuthToken(data.access_token);
  }
  return {
    id: data.id,
    email: data.email,
    roles: data.roles || ['ENTREPRENEUR'],
    full_name: data.full_name,
  };
}

export async function requestPasswordReset(
  email: string,
): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE_URL}/auth/password-reset/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  return await res.json();
}

export async function confirmPasswordReset(
  token: string,
  newPassword: string,
): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE_URL}/auth/password-reset/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Password reset failed');
  }
  return await res.json();
}

export async function logoutUser(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } catch (err) {
    console.warn('Logout notice:', err);
  } finally {
    setAuthToken(null);
  }
}

export async function getCurrentUser(): Promise<UserProfile | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('getCurrentUser notice:', err);
  }
  return null;
}

export interface AdminUserRecord {
  id: string;
  email: string;
  quota_counters: Record<string, any>;
  roles: string[];
  created_at?: string | null;
}

export async function fetchAdminUsers(): Promise<AdminUserRecord[]> {
  const res = await fetch(`${API_BASE_URL}/admin/users`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  if (res.status === 401) throw new AuthenticationError();
  if (res.status === 403) throw new ForbiddenError('Administrator access required.');
  if (!res.ok) throw new ApiError(res.status, 'Failed to fetch user directory.');
  return await res.json();
}

export async function updateUserRole(userId: string, role: string): Promise<{ status: string; roles: string[] }> {
  const res = await fetch(`${API_BASE_URL}/admin/users/${encodeURIComponent(userId)}/role`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    credentials: 'include',
    body: JSON.stringify({ role }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || 'Failed to update user role.');
  }
  return await res.json();
}

export async function deactivateUserAccount(userId: string): Promise<{ status: string; is_active: boolean }> {
  const res = await fetch(`${API_BASE_URL}/admin/users/${encodeURIComponent(userId)}/deactivate`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || 'Failed to deactivate account.');
  }
  return await res.json();
}

export async function activateUserAccount(userId: string): Promise<{ status: string; is_active: boolean }> {
  const res = await fetch(`${API_BASE_URL}/admin/users/${encodeURIComponent(userId)}/activate`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || 'Failed to activate account.');
  }
  return await res.json();
}

/**
 * Fetch verified pilot boundary GeoJSON FeatureCollection (Prayagraj).
 * Kept for backward compatibility.
 */
export async function fetchPilotBoundaries(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/geo/pilot-boundaries`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  if (!res.ok) {
    if (res.status === 401 || res.status === 403) {
      throw new Error(`Authentication required to access boundary vectors (${res.status})`);
    }
    if (res.status === 404) {
      throw new Error('Pilot boundary not available in official registry (404)');
    }
    throw new Error(`Failed to fetch pilot boundaries: HTTP ${res.status}`);
  }
  return await res.json();
}

/**
 * Fetch genuine boundary GeoJSON FeatureCollection for a specific geographic unit.
 * Returns FeatureCollection with genuine geometry if persisted in PostGIS,
 * or FeatureCollection with 0 features and metadata if geometry is unavailable.
 * Strictly throws ApiError on 401/403/404/500 errors.
 */
export async function fetchUnitBoundary(geoId: string, indicator?: string): Promise<any> {
  const url = buildUrl(`/geo/${encodeURIComponent(geoId)}/boundary`);
  if (indicator) {
    url.searchParams.set('indicator', indicator);
  }
  const res = await fetch(url.toString(), {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  if (!res.ok) {
    if (res.status === 401 || res.status === 403) {
      throw new AuthenticationRequiredError(`Authentication required to access boundary vectors (${res.status})`);
    }
    if (res.status === 404) {
      throw new NotFoundError(`GeoUnit '${geoId}' boundary not found (404)`);
    }
    throw new ApiError(res.status, `Failed to fetch boundary for '${geoId}': HTTP ${res.status}`);
  }
  return await res.json();
}

/**
 * List or search geographic units in national hierarchy.
 * Returns genuine records from PostgreSQL backend.
 * Fails closed with typed errors; never manufactures mock seed records.
 */
export async function fetchGeoUnits(params?: {
  level?: number;
  parent_id?: string;
  search?: string;
}): Promise<GeoUnitSummary[]> {
  const url = buildUrl('/geo/units');
  if (params?.level !== undefined) url.searchParams.set('level', String(params.level));
  if (params?.parent_id) url.searchParams.set('parent_id', params.parent_id);
  if (params?.search) url.searchParams.set('search', params.search);

  let res: Response;
  try {
    res = await fetch(url.toString(), {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to reach geographic registry: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to access national geographic hierarchy.');
  }
  if (res.status === 403) {
    throw new ForbiddenError('Insufficient privileges to query geographic units.');
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Geographic registry query failed (HTTP ${res.status}).`);
  }

  const data = await res.json();
  return data.units || [];
}

/**
 * Fetch detailed GeoUnit metadata and verified geometry.
 * Strictly queries authoritative backend; never synthesizes fake subunits or verification claims.
 */
export async function fetchGeoUnitDetail(geoId: string): Promise<GeoUnitDetail> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/geo/${encodeURIComponent(geoId)}`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to reach geographic registry for unit '${geoId}': ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError(`Authentication required to inspect geographic unit '${geoId}'.`);
  }
  if (res.status === 403) {
    throw new ForbiddenError(`Insufficient privileges to inspect geographic unit '${geoId}'.`);
  }
  if (res.status === 404) {
    throw new NotFoundError(`Geographic unit '${geoId}' does not exist in the authoritative baseline.`);
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Failed to fetch unit details for '${geoId}' (HTTP ${res.status}).`);
  }

  return await res.json();
}

/**
 * Fetch indicator items for a geographic unit.
 * When no persisted evidence exists in the database, returns indicators marked UNAVAILABLE.
 * Fails closed with typed errors on communication failures.
 */
export async function fetchGeoIndicators(geoId: string): Promise<IndicatorItem[]> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/geo/${encodeURIComponent(geoId)}/indicators`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to retrieve economic indicators for unit '${geoId}': ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError(`Authentication required to query economic indicators for '${geoId}'.`);
  }
  if (res.status === 403) {
    throw new ForbiddenError(`Insufficient privileges to access economic indicators for '${geoId}'.`);
  }
  if (res.status === 404) {
    throw new NotFoundError(`Geographic unit '${geoId}' not found in indicator registry.`);
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Failed to fetch indicators for '${geoId}' (HTTP ${res.status}).`);
  }

  const data = await res.json();
  return data.indicators || [];
}

/**
 * Fetch full quantity ledger record for Provenance Drawer.
 * Mandatory Invariant: Every displayed number opens its ledger record.
 */
export async function fetchLedgerQuantity(quantityId: string): Promise<LedgerQuantityDetail> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/ledger/${encodeURIComponent(quantityId)}`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to reach epistemic ledger: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError(`Authentication required to inspect ledger record '${quantityId}'.`);
  }
  if (res.status === 403) {
    throw new ForbiddenError(`Insufficient privileges to inspect ledger record '${quantityId}'.`);
  }
  if (res.status === 404) {
    throw new NotFoundError(`Quantity record '${quantityId}' not found in epistemic ledger.`);
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Ledger query for '${quantityId}' failed (HTTP ${res.status}).`);
  }

  return await res.json();
}

/**
 * Fetch Cytoscape.js Evidence Graph DAG for a quantity.
 */
export async function fetchEvidenceGraph(quantityId: string): Promise<EvidenceGraphData> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/ledger/${encodeURIComponent(quantityId)}/graph`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to reach evidence graph service: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError(`Authentication required to explore evidence graph for '${quantityId}'.`);
  }
  if (res.status === 403) {
    throw new ForbiddenError(`Insufficient privileges to explore evidence graph for '${quantityId}'.`);
  }
  if (res.status === 404) {
    throw new NotFoundError(`Evidence graph for quantity '${quantityId}' not found.`);
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Evidence graph query failed (HTTP ${res.status}).`);
  }

  return await res.json();
}

export interface PolicyRuleRecord {
  id: string;
  scheme_id: string;
  rule_id?: string;
  expression?: any;
  rule_ast?: any;
  version?: string | number;
  status?: string;
  created_at?: string;
  source_document_id?: string;
  effective_from?: string;
  effective_to?: string;
}

export interface ScenarioRecord {
  id: string;
  name: string;
  owner_id: string;
  scenario: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface ScenarioComparisonResult {
  id: string;
  status: 'COMPLETED' | 'PARTIAL' | 'INSUFFICIENT_DATA';
  left_scenario_id: string;
  right_scenario_id: string;
  metrics: Record<string, {
    status: string;
    unit: string;
    left: { value: number; quantity_id: string; scenario_name: string };
    right: { value: number; quantity_id: string; scenario_name: string };
    delta_right_minus_left: { value: number; quantity_id: string };
  }>;
  unavailable_metrics: Record<string, string>;
  created_at?: string | null;
}

/**
 * Fetch statutory policy rules from backend (/policy/rules).
 */
export async function fetchPolicyRules(schemeId?: string): Promise<PolicyRuleRecord[]> {
  const url = schemeId
    ? `${API_BASE_URL}/policy/rules?scheme_id=${encodeURIComponent(schemeId)}`
    : `${API_BASE_URL}/policy/rules`;

  let res: Response;
  try {
    res = await fetch(url, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to reach policy registry: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to inspect statutory policy rules.');
  }
  if (res.status === 403) {
    throw new ForbiddenError('Insufficient privileges to inspect statutory policy rules.');
  }
  if (!res.ok) {
    throw new ApiError(res.status, `Policy rule fetch failed (HTTP ${res.status}).`);
  }

  return await res.json();
}

/**
 * Fetch current user's scenarios (/scenarios).
 */
export async function fetchMyScenarios(): Promise<ScenarioRecord[]> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/scenarios`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to fetch scenarios: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to view scenarios.');
  }
  if (!res.ok) {
    throw new ApiError(res.status, `Failed to load scenarios (HTTP ${res.status}).`);
  }

  const data = await res.json();
  return Array.isArray(data) ? data : data.scenarios || [];
}

/**
 * Fetch a single scenario by ID (/scenarios/{id}).
 */
export async function getScenario(scenarioId: string): Promise<ScenarioRecord> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/scenarios/${encodeURIComponent(scenarioId)}`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to fetch scenario: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to inspect scenario.');
  }
  if (res.status === 404) {
    throw new NotFoundError('Scenario not found or ownership mismatch.');
  }
  if (!res.ok) {
    throw new ApiError(res.status, `Failed to load scenario (HTTP ${res.status}).`);
  }

  return await res.json();
}

/**
 * Update a scenario (/scenarios/{id}).
 */
export async function updateScenario(
  scenarioId: string,
  name?: string,
  scenarioData?: Record<string, any>
): Promise<ScenarioRecord> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/scenarios/${encodeURIComponent(scenarioId)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      credentials: 'include',
      body: JSON.stringify({ name, scenario: scenarioData }),
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to update scenario: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to update scenario.');
  }
  if (res.status === 404) {
    throw new NotFoundError('Scenario not found or ownership mismatch.');
  }
  if (!res.ok) {
    throw new ApiError(res.status, `Failed to update scenario (HTTP ${res.status}).`);
  }

  return await res.json();
}

/**
 * Delete a scenario (/scenarios/{id}).
 */
export async function deleteScenario(scenarioId: string): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/scenarios/${encodeURIComponent(scenarioId)}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to delete scenario: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to delete scenario.');
  }
  if (res.status === 404) {
    throw new NotFoundError('Scenario not found or ownership mismatch.');
  }
  if (!res.ok) {
    throw new ApiError(res.status, `Failed to delete scenario (HTTP ${res.status}).`);
  }
}

/**
 * Create a new user exploratory scenario (/scenarios).
 * Strictly Floor 1 (Uncalibrated Scenario) per Handbook Part 4.2.
 */
export async function createScenario(name: string, scenarioData: any = {}): Promise<any> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/scenarios`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      credentials: 'include',
      body: JSON.stringify({ name, scenario: scenarioData }),
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to reach scenario service: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to save user scenario.');
  }
  if (res.status === 403) {
    throw new ForbiddenError('Only ENTREPRENEUR role may author scenarios.');
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Scenario creation failed (HTTP ${res.status}).`);
  }

  return await res.json();
}

/**
 * Branch an existing user scenario (/scenarios/{id}/branch).
 */
export async function branchScenario(scenarioId: string, name: string): Promise<any> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/scenarios/${encodeURIComponent(scenarioId)}/branch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      credentials: 'include',
      body: JSON.stringify({ name }),
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to branch scenario: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to branch scenario.');
  }
  if (res.status === 404) {
    throw new NotFoundError('Scenario not found or ownership mismatch.');
  }
  if (!res.ok) {
    throw new ApiError(res.status, `Branching failed (HTTP ${res.status}).`);
  }

  return await res.json();
}

export interface ScenarioCalculationParams {
  price_per_unit?: number;
  variable_cost_per_unit?: number;
  fixed_costs_per_month?: number;
  loan_principal?: number;
  annual_interest_rate?: number;
  loan_term_months?: number;
  moratorium_months?: number;
  moratorium_interest_treatment?: 'PAID' | 'CAPITALISED';
  subsidy_amount?: number;
  subsidy_treatment?: 'ADJUSTS_PRINCIPAL' | 'BACK_ENDED_RELEASE' | 'LOCKED_DEPOSIT';
  subsidy_release_month?: number;
  target_monthly_units?: number;
  working_capital?: {
    inventory_value: number;
    accounts_receivable: number;
    accounts_payable: number;
  };
  projection?: {
    initial_quantity: number;
    monthly_growth_rate: number;
    seasonality_factors: number[];
    price_per_unit_by_month: number[];
    variable_cost_per_unit_by_month: number[];
    operating_expenses_by_month: number[];
    debt_service_by_month: number[];
    taxes_by_month: number[];
    other_payments_by_month: number[];
    subsidy_cash_release_by_month: number[];
    working_capital_need_by_month: number[];
    equity: number;
    disbursed_loan: number;
    capex: number;
    days_inventory: number;
    days_receivable: number;
    days_payable: number;
    minimum_dscr: number;
    repayment_capacity_annual_interest_rate: number;
    repayment_capacity_months: number;
  };
}

export interface ScenarioCalculationResults {
  price_per_unit: number | null;
  variable_cost_per_unit: number | null;
  fixed_costs_per_month: number | null;
  contribution_margin: number | null;
  margin_percentage: number | null;
  break_even_units: number | null;
  target_monthly_units: number | null;
  loan_principal: number | null;
  financed_principal: number | null;
  subsidy_applied: number | null;
  annual_interest_rate: number | null;
  monthly_emi: number | null;
  total_repaid: number | null;
  total_interest: number | null;
  repayment_months: number | null;
  moratorium_months: number | null;
  loan_schedule_status: 'COMPLETED' | 'INSUFFICIENT_DATA';
  loan_schedule_missing_inputs: string[];
  loan_schedule: Array<Record<string, number | string | Record<string, string>>>;
  break_even_status: 'COMPLETED' | 'NO_BREAK_EVEN' | 'INSUFFICIENT_DATA';
  working_capital_requirement: number | null;
  working_capital_status: 'COMPLETED' | 'INSUFFICIENT_DATA';
  financial_projection: {
    status: 'COMPLETED' | 'INSUFFICIENT_DATA';
    initial_cash?: number;
    total_revenue?: number;
    total_debt_service?: number;
    cash_conversion_cycle_days?: number;
    minimum_dscr?: number | null;
    dscr_status?: 'COMPLETED' | 'INSUFFICIENT_DATA';
    minimum_cash?: number;
    first_shortfall_month?: number | null;
    funding_shortfall?: number;
    repayment_capacity_monthly_debt_service?: number;
    repayment_capacity_supported_principal?: number;
    quantity_ids?: Record<string, string>;
    months?: Array<Record<string, unknown>>;
  };
  input_quantity_ids: Record<string, string>;
  quantity_ids: Record<string, string>;
  spatial_demand_allocated: number | null;
  spatial_demand_status: 'COMPLETED' | 'INSUFFICIENT_DATA';
  spatial_demand_missing_evidence: string[];
  feasibility_status: string;
  calculated_at: string;
  epistemic_floor: string;
}

export interface FinancialSimulationRequest {
  projection: {
    initial_quantity: number;
    monthly_growth_rate: number;
    seasonality_factors: number[];
    price_per_unit_by_month: number[];
    variable_cost_per_unit_by_month: number[];
    operating_expenses_by_month: number[];
    debt_service_by_month: number[];
    taxes_by_month: number[];
    other_payments_by_month: number[];
    subsidy_cash_release_by_month: number[];
    working_capital_need_by_month: number[];
    opening_working_capital_need: number;
    equity: number;
    disbursed_loan: number;
    capex: number;
    days_inventory: number;
    days_receivable: number;
    days_payable: number;
  };
  distributions: Array<{
    parameter: string;
    distribution: 'NORMAL' | 'UNIFORM' | 'TRIANGULAR';
    parameters: Record<string, number>;
  }>;
  sensitivity_parameter_values: Record<string, number[]>;
  seed: number;
  sample_count: number;
  minimum_sample_count: number;
  quantile_levels: number[];
  convergence_tolerances: Record<'total_revenue' | 'total_debt_service' | 'minimum_cash', number>;
  shortfall_probability_tolerance: number;
}

export interface FinancialSimulationMetric {
  mean: number;
  mean_quantity_id: string;
  quantiles: Record<string, { value: number; quantity_id: string }>;
  standard_error: number;
  standard_error_quantity_id: string;
  converged: boolean;
}

export interface FinancialSimulationResults {
  run_id: string;
  scenario_id: string;
  execution_id: string;
  status: 'COMPLETED';
  metadata: {
    scenario_id: string;
    model_version: string;
    seed: number;
    sample_count: number;
    data_versions: string[];
  };
  converged: boolean;
  metrics: Record<string, FinancialSimulationMetric>;
  cash_shortfall_probability: {
    value: number;
    quantity_id: string;
    standard_error: number;
    standard_error_quantity_id: string;
    converged: boolean;
  };
  sensitivity: {
    baseline_outputs: Record<string, { value: number; quantity_id: string }>;
    points: Array<{
      parameter: string;
      value: number;
      parameter_quantity_id?: string;
      outputs: Record<string, {
        value: number;
        quantity_id: string;
        delta: number;
        delta_quantity_id: string;
      }>;
    }>;
  };
  input_quantity_ids: {
    projection: Record<string, string>;
    distributions: Record<string, string>;
    sensitivity: Record<string, string[]>;
  };
}

/**
 * Execute deterministic financial calculations. Spatial allocation is returned only
 * when its traceable inputs have been supplied through the dedicated tool flow.
 */
export async function calculateScenario(
  scenarioId: string,
  params: ScenarioCalculationParams = {}
): Promise<{ scenario_id: string; name: string; calculations: ScenarioCalculationResults }> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/scenarios/${encodeURIComponent(scenarioId)}/calculate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      credentials: 'include',
      body: JSON.stringify(params),
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to reach calculation service: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to execute calculations.');
  }
  if (res.status === 404) {
    throw new NotFoundError('Scenario not found.');
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Calculation failed (HTTP ${res.status}).`);
  }

  return await res.json();
}

export async function simulateScenario(
  scenarioId: string,
  request: FinancialSimulationRequest
): Promise<FinancialSimulationResults> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/scenarios/${encodeURIComponent(scenarioId)}/simulate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      credentials: 'include',
      body: JSON.stringify(request),
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to reach financial simulation service: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to run financial simulations.');
  }
  if (res.status === 404) {
    throw new NotFoundError('Scenario not found.');
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Simulation failed (HTTP ${res.status}).`);
  }
  return await res.json();
}

async function postScenarioWorkflow<T>(scenarioId: string, workflow: string, payload: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/scenarios/${encodeURIComponent(scenarioId)}/${workflow}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      credentials: 'include',
      body: JSON.stringify(payload),
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to reach scenario ${workflow} service: ${err.message || err}`);
  }
  if (res.status === 401) throw new AuthenticationError('Authentication required to run this scenario workflow.');
  if (res.status === 403) throw new ForbiddenError('Your role cannot run this scenario workflow.');
  if (res.status === 404) throw new NotFoundError('Scenario or required registered evidence was not found.');
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Scenario ${workflow} failed (HTTP ${res.status}).`);
  }
  return await res.json();
}

export function allocateScenarioSpatialDemand(scenarioId: string, payload: unknown): Promise<Record<string, any>> {
  return postScenarioWorkflow(scenarioId, 'spatial-demand', payload);
}

export function calculateScenarioAccessibility(scenarioId: string, payload: unknown): Promise<Record<string, any>> {
  return postScenarioWorkflow(scenarioId, 'accessibility', payload);
}

export function evaluateScenarioPolicy(scenarioId: string, payload: unknown): Promise<Record<string, any>> {
  return postScenarioWorkflow(scenarioId, 'policy', payload);
}

export function calculateScenarioSchemeViability(scenarioId: string, payload: unknown): Promise<Record<string, any>> {
  return postScenarioWorkflow(scenarioId, 'scheme-viability', payload);
}

export async function compareScenarios(leftScenarioId: string, rightScenarioId: string): Promise<ScenarioComparisonResult> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/scenarios/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      credentials: 'include',
      body: JSON.stringify({ left_scenario_id: leftScenarioId, right_scenario_id: rightScenarioId }),
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to reach scenario comparison service: ${err.message || err}`);
  }
  if (res.status === 401) throw new AuthenticationError('Authentication required to compare scenarios.');
  if (res.status === 404) throw new NotFoundError('One or both scenarios were not found.');
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Scenario comparison failed (HTTP ${res.status}).`);
  }
  return await res.json();
}

export async function getScenarioComparison(comparisonId: string): Promise<Record<string, any>> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/scenarios/comparisons/${encodeURIComponent(comparisonId)}`, {
      headers: getAuthHeaders(), credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to retrieve saved scenario comparison: ${err.message || err}`);
  }
  if (res.status === 401) throw new AuthenticationError('Authentication required to retrieve this comparison.');
  if (res.status === 404) throw new NotFoundError('Scenario comparison not found.');
  if (!res.ok) throw new ApiError(res.status, `Scenario comparison retrieval failed (HTTP ${res.status}).`);
  return await res.json();
}

/**
 * Generate authenticated download URL or trigger client-side download for reports.
 */
export function getScenarioReportDownloadUrl(
  scenarioId: string,
  format: 'json' | 'csv' | 'xlsx' | 'pdf' = 'json'
): string {
  return `${API_BASE_URL}/scenarios/${encodeURIComponent(scenarioId)}/report?format=${format}`;
}

export function getTerritorialDossierDownloadUrl(
  geoId: string,
  format: 'json' | 'csv' | 'xlsx' | 'pdf' = 'json',
  scenarioId?: string
): string {
  const scenParam = scenarioId ? `&scenario_id=${encodeURIComponent(scenarioId)}` : '';
  return `${API_BASE_URL}/reports/dossier?geo_id=${encodeURIComponent(geoId)}&format=${format}${scenParam}`;
}

export async function downloadReportFile(url: string, defaultFilename: string): Promise<void> {
  const res = await fetch(url, {
    headers: { ...getAuthHeaders() },
    credentials: 'include',
  });
  if (!res.ok) {
    throw new ApiError(res.status, `Report download failed (HTTP ${res.status}).`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get('content-disposition');
  let filename = defaultFilename;
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) filename = match[1];
  }
  const blobUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(blobUrl);
  document.body.removeChild(a);
}

/**
 * Create an agent planning run (/runs).
 * Enforces per-run cost cap ($0.25 baseline per Handbook Part 8.3).
 */
export async function createSimulationRun(objective: any): Promise<any> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/runs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      credentials: 'include',
      body: JSON.stringify({
        objective,
        max_cost_usd: 0.25,
        seed: 42,
      }),
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to initialize agent run: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to launch agent runs.');
  }
  if (res.status === 429) {
    throw new ApiError(429, 'Rate limit or cost budget exceeded for current session.');
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Agent run launch failed (HTTP ${res.status}).`);
  }

  const data = await res.json();
  return {
    ...data,
    cost_usd: Number(data.cost_usd ?? data.cost_accumulated_usd ?? 0),
  };
}


export interface AgentRunRecord {
  id: string;
  owner_id: string;
  objective: Record<string, unknown>;
  state: string;
  steps_used: number;
  replans_used: number;
  model_calls_used: number;
  cost_usd: number;
  created_at: string;
  updated_at: string;
}

export interface AgentRunEventRecord {
  seq: number;
  type: string;
  payload: Record<string, unknown>;
  at: string;
}

export interface AgentRunEventsResponse {
  run_id: string;
  state: string;
  events: AgentRunEventRecord[];
  next_sequence: number;
}

/**
 * Create a persisted agent-run record.
 */
export async function createAgentRun(
  objective: Record<string, unknown>,
): Promise<AgentRunRecord> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/agent-runs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      credentials: 'include',
      body: JSON.stringify({ objective }),
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to initialize agent run: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to launch agent runs.');
  }
  if (res.status === 429) {
    throw new ApiError(429, 'Agent run creation was rate limited.');
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Agent run launch failed (HTTP ${res.status}).`);
  }

  const data = await res.json();
  return {
    ...data,
    cost_usd: Number(data.cost_usd ?? data.cost_accumulated_usd ?? 0),
  };
}

/**
 * Start background execution of a persisted agent run.
 */
export async function startAgentRun(runId: string): Promise<{ status: string; run_id: string }> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/agent-runs/${encodeURIComponent(runId)}/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to start agent run: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to start agent runs.');
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || `Agent run start failed (HTTP ${res.status}).`);
  }

  return await res.json();
}

export async function fetchAgentRun(runId: string): Promise<AgentRunRecord> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/agent-runs/${encodeURIComponent(runId)}`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to fetch agent run: ${err.message || err}`);
  }

  if (res.status === 401) {
    throw new AuthenticationError('Authentication required to view agent run.');
  }
  if (!res.ok) {
    throw new ApiError(res.status, `Agent run not found (HTTP ${res.status}).`);
  }

  const data = await res.json();
  return {
    ...data,
    cost_usd: Number(data.cost_usd ?? data.cost_accumulated_usd ?? 0),
  };
}

export async function fetchAgentRunEvents(
  runId: string,
  afterSequence: number = 0,
): Promise<AgentRunEventsResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/agent-runs/${encodeURIComponent(runId)}/events?after_sequence=${afterSequence}`, {
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } catch (err: any) {
    throw new NetworkError(`Failed to fetch run events: ${err.message || err}`);
  }

  if (!res.ok) {
    throw new ApiError(res.status, `Failed to load events for run ${runId}`);
  }

  return await res.json();
}

/**
 * Stream persisted agent run events via SSE with chunk-boundary parsing and sequence validation.
 */
export async function streamAgentRunEvents(
  runId: string,
  afterSequence: number,
  onEvent: (event: AgentRunEventRecord) => void,
  signal?: AbortSignal,
): Promise<void> {
  const url = `${API_BASE_URL}/agent-runs/${encodeURIComponent(runId)}/events/stream?after_sequence=${afterSequence}`;
  const res = await fetch(url, {
    headers: {
      Accept: 'text/event-stream',
      ...getAuthHeaders(),
    },
    credentials: 'include',
    signal,
  });

  if (!res.ok || !res.body) {
    throw new ApiError(res.status, `Event stream failed (HTTP ${res.status}).`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop() ?? '';

      for (const frame of frames) {
        if (!frame.trim() || frame.startsWith(':')) continue;

        let idStr: string | null = null;
        let eventType: string | null = null;
        let dataStr: string | null = null;

        for (const line of frame.split('\n')) {
          if (line.startsWith('id:')) {
            idStr = line.slice(3).trim();
          } else if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            dataStr = line.slice(5).trim();
          }
        }

        if (dataStr) {
          const parsed = JSON.parse(dataStr);
          if (idStr !== null && Number(idStr) !== parsed.seq) {
            throw new Error(`ID/type did not match: expected seq ${parsed.seq}, got id ${idStr}`);
          }
          onEvent(parsed);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
