import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../types";

interface Props {
  messages: ChatMessage[];
  busy: boolean;
  error: string | null;
  mode: "mock" | "live" | null;
  suggestions: string[];
  onSend: (text: string) => void;
}

export function Chat({ messages, busy, error, mode, suggestions, onSend }: Props) {
  const [text, setText] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const el = listRef.current;
    if (el && typeof el.scrollTo === "function") el.scrollTo({ top: el.scrollHeight });
  }, [messages, busy]);

  function submit(value: string) {
    const trimmed = value.trim();
    if (!trimmed || busy) return;
    onSend(trimmed);
    setText("");
    inputRef.current?.focus();
  }

  return (
    <section className="chat" aria-label="Assistant conversation">
      <div className="chat-head">
        <div className={`ring${busy ? " busy" : ""}`} aria-hidden="true" />
        <div>
          <h2>Ask about your cash</h2>
          <p className="hint">
            {mode === "live" ? "Live model with real tool calls." : "Mock mode: a rule-based planner, same tools, no model call."} Type or pick a question.
          </p>
        </div>
      </div>

      <div className="messages" ref={listRef} role="log" aria-live="polite" aria-relevant="additions">
        {messages.length === 0 && <p className="hint">Try: “Can we cover Friday's payroll if Customer A pays two weeks late?”</p>}
        {messages.map((m) => (
          <div key={m.id} className={`msg ${m.role}${m.failed ? " failed" : ""}`}>
            {m.text}
            {m.response && (
              <div className="meta">
                {m.response.tool_trace.map((t, i) => (
                  <span key={i} className={`chip ${t.status}`} title={JSON.stringify(t.arguments)}>
                    {t.tool}
                    {t.status === "error" ? ` ✕ ${t.error_code}` : ""}
                  </span>
                ))}
                {m.response.tool_trace.length > 0 && (
                  <span className={`chip ${m.response.grounded ? "ok" : "error"}`}>{m.response.grounded ? "figures grounded in tools" : "ungrounded text replaced"}</span>
                )}
                {m.response.tool_trace.length === 0 && m.response.status === "ok" && <span className="chip">no tool needed</span>}
              </div>
            )}
            {m.response && m.response.warnings.length > 0 && (
              <details>
                <summary>{m.response.warnings.length} note{m.response.warnings.length === 1 ? "" : "s"}</summary>
                <ul>
                  {m.response.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </details>
            )}
            {m.response && m.response.tool_trace.length > 0 && (
              <details>
                <summary>Tool trace</summary>
                <pre>{JSON.stringify(m.response.tool_trace, null, 2)}</pre>
              </details>
            )}
          </div>
        ))}
        {busy && (
          <div className="msg assistant" aria-label="Working">
            Working…
          </div>
        )}
      </div>

      {error && (
        <div className="error-box" role="alert">
          {error}
        </div>
      )}

      <div className="suggestions" aria-label="Suggested questions">
        {suggestions.map((s) => (
          <button key={s} type="button" onClick={() => submit(s)} disabled={busy}>
            {s}
          </button>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(text);
        }}
      >
        <label className="sr-only" htmlFor="chat-input">
          Your question
        </label>
        <input id="chat-input" ref={inputRef} type="text" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask about cash, a late payment, overdue items, or a reminder" maxLength={2000} autoComplete="off" />
        <button type="submit" className="btn primary" disabled={busy || !text.trim()}>
          Ask
        </button>
      </form>
    </section>
  );
}
