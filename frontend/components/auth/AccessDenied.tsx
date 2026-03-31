interface AccessDeniedProps {
  message: string;
}

export default function AccessDenied({ message }: AccessDeniedProps) {
  return (
    <section className="rounded-2xl border border-amber-400/20 bg-amber-950/20 p-8">
      <p className="text-xs uppercase tracking-[0.22em] text-amber-300">Authorization</p>
      <h2 className="mt-2 text-xl font-semibold text-white">Access denied</h2>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">{message}</p>
    </section>
  );
}
