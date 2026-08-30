import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { api } from "../services/api";
import { Card, SectionHeader, Badge } from "../components/ui";
import { AnimatedNumber, RevealItem, Stagger, Toast } from "../motion";
import { inr0 } from "../lib";
import type { RiskEvent } from "../types";

export default function Alerts({ events }: { events: RiskEvent[] }) {
  const [analysis, setAnalysis] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [lastEvent, setLastEvent] = useState<RiskEvent | null>(null);
  const [toastMsg, setToastMsg] = useState<string>("");
  const [toastShow, setToastShow] = useState(false);
  const [edgeFlash, setEdgeFlash] = useState(false);
  const prevCount = useRef(events.length);
  const relevant = events.filter((e) => e.event !== "connected");

  // On a new real-time alert, pop a coral toast + brief edge flash.
  useEffect(() => {
    if (events.length > prevCount.current) {
      const newest = events[0];
      setToastMsg(`${newest.severity}: ${(newest as any).title || newest.message || newest.event}`);
      setToastShow(true);
      setEdgeFlash(true);
      const t1 = setTimeout(() => setToastShow(false), 2000);
      const t2 = setTimeout(() => setEdgeFlash(false), 650);
      prevCount.current = events.length;
      return () => {
        clearTimeout(t1);
        clearTimeout(t2);
      };
    }
    prevCount.current = events.length;
  }, [events.length]);

  async function inject(amount: number, desc: string) {
    await api.injectTxn({ account_id: "ACC001", amount, description: desc, type: "DEBIT", category: "TRANSFER" });
  }

  async function analyzeEvent(e: RiskEvent) {
    setAnalysis(null);
    setLastEvent(e);
    setAnalyzing(true);
    try {
      const res = await api.analyzeEvent({ account_id: e.account_id || "ACC001", amount: Math.abs(e.amount || 80000) });
      setAnalysis(res);
    } catch (err: any) {
      setAnalysis({ error: err.message });
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div className={`space-y-6 ${edgeFlash ? "edge-flash" : ""}`}>
      <Toast show={toastShow} tone="coral">
        <div className="font-semibold">⚠ Real-time alert</div>
        <div className="text-xs text-text2 mt-0.5">{toastMsg}</div>
      </Toast>
      <SectionHeader title="Risk Alerts" sub="Real-time alerts from the Risk Observer (SSE)" />

      <Card>
        <SectionHeader title="Demo: Inject a large transaction" sub="Simulates the Risk Observer detecting a ₹80,000 debit" />
        <div className="mt-3 flex flex-wrap gap-3">
          <button onClick={() => inject(80000, "LARGE DEBIT - ACC001")} className="px-4 py-2 rounded-xl bg-red text-white text-sm font-bold">
            Inject ₹80,000 debit
          </button>
          <button onClick={() => inject(60000, "BIG CUSTOMER PAYMENT")} className="px-4 py-2 rounded-xl bg-green text-bg text-sm font-bold">
            Inject ₹60,000 credit
          </button>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <SectionHeader title="Live Events" sub={`${relevant.length} events`} />
          <div className="mt-3 space-y-2 max-h-[50vh] overflow-y-auto">
            {relevant.length === 0 && <div className="text-xs text-muted">No events yet. Inject one above.</div>}
            {relevant.map((e, i) => (
              <motion.div
                key={e.event_id || i}
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: [0, 0, 0.2, 1] }}
                className="border border-border rounded-xl p-3 bg-card2 insert-flash"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold">{e.event}</span>
                  <Badge tone={e.severity === "HIGH" || e.severity === "CRITICAL" ? "red" : e.severity === "MEDIUM" ? "amber" : "blue"}>
                    {e.severity}
                  </Badge>
                </div>
                <div className="mt-1 text-xs text-text2">{e.message}</div>
                {e.amount != null && <div className="mt-1 text-xs">Amount: {inr0(Math.abs(e.amount))}</div>}
                {e.balance_after != null && <div className="text-xs">Balance after: {inr0(e.balance_after)}</div>}
                <button onClick={() => analyzeEvent(e)} className="mt-2 text-[11px] text-blue underline">
                  Analyze Impact
                </button>
              </motion.div>
            ))}
          </div>
        </Card>

        <Card>
          <SectionHeader title="Impact Analysis" sub="Updated cash · health · loan affordability" />
          {analyzing && <div className="mt-4 text-sm text-blue animate-pulse">Analyzing impact…</div>}
          {analysis && !analysis.error && (
            <Stagger className="mt-4 space-y-3">
              <RevealItem>
                <div className="grid grid-cols-2 gap-3">
                  <Mini label="Net Cash After" tone="text-red"
                    value={analysis.snapshot?.net_cash != null ? <AnimatedNumber value={analysis.snapshot.net_cash} flash format={(v) => inr0(v)} /> : "—"} />
                  <Mini label="Health Score" tone={analysis.health?.overall_score >= 75 ? "text-green" : "text-amber"}
                    value={analysis.health?.overall_score != null ? <AnimatedNumber value={analysis.health.overall_score} flash format={(v) => `${Math.round(v)}/100`} /> : "—"} />
                </div>
              </RevealItem>
              <RevealItem>
                <div className="text-xs text-text2">Risk: {analysis.health?.risk_level}</div>
              </RevealItem>
              <RevealItem>
                {analysis.loan_affordability && (
                  <div className="border border-border rounded-xl p-3 bg-card2">
                    <div className="text-[11px] uppercase tracking-widest text-muted">Loan Affordability Impact (₹3L reference)</div>
                    <div className="mt-2 space-y-1 text-xs">
                      <Mini label="EMI" value={inr0(analysis.loan_affordability.emi)} tone="text-text" />
                      <Mini label="DTI" value={`${(analysis.loan_affordability.dti * 100).toFixed(1)}%`} tone="text-text" />
                      <Mini label="Risk" value={analysis.loan_affordability.risk_level} tone={analysis.loan_affordability.risk_level === "LOW" ? "text-green" : "text-amber"} />
                    </div>
                  </div>
                )}
              </RevealItem>
              <RevealItem>
                <div className="space-y-1">
                  {(analysis.risk?.warnings || []).map((w: string, i: number) => (
                    <div key={i} className="text-xs text-amber">⚠ {w}</div>
                  ))}
                </div>
              </RevealItem>
            </Stagger>
          )}
          {analysis?.error && <div className="mt-4 text-xs text-red">{analysis.error}</div>}
        </Card>
      </div>
    </div>
  );
}

function Mini({ label, value, tone }: { label: string; value: React.ReactNode; tone: string }) {
  return (
    <div className="border border-border rounded-xl p-3">
      <div className="text-[11px] uppercase tracking-widest text-muted">{label}</div>
      <div className={`mt-1 text-lg font-bold ${tone}`}>{value}</div>
    </div>
  );
}
