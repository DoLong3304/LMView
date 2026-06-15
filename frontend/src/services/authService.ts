/**
 * Auth service — API calls for authentication.
 *
 * Talks to POST /api/auth/register, /api/auth/login, /api/auth/logout, /api/auth/me
 * Falls back to localStorage mock when API is unavailable or VITE_DATA_SOURCE=mock.
 */

import { API_BASE_URL, DATA_SOURCE } from "@/constants/env";
import { createApiError } from "@/utils/errors";

// ── Types ────────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: string;
  email: string;
  username?: string | null;
  display_name: string;
  avatar_url?: string | null;
  date_of_birth?: string | null;
  bio?: string | null;
  role: string;
  preferred_language?: string | null;
  timezone?: string | null;
  is_active: boolean;
  is_verified: boolean;
  must_change_password: boolean;
  password_changed_at?: string | null;
  deactivated_at?: string | null;
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

export function clearStoredSession(): void {
  clearToken();
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
    throw createApiError("auth", resp.status, errorData, { endpoint: path });
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

export async function apiUpdateProfile(
  updates: Partial<Pick<
    UserResponse,
    | "display_name"
    | "username"
    | "avatar_url"
    | "date_of_birth"
    | "bio"
    | "preferred_language"
    | "timezone"
  >>,
): Promise<UserResponse> {
  return authFetch<UserResponse>("/auth/profile", {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function apiChangePassword(
  currentPassword: string,
  newPassword: string,
): Promise<UserResponse> {
  return authFetch<UserResponse>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export async function apiDeleteAccount(confirmation: string): Promise<void> {
  await authFetch("/auth/account", {
    method: "DELETE",
    body: JSON.stringify({ confirmation }),
  });
  clearToken();
}

// ── Mock auth (fallback for VITE_DATA_SOURCE=mock) ───────────────────────────

const MOCK_USERS_KEY = "lmview_mock_users";

interface MockUser {
  id: string;
  email: string;
  username?: string | null;
  display_name: string;
  avatar_url?: string | null;
  date_of_birth?: string | null;
  bio?: string | null;
  password: string;
  role: string;
  is_active?: boolean;
  is_verified?: boolean;
  must_change_password?: boolean;
  password_changed_at?: string | null;
  created_at?: string | null;
  last_login_at?: string | null;
}

function getMockUsers(): MockUser[] {
  try {
    const users = JSON.parse(localStorage.getItem(MOCK_USERS_KEY) || "[]") as MockUser[];
    if (users.length > 0) return users;
    const seeded: MockUser[] = [
      {
        id: "mock-admin",
        email: "admin@lmview.local",
        username: "admin",
        display_name: "LMView Admin",
        password: "admin123",
        role: "admin",
        is_active: true,
        is_verified: true,
        must_change_password: true,
        created_at: new Date().toISOString(),
      },
    ];
    saveMockUsers(seeded);
    return seeded;
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
    is_active: true,
    is_verified: false,
    must_change_password: false,
    created_at: new Date().toISOString(),
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
    must_change_password: false,
    created_at: newUser.created_at,
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
    is_active: found.is_active !== false,
    is_verified: Boolean(found.is_verified),
    username: found.username,
    avatar_url: found.avatar_url,
    date_of_birth: found.date_of_birth,
    bio: found.bio,
    must_change_password: Boolean(found.must_change_password),
    password_changed_at: found.password_changed_at,
    created_at: found.created_at,
    last_login_at: new Date().toISOString(),
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
    username: found.username,
    display_name: found.display_name,
    avatar_url: found.avatar_url,
    date_of_birth: found.date_of_birth,
    bio: found.bio,
    role: found.role,
    is_active: found.is_active !== false,
    is_verified: Boolean(found.is_verified),
    must_change_password: Boolean(found.must_change_password),
    password_changed_at: found.password_changed_at,
    created_at: found.created_at,
    last_login_at: found.last_login_at,
  };
}

export function mockUpdateProfile(
  updates: Partial<UserResponse>,
): UserResponse | null {
  const token = getStoredToken();
  if (!token?.startsWith("mock-token-")) return null;
  const userId = token.replace("mock-token-", "");
  const users = getMockUsers();
  const index = users.findIndex((u) => u.id === userId);
  if (index < 0) return null;
  users[index] = { ...users[index], ...updates };
  saveMockUsers(users);
  return mockGetCurrentUser();
}

export function mockChangePassword(
  currentPassword: string,
  newPassword: string,
): { success: boolean; error?: string; user?: UserResponse } {
  const token = getStoredToken();
  if (!token?.startsWith("mock-token-")) return { success: false, error: "invalidCredentials" };
  const userId = token.replace("mock-token-", "");
  const users = getMockUsers();
  const index = users.findIndex((u) => u.id === userId);
  if (index < 0 || users[index].password !== currentPassword) {
    return { success: false, error: "invalidCredentials" };
  }
  users[index].password = newPassword;
  users[index].must_change_password = false;
  users[index].password_changed_at = new Date().toISOString();
  saveMockUsers(users);
  const user = mockGetCurrentUser();
  return user ? { success: true, user } : { success: false, error: "invalidCredentials" };
}

export function mockDeleteAccount(confirmation: string): boolean {
  if (confirmation.toUpperCase() !== "DELETE") return false;
  const token = getStoredToken();
  if (!token?.startsWith("mock-token-")) return false;
  const userId = token.replace("mock-token-", "");
  const users = getMockUsers();
  const index = users.findIndex((u) => u.id === userId);
  if (index < 0) return false;
  users[index].is_active = false;
  saveMockUsers(users);
  clearToken();
  return true;
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
