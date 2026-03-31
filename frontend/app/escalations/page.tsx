import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import AccessDenied from "@/components/auth/AccessDenied";
import DashboardAuthActions from "@/components/auth/DashboardAuthActions";
import BackendUnavailable from "@/components/escalations/BackendUnavailable";
import DashboardShell from "@/components/escalations/DashboardShell";
import EscalationQueue from "@/components/escalations/EscalationQueue";
import { getCurrentUser } from "@/lib/auth";
import { AUTH_TOKEN_COOKIE } from "@/lib/auth-storage";
import { ApiError } from "@/lib/api";
import { listEscalations } from "@/lib/escalations";

interface EscalationsPageProps {
  searchParams?: {
    status?: string;
    severity?: string;
    assigned_to?: string;
    search?: string;
  };
}

export default async function EscalationsPage({ searchParams }: EscalationsPageProps) {
  const authToken = cookies().get(AUTH_TOKEN_COOKIE)?.value;
  if (!authToken) {
    redirect("/login?next=/escalations");
  }

  let currentUser;
  try {
    currentUser = await getCurrentUser(authToken);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      redirect("/login?next=/escalations");
    }
    throw error;
  }

  const status = searchParams?.status ?? "";
  const severity = searchParams?.severity ?? "";
  const assignedTo = searchParams?.assigned_to ?? "";
  const search = searchParams?.search ?? "";

  let response;
  let integrationError: string | null = null;

  try {
    response = await listEscalations({
      limit: 100,
      status: status || undefined,
      severity: severity || undefined,
      assigned_to: assignedTo || undefined,
      authToken,
    });
  } catch (error) {
    integrationError =
      error instanceof Error ? error.message : "Unable to load escalation cases.";
  }

  return (
    <DashboardShell
      eyebrow="Human In The Loop"
      title="Escalation Queue"
      description="Review escalated cases, focus the queue with backend filters, and drill directly into the reviewer workflow."
      actions={<DashboardAuthActions currentUser={currentUser} />}
    >
      {currentUser.role !== "reviewer" && currentUser.role !== "admin" ? (
        <AccessDenied message="Reviewer or admin access is required to view escalation cases." />
      ) : (
        <>
      <section className="mb-5 rounded-2xl border border-white/10 bg-slate-950/60 p-5">
        <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <label className="text-sm text-slate-300">
            Status
            <select
              name="status"
              defaultValue={status}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400/60"
            >
              <option value="">All statuses</option>
              <option value="open">Open</option>
              <option value="in_review">In review</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="resolved">Resolved</option>
            </select>
          </label>

          <label className="text-sm text-slate-300">
            Severity
            <select
              name="severity"
              defaultValue={severity}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400/60"
            >
              <option value="">All severities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </label>

          <label className="text-sm text-slate-300">
            Assigned to
            <input
              name="assigned_to"
              defaultValue={assignedTo}
              placeholder="reviewer-name"
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
            />
          </label>

          <label className="text-sm text-slate-300">
            Search
            <input
              name="search"
              defaultValue={search}
              placeholder="case_id or user_id"
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
            />
          </label>

          <div className="flex items-end gap-3">
            <button
              type="submit"
              className="inline-flex h-[46px] items-center justify-center rounded-xl bg-cyan-500 px-4 text-sm font-medium text-slate-950 transition hover:bg-cyan-400"
            >
              Apply filters
            </button>
            <Link
              href="/escalations"
              className="inline-flex h-[46px] items-center justify-center rounded-xl border border-white/10 px-4 text-sm font-medium text-slate-300 transition hover:bg-white/5"
            >
              Reset
            </Link>
          </div>
        </form>
      </section>

      {integrationError ? (
        <BackendUnavailable
          title="Escalation queue unavailable"
          message={`${integrationError} Start the backend and confirm the API base URL before opening the review queue.`}
        />
      ) : response && response.cases.length > 0 ? (
        <EscalationQueue cases={response.cases} total={response.total} initialSearch={search} />
      ) : (
        <section className="rounded-2xl border border-dashed border-white/10 bg-slate-950/60 p-12 text-center">
          <p className="text-lg font-medium text-white">No escalation cases found</p>
          <p className="mt-2 text-sm text-slate-400">
            Try clearing one of the filters or create a new escalation through the existing workflow.
          </p>
        </section>
      )}
        </>
      )}
    </DashboardShell>
  );
}
