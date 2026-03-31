import { formatDateTime, titleize } from "@/components/escalations/utils";
import type { TraceSummary } from "@/types/observability";

interface TraceSnapshotProps {
  trace: TraceSummary | null;
  unavailableReason?: string;
}

export default function TraceSnapshot({
  trace,
  unavailableReason = "Trace data is unavailable for this case.",
}: TraceSnapshotProps) {
  if (!trace) {
    return (
      <section className="rounded-2xl border border-white/10 bg-slate-950/70 p-5">
        <p className="text-xs uppercase tracking-[0.22em] text-cyan-300">Trace Snapshot</p>
        <div className="mt-4 rounded-2xl border border-dashed border-white/10 bg-slate-900/60 p-6 text-sm text-slate-400">
          {unavailableReason}
        </div>
      </section>
    );
  }

  const recentEvents = trace.events
    .filter((event) => Boolean(event.event_type || event.message || event.component))
    .slice(-6)
    .reverse();
  const executionSummary = [
    trace.agent_used ? `Agent: ${trace.agent_used}` : null,
    trace.tools_used.length ? `Tools: ${trace.tools_used.join(", ")}` : null,
  ]
    .filter(Boolean)
    .join(" | ");

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/70 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-cyan-300">Trace Snapshot</p>
          <h2 className="mt-2 text-lg font-semibold text-white">{trace.trace_id}</h2>
          <p className="mt-2 text-sm text-slate-400">
            {executionSummary || "Recent execution activity for this escalation trace."}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="rounded-2xl border border-white/8 bg-slate-900/75 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Stage Timings</p>
          <div className="mt-4 space-y-3">
            {Object.keys(trace.stage_timings).length > 0 ? (
              Object.entries(trace.stage_timings).map(([stage, value]) => (
                <div
                  key={stage}
                  className="flex items-center justify-between rounded-xl bg-slate-950/80 px-3 py-2.5"
                >
                  <span className="text-sm text-slate-300">{titleize(stage)}</span>
                  <span className="text-sm font-medium text-white">{value} ms</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-400">Stage timings were not recorded for this trace.</p>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-white/8 bg-slate-900/75 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Recent Events</p>
          <div className="mt-4 space-y-3">
            {recentEvents.length > 0 ? (
              recentEvents.map((event, index) => (
                <article
                  key={`${event.event_type ?? "event"}-${index}`}
                  className="rounded-xl bg-slate-950/80 p-3"
                >
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span>{event.event_type ?? "event"}</span>
                    <span>{titleize(String(event.stage ?? "unknown"))}</span>
                    <span>{formatDateTime(event.timestamp ? String(event.timestamp) : undefined)}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-200">
                    {String(event.component ?? "system")} | {String(event.status ?? "recorded")}
                  </p>
                  {typeof event.message === "string" ? (
                    <p className="mt-1 text-sm text-slate-400">{event.message}</p>
                  ) : null}
                </article>
              ))
            ) : (
              <p className="text-sm text-slate-400">No recent events were available for this trace.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
