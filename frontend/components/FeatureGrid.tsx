const features = [
  {
    title: "Orchestrator Engine",
    description:
      "Staged pipeline: intake → memory → retrieval → triage → response → escalation → event log. Every request flows through a structured, observable pipeline.",
    icon: "⬡",
    color: "from-violet-500/20 to-violet-600/5 border-violet-500/20",
  },
  {
    title: "Memory Layer",
    description:
      "Short-term conversation history, session summaries, and long-term user memory. Context persists across turns and sessions.",
    icon: "◈",
    color: "from-blue-500/20 to-blue-600/5 border-blue-500/20",
  },
  {
    title: "RAG Retrieval",
    description:
      "Document ingestion, semantic chunking, vector embeddings, and Qdrant-powered search. Ground responses in your knowledge base.",
    icon: "◎",
    color: "from-cyan-500/20 to-cyan-600/5 border-cyan-500/20",
  },
  {
    title: "Multi-Agent Layer",
    description:
      "Support, Research, Summarizer, Planner, and Escalation agents. The triage stage routes each request to the most appropriate specialist.",
    icon: "◇",
    color: "from-emerald-500/20 to-emerald-600/5 border-emerald-500/20",
  },
  {
    title: "Observability",
    description:
      "Correlation IDs on every request, structured JSON logging, event store, and metrics-ready architecture. Trace any request end-to-end.",
    icon: "◉",
    color: "from-amber-500/20 to-amber-600/5 border-amber-500/20",
  },
  {
    title: "Production Architecture",
    description:
      "Modular monolith with clear service boundaries. Async-first FastAPI, Pydantic settings, clean dependency injection, and phase-based roadmap.",
    icon: "▣",
    color: "from-rose-500/20 to-rose-600/5 border-rose-500/20",
  },
];

export default function FeatureGrid() {
  return (
    <section id="features" className="max-w-6xl mx-auto px-6 pb-24">
      <h2 className="text-3xl font-bold text-white text-center mb-4">
        Platform Capabilities
      </h2>
      <p className="text-gray-500 text-center mb-12 max-w-xl mx-auto">
        Phase 1 foundation — built to grow from scaffold to full production system
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {features.map((f) => (
          <div
            key={f.title}
            className={`p-6 rounded-xl border bg-gradient-to-br ${f.color} hover:scale-[1.01] transition-transform`}
          >
            <div className="text-2xl mb-3 text-gray-300">{f.icon}</div>
            <h3 className="font-semibold text-white mb-2">{f.title}</h3>
            <p className="text-sm text-gray-400 leading-relaxed">{f.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
