import LoginForm from "@/components/auth/LoginForm";

interface LoginPageProps {
  searchParams?: {
    next?: string;
  };
}

export default function LoginPage({ searchParams }: LoginPageProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,#14304d_0%,#08101d_35%,#020617_100%)] px-6 py-16 text-slate-100">
      <LoginForm nextPath={searchParams?.next} />
    </main>
  );
}
