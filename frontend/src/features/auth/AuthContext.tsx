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
  mockRegister,
  mockLogin,
  mockLogout,
  mockGetCurrentUser,
  shouldUseMockAuth,
  hasStoredSession,
} from "@/services/authService";

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
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        const message =
          err instanceof Error ? err.message : "Login failed";
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
        const message =
          err instanceof Error ? err.message : "Registration failed";
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

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        isAuthenticated: user !== null,
        login,
        register,
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
