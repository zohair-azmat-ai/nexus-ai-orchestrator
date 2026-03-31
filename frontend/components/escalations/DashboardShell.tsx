import Link from "next/link";
import type { ReactNode } from "react";

interface DashboardShellProps {
  title: string;
  eyebrow: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
}

export default function DashboardShell({
  title,
  eyebrow,
  description,
  actions,
  children,
}: DashboardShellProps) {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#14304d_0%,#08101d_35%,#020617_100%)] text-slate-100">
      <div className="border-b border-white/10 bg-slate-950/70 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div className="space-y-1">
            <Link
              href="/"
              className="text-sm font-medium text-cyan-300 transition hover:text-cyan-200"
            >
              Nexus AI
            </Link>
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{eyebrow}</p>
              <h1 className="mt-2 text-2xl font-semibold text-white">{title}</h1>
              <p className="mt-2 max-w-2xl text-sm text-slate-400">{description}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">{actions}</div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 py-8">{children}</div>
    </main>
  );
}
