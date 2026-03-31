"use client";

import { useState } from "react";

import { formatDateTime, titleize } from "@/components/escalations/utils";
import { createEscalationNote } from "@/lib/escalations";
import type {
  EscalationCase,
  EscalationNote,
  EscalationNoteType,
} from "@/types/escalations";

interface NotesPanelProps {
  escalationCase: EscalationCase;
  initialNotes: EscalationNote[];
}

export default function NotesPanel({ escalationCase, initialNotes }: NotesPanelProps) {
  const [notes, setNotes] = useState(initialNotes);
  const [author, setAuthor] = useState("");
  const [content, setContent] = useState("");
  const [noteType, setNoteType] = useState<EscalationNoteType>("human");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const note = await createEscalationNote(escalationCase.case_id, {
        author,
        content,
        note_type: noteType,
      });
      setNotes((current) => [...current, note]);
      setContent("");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to save note.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/70 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-cyan-300">Notes</p>
          <h2 className="mt-2 text-lg font-semibold text-white">Reviewer timeline</h2>
        </div>
        <p className="text-sm text-slate-500">{notes.length} notes</p>
      </div>

      <div className="mt-5 space-y-3">
        {notes.length > 0 ? (
          notes.map((note) => (
            <article
              key={note.note_id}
              className="rounded-2xl border border-white/8 bg-slate-900/80 p-4"
            >
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <p className="font-medium text-white">{note.author}</p>
                <span className="rounded-full border border-white/10 bg-slate-800 px-2 py-1 text-xs text-slate-300">
                  {titleize(note.note_type)}
                </span>
                <span className="text-xs text-slate-500">{formatDateTime(note.created_at)}</span>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-300">
                {note.content}
              </p>
            </article>
          ))
        ) : (
          <div className="rounded-2xl border border-dashed border-white/10 bg-slate-900/50 p-6 text-sm text-slate-400">
            No notes yet. Add the first reviewer note to capture context and decisions.
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4 rounded-2xl border border-white/10 bg-slate-900/70 p-4">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="text-sm text-slate-300">
            Author
            <input
              required
              value={author}
              onChange={(event) => setAuthor(event.target.value)}
              placeholder="reviewer-name"
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
            />
          </label>

          <label className="text-sm text-slate-300">
            Note type
            <select
              value={noteType}
              onChange={(event) => setNoteType(event.target.value as EscalationNoteType)}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400/60"
            >
              <option value="human">Human</option>
              <option value="agent">Agent</option>
              <option value="system">System</option>
            </select>
          </label>
        </div>

        <label className="block text-sm text-slate-300">
          Content
          <textarea
            required
            value={content}
            onChange={(event) => setContent(event.target.value)}
            rows={4}
            placeholder="Capture review context, decision notes, or next steps."
            className="mt-2 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/60"
          />
        </label>

        {error ? <p className="text-sm text-rose-300">{error}</p> : null}

        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-cyan-500/60"
        >
          {isSubmitting ? "Saving note..." : "Add note"}
        </button>
      </form>
    </section>
  );
}
