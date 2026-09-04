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
  const [retryCount, setRetryCount] = useState(0);
  const [injecting, setInjecting] = useState(false);
  const [injectError, setInjectError] = useState<string | null>(null);
  const [lastEvent, setLastEvent] = useState<RiskEvent | null>(null);
  const [toastMsg, setToastMsg] = useState<string>("");
  const [toastShow, setToastShow] = useState(false);
  const [edgeFlash, setEdgeFlash] = useState(false);
  const prevCount = useRef(events.length);
  // Keep volatile market feed (volatility_spike) and system alerts out of
  // the "Live Events" list. system_alert events lack event_id / severity /
  // account_id which causes rendering issues and interferes with the
  // dedup logic (undefined event_id matches any previous undefined).
  const relevant = events.filter(
    (e) => e.event !== "connected" && e.event !== "volatility_spike" && e.event !== "system_alert"
  );

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

  async function inject(amount: number, desc: string, type: "DEBIT" | "CREDIT") {
    setInjecting(true);
    setInjectError(null);
    try {
      const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
      const res = await api.injectTxn({ account_id: "ACC001", amount, description: desc, type, category: "TRANSFER", date: today });
      if (!res || !res.success) {
        setInjectError(res?.message || "Injection was not acknowledged by the server.");
      }
    } catch (err: any) {
      // Surface failures instead of throwing an unhandled promise rejection
      // that could propagate into a blank-screen crash.
      setInjectError(err?.message || "Failed to inject transaction.");
    } finally {
      setInjecting(false);
    }
  }

  const MAX_RETRIES = 2;

  async function analyzeEvent(e: RiskEvent, attempt = 0) {
    setAnalysis(null);
    setLastEvent(e);
    setAnalyzing(true);
    setRetryCount(attempt);
    try {
      const res = await api.analyzeEvent({ account_id: e.account_id || "ACC001", amount: Math.abs(e.amount || 80000) });
      if (!res || typeof res !== "object") {
        setAnalysis({ error: "Empty analysis response." });
      } else if (res.error || !res.success) {
        setAnalysis({ error: res.error || res.message || "Analysis failed on the server." });
      } else {
        setAnalysis(res);
        setRetryCount(0); // Success resets retry counter
      }
    } catch (err: any) {
      setAnalysis({ error: err?.message || "Failed to analyze impact." });
    } finally {
      setAnalyzing(false);
    }
  }

  function retryAnalysis() {
    if (!lastEvent || retryCount >= MAX_RETRIES) return;
    // Exponential backoff: 1s on first retry, 2s on second
    const delay = 1000 * Math.pow(2, retryCount);
    setAnalyzing(true);
    setAnalysis(null);
    setTimeout(() => analyzeEvent(lastEvent, retryCount + 1), delay);
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
            <button
              onClick={() => inject(80000, "LARGE DEBIT - ACC001", "DEBIT")}
              disabled={injecting}
              className="px-4 py-2 rounded-xl bg-red text-white text-sm font-bold disabled:opacity-50"
            >
              {injecting ? "Injecting…" : "Inject ₹80,000 debit"}
            </button>
            <button
              onClick={() => inject(60000, "BIG CUSTOMER PAYMENT", "CREDIT")}
              disabled={injecting}
              className="px-4 py-2 rounded-xl bg-green text-bg text-sm font-bold disabled:opacity-50"
            >
              {injecting ? "Injecting…" : "Inject ₹60,000 credit"}
            </button>
          </div>
          {injectError && <div className="mt-2 text-xs text-red">{injectError}</div>}
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
                <button onClick={() => analyzeEvent(e)} disabled={analyzing} className="mt-2 text-[11px] text-blue underline disabled:opacity-50">
                  Analyze Impact
                </button>
              </motion.div>
            ))}
          </div>
        </Card>

        <Card>
          <SectionHeader title="Impact Analysis" sub="Updated cash · health · loan affordability" />
          {analyzing && <div className="mt-4 text-sm text-blue animate-pulse">Analyzing impact…</div>}
          {!analyzing && !analysis && (
            <div className="mt-4 text-xs text-muted">
              Click <span className="font-semibold text-text2">Analyze Impact</span> on an event to compute updated cash, health and loan affordability.
            </div>
          )}
          {analysis && !analysis.error && (
            <Stagger className="mt-4 space-y-3">
              <RevealItem>
                <div className="grid grid-cols-2 gap-3">
                  <Mini label="Net Cash After" tone="text-red"
                    value={analysis.snapshot?.net_cash != null && !isNaN(analysis.snapshot.net_cash) ? <AnimatedNumber value={analysis.snapshot.net_cash} flash format={(v) => inr0(v)} /> : "—"} />
                  <Mini label="Health Score" tone={analysis.health?.overall_score != null && analysis.health.overall_score >= 75 ? "text-green" : "text-amber"}
                    value={analysis.health?.overall_score != null && !isNaN(analysis.health.overall_score) ? <AnimatedNumber value={analysis.health.overall_score} flash format={(v) => `${Math.round(v)}/100`} /> : "—"} />
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
                      <Mini label="DTI" value={analysis.loan_affordability.dti != null && !isNaN(analysis.loan_affordability.dti) ? `${(analysis.loan_affordability.dti * 100).toFixed(1)}%` : "—"} tone="text-text" />
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
          {analysis?.error && (
            <div className="mt-4 space-y-2">
              <div className="text-xs text-red">{analysis.error}</div>
              {retryCount < MAX_RETRIES && (
                <button
                  onClick={retryAnalysis}
                  disabled={analyzing}
                  className="px-3 py-1.5 rounded-lg bg-blue/10 border border-blue/30 text-[11px] font-semibold text-blue disabled:opacity-50 transition-colors"
                >
                  {analyzing ? "Retrying…" : `Retry (${retryCount + 1}/${MAX_RETRIES})`}
                </button>
              )}
              {retryCount >= MAX_RETRIES && (
                <div className="text-[10px] text-muted">Max retries reached. Try again later.</div>
              )}
            </div>
          )}
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
