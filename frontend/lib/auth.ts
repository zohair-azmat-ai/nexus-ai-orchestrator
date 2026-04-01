import { apiRequest } from "@/lib/api";
import {
  AUTH_TOKEN_COOKIE,
  AUTH_TOKEN_STORAGE_KEY,
  AUTH_USER_STORAGE_KEY,
} from "@/lib/auth-storage";
import type { AuthUser, LoginRequest, LoginResponse } from "@/types/auth";

export async function login(payload: LoginRequest): Promise<LoginResponse> {
  return apiRequest("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuth: true,
  });
}

export async function getCurrentUser(authToken?: string | null): Promise<AuthUser> {
  return apiRequest("/api/v1/auth/me", {
    cache: "no-store",
    authToken,
  });
}

export function persistAuthSession(session: LoginResponse) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, session.access_token);
  window.localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(session.user));
  document.cookie = `${AUTH_TOKEN_COOKIE}=${session.access_token}; path=/; max-age=${session.expires_in}; samesite=lax`;
}

export function clearAuthSession() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(AUTH_USER_STORAGE_KEY);
  document.cookie = `${AUTH_TOKEN_COOKIE}=; path=/; max-age=0; samesite=lax`;
}

export function getStoredAuthToken() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
}

export function getStoredAuthUser(): AuthUser | null {
  if (typeof window === "undefined") {
    return null;
  }

  const rawValue = window.localStorage.getItem(AUTH_USER_STORAGE_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    return JSON.parse(rawValue) as AuthUser;
  } catch {
    window.localStorage.removeItem(AUTH_USER_STORAGE_KEY);
    return null;
  }
}
