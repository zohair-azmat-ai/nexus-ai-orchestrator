"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import StatusBadge from "@/components/escalations/StatusBadge";
import { formatDateTime } from "@/components/escalations/utils";
import type { EscalationCase } from "@/types/escalations";

interface EscalationQueueProps {
  cases: EscalationCase[];
  total: number;
  initialSearch?: string;
}

export default function EscalationQueue({
  cases,
  total,
  initialSearch = "",
}: EscalationQueueProps) {
  const [search, setSearch] = useState(initialSearch);

  const filteredCases = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) {
      return cases;
    }

    return cases.filter((item) => {
      return (
        item.case_id.toLowerCase().includes(term) ||
        item.user_id.toLowerCase().includes(term)
      );
    });
  }, [cases, search]);

  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-[1.4fr_0.8fr_0.8fr]">
        <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-5 shadow-2xl shadow-slate-950/20">
          <p className="text-xs uppercase tracking-[0.22em] text-cyan-300">Queue Overview</p>
          <div className="mt-4 flex flex-wrap items-end gap-6">
            <div>
              <p className="text-3xl font-semibold text-white">{filteredCases.length}</p>
              <p className="mt-1 text-sm text-slate-400">Visible cases</p>
            </div>
            <div>
              <p className="text-3xl font-semibold text-white">{total}</p>
              <p className="mt-1 text-sm text-slate-400">Fetched from backend</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-5">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Search</p>
          <label className="mt-3 block text-sm text-slate-300">
            Case or user
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search case_id or user_id"
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none ring-0 transition placeholder:text-slate-500 focus:border-cyan-400/60"
            />
          </label>
        </div>

        <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-5">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Workflow</p>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            Filter on the server, narrow locally by ID, and jump straight into case review.
          </p>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-950/70">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-white/10 text-sm">
            <thead className="bg-slate-900/80 text-left text-xs uppercase tracking-[0.18em] text-slate-500">
              <tr>
                <th className="px-4 py-3">Case</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Severity</th>
                <th className="px-4 py-3">Reason</th>
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">Assigned</th>
                <th className="px-4 py-3">Agent</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredCases.length > 0 ? (
                filteredCases.map((item) => (
                  <tr key={item.case_id} className="group transition hover:bg-white/[0.03]">
                    <td className="px-4 py-4 align-top">
                      <Link
                        href={`/escalations/${item.case_id}`}
                        className="font-medium text-white transition group-hover:text-cyan-200"
                      >
                        {item.case_id}
                      </Link>
                    </td>
                    <td className="px-4 py-4 align-top">
                      <StatusBadge tone="status" value={item.status} />
                    </td>
                    <td className="px-4 py-4 align-top">
                      <StatusBadge tone="severity" value={item.severity} />
                    </td>
                    <td className="max-w-xs px-4 py-4 align-top text-slate-300">
                      <p className="line-clamp-2">{item.escalation_reason}</p>
                    </td>
                    <td className="px-4 py-4 align-top text-slate-300">{item.user_id}</td>
                    <td className="px-4 py-4 align-top text-slate-300">
                      {item.assigned_to ?? "Unassigned"}
                    </td>
                    <td className="px-4 py-4 align-top text-slate-300">
                      {item.latest_agent ?? "Unknown"}
                    </td>
                    <td className="px-4 py-4 align-top text-slate-400">
                      {formatDateTime(item.created_at)}
                    </td>
                    <td className="px-4 py-4 align-top text-slate-400">
                      {formatDateTime(item.updated_at)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={9} className="px-4 py-16 text-center text-slate-400">
                    No escalation cases match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
