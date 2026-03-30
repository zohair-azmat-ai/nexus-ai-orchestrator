import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import FeatureGrid from "@/components/FeatureGrid";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-950">
      <Navbar />
      <Hero />
      <FeatureGrid />

      <footer className="border-t border-gray-800 py-8 text-center text-sm text-gray-500">
        <p>Nexus AI &mdash; Multi-Agent RAG Orchestration Platform &mdash; Phase 1</p>
      </footer>
    </main>
  );
}
