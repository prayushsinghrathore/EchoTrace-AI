"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import {
  type UserProfile,
  loginUser,
  logoutUser,
  registerUser,
  refreshTokens,
  getProfile,
  clearTokens,
  getAccessToken,
  type LoginRequest,
  type RegisterRequest,
} from "@/lib/auth-client";

/* ── Types ──────────────────────────────────────────────────────────────── */

interface AuthState {
  user: UserProfile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

interface AuthContextValue extends AuthState {
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  clearError: () => void;
}

/* ── Context ────────────────────────────────────────────────────────────── */

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/* ── Provider ───────────────────────────────────────────────────────────── */

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
    error: null,
  });

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  const refreshSession = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setState({ user: null, isLoading: false, isAuthenticated: false, error: null });
      return;
    }

    try {
      const user = await getProfile();
      setState({ user, isLoading: false, isAuthenticated: true, error: null });
    } catch {
      try {
        await refreshTokens();
        const user = await getProfile();
        setState({ user, isLoading: false, isAuthenticated: true, error: null });
      } catch {
        clearTokens();
        setState({ user: null, isLoading: false, isAuthenticated: false, error: null });
      }
    }
  }, []);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  const login = useCallback(async (data: LoginRequest) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      await loginUser(data);
      const user = await getProfile();
      setState({ user, isLoading: false, isAuthenticated: true, error: null });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      throw err;
    }
  }, []);

  const register = useCallback(async (data: RegisterRequest) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      await registerUser(data);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: null,
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Registration failed";
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } catch {
      clearTokens();
    }
    setState({ user: null, isLoading: false, isAuthenticated: false, error: null });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        register,
        logout,
        refreshSession,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/* ── Hook ────────────────────────────────────────────────────────────────── */

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
