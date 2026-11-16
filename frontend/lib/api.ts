/**
 * ArthLens API Client for Authentication, User Management, and Administration.
 * Authoritative Specification: ArthLens — Business Operating System & Decision Intelligence Platform.
 */

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

export interface UserProfile {
  id: string;
  email: string;
  roles: string[];
  full_name?: string;
}

export interface AdminUserRecord {
  id: string;
  email: string;
  quota_counters: Record<string, any>;
  roles: string[];
  created_at?: string | null;
}

/**
 * Typed Error Hierarchy for API Communications.
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
  constructor(message = 'The requested resource was not found.') {
    super(404, message, 'NOT_FOUND');
    this.name = 'NotFoundError';
  }
}

export class NetworkError extends ApiError {
  constructor(message = 'Network connection failed. Backend is unreachable.') {
    super(0, message, 'NETWORK_ERROR');
    this.name = 'NetworkError';
  }
}

// In-memory token carrier for programmatic CLI/SSR/testing sessions
let inMemoryToken: string | null = null;

export function isDevAutoAuthEnabled(): boolean {
  if (process.env.NODE_ENV === 'production') {
    return false;
  }
  return true;
}

export function setAuthToken(token: string | null) {
  inMemoryToken = token;
  if (typeof window !== 'undefined') {
    if (token) {
      window.localStorage.setItem('arthlens_token', token);
      window.localStorage.removeItem('token');
    } else {
      window.localStorage.removeItem('arthlens_token');
      window.localStorage.removeItem('token');
    }
  }
}

export function getAuthToken(): string | null {
  if (inMemoryToken) return inMemoryToken;
  if (typeof window !== 'undefined') {
    inMemoryToken = window.localStorage.getItem('arthlens_token') || window.localStorage.getItem('token');
  }
  return inMemoryToken;
}

function getCsrfToken(): string | null {
  if (typeof document === 'undefined') return null;
  const cookie = document.cookie.split(';').map((part) => part.trim());
  for (const name of ['arthlens_csrf', 'csrf_token']) {
    const entry = cookie.find((part) => part.startsWith(`${name}=`));
    if (entry) return decodeURIComponent(entry.slice(name.length + 1));
  }
  return null;
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
  options: { authenticated?: boolean; refreshOn401?: boolean } = {},
): Promise<Response> {
  const authenticated = options.authenticated !== false;
  const refreshOn401 = options.refreshOn401 !== false;
  const url = /^https?:\/\//i.test(path) ? path : `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
  const requestOnce = (token: string | null): Promise<Response> => {
    const headers = new Headers(init.headers);
    if (!headers.has('Content-Type') && !(typeof FormData !== 'undefined' && init.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }
    if (authenticated && token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes((init.method || 'GET').toUpperCase())) {
      const csrf = getCsrfToken();
      if (csrf && !headers.has('X-CSRF-Token')) headers.set('X-CSRF-Token', csrf);
    }
    return fetch(url, {
      ...init,
      headers: Object.fromEntries(headers.entries()),
      credentials: 'include',
    });
  };

  const response = await requestOnce(authenticated ? getAuthToken() : null);
  const noRefreshPaths = new Set([
    '/auth/login', '/auth/register', '/auth/refresh', '/auth/logout',
    '/auth/login/initiate', '/auth/login/verify-otp', '/auth/register/initiate',
    '/auth/register/verify-otp', '/auth/otp/resend', '/auth/google',
    '/auth/password-reset/request', '/auth/password-reset/confirm',
  ]);
  if (response.status !== 401 || !authenticated || !refreshOn401 || noRefreshPaths.has(path)) {
    return response;
  }

  const csrf = getCsrfToken();
  const refreshHeaders = new Headers({ 'Content-Type': 'application/json' });
  if (csrf) refreshHeaders.set('X-CSRF-Token', csrf);
  let refreshedToken: string | null = null;
  try {
    const refreshed = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST', headers: refreshHeaders, credentials: 'include',
    });
    if (refreshed.ok) {
      const payload = await refreshed.json().catch(() => ({}));
      refreshedToken = typeof payload.access_token === 'string' ? payload.access_token : null;
    }
  } catch {
    // The original authenticated response carries the actionable failure.
  }
  if (!refreshedToken) {
    setAuthToken(null);
    return response;
  }
  setAuthToken(refreshedToken);
  return requestOnce(refreshedToken);
}

export function getAuthHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const csrf = getCsrfToken();
  if (csrf) headers['X-CSRF-Token'] = csrf;
  return headers;
}

export async function loginUser(email: string, password: string): Promise<UserProfile> {
  const res = await apiFetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  }, { authenticated: false, refreshOn401: false });
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

export interface OtpChallenge {
  otp_required: true;
  challenge_id: string;
  email: string;
  purpose: 'REGISTER_VERIFY' | 'LOGIN_2FA';
  expires_in_seconds: number;
  dev_otp_preview?: string;
}

async function postAuth<T>(path: string, payload: Record<string, unknown>): Promise<T> {
  const res = await apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }, { authenticated: false, refreshOn401: false });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'Authentication request failed.');
  return data as T;
}

export async function initiateEmailLogin(email: string, password: string): Promise<OtpChallenge> {
  return postAuth<OtpChallenge>('/auth/login/initiate', { email, password });
}

export async function initiateEmailRegistration(
  fullName: string,
  email: string,
  password: string,
): Promise<OtpChallenge> {
  return postAuth<OtpChallenge>('/auth/register/initiate', {
    full_name: fullName, email, password,
  });
}

export async function resendEmailOtp(challengeId: string, email: string): Promise<OtpChallenge> {
  return postAuth<OtpChallenge>('/auth/otp/resend', { challenge_id: challengeId, email });
}

async function verifyEmailOtp(
  path: '/auth/login/verify-otp' | '/auth/register/verify-otp',
  challengeId: string,
  email: string,
  otpCode: string,
): Promise<UserProfile> {
  const data = await postAuth<UserProfile & { access_token?: string }>(path, {
    challenge_id: challengeId, email, otp_code: otpCode,
  });
  if (data.access_token) setAuthToken(data.access_token);
  return data;
}

export function verifyEmailLoginOtp(challengeId: string, email: string, otpCode: string) {
  return verifyEmailOtp('/auth/login/verify-otp', challengeId, email, otpCode);
}

export function verifyEmailRegistrationOtp(challengeId: string, email: string, otpCode: string) {
  return verifyEmailOtp('/auth/register/verify-otp', challengeId, email, otpCode);
}

export async function authenticateWithGoogle(input: {
  mode: 'login' | 'register';
  idToken?: string;
  email?: string;
  fullName?: string;
}): Promise<UserProfile> {
  const data = await postAuth<UserProfile & { access_token?: string }>('/auth/google', {
    mode: input.mode,
    ...(input.idToken ? { id_token: input.idToken } : {}),
    ...(input.email ? { email: input.email } : {}),
    ...(input.fullName ? { full_name: input.fullName } : {}),
  });
  if (data.access_token) setAuthToken(data.access_token);
  return data;
}

export async function registerUser(
  fullName: string,
  email: string,
  password: string,
): Promise<UserProfile> {
  const res = await apiFetch('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      full_name: fullName,
      email: email,
      password: password,
    }),
  }, { authenticated: false, refreshOn401: false });
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
): Promise<{ status: string; message: string; dev_recovery_token?: string; dev_reset_url?: string }> {
  const cleanEmail = email.trim().toLowerCase();
  const res = await apiFetch('/auth/password-reset/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: cleanEmail }),
  }, { authenticated: false, refreshOn401: false });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Password recovery request failed');
  }
  return await res.json();
}

export async function confirmPasswordReset(
  token: string,
  newPassword: string,
): Promise<{ status: string; message: string }> {
  const cleanToken = token.trim();
  const res = await apiFetch('/auth/password-reset/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: cleanToken, new_password: newPassword }),
  }, { authenticated: false, refreshOn401: false });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Password reset failed');
  }
  return await res.json();
}

export async function logoutUser(): Promise<void> {
  try {
    await apiFetch('/auth/logout', {
      method: 'POST',
      headers: getAuthHeaders(),
    }, { refreshOn401: false });
  } catch (err) {
    console.warn('Logout notice:', err);
  } finally {
    setAuthToken(null);
  }
}

export async function getCurrentUser(): Promise<UserProfile | null> {
  try {
    const res = await apiFetch('/auth/me', {
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('getCurrentUser notice:', err);
  }
  return null;
}

export const getMe = getCurrentUser;

export async function fetchAdminUsers(): Promise<AdminUserRecord[]> {
  const res = await apiFetch('/admin/users', {
    headers: getAuthHeaders(),
  });
  if (res.status === 401) throw new AuthenticationError();
  if (res.status === 403) throw new ForbiddenError('Administrator access required.');
  if (!res.ok) throw new ApiError(res.status, 'Failed to fetch user directory.');
  return await res.json();
}

export async function updateUserRole(userId: string, role: string): Promise<{ status: string; roles: string[] }> {
  const res = await apiFetch(`/admin/users/${encodeURIComponent(userId)}/role`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ role }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || 'Failed to update user role.');
  }
  return await res.json();
}

export async function deactivateUserAccount(userId: string): Promise<{ status: string; is_active: boolean }> {
  const res = await apiFetch(`/admin/users/${encodeURIComponent(userId)}/deactivate`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || 'Failed to deactivate account.');
  }
  return await res.json();
}

export async function activateUserAccount(userId: string): Promise<{ status: string; is_active: boolean }> {
  const res = await apiFetch(`/admin/users/${encodeURIComponent(userId)}/activate`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || 'Failed to activate account.');
  }
  return await res.json();
}
