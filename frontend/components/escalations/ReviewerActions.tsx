"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import StatusBadge from "@/components/escalations/StatusBadge";
import { assignEscalation, updateEscalationStatus } from "@/lib/escalations";
import type { AuthUser } from "@/types/auth";
import type { EscalationCase, EscalationStatus } from "@/types/escalations";

const statuses: EscalationStatus[] = [
  "open",
  "in_review",
  "approved",
  "rejected",
  "resolved",
];

interface ReviewerActionsProps {
  escalationCase: EscalationCase;
  authToken: string;
  currentUser: AuthUser;
  onCaseUpdated: (nextCase: EscalationCase) => void;
}

export default function ReviewerActions({
  escalationCase,
  authToken,
  currentUser,
  onCaseUpdated,
}: ReviewerActionsProps) {
  const router = useRouter();
  const [assignedTo, setAssignedTo] = useState(escalationCase.assigned_to ?? "");
  const [assignActor, setAssignActor] = useState(currentUser.full_name || currentUser.email);
  const [status, setStatus] = useState<EscalationStatus>(escalationCase.status);
  const [statusActor, setStatusActor] = useState(currentUser.full_name || currentUser.email);
  const [isRefreshing, startRefresh] = useTransition();
  const [assignError, setAssignError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [isAssigning, setIsAssigning] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  useEffect(() => {
    setAssignedTo(escalationCase.assigned_to ?? "");
    setStatus(escalationCase.status);
  }, [escalationCase.assigned_to, escalationCase.status]);

  useEffect(() => {
    setAssignActor(currentUser.full_name || currentUser.email);
    setStatusActor(currentUser.full_name || currentUser.email);
  }, [currentUser.email, currentUser.full_name]);

  async function handleAssign(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAssignError(null);
    setIsAssigning(true);

    try {
      const nextCase = await assignEscalation(escalationCase.case_id, {
        assigned_to: assignedTo,
        actor: assignActor || undefined,
        move_to_in_review: true,
      }, authToken);
      onCaseUpdated(nextCase);
      setStatus(nextCase.status);
      setAssignError(null);
      startRefresh(() => {
        router.refresh();
      });
    } catch (error) {
      setAssignError(error instanceof Error ? error.message : "Unable to assign case.");
    } finally {
      setIsAssigning(false);
    }
  }

  async function handleStatusUpdate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatusError(null);
    setIsUpdatingStatus(true);

    try {
      const nextCase = await updateEscalationStatus(escalationCase.case_id, {
        status,
        actor: statusActor || undefined,
      }, authToken);
      onCaseUpdated(nextCase);
      setStatusError(null);
      startRefresh(() => {
        router.refresh();
      });
    } catch (error) {
      setStatusError(error instanceof Error ? error.message : "Unable to update status.");
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/70 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-cyan-300">Reviewer Actions</p>
          <h2 className="mt-2 text-lg font-semibold text-white">Assignment and status</h2>
        </div>
        <StatusBadge tone="status" value={escalationCase.status} />
      </div>

      <div className="mt-5 space-y-5">
        <form onSubmit={handleAssign} className="space-y-4 rounded-2xl border border-white/10 bg-slate-900/70 p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm text-slate-300">
              Assign to
              <input
                required
                value={assignedTo}
                onChange={(event) => setAssignedTo(event.target.value)}
                placeholder="reviewer-name"
                className="mt-2 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
              />
            </label>

            <label className="text-sm text-slate-300">
              Actor
              <input
                value={assignActor}
                onChange={(event) => setAssignActor(event.target.value)}
                placeholder="team-lead"
                className="mt-2 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
              />
            </label>
          </div>

          {assignError ? <p className="text-sm text-rose-300">{assignError}</p> : null}
          {isRefreshing ? <p className="text-sm text-slate-400">Refreshing case data...</p> : null}

          <button
            type="submit"
            disabled={isAssigning}
            className="inline-flex items-center rounded-xl bg-white px-4 py-2.5 text-sm font-medium text-slate-950 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:bg-white/70"
          >
            {isAssigning ? "Assigning..." : "Assign case"}
          </button>
        </form>

        <form
          onSubmit={handleStatusUpdate}
          className="space-y-4 rounded-2xl border border-white/10 bg-slate-900/70 p-4"
        >
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm text-slate-300">
              Status
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value as EscalationStatus)}
                className="mt-2 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400/60"
              >
                {statuses.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm text-slate-300">
              Actor
              <input
                value={statusActor}
                onChange={(event) => setStatusActor(event.target.value)}
                placeholder="reviewer-name"
                className="mt-2 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
              />
            </label>
          </div>

          {statusError ? <p className="text-sm text-rose-300">{statusError}</p> : null}
          {isRefreshing ? <p className="text-sm text-slate-400">Refreshing case data...</p> : null}

          <button
            type="submit"
            disabled={isUpdatingStatus}
            className="inline-flex items-center rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-800/70"
          >
            {isUpdatingStatus ? "Updating status..." : "Update status"}
          </button>
        </form>
      </div>
    </section>
  );
}
