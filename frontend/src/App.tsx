import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, MotionConfig, motion } from "framer-motion";
import Dashboard from "./pages/Dashboard";
import Advisor from "./pages/Advisor";
import Loans from "./pages/Loans";
import Markets from "./pages/Markets";
import Transactions from "./pages/Transactions";
import Alerts from "./pages/Alerts";
import Governance from "./pages/Governance";
import Intelligence from "./pages/Intelligence";
import ControlCenter from "./pages/ControlCenter";
import Trading from "./pages/Trading";
import { Card } from "./components/ui";
import type { RiskEvent } from "./types";

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: "🏠" },
  { id: "trading", label: "Paper Trading", icon: "📊" },
  { id: "markets", label: "Markets", icon: "📈" },
  { id: "advisor", label: "AI Advisor", icon: "🤖" },
  { id: "intelligence", label: "Intelligence", icon: "🧠" },
  { id: "control", label: "Control Center", icon: "🎛" },
  { id: "loans", label: "Loans", icon: "💰" },
  { id: "transactions", label: "Transactions", icon: "💳" },
  { id: "alerts", label: "Risk Alerts", icon: "⚠" },
  { id: "governance", label: "Governance", icon: "🛡" },
];

// Decision pulse waveform: flat by default, amber spike on volatility events.
// Pulses for PULSE_DURATION_MS after each spike, then goes flat again.
const PULSE_DURATION_MS = 3000;
const PULSE_BAR_HEIGHTS = [4, 6, 8, 10, 12, 14, 10, 8, 6, 4]; // deterministic wave shape

