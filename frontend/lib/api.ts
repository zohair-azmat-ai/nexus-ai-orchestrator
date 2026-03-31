const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

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

    throw new Error(message);
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

export { API_URL, apiRequest };
