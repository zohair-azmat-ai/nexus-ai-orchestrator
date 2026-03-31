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