function DecisionPulse({ events }: { events: RiskEvent[] }) {
  const [pulseUntil, setPulseUntil] = useState(0);

  // Watch for new volatility_spike events and start a pulse window
  useEffect(() => {
    const hasSpike = events.some((e) => e.event === "volatility_spike");
    if (hasSpike) {
      setPulseUntil(Date.now() + PULSE_DURATION_MS);
    }
  }, [events]);

  // Clear the pulse after the duration expires
  useEffect(() => {
    if (pulseUntil <= 0) return;
    const t = setTimeout(() => setPulseUntil(0), PULSE_DURATION_MS);
    return () => clearTimeout(t);
  }, [pulseUntil]);

  const isActive = pulseUntil > Date.now();
  const bars = 60;
  return (
    <div className="flex items-end gap-[1px] h-4 mx-4">
      {Array.from({ length: bars }).map((_, i) => {
        // The last 10 bars form the spike wave; the rest stay flat
        const spikeIndex = i - (bars - PULSE_BAR_HEIGHTS.length);
        const isSpikeBar = isActive && spikeIndex >= 0;
        const height = isSpikeBar ? PULSE_BAR_HEIGHTS[spikeIndex] : 2;
        return (
          <div
            key={i}
            className={`decision-pulse-bar ${isSpikeBar ? "active" : ""}`}
            style={{ height: `${height}px` }}
          />
        );
      })}
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [online, setOnline] = useState<boolean | null>(null);
  const [events, setEvents] = useState<RiskEvent[]>([]);
  const [feedState, setFeedState] = useState<"connected" | "reconnecting" | "offline">("connected");
  const esRef = useRef<EventSource | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Health check
  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then((h) => {
        setOnline(h.status === "healthy" || h.status === "degraded");
        setFeedState("connected");
      })
      .catch(() => {
        setOnline(false);
        setFeedState("offline");
      });
  }, []);

  // SSE with reconnect logic and exponential backoff
  useEffect(() => {
    let backoff = 1000;
    let mounted = true;

    function connect() {
      if (!mounted) return;
      const es = new EventSource("/api/events");
      esRef.current = es;

      es.onopen = () => {
        if (!mounted) return;
        setOnline(true);
        setFeedState("connected");
        backoff = 1000; // reset backoff on success
      };

      es.onerror = () => {
        if (!mounted) return;
        es.close();
        setOnline(false);
        setFeedState("reconnecting");
        // Exponential backoff with cap
        reconnectTimer.current = setTimeout(() => {
          backoff = Math.min(backoff * 2, 30000);
          connect();
        }, backoff);
      };

      ["risk_alert", "transaction_alert", "system_alert", "financial_alert", "volatility_spike"].forEach((n) =>
        es.addEventListener(n, (raw: any) => {
          try {
            const data = JSON.parse(raw.data);
            if (mounted) {
              setEvents((prev) => [{ ...data, event: n }, ...prev].slice(0, 40));
            }
          } catch {
            /* ignore */
          }
        })
      );
    }

    connect();

    return () => {
      mounted = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (esRef.current) esRef.current.close();
    };
  }, []);

  const renderPage = useCallback(() => {
    switch (page) {
      case "advisor":
        return <Advisor />;
      case "intelligence":
        return <Intelligence />;
      case "control":
        return <ControlCenter />;
      case "trading":
        return <Trading />;
      case "loans":
        return <Loans />;
      case "markets":
        return <Markets />;
      case "transactions":
        return <Transactions />;
      case "alerts":
        return <Alerts events={events} />;
      case "governance":
        return <Governance />;
      default:
        return <Dashboard goTo={(p) => setPage(p)} online={online} alertCount={events.length} />;
    }
  }, [page, online, events]);

  return (
    <MotionConfig reducedMotion="user">
      <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-56 hidden md:flex flex-col gap-0.5 p-3 border-r border-border bg-panel">
        {/* Brand */}
        <div className="flex items-center gap-2.5 px-2 mb-5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green to-blue flex items-center justify-center text-xs font-extrabold text-bg">
            F
          </div>
          <div>
            <div className="text-xs font-extrabold tracking-wide font-display">
              FinPilot <span className="text-green">AI</span>
            </div>
            <div className="text-[9px] text-muted tracking-[0.15em]">INSTRUMENT PANEL</div>
          </div>
        </div>

        {/* System status */}
        <div className="flex items-center gap-2 px-2 mb-3 py-1.5 rounded bg-panel-raised border border-border">
          <span className={`status-dot ${feedState}`} />
          <span className="text-[10px] font-semibold text-text2">
            {feedState === "connected" ? "System Online" : feedState === "reconnecting" ? "Reconnecting…" : "Offline"}
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-0.5">
          {NAV.map((item) => (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`flex items-center gap-2.5 px-2.5 py-2 rounded text-xs font-semibold text-left transition-colors ${
                page === item.id ? "bg-green/10 text-green" : "text-text2 hover:bg-panel-raised hover:text-text"
              }`}
            >
              <span className="text-sm">{item.icon}</span>
              {item.label}
              {item.id === "alerts" &&
                events.filter((e) => e.severity === "HIGH" || e.severity === "CRITICAL").length > 0 && (
                  <span className="ml-auto text-[9px] bg-red text-white rounded px-1.5 py-0.5 font-bold">
                    {events.filter((e) => e.severity === "HIGH" || e.severity === "CRITICAL").length}
                  </span>
                )}
            </button>
          ))}
        </nav>

        {/* Bottom */}
        <div className="mt-auto pt-4">
          <Card className="!p-2.5 !bg-panel-raised !border-border">
            <div className="text-[9px] uppercase tracking-widest text-muted font-semibold">System</div>
            <div className="flex items-center gap-1.5 mt-1 text-[10px] font-semibold text-green">
              <span className={`status-dot ${online ? "online" : "offline"}`} />
              {online ? "Connected" : "Offline"}
            </div>
          </Card>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col min-h-screen overflow-hidden">
        {/* Top bar with decision pulse */}
        <div className="flex items-center border-b border-border bg-panel px-4 py-2 shrink-0">
          <div className="flex items-center gap-3">
            <span className={`status-dot ${feedState}`} />
            <span className="text-[11px] font-semibold text-text2 font-mono">
              {feedState === "connected" ? "LIVE" : feedState === "reconnecting" ? "RECONNECTING" : "OFFLINE"}
            </span>
          </div>
          <DecisionPulse events={events} />
          <div className="ml-auto flex items-center gap-4 text-[10px] text-muted">
            <span className="font-mono">{events.length} events</span>
            <span className="font-mono">FinPilot v0.4.0</span>
          </div>
        </div>

        {/* Page content */}
        <div className="flex-1 p-5 overflow-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={page}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35, ease: [0, 0, 0.2, 1] }}
            >
              {renderPage()}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      {/* Mobile nav */}
      <div className="md:hidden fixed bottom-0 inset-x-0 bg-panel border-t border-border p-2 flex justify-around z-50">
        {NAV.slice(0, 5).map((item) => (
          <button key={item.id} onClick={() => setPage(item.id)} className={`text-xs ${page === item.id ? "text-green" : "text-text2"}`}>
            <div className="text-lg">{item.icon}</div>
          </button>
        ))}
      </div>
    </div>
    </MotionConfig>
  );
}
