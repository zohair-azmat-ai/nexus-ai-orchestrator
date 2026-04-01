import { apiRequest } from "@/lib/api";
import type { TraceSummary } from "@/types/observability";

export async function getTraceSummary(traceId: string, authToken?: string | null): Promise<TraceSummary> {
  return apiRequest(`/api/v1/observability/trace/${traceId}`, {
    cache: "no-store",
    authToken,
  });
}
