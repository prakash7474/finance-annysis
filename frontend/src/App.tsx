import { useCallback, useEffect, useState } from "react";
import Dashboard from "./pages/Dashboard";
import Advisor from "./pages/Advisor";
import Loans from "./pages/Loans";
import Markets from "./pages/Markets";
import Transactions from "./pages/Transactions";
import Alerts from "./pages/Alerts";
import Governance from "./pages/Governance";
import Intelligence from "./pages/Intelligence";
import ControlCenter from "./pages/ControlCenter";
import { Badge, Card } from "./components/ui";
import type { RiskEvent } from "./types";

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: "🏠" },
  { id: "advisor", label: "AI Advisor", icon: "🤖" },
  { id: "intelligence", label: "Intelligence", icon: "🧠" },
  { id: "control", label: "Control Center", icon: "🎛" },
  { id: "loans", label: "Loans", icon: "💰" },
  { id: "markets", label: "Markets", icon: "📈" },
  { id: "transactions", label: "Transactions", icon: "💳" },
  { id: "alerts", label: "Risk Alerts", icon: "⚠" },
  { id: "governance", label: "Governance", icon: "🛡" },
];

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [online, setOnline] = useState<boolean | null>(null);
  const [events, setEvents] = useState<RiskEvent[]>([]);

  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then((h) => setOnline(h.status === "healthy" || h.status === "degraded"))
      .catch(() => setOnline(false));
  }, []);

  // Global SSE subscription → live risk alerts appear in the panel.
  useEffect(() => {
    const es = new EventSource("/api/events");
    const handle = (name: string, data: any) => {
      if (["risk_alert", "transaction_alert", "system_alert", "financial_alert"].includes(name)) {
        setEvents((prev) => [{ ...data, event: name }, ...prev].slice(0, 40));
      }
    };
    es.onopen = () => setOnline(true);
    es.onerror = () => setOnline(false);
    ["risk_alert", "transaction_alert", "system_alert", "financial_alert"].forEach((n) =>
      es.addEventListener(n, (raw: any) => {
        try {
          handle(n, JSON.parse(raw.data));
        } catch {
          /* ignore */
        }
      })
    );
    return () => es.close();
  }, []);

  const renderPage = useCallback(() => {
    switch (page) {
      case "advisor":
        return <Advisor />;
      case "intelligence":
        return <Intelligence />;
      case "control":
        return <ControlCenter />;
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
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-60 hidden md:flex flex-col gap-1 p-4 border-r border-border bg-panel">
        <div className="flex items-center gap-3 px-2 mb-6">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-green to-blue flex items-center justify-center text-base font-extrabold text-bg">
            F
          </div>
          <div>
            <div className="text-sm font-extrabold tracking-wide">
              FinPilot <span className="text-green">AI</span>
            </div>
            <div className="text-[10px] text-muted tracking-[0.15em]">FINANCE CONTROLLER</div>
          </div>
        </div>

        <div className="flex items-center gap-2 px-2 mb-4 text-xs font-semibold text-green">
          <span className={`w-2 h-2 rounded-full ${online ? "bg-green shadow-green" : "bg-red"} shadow`} />
          {online ? "System Online" : "Connecting…"}
        </div>

        <nav className="flex flex-col gap-1">
          {NAV.map((item) => (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold text-left transition-colors ${
                page === item.id ? "bg-green/12 text-green" : "text-text2 hover:bg-card hover:text-text"
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
              {item.id === "alerts" && events.filter((e) => e.severity === "HIGH" || e.severity === "CRITICAL").length > 0 && (
                <span className="ml-auto text-[10px] bg-red text-white rounded-full px-2 py-0.5">
                  {events.filter((e) => e.severity === "HIGH" || e.severity === "CRITICAL").length}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="mt-auto">
          <Card className="!p-3">
            <div className="text-[10px] uppercase tracking-widest text-muted">Available</div>
            <div className="text-lg font-bold text-green" id="sidebar-cash">
              —
            </div>
          </Card>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 p-6 overflow-auto">{renderPage()}</main>

      {/* Mobile nav */}
      <div className="md:hidden fixed bottom-0 inset-x-0 bg-panel border-t border-border p-2 flex justify-around">
        {NAV.slice(0, 5).map((item) => (
          <button key={item.id} onClick={() => setPage(item.id)} className={`text-xs ${page === item.id ? "text-green" : "text-text2"}`}>
            <div className="text-lg">{item.icon}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
