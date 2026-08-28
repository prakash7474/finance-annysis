import { useEffect, useRef, useState } from "react";
import { api, openEventSource } from "../services/api";
import { Card } from "../components/ui";
import type { ChatResponse } from "../types";

interface Msg {
  role: "user" | "assistant";
  text: string;
  tools?: string[];
  error?: boolean;
}

const SAFE_STEPS = [
  "Calling Bank MCP",
  "Calculating loan",
  "Validating result",
  "Preparing response",
];

export default function Advisor() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [steps, setSteps] = useState<string[]>([]);
  const [voiceActive, setVoiceActive] = useState(false);
  const [connected, setConnected] = useState(false);
  const session = useRef<string>();
  const stepTimer = useRef<any>(null);

  useEffect(() => {
    const es = openEventSource((evt) => {
      if (evt === "connected") setConnected(true);
      if (evt === "error") setConnected(false);
    });
    return () => es.close();
  }, []);

  async function send(text: string) {
    if (!text.trim() || thinking) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setThinking(true);
    setSteps([]);

    // Animate safe operational steps (not chain-of-thought).
    SAFE_STEPS.forEach((s, i) => {
      setTimeout(() => setSteps((prev) => (prev.includes(s) ? prev : [...prev, s])), i * 350);
    });

    try {
      const resp = await api.chat(text, session.current);
      session.current = resp.session_id;
      setMessages((m) => [
        ...m,
        { role: "assistant", text: resp.message, tools: resp.tools_used, error: !resp.success },
      ]);
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: `AI service unavailable.\nDeterministic finance tools are still available.\n\n${e?.message || ""}`, error: true },
      ]);
    } finally {
      setThinking(false);
      setSteps([]);
      if (stepTimer.current) clearTimeout(stepTimer.current);
    }
  }

  async function useVoice() {
    try {
      const session2 = await api.voiceStart();
      setVoiceActive(true);
      await new Promise((r) => setTimeout(r, 500));
      const res = await api.voiceSend(session2.session_id, "What is my current financial status?");
      setMessages((m) => [...m, { role: "user", text: "🎙 (voice): What is my current financial status?" }]);
      setMessages((m) => [...m, { role: "assistant", text: "🎙 " + res.reply, tools: res.tools_used }]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", text: "Voice is unavailable. Text works normally.", error: true }]);
    } finally {
      setVoiceActive(false);
    }
  }

  function key(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <Card className="min-h-[80vh] flex flex-col !p-0">
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div>
            <h2 className="font-bold">FinPilot AI</h2>
            <div className="flex items-center gap-2 text-xs text-text2">
              <span className={`w-2 h-2 rounded-full ${connected ? "bg-green" : "bg-red"}`} />
              {connected ? "Connected · Live" : "Reconnecting…"}
            </div>
          </div>
          <button onClick={useVoice} className={`px-4 py-2 rounded-xl text-sm font-bold ${voiceActive ? "bg-amber/20 text-amber" : "bg-green text-bg"}`}>
            🎙 {voiceActive ? "Listening…" : "Voice"}
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-text2 mt-16">
              <div className="text-4xl mb-3">🤖</div>
              <div className="text-lg font-semibold text-text">Ask FinPilot anything</div>
              <div className="mt-2 text-xs">Finance · Loans · Markets · What-if</div>
              <div className="mt-6 space-y-2">
                {[
                  "Can I afford a ₹3 lakh loan?",
                  "What is my current cash position?",
                  "Compare HDFC and ICICI.",
                  "How is RELIANCE performing?",
                ].map((q) => (
                  <button key={q} onClick={() => send(q)} className="block w-full text-left bg-card2 border border-border rounded-xl px-4 py-2.5 text-sm hover:border-blue">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                  m.role === "user"
                    ? "bg-blue/20 text-text"
                    : m.error
                    ? "bg-red/10 text-text border border-red/30"
                    : "bg-card2 text-text"
                }`}
              >
                {m.text}
                {m.tools && m.tools.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-border flex flex-wrap gap-2">
                    {m.tools.map((t) => (
                      <span key={t} className="text-[11px] bg-green/15 text-green px-2 py-1 rounded-md">✓ {t}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {thinking && (
            <div className="flex justify-start">
              <div className="bg-card2 rounded-2xl px-4 py-3">
                <div className="flex items-center gap-2 text-xs text-green font-semibold">
                  AI THINKING
                  <span className="inline-flex gap-1">
                    {[0, 1, 2].map((d) => (
                      <span key={d} className="w-1.5 h-1.5 rounded-full bg-green animate-pulse" style={{ animationDelay: `${d * 0.15}s` }} />
                    ))}
                  </span>
                </div>
                <div className="mt-2 space-y-1">
                  {steps.map((s, i) => (
                    <div key={i} className="text-xs text-text2">✓ {s}</div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="p-4 border-t border-border flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={key}
            placeholder="Ask anything…"
            rows={2}
            className="flex-1 bg-card2 border border-border rounded-xl px-4 py-3 text-sm outline-none focus:border-blue resize-none"
          />
          <button
            onClick={() => send(input)}
            disabled={thinking}
            className="px-5 rounded-xl bg-green text-bg font-bold disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </Card>
    </div>
  );
}
