import { titleize } from "@/components/escalations/utils";

const statusClasses: Record<string, string> = {
  open: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  in_review: "border-sky-400/30 bg-sky-400/10 text-sky-200",
  approved: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  rejected: "border-rose-400/30 bg-rose-400/10 text-rose-200",
  resolved: "border-slate-400/30 bg-slate-300/10 text-slate-200",
};

const severityClasses: Record<string, string> = {
  low: "border-slate-500/30 bg-slate-400/10 text-slate-200",
  medium: "border-cyan-500/30 bg-cyan-500/10 text-cyan-200",
  high: "border-orange-500/30 bg-orange-500/10 text-orange-200",
  critical: "border-rose-500/30 bg-rose-500/10 text-rose-200",
};

interface StatusBadgeProps {
  tone: "status" | "severity";
  value: string;
}

export default function StatusBadge({ tone, value }: StatusBadgeProps) {
  const palette = tone === "status" ? statusClasses : severityClasses;

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${palette[value] ?? "border-slate-600/40 bg-slate-800/70 text-slate-200"}`}
    >
      {titleize(value)}
    </span>
  );
}
