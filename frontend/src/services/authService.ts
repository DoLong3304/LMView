/**
 * Auth service — API calls for authentication.
 *
 * Talks to POST /api/auth/register, /api/auth/login, /api/auth/logout, /api/auth/me
 * Falls back to localStorage mock when API is unavailable or VITE_DATA_SOURCE=mock.
 */

import { API_BASE_URL, DATA_SOURCE } from "@/constants/env";

// ── Types ────────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: string;
  email: string;
  display_name: string;
  role: string;
  preferred_language?: string | null;
  timezone?: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at?: string | null;
  last_login_at?: string | null;
}

export interface SessionInfo {
  session_token: string;
  expires_at: string;
}

export interface AuthResponse {
  user: UserResponse;
  session: SessionInfo;
}

export interface UserPreferences {
  user_id: string;
  default_symbol?: string | null;
  default_timeframe?: string | null;
  default_exchange?: string | null;
  preferred_language?: string | null;
  theme?: string | null;
  risk_profile?: string | null;
  favorite_indicators: string[];
  ai_response_style?: string | null;
}

export interface MeResponse {
  user: UserResponse;
  preferences?: UserPreferences | null;
}

// ── Token storage ────────────────────────────────────────────────────────────

const TOKEN_KEY = "lmview_session_token";

function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function storeToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Storage unavailable
  }
}

function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Storage unavailable
  }
}

export function getAuthHeaders(): Record<string, string> {
  const token = getStoredToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

// ── API calls ────────────────────────────────────────────────────────────────

async function authFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...getAuthHeaders(),
    ...(options.headers as Record<string, string> || {}),
  };

  const resp = await fetch(url, { ...options, headers });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Auth API error: ${resp.status}`
    );
  }

  return resp.json();
}

export async function apiRegister(
  email: string,
  password: string,
  displayName: string,
  preferredLanguage?: string,
): Promise<AuthResponse> {
  const data = await authFetch<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      display_name: displayName,
      preferred_language: preferredLanguage,
    }),
  });

  storeToken(data.session.session_token);
  return data;
}

export async function apiLogin(
  email: string,
  password: string,
): Promise<AuthResponse> {
  const data = await authFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  storeToken(data.session.session_token);
  return data;
}

export async function apiLogout(): Promise<void> {
  try {
    await authFetch("/auth/logout", { method: "POST" });
  } catch {
    // Logout even if API fails
  }
  clearToken();
}

export async function apiGetMe(): Promise<MeResponse> {
  return authFetch<MeResponse>("/auth/me");
}

export async function apiUpdatePreferences(
  updates: Partial<UserPreferences>,
): Promise<UserPreferences> {
  return authFetch<UserPreferences>("/auth/preferences", {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

// ── Mock auth (fallback for VITE_DATA_SOURCE=mock) ───────────────────────────

const MOCK_USERS_KEY = "lmview_mock_users";

interface MockUser {
  id: string;
  email: string;
  display_name: string;
  password: string;
  role: string;
}

function getMockUsers(): MockUser[] {
  try {
    return JSON.parse(localStorage.getItem(MOCK_USERS_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveMockUsers(users: MockUser[]): void {
  try {
    localStorage.setItem(MOCK_USERS_KEY, JSON.stringify(users));
  } catch {
    // Storage unavailable
  }
}

export function mockRegister(
  name: string,
  email: string,
  password: string,
): { success: boolean; error?: string; user?: UserResponse } {
  const users = getMockUsers();
  if (users.some((u) => u.email === email.toLowerCase())) {
    return { success: false, error: "emailExists" };
  }

  const newUser: MockUser = {
    id: `mock-${Date.now()}`,
    email: email.toLowerCase(),
    display_name: name,
    password,
    role: "user",
  };
  users.push(newUser);
  saveMockUsers(users);

  const userResp: UserResponse = {
    id: newUser.id,
    email: newUser.email,
    display_name: newUser.display_name,
    role: newUser.role,
    is_active: true,
    is_verified: false,
  };

  // Store a mock token
  storeToken(`mock-token-${newUser.id}`);
  return { success: true, user: userResp };
}

export function mockLogin(
  email: string,
  password: string,
): { success: boolean; error?: string; user?: UserResponse } {
  const users = getMockUsers();
  const found = users.find(
    (u) => u.email === email.toLowerCase() && u.password === password,
  );
  if (!found) {
    return { success: false, error: "invalidCredentials" };
  }

  const userResp: UserResponse = {
    id: found.id,
    email: found.email,
    display_name: found.display_name,
    role: found.role,
    is_active: true,
    is_verified: false,
  };

  storeToken(`mock-token-${found.id}`);
  return { success: true, user: userResp };
}

export function mockLogout(): void {
  clearToken();
}

export function mockGetCurrentUser(): UserResponse | null {
  const token = getStoredToken();
  if (!token?.startsWith("mock-token-")) return null;

  const userId = token.replace("mock-token-", "");
  const users = getMockUsers();
  const found = users.find((u) => u.id === userId);
  if (!found) return null;

  return {
    id: found.id,
    email: found.email,
    display_name: found.display_name,
    role: found.role,
    is_active: true,
    is_verified: false,
  };
}

/**
 * Check if we should use mock auth (no backend available).
 */
export function shouldUseMockAuth(): boolean {
  return DATA_SOURCE === "mock";
}

/**
 * Check if user has a stored auth token.
 */
export function hasStoredSession(): boolean {
  return getStoredToken() !== null;
}
