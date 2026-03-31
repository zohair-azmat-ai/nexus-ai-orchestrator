export interface TraceEvent {
  trace_id?: string;
  event_type?: string;
  stage?: string;
  component?: string;
  status?: string;
  latency_ms?: number;
  timestamp?: string;
  message?: string;
  details?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface TraceSummary {
  trace_id: string;
  events: TraceEvent[];
  stage_timings: Record<string, number>;
  agent_used: string;
  tools_used: string[];
}
