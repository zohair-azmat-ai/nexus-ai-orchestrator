export const escalationStatuses = [
  "open",
  "in_review",
  "approved",
  "rejected",
  "resolved",
] as const;

export const escalationSeverities = [
  "low",
  "medium",
  "high",
  "critical",
] as const;

export const escalationNoteTypes = ["system", "agent", "human"] as const;

export type EscalationStatus = (typeof escalationStatuses)[number];
export type EscalationSeverity = (typeof escalationSeverities)[number];
export type EscalationNoteType = (typeof escalationNoteTypes)[number];

export interface EscalationCase {
  case_id: string;
  conversation_id: string;
  trace_id: string | null;
  user_id: string;
  escalation_reason: string;
  severity: string;
  status: EscalationStatus;
  assigned_to: string | null;
  latest_agent: string | null;
  latest_summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface EscalationCaseListResponse {
  cases: EscalationCase[];
  total: number;
}

export interface EscalationNote {
  note_id: string;
  case_id: string;
  author: string;
  note_type: EscalationNoteType;
  content: string;
  created_at: string;
}

export interface EscalationNoteListResponse {
  notes: EscalationNote[];
  total: number;
}

export interface EscalationAssignRequest {
  assigned_to: string;
  actor?: string;
  move_to_in_review?: boolean;
}

export interface EscalationStatusUpdateRequest {
  status: EscalationStatus;
  actor?: string;
}

export interface EscalationNoteCreateRequest {
  author: string;
  content: string;
  note_type: EscalationNoteType;
}
