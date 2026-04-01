export default function EscalationsLoading() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-16 text-slate-100">
      <div className="mx-auto max-w-7xl animate-pulse space-y-6">
        <div className="h-20 rounded-2xl bg-slate-900/80" />
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="h-36 rounded-2xl bg-slate-900/70" />
          <div className="h-36 rounded-2xl bg-slate-900/70" />
          <div className="h-36 rounded-2xl bg-slate-900/70" />
        </div>
        <div className="h-[28rem] rounded-2xl bg-slate-900/70" />
      </div>
    </main>
  );
}
