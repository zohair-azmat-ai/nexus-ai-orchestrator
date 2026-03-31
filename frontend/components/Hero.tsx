import { API_URL } from "@/lib/api";

export default function Hero() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-28 text-center">
      {/* Logo placeholder */}
      <div className="flex justify-center mb-8">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-600 via-blue-600 to-cyan-500 flex items-center justify-center shadow-2xl shadow-violet-500/20">
          <span className="text-white font-black text-3xl">N</span>
        </div>
      </div>

      <div className="inline-block mb-4 px-3 py-1 rounded-full border border-violet-500/30 bg-violet-500/10 text-violet-400 text-xs font-medium tracking-widest uppercase">
        Multi-Agent RAG Orchestration Platform
      </div>

      <h1 className="text-5xl md:text-6xl font-bold text-white mt-4 mb-6 leading-tight">
        Nexus AI
      </h1>

      <p className="text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed mb-8">
        Production-grade AI operating infrastructure. Memory-aware, retrieval-augmented,
        multi-agent orchestration with full observability built in from day one.
      </p>

      <div className="flex flex-wrap justify-center gap-3 text-sm text-gray-400 mb-10">
        {["FastAPI", "Next.js", "PostgreSQL", "Qdrant", "OpenAI", "Docker"].map((tech) => (
          <span key={tech} className="px-3 py-1 bg-gray-800 rounded-full border border-gray-700">
            {tech}
          </span>
        ))}
      </div>

      <div className="flex flex-wrap justify-center gap-4">
        <a
          href={`${API_URL}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="px-6 py-3 bg-violet-600 hover:bg-violet-500 text-white rounded-lg font-medium transition-colors"
        >
          API Explorer
        </a>
        <a
          href={`${API_URL}/api/v1/health`}
          target="_blank"
          rel="noopener noreferrer"
          className="px-6 py-3 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg font-medium border border-gray-700 transition-colors"
        >
          Health Check
        </a>
      </div>
    </section>
  );
}
