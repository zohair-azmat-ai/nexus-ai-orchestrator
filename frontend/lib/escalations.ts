import { apiRequest } from "@/lib/api";
import type {
  EscalationAssignRequest,
  EscalationCase,
  EscalationCaseListResponse,
  EscalationNote,
  EscalationNoteCreateRequest,
  EscalationNoteListResponse,
  EscalationStatusUpdateRequest,
} from "@/types/escalations";

interface ListEscalationsOptions {
  limit?: number;
  status?: string;
  severity?: string;
  assigned_to?: string;
  authToken?: string | null;
}

function buildQuery(params: Iterable<[string, string | number | undefined]>) {
  const searchParams = new URLSearchParams();

  Array.from(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      searchParams.set(key, String(value));
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export async function listEscalations(
  options: ListEscalationsOptions = {},
): Promise<EscalationCaseListResponse> {
  const { authToken, ...queryOptions } = options;

  return apiRequest(`/api/v1/escalations${buildQuery(Object.entries(queryOptions))}`, {
    cache: "no-store",
    authToken,
  });
}

export async function getEscalation(caseId: string, authToken?: string | null): Promise<EscalationCase> {
  return apiRequest(`/api/v1/escalations/${caseId}`, {
    cache: "no-store",
    authToken,
  });
}

export async function listEscalationNotes(
  caseId: string,
  authToken?: string | null,
): Promise<EscalationNoteListResponse> {
  return apiRequest(`/api/v1/escalations/${caseId}/notes`, {
    cache: "no-store",
    authToken,
  });
}

export async function assignEscalation(
  caseId: string,
  payload: EscalationAssignRequest,
  authToken?: string | null,
): Promise<EscalationCase> {
  return apiRequest(`/api/v1/escalations/${caseId}/assign`, {
    method: "POST",
    body: JSON.stringify(payload),
    authToken,
  });
}

export async function updateEscalationStatus(
  caseId: string,
  payload: EscalationStatusUpdateRequest,
  authToken?: string | null,
): Promise<EscalationCase> {
  return apiRequest(`/api/v1/escalations/${caseId}/status`, {
    method: "POST",
    body: JSON.stringify(payload),
    authToken,
  });
}

export async function createEscalationNote(
  caseId: string,
  payload: EscalationNoteCreateRequest,
  authToken?: string | null,
): Promise<EscalationNote> {
  return apiRequest(`/api/v1/escalations/${caseId}/notes`, {
    method: "POST",
    body: JSON.stringify(payload),
    authToken,
  });
}

export interface TestEscalationPayload {
  customer_ref: string;
  message: string;
  severity: string;
}

export interface TestEscalationResult {
  caseId: string | null;
  caseStatus: string | null;
  escalated: boolean;
  answer: string;
}

function buildTestMessage(payload: TestEscalationPayload): string {
  const severityPrefix =
    payload.severity === "critical"
      ? "[CRITICAL] "
      : payload.severity === "high"
        ? "[URGENT] "
        : "";

  let msg = `${severityPrefix}${payload.message}`;

  if (payload.severity === "high" || payload.severity === "critical") {
    msg += "\n\nThis issue requires immediate attention and escalation to human review.";
  }

  return msg;
}

export async function triggerTestEscalation(
  payload: TestEscalationPayload,
): Promise<TestEscalationResult> {
  const response = await apiRequest<{
    escalation: boolean;
    escalation_case_id: string | null;
    escalation_status: string | null;
    conversation_id: string;
    answer: string;
  }>("/api/v1/chat", {
    method: "POST",
    skipAuth: true,
    body: JSON.stringify({
      user_id: payload.customer_ref || "admin-test",
      session_id:
        typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
          ? crypto.randomUUID()
          : Date.now().toString(36) + Math.random().toString(36).slice(2),
      message: buildTestMessage(payload),
      history: [],
      metadata: {
        source: "admin_test",
        severity: payload.severity,
      },
    }),
  });

  return {
    caseId: response.escalation_case_id,
    caseStatus: response.escalation_status,
    escalated: response.escalation,
    answer: response.answer,
  };
}
