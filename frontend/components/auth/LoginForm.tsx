"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { login } from "@/lib/auth";

export default function LoginForm({ nextPath }: { nextPath?: string }) {
  const router = useRouter();
  const { setSession } = useAuth();
  const [email, setEmail] = useState("reviewer@nexus.local");
  const [password, setPassword] = useState("ReviewerPass123!");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await login({ email, password });
      setSession(response);

      if (response.user.role === "reviewer" || response.user.role === "admin") {
        router.push(nextPath || "/escalations");
      } else {
        router.push("/");
      }
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="w-full max-w-md rounded-3xl border border-white/10 bg-slate-950/80 p-8 shadow-2xl shadow-slate-950/30">
      <div>
        <p className="text-xs uppercase tracking-[0.22em] text-cyan-300">Authentication</p>
        <h1 className="mt-3 text-3xl font-semibold text-white">Reviewer login</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Sign in with a reviewer or admin account to access the escalation queue and protected review actions.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4">
        <label className="block text-sm text-slate-300">
          Email
          <input
            required
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400/60"
          />
        </label>

        <label className="block text-sm text-slate-300">
          Password
          <input
            required
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400/60"
          />
        </label>

        {error ? <p className="text-sm text-rose-300">{error}</p> : null}

        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex w-full items-center justify-center rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-cyan-500/60"
        >
          {isSubmitting ? "Signing in..." : "Sign in"}
        </button>
      </form>

      <div className="mt-6 rounded-2xl border border-white/10 bg-slate-900/70 p-4 text-sm text-slate-400">
        <p className="font-medium text-slate-200">Local development accounts</p>
        <p className="mt-2">Reviewer: `reviewer@nexus.local` / `ReviewerPass123!`</p>
        <p className="mt-1">Admin: `admin@nexus.local` / `AdminPass123!`</p>
      </div>

      <div className="mt-6 text-sm text-slate-500">
        <Link href="/" className="transition hover:text-slate-300">
          Back to home
        </Link>
      </div>
    </div>
  );
}
