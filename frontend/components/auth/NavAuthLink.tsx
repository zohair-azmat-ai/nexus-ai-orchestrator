"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";

export default function NavAuthLink() {
  const router = useRouter();
  const { user, logout, isLoading } = useAuth();

  if (isLoading) {
    return <span className="text-gray-500">Auth</span>;
  }

  if (!user) {
    return (
      <Link href="/login" className="hover:text-white transition-colors">
        Login
      </Link>
    );
  }

  return (
    <button
      type="button"
      onClick={() => {
        logout();
        router.push("/login");
        router.refresh();
      }}
      className="hover:text-white transition-colors"
    >
      Logout
    </button>
  );
}
