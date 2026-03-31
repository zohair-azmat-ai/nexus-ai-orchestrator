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
  return apiRequest(`/api/v1/escalations${buildQuery(Object.entries(options))}`, {
    cache: "no-store",
  });
}

export async function getEscalation(caseId: string): Promise<EscalationCase> {
  return apiRequest(`/api/v1/escalations/${caseId}`, {
    cache: "no-store",
  });
}

export async function listEscalationNotes(caseId: string): Promise<EscalationNoteListResponse> {
  return apiRequest(`/api/v1/escalations/${caseId}/notes`, {
    cache: "no-store",
  });
}

export async function assignEscalation(
  caseId: string,
  payload: EscalationAssignRequest,
): Promise<EscalationCase> {
  return apiRequest(`/api/v1/escalations/${caseId}/assign`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateEscalationStatus(
  caseId: string,
  payload: EscalationStatusUpdateRequest,
): Promise<EscalationCase> {
  return apiRequest(`/api/v1/escalations/${caseId}/status`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createEscalationNote(
  caseId: string,
  payload: EscalationNoteCreateRequest,
): Promise<EscalationNote> {
  return apiRequest(`/api/v1/escalations/${caseId}/notes`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
