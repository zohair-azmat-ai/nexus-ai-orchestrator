"use client";

import Link from "next/link";
import { useState } from "react";

import NotesPanel from "@/components/escalations/NotesPanel";
import ReviewerActions from "@/components/escalations/ReviewerActions";
import StatusBadge from "@/components/escalations/StatusBadge";
import TraceSnapshot from "@/components/escalations/TraceSnapshot";
import { formatDateTime } from "@/components/escalations/utils";
import type { EscalationCase, EscalationNote } from "@/types/escalations";
import type { TraceSummary } from "@/types/observability";

interface CaseDetailClientProps {
  initialCase: EscalationCase;
  initialNotes: EscalationNote[];
  trace: TraceSummary | null;
  traceUnavailableReason?: string;
}

export default function CaseDetailClient({
  initialCase,
  initialNotes,
  trace,
  traceUnavailableReason,
}: CaseDetailClientProps) {
  const [escalationCase, setEscalationCase] = useState(initialCase);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link href="/escalations" className="text-sm text-cyan-300 transition hover:text-cyan-200">
              Back to queue
            </Link>
            <h2 className="mt-3 text-2xl font-semibold text-white">{escalationCase.case_id}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
              {escalationCase.latest_summary ?? escalationCase.escalation_reason}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <StatusBadge tone="status" value={escalationCase.status} />
            <StatusBadge tone="severity" value={escalationCase.severity} />
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-white/8 bg-slate-900/75 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Trace</p>
            <p className="mt-2 text-sm text-white">{escalationCase.trace_id ?? "Unavailable"}</p>
            <p className="mt-1 text-sm text-slate-400">Conversation {escalationCase.conversation_id}</p>
          </div>

          <div className="rounded-2xl border border-white/8 bg-slate-900/75 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Owner</p>
            <p className="mt-2 text-sm text-white">{escalationCase.assigned_to ?? "Unassigned"}</p>
            <p className="mt-1 text-sm text-slate-400">User {escalationCase.user_id}</p>
          </div>

          <div className="rounded-2xl border border-white/8 bg-slate-900/75 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Agent</p>
            <p className="mt-2 text-sm text-white">{escalationCase.latest_agent ?? "Unknown"}</p>
            <p className="mt-1 text-sm text-slate-400">Reason {escalationCase.escalation_reason}</p>
          </div>

          <div className="rounded-2xl border border-white/8 bg-slate-900/75 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Timestamps</p>
            <p className="mt-2 text-sm text-white">{formatDateTime(escalationCase.created_at)}</p>
            <p className="mt-1 text-sm text-slate-400">Updated {formatDateTime(escalationCase.updated_at)}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-6">
          <NotesPanel escalationCase={escalationCase} initialNotes={initialNotes} />
        </div>

        <div className="space-y-6">
          <ReviewerActions escalationCase={escalationCase} onCaseUpdated={setEscalationCase} />
          <TraceSnapshot trace={trace} unavailableReason={traceUnavailableReason} />
        </div>
      </div>
    </div>
  );
}
