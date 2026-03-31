import { notFound } from "next/navigation";

import CaseDetailClient from "@/components/escalations/CaseDetailClient";
import DashboardShell from "@/components/escalations/DashboardShell";
import { getEscalation, listEscalationNotes } from "@/lib/escalations";
import { getTraceSummary } from "@/lib/observability";

interface EscalationCasePageProps {
  params: {
    caseId: string;
  };
}

export default async function EscalationCasePage({ params }: EscalationCasePageProps) {
  let escalationCase;

  try {
    escalationCase = await getEscalation(params.caseId);
  } catch (error) {
    if (error instanceof Error && error.message.toLowerCase().includes("not found")) {
      notFound();
    }
    throw error;
  }

  const notesPromise = listEscalationNotes(params.caseId);
  const tracePromise = escalationCase.trace_id
    ? getTraceSummary(escalationCase.trace_id)
        .then((value) => ({ trace: value, unavailableReason: undefined }))
        .catch((error: Error) => ({
          trace: null,
          unavailableReason: error.message || "Trace unavailable.",
        }))
    : Promise.resolve({
        trace: null,
        unavailableReason: "This escalation case does not have an associated trace.",
      });

  const [notesResponse, traceResult] = await Promise.all([notesPromise, tracePromise]);

  return (
    <DashboardShell
      eyebrow="Human In The Loop"
      title="Escalation Case"
      description="Inspect the escalation context, capture reviewer notes, update ownership, and review the execution trace."
    >
      <CaseDetailClient
        initialCase={escalationCase}
        initialNotes={notesResponse.notes}
        trace={traceResult.trace}
        traceUnavailableReason={traceResult.unavailableReason}
      />
    </DashboardShell>
  );
}
