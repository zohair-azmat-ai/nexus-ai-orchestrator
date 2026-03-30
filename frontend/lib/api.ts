const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchHealth() {
  const res = await fetch(`${API_URL}/api/v1/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function sendChat(payload: {
  user_id: string;
  session_id: string;
  message: string;
  history?: { role: string; content: string }[];
}) {
  const res = await fetch(`${API_URL}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, history: payload.history ?? [], metadata: {} }),
  });
  if (!res.ok) throw new Error("Chat request failed");
  return res.json();
}
