import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/auth-storage";

function resolveApiUrl() {
  const internalUrl =
    typeof window === "undefined" ? process.env.INTERNAL_API_BASE_URL ?? "" : "";
  const configuredUrl =
    internalUrl ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "";
  const normalizedUrl = configuredUrl.replace(/\/+$/, "");

  if (normalizedUrl) {
    return normalizedUrl;
  }

  if (process.env.NODE_ENV !== "production") {
    return "http://localhost:8000";
  }

  throw new Error(
    "NEXT_PUBLIC_API_BASE_URL must be configured in production so the frontend can reach the Nexus AI backend.",
  );
}

const API_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NODE_ENV !== "production" ? "http://localhost:8000" : "")
).replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface ApiRequestOptions extends RequestInit {
  authToken?: string | null;
  skipAuth?: boolean;
}

function getBrowserAuthToken() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
}

async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const apiUrl = resolveApiUrl();
  const authToken = options.skipAuth ? null : (options.authToken ?? getBrowserAuthToken());
  let response: Response;

  try {
    response = await fetch(`${apiUrl}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        ...(options.headers ?? {}),
      },
    });
  } catch {
    throw new Error(`Unable to reach the Nexus AI backend at ${apiUrl}.`);
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const error = (await response.json()) as { detail?: string };
      if (error?.detail) {
        message = error.detail;
      }
    } catch {
      // Keep the default fallback when the response body is empty or not JSON.
    }

    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function fetchHealth() {
  return apiRequest("/api/v1/health", {
    next: { revalidate: 30 },
  });
}

export async function sendChat(payload: {
  user_id: string;
  session_id: string;
  message: string;
  history?: { role: string; content: string }[];
}) {
  return apiRequest("/api/v1/chat", {
    method: "POST",
    body: JSON.stringify({ ...payload, history: payload.history ?? [], metadata: {} }),
  });
}

export { API_URL, apiRequest, resolveApiUrl };
