"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError } from "@/lib/api";
import {
  clearAuthSession,
  getCurrentUser,
  getStoredAuthToken,
  getStoredAuthUser,
  persistAuthSession,
} from "@/lib/auth";
import type { LoginResponse } from "@/types/auth";
import type { AuthUser } from "@/types/auth";

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  setSession: (session: LoginResponse) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = getStoredAuthToken();
    const storedUser = getStoredAuthUser();

    setToken(storedToken);
    setUser(storedUser);

    if (!storedToken) {
      setIsLoading(false);
      return;
    }

    void getCurrentUser(storedToken)
      .then((currentUser) => {
        setUser(currentUser);
      })
      .catch((error) => {
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          clearAuthSession();
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  async function refreshUser() {
    const nextToken = getStoredAuthToken();
    if (!nextToken) {
      setToken(null);
      setUser(null);
      return;
    }

    const currentUser = await getCurrentUser(nextToken);
    setToken(nextToken);
    setUser(currentUser);
  }

  function setSession(session: LoginResponse) {
    persistAuthSession(session);
    setToken(session.access_token);
    setUser(session.user);
  }

  function logout() {
    clearAuthSession();
    setToken(null);
    setUser(null);
  }

  const value = useMemo(
    () => ({ user, token, isLoading, setSession, logout, refreshUser }),
    [user, token, isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
