import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import {
  type UserResponse,
  apiRegister,
  apiLogin,
  apiLogout,
  apiGetMe,
  apiUpdateProfile,
  apiChangePassword,
  apiDeleteAccount,
  mockRegister,
  mockLogin,
  mockLogout,
  mockGetCurrentUser,
  mockUpdateProfile,
  mockChangePassword,
  mockDeleteAccount,
  shouldUseMockAuth,
  hasStoredSession,
  clearStoredSession,
} from "@/services/authService";
import { getRoleAwareErrorMessage } from "@/utils/errors";

interface AuthContextValue {
  user: UserResponse | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (
    email: string,
    password: string,
  ) => Promise<{ success: boolean; error?: string }>;
  register: (
    name: string,
    email: string,
    password: string,
  ) => Promise<{ success: boolean; error?: string }>;
  refreshUser: () => Promise<void>;
  updateProfile: (
    updates: Partial<UserResponse>,
  ) => Promise<{ success: boolean; error?: string }>;
  changePassword: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<{ success: boolean; error?: string }>;
  deleteAccount: (confirmation: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const AUTH_ROLE_SNAPSHOT_KEY = "lmview_auth_role";

function storeRoleSnapshot(user: UserResponse | null): void {
  try {
    if (user?.role) {
      localStorage.setItem(AUTH_ROLE_SNAPSHOT_KEY, user.role);
    } else {
      localStorage.removeItem(AUTH_ROLE_SNAPSHOT_KEY);
    }
  } catch {
    // Storage unavailable
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    storeRoleSnapshot(user);
  }, [user]);

  // Restore session on mount
  useEffect(() => {
    const restore = async () => {
      if (shouldUseMockAuth()) {
        const mockUser = mockGetCurrentUser();
        setUser(mockUser);
        setLoading(false);
        return;
      }

      if (!hasStoredSession()) {
        setLoading(false);
        return;
      }

      try {
        const me = await apiGetMe();
        setUser(me.user);
      } catch {
        clearStoredSession();
        // Token invalid/expired — clear silently
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    restore();
  }, []);

  const login = useCallback(
    async (
      email: string,
      password: string,
    ): Promise<{ success: boolean; error?: string }> => {
      setError(null);

      if (shouldUseMockAuth()) {
        const result = mockLogin(email, password);
        if (result.success && result.user) {
          setUser(result.user);
        }
        return result;
      }

      try {
        const data = await apiLogin(email, password);
        setUser(data.user);
        return { success: true };
      } catch (err) {
        const message = getRoleAwareErrorMessage(err, {
          area: "auth",
          fallback: "We could not sign you in. Please check your account information and try again.",
        });
        setError(message);
        return { success: false, error: message };
      }
    },
    [],
  );

  const register = useCallback(
    async (
      name: string,
      email: string,
      password: string,
    ): Promise<{ success: boolean; error?: string }> => {
      setError(null);

      if (shouldUseMockAuth()) {
        const result = mockRegister(name, email, password);
        if (result.success && result.user) {
          setUser(result.user);
        }
        return result;
      }

      try {
        const data = await apiRegister(email, password, name);
        setUser(data.user);
        return { success: true };
      } catch (err) {
        const message = getRoleAwareErrorMessage(err, {
          area: "auth",
          fallback: "We could not create the account. Please check the form and try again.",
        });
        setError(message);
        return { success: false, error: message };
      }
    },
    [],
  );

  const logout = useCallback(async () => {
    if (shouldUseMockAuth()) {
      mockLogout();
    } else {
      await apiLogout();
    }
    setUser(null);
    setError(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (shouldUseMockAuth()) {
      setUser(mockGetCurrentUser());
      return;
    }
    const me = await apiGetMe();
    setUser(me.user);
  }, []);

  const updateProfile = useCallback(
    async (updates: Partial<UserResponse>): Promise<{ success: boolean; error?: string }> => {
      try {
        if (shouldUseMockAuth()) {
          const updated = mockUpdateProfile(updates);
          if (updated) setUser(updated);
          return updated ? { success: true } : { success: false, error: "User not found" };
        }
        const updated = await apiUpdateProfile(updates);
        setUser(updated);
        return { success: true };
      } catch (err) {
        const message = getRoleAwareErrorMessage(err, {
          isAdmin: user?.role === "admin",
          fallback: "Profile update failed",
        });
        setError(message);
        return { success: false, error: message };
      }
    },
    [user?.role],
  );

  const changePassword = useCallback(
    async (
      currentPassword: string,
      newPassword: string,
    ): Promise<{ success: boolean; error?: string }> => {
      try {
        if (shouldUseMockAuth()) {
          const result = mockChangePassword(currentPassword, newPassword);
          if (result.success && result.user) setUser(result.user);
          return result.success ? { success: true } : { success: false, error: result.error };
        }
        const updated = await apiChangePassword(currentPassword, newPassword);
        setUser(updated);
        return { success: true };
      } catch (err) {
        const message = getRoleAwareErrorMessage(err, {
          isAdmin: user?.role === "admin",
          fallback: "Password change failed",
        });
        setError(message);
        return { success: false, error: message };
      }
    },
    [user?.role],
  );

  const deleteAccount = useCallback(
    async (confirmation: string): Promise<{ success: boolean; error?: string }> => {
      try {
        if (shouldUseMockAuth()) {
          if (!mockDeleteAccount(confirmation)) {
            return { success: false, error: "Confirmation must be DELETE" };
          }
        } else {
          await apiDeleteAccount(confirmation);
        }
        setUser(null);
        setError(null);
        return { success: true };
      } catch (err) {
        const message = getRoleAwareErrorMessage(err, {
          isAdmin: user?.role === "admin",
          fallback: "Account deletion failed",
        });
        setError(message);
        return { success: false, error: message };
      }
    },
    [user?.role],
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        isAuthenticated: user !== null,
        login,
        register,
        refreshUser,
        updateProfile,
        changePassword,
        deleteAccount,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
