interface BackendUnavailableProps {
  title?: string;
  message: string;
}

export default function BackendUnavailable({
  title = "Backend unavailable",
  message,
}: BackendUnavailableProps) {
  return (
    <section className="rounded-2xl border border-rose-400/20 bg-rose-950/20 p-8">
      <p className="text-xs uppercase tracking-[0.22em] text-rose-300">Integration</p>
      <h2 className="mt-2 text-xl font-semibold text-white">{title}</h2>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">{message}</p>
    </section>
  );
}
