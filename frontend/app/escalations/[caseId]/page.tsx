import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { redirect } from "next/navigation";

import AccessDenied from "@/components/auth/AccessDenied";
import DashboardAuthActions from "@/components/auth/DashboardAuthActions";
import BackendUnavailable from "@/components/escalations/BackendUnavailable";
import CaseDetailClient from "@/components/escalations/CaseDetailClient";
import DashboardShell from "@/components/escalations/DashboardShell";
import { getCurrentUser } from "@/lib/auth";
import { AUTH_TOKEN_COOKIE } from "@/lib/auth-storage";
import { ApiError } from "@/lib/api";
import { getEscalation, listEscalationNotes } from "@/lib/escalations";
import { getTraceSummary } from "@/lib/observability";

interface EscalationCasePageProps {
  params: {
    caseId: string;
  };
}

export default async function EscalationCasePage({ params }: EscalationCasePageProps) {
  const authToken = cookies().get(AUTH_TOKEN_COOKIE)?.value;
  if (!authToken) {
    redirect(`/login?next=/escalations/${params.caseId}`);
  }

  let currentUser;
  try {
    currentUser = await getCurrentUser(authToken);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      redirect(`/login?next=/escalations/${params.caseId}`);
    }
    throw error;
  }

  if (currentUser.role !== "reviewer" && currentUser.role !== "admin") {
    return (
      <DashboardShell
        eyebrow="Human In The Loop"
        title="Escalation Case"
        description="Inspect the escalation context, capture reviewer notes, update ownership, and review the execution trace."
        actions={<DashboardAuthActions currentUser={currentUser} />}
      >
        <AccessDenied message="Reviewer or admin access is required to inspect escalation cases." />
      </DashboardShell>
    );
  }

  let escalationCase;

  try {
    escalationCase = await getEscalation(params.caseId, authToken);
  } catch (error) {
    if (error instanceof Error && error.message.toLowerCase().includes("not found")) {
      notFound();
    }

    return (
      <DashboardShell
        eyebrow="Human In The Loop"
        title="Escalation Case"
        description="Inspect the escalation context, capture reviewer notes, update ownership, and review the execution trace."
      >
        <BackendUnavailable
          title="Escalation case unavailable"
          message={
            error instanceof Error
              ? `${error.message} Start the backend and verify the case API is reachable.`
              : "Unable to load the escalation case."
          }
        />
      </DashboardShell>
    );
  }

  const notesPromise = listEscalationNotes(params.caseId, authToken)
    .then((value) => ({ notes: value.notes, unavailableReason: undefined }))
    .catch((error: Error) => ({
      notes: [],
      unavailableReason: error.message || "Notes unavailable.",
    }));
  const tracePromise = escalationCase.trace_id
    ? getTraceSummary(escalationCase.trace_id, authToken)
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
      actions={<DashboardAuthActions currentUser={currentUser} />}
    >
      <CaseDetailClient
        initialCase={escalationCase}
        initialNotes={notesResponse.notes}
        notesUnavailableReason={notesResponse.unavailableReason}
        authToken={authToken}
        currentUser={currentUser}
        trace={traceResult.trace}
        traceUnavailableReason={traceResult.unavailableReason}
      />
    </DashboardShell>
  );
}
