import Link from "next/link";

import Navbar from "@/components/Navbar";
import ReportIssueForm from "@/components/report/ReportIssueForm";

export const metadata = {
  title: "Report an Issue — Nexus AI",
  description: "Submit a support request or issue report. Our AI orchestration system will process your request and escalate urgent cases to human review.",
};

export default function ReportPage() {
  return (
    <main className="min-h-screen bg-gray-950">
      <Navbar />

      <div className="mx-auto max-w-2xl px-6 py-16">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/"
            className="mb-6 inline-flex items-center gap-1.5 text-sm text-slate-500 transition hover:text-slate-300"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Back to home
          </Link>

          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs font-medium uppercase tracking-widest text-violet-400">
            Customer Support
          </div>

          <h1 className="mt-3 text-3xl font-bold text-white">Report an Issue</h1>
          <p className="mt-2 text-slate-400">
            Describe your problem below. Our AI system will process your report immediately.
            Urgent and critical issues are automatically routed to human review.
          </p>
        </div>

        {/* Form card */}
        <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-6 sm:p-8">
          <ReportIssueForm />
        </div>

        {/* Footer note */}
        <p className="mt-6 text-center text-xs text-slate-600">
          Powered by{" "}
          <span className="text-slate-500">Nexus AI</span>
          {" "}— Multi-Agent RAG Orchestration Platform
        </p>
      </div>
    </main>
  );
}
