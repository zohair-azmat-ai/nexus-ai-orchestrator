import { apiRequest } from "@/lib/api";

export type ReportPriority = "normal" | "high" | "urgent" | "critical";

export interface ReportIssuePayload {
  customerRef: string;
  email: string;
  title: string;
  description: string;
  priority: ReportPriority;
}

export interface ReportIssueResult {
  conversationId: string;
  escalated: boolean;
  caseId: string | null;
  caseStatus: string | null;
  answer: string;
}

function buildMessage(payload: ReportIssuePayload): string {
  // Compose a message that passes through the chat pipeline naturally.
  // High/urgent/critical priorities inject escalation-trigger keywords so
  // the triage stage routes to the escalation agent and creates a DB case.
  const prefix =
    payload.priority === "critical"
      ? "[CRITICAL] "
      : payload.priority === "urgent"
        ? "[URGENT] "
        : payload.priority === "high"
          ? "[HIGH PRIORITY] "
          : "";

  let message = `${prefix}Issue Report: ${payload.title}\n\n${payload.description}`;

  if (payload.priority === "urgent" || payload.priority === "critical") {
    message += "\n\nThis issue is urgent and needs immediate attention.";
  }

  return message;
}

export async function reportIssue(
  payload: ReportIssuePayload,
): Promise<ReportIssueResult> {
  const response = await apiRequest<{
    escalation: boolean;
    escalation_case_id: string | null;
    escalation_status: string | null;
    conversation_id: string;
    answer: string;
  }>("/api/v1/chat", {
    method: "POST",
    body: JSON.stringify({
      user_id: payload.customerRef || "anonymous",
      session_id: crypto.randomUUID(),
      message: buildMessage(payload),
      history: [],
      metadata: {
        source: "customer_report",
        email: payload.email,
        priority: payload.priority,
        title: payload.title,
      },
    }),
  });

  return {
    conversationId: response.conversation_id,
    escalated: response.escalation,
    caseId: response.escalation_case_id,
    caseStatus: response.escalation_status,
    answer: response.answer,
  };
}
