"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { triggerTestEscalation } from "@/lib/escalations";
import type { EscalationSeverity } from "@/types/escalations";

type TestResult =
  | { ok: true; caseId: string | null; caseStatus: string | null; escalated: boolean }
  | { ok: false; error: string };

export default function TestEscalationPanel() {
  const router = useRouter();

  const [customerRef, setCustomerRef] = useState("");
  const [message, setMessage] = useState("");
  const [severity, setSeverity] = useState<EscalationSeverity>("medium");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      const res = await triggerTestEscalation({ customer_ref: customerRef, message, severity });
      setResult({ ok: true, caseId: res.caseId, caseStatus: res.caseStatus, escalated: res.escalated });
      if (res.escalated) {
        router.refresh();
      }
    } catch (err) {
      setResult({ ok: false, error: err instanceof Error ? err.message : "Request failed" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-2xl border border-dashed border-white/10 bg-slate-950/60 p-5">
      <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-slate-500">
        Admin — Test Escalation Generator
      </p>

      <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label className="text-sm text-slate-300">
          Customer ref
          <input
            required
            value={customerRef}
            onChange={(e) => setCustomerRef(e.target.value)}
            placeholder="user-123"
            className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
          />
        </label>

        <label className="text-sm text-slate-300">
          Severity
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value as EscalationSeverity)}
            className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400/60"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </label>

        <div className="flex items-end xl:col-span-2">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex h-[46px] w-full items-center justify-center rounded-xl bg-violet-600 px-4 text-sm font-medium text-white transition hover:bg-violet-500 disabled:opacity-50"
          >
            {loading ? "Triggering…" : "Trigger Test Escalation"}
          </button>
        </div>

        <label className="text-sm text-slate-300 md:col-span-2 xl:col-span-4">
          Escalation reason
          <textarea
            required
            rows={2}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Describe the issue that should trigger this escalation…"
            className="mt-2 w-full resize-none rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
          />
        </label>
      </form>

      {result && (
        <div
          className={`mt-3 rounded-xl px-4 py-3 text-sm ${
            result.ok
              ? result.escalated
                ? "bg-emerald-950/60 text-emerald-400"
                : "bg-amber-950/60 text-amber-400"
              : "bg-red-950/60 text-red-400"
          }`}
        >
          {result.ok ? (
            result.escalated ? (
              <span>
                ✓ Escalated — Case <span className="font-mono">{result.caseId}</span>
                {result.caseStatus && (
                  <span className="ml-2 rounded-full bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-400 capitalize">
                    {result.caseStatus}
                  </span>
                )}
              </span>
            ) : (
              <span>⚠ Pipeline ran but no escalation was triggered — try a higher severity or add urgency keywords to the message.</span>
            )
          ) : (
            <span>✗ {result.error}</span>
          )}
        </div>
      )}
    </section>
  );
}
