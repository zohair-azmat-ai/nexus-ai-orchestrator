"use client";

import { useState } from "react";

import { reportIssue, type ReportIssueResult, type ReportPriority } from "@/lib/report";

export default function ReportIssueForm() {
  const [customerRef, setCustomerRef] = useState("");
  const [email, setEmail] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<ReportPriority>("normal");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReportIssueResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await reportIssue({ customerRef, email, title, description, priority });
      setResult(res);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Submission failed. Please try again.";
      setError(
        msg.includes("405") || msg.toLowerCase().includes("method not allowed")
          ? "Unable to reach the backend. Ensure NEXT_PUBLIC_API_BASE_URL is set correctly in your deployment."
          : msg,
      );
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setResult(null);
    setError(null);
    setCustomerRef("");
    setEmail("");
    setTitle("");
    setDescription("");
    setPriority("normal");
  }

  // ── Success state ────────────────────────────────────────────────────────────
  if (result) {
    return (
      <div className="rounded-2xl border border-emerald-500/20 bg-emerald-950/30 p-8 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/10">
          <svg className="h-7 w-7 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <h2 className="mb-1 text-xl font-semibold text-white">Issue submitted</h2>
        <p className="mb-6 text-sm text-slate-400">
          Your report has been received and processed by the AI orchestration system.
        </p>

        <div className="mx-auto mb-6 max-w-sm space-y-2 rounded-xl border border-white/5 bg-slate-900/60 p-4 text-left text-sm">
          <div className="flex justify-between gap-4">
            <span className="text-slate-500">Conversation</span>
            <span className="font-mono text-slate-300 break-all">{result.conversationId}</span>
          </div>
          {result.escalated && result.caseId && (
            <>
              <div className="my-2 border-t border-white/5" />
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Case ID</span>
                <span className="font-mono text-cyan-400 break-all">{result.caseId}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">Status</span>
                <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-400 capitalize">
                  {result.caseStatus ?? "open"}
                </span>
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Your issue has been flagged for human review and is now visible in the reviewer queue.
              </p>
            </>
          )}
        </div>

        {result.answer && (
          <div className="mx-auto mb-6 max-w-sm rounded-xl border border-white/5 bg-slate-900/60 p-4 text-left">
            <p className="mb-1 text-xs font-medium uppercase tracking-widest text-slate-500">AI Response</p>
            <p className="text-sm text-slate-300">{result.answer}</p>
          </div>
        )}

        <button
          type="button"
          onClick={handleReset}
          className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-5 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-white/5"
        >
          Submit another issue
        </button>
      </div>
    );
  }

  // ── Form ─────────────────────────────────────────────────────────────────────
  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <label className="block text-sm text-slate-300">
          Your name or customer ID
          <input
            required
            value={customerRef}
            onChange={(e) => setCustomerRef(e.target.value)}
            placeholder="e.g. john-doe or CUS-001"
            className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
          />
        </label>

        <label className="block text-sm text-slate-300">
          Email <span className="text-slate-500">(optional)</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
          />
        </label>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <label className="block text-sm text-slate-300">
          Issue title
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Brief summary of the problem"
            className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
          />
        </label>

        <label className="block text-sm text-slate-300">
          Priority
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as ReportPriority)}
            className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400/60"
          >
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
            <option value="critical">Critical</option>
          </select>
        </label>
      </div>

      <label className="block text-sm text-slate-300">
        Describe the issue
        <textarea
          required
          rows={5}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Please describe the issue in detail. Include steps to reproduce, what you expected, and what actually happened."
          className="mt-2 w-full resize-none rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
        />
      </label>

      {(priority === "urgent" || priority === "critical") && (
        <p className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-2.5 text-sm text-amber-400">
          Issues marked as <strong>{priority}</strong> are automatically routed for human review.
        </p>
      )}

      {error && (
        <p className="rounded-xl border border-red-500/20 bg-red-950/30 px-4 py-2.5 text-sm text-red-400">
          {error}
        </p>
      )}

      <div className="flex items-center justify-between pt-1">
        <p className="text-xs text-slate-600">
          Submissions are processed by the Nexus AI orchestration pipeline.
        </p>
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-violet-500 disabled:opacity-50"
        >
          {loading ? (
            <>
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Submitting…
            </>
          ) : (
            "Submit Report"
          )}
        </button>
      </div>
    </form>
  );
}
