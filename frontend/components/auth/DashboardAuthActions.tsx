"use client";

import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import type { AuthUser } from "@/types/auth";

interface DashboardAuthActionsProps {
  currentUser: AuthUser;
}

export default function DashboardAuthActions({ currentUser }: DashboardAuthActionsProps) {
  const router = useRouter();
  const { logout } = useAuth();

  return (
    <div className="flex items-center gap-3">
      <div className="hidden rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-2 text-right md:block">
        <p className="text-sm font-medium text-white">{currentUser.full_name}</p>
        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{currentUser.role}</p>
      </div>
      <button
        type="button"
        onClick={() => {
          logout();
          router.push("/login");
          router.refresh();
        }}
        className="inline-flex items-center rounded-xl border border-white/10 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/5"
      >
        Logout
      </button>
    </div>
  );
}
