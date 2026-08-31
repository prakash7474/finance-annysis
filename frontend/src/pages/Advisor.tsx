import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, openEventSource } from "../services/api";
import { Card } from "../components/ui";
import { Reveal, ShimmerBar, Check } from "../motion";
import type { ChatResponse } from "../types";

interface Msg {
  role: "user" | "assistant";
  text: string;
  tools?: string[];
  error?: boolean;
  streaming?: boolean;
}

const SAFE_STEPS = [
  "Calling Bank MCP",
  "Calculating loan",
  "Validating result",
  "Preparing response",
];

// Wrap ₹ amounts and % in a mono, briefly-highlighted span so the reader's eye
// lands on the computed (deterministic) numbers, not generated ones.
const NUM_SPLIT = /(₹[\d,]+(?:\.\d+)?|[\d,]+(?:\.\d+)?%)/g;
const NUM_TEST = /₹[\d,]+(?:\.\d+)?|[\d,]+(?:\.\d+)?%/;
function renderMono(text: string) {
  const parts = text.split(NUM_SPLIT);
  return parts.map((p, i) =>
    NUM_TEST.test(p) ? (
      <span key={i} className="mono-flash">{p}</span>
    ) : (
      <span key={i}>{p}</span>
    )
  );
}

export default function Advisor() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [steps, setSteps] = useState<string[]>([]);
  const [voiceActive, setVoiceActive] = useState(false);
  const [interrupted, setInterrupted] = useState(false);
  const [connected, setConnected] = useState(false);
  const session = useRef<string>();
  const stepTimer = useRef<any>(null);
  const voiceWs = useRef<WebSocket | null>(null);
  const voiceBuffer = useRef<string>("");

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
    if (voiceActive) return;
    setVoiceActive(true);
    setInterrupted(false);
    setMessages((m) => [...m, { role: "user", text: "🎙 (voice): What is my current financial status?" }]);
    setMessages((m) => [...m, { role: "assistant", text: "", streaming: true }]);

    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/api/voice`);
    voiceWs.current = ws;
    voiceBuffer.current = "";

    const updateStream = (tail: string) => {
      setMessages((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last && last.streaming) copy[copy.length - 1] = { ...last, text: tail };
        return copy;
      });
    };

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "audio", data: "What is my current financial status?" }));
    };
    ws.onmessage = (e) => {
      try {
        const m = JSON.parse(e.data);
        if (m.type === "reply") {
          voiceBuffer.current += m.chunk;
          updateStream(voiceBuffer.current);
        } else if (m.type === "done") {
          updateStream(voiceBuffer.current);
          setMessages((prev) => prev.map((x) => ({ ...x, streaming: false })));
          setVoiceActive(false);
          ws.close();
        } else if (m.type === "interrupted") {
          setMessages((prev) => prev.map((x) => ({ ...x, streaming: false })));
          setVoiceActive(false);
          ws.close();
        }
      } catch {
        /* ignore malformed frames */
      }
    };
    ws.onerror = () => {
      setMessages((prev) => prev.map((x) => ({ ...x, streaming: false })));
      setMessages((m) => [...m, { role: "assistant", text: "Voice channel unavailable. Text works normally.", error: true }]);
      setVoiceActive(false);
      ws.close();
    };
  }

  function interruptVoice() {
    if (voiceWs.current && voiceWs.current.readyState === WebSocket.OPEN) {
      voiceWs.current.send(JSON.stringify({ type: "interrupt" }));
    }
    setVoiceActive(false);
    setInterrupted(true);
    setTimeout(() => setInterrupted(false), 1200);
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
          <div className="flex items-center gap-2">
            {interrupted && (
              <span className="interrupt-tag text-[10px] font-bold text-amber bg-amber/15 px-2 py-1 rounded">INTERRUPTED</span>
            )}
            {voiceActive ? (
              <>
                <span className="voice-bars" aria-label="listening"><span /><span /><span /></span>
                <button onClick={interruptVoice} className="px-3 py-2 rounded-xl text-sm font-bold bg-red text-white">
                  Interrupt
                </button>
              </>
            ) : (
              <button onClick={useVoice} className={`px-4 py-2 rounded-xl text-sm font-bold bg-green text-bg`}>
                🎙 Voice
              </button>
            )}
          </div>
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
            <AnimatePresence key={i} initial>
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: m.role === "user" ? 0.2 : 0.35, ease: [0, 0, 0.2, 1] }}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                    m.role === "user"
                      ? "bg-blue/20 text-text"
                      : m.error
                      ? "bg-red/10 text-text border border-red/30"
                      : "bg-card2 text-text"
                  }`}
                >
                  {renderMono(m.text)}
                  {m.streaming && <span className="streaming-caret" />}
                  {m.tools && m.tools.length > 0 && (
                    <Reveal delay={0.1} className="mt-3 pt-2 border-t border-border flex flex-wrap gap-2">
                      {m.tools.map((t, ti) => (
                        <motion.span
                          key={t}
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: 0.1 + ti * 0.05, duration: 0.2 }}
                          className="text-[11px] bg-green/15 text-green px-2 py-1 rounded-md inline-flex items-center gap-1"
                        >
                          <Check size={12} /> {t}
                        </motion.span>
                      ))}
                    </Reveal>
                  )}
                </div>
              </motion.div>
            </AnimatePresence>
          ))}

          {thinking && (
            <div className="flex justify-start">
              <div className="bg-card2 rounded-2xl px-4 py-3">
                <div className="flex items-center gap-3 text-xs text-green font-semibold">
                  AI THINKING
                  <ShimmerBar className="w-24" />
                </div>
                <div className="mt-2 space-y-1">
                  {steps.map((s, i) => (
                    <div key={i} className="text-xs text-text2 inline-flex items-center gap-2">
                      <Check size={12} /> {s}
                    </div>
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
