import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Card, StatCard, SectionHeader, Badge, RiskBar } from "../components/ui";
import { AnimatedNumber, Stagger, RevealItem } from "../motion";
import { inr, inr0, riskTone } from "../lib";

export default function Dashboard({
  goTo,
  online,
  alertCount,
}: {
  goTo: (p: string) => void;
  online: boolean | null;
  alertCount: number;
}) {
  const [cash, setCash] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [emis, setEmis] = useState<any>(null);
  const [flow, setFlow] = useState<{ month: string; credit: number; debit: number; net: number }[]>([]);

  useEffect(() => {
    reload();
  }, []);

  async function reload() {
    const [c, h, s, e] = await Promise.all([
      api.cashPosition(),
      api.healthScore().catch(() => null),
      api.monthlySummary(),
      api.emiSummary(),
    ]);
    setCash(c);
    setHealth(h);
    setSummary(s);
    setEmis(e);
    // Simple monthly cash-flow for the chart (July vs August from the engine).
    const [jul, aug] = await Promise.all([
      api.monthlySummary("2026-07-01", "2026-07-31"),
      api.monthlySummary("2026-08-01", "2026-08-31"),
    ]);
    setFlow([
      { month: "July 2026", credit: jul.total_credit, debit: jul.total_debit, net: jul.net_change },
      { month: "Aug 2026", credit: aug.total_credit, debit: aug.total_debit, net: aug.net_change },
    ]);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">FINPILOT</h1>
          <p className="text-sm text-text2 mt-1">AI Finance Controller</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge tone={online ? "green" : "gray"}>
            <span className={`w-2 h-2 rounded-full ${online ? "bg-green" : "bg-red"}`} />
            {online ? "System Online" : "Offline"}
          </Badge>
          {alertCount > 0 && (
            <button onClick={() => goTo("alerts")} className="text-xs text-red underline">
              {alertCount} alert{alertCount > 1 ? "s" : ""}
            </button>
          )}
        </div>
      </div>

      {/* KPI cards */}
      <Stagger className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <RevealItem>
          <StatCard label="Available Cash" accent="text-green"
            value={cash ? <AnimatedNumber value={cash.net_cash} flash format={(v) => inr0(v)} /> : "—"} />
        </RevealItem>
        <RevealItem>
          <StatCard label="Monthly Income"
            value={summary ? <AnimatedNumber value={summary.total_credit} flash format={(v) => inr0(v)} /> : "—"} />
        </RevealItem>
        <RevealItem>
          <StatCard label="Existing EMI" accent="text-amber"
            value={emis ? <AnimatedNumber value={emis.total_emi} flash format={(v) => inr0(v)} /> : "—"} />
        </RevealItem>
        <RevealItem>
          <StatCard
            label="Financial Health"
            value={health ? <AnimatedNumber value={health.overall_score} format={(v) => `${Math.round(v)} / 100`} /> : "—"}
            accent={health ? (health.overall_score >= 75 ? "text-green" : health.overall_score >= 50 ? "text-amber" : "text-red") : "text-text"}
            sub={health?.risk_level}
          />
        </RevealItem>
      </Stagger>

      {/* Health + Cash flow */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <SectionHeader title="Financial Health" sub={`Status: ${health?.risk_level || "—"}`} />
          {health && (
            <>
              <div className="mt-3 flex items-baseline gap-2">
                <AnimatedNumber value={health.overall_score} className="text-4xl font-extrabold" format={(v) => `${Math.round(v)}`} />
                <span className="text-sm text-muted">/ 100</span>
                <span className="ml-auto">
                  <Badge tone={riskTone(health.risk_level)}>{health.risk_level}</Badge>
                </span>
              </div>
              <RiskBar score={health.overall_score} />
              <div className="mt-4 space-y-1.5 text-xs">
                <Row label="Cash score" value={`${health.cash_score}`} />
                <Row label="EMI score" value={`${health.emi_score}`} />
                <Row label="DTI score" value={`${health.dti_score}`} />
                <Row label="Liquidity score" value={`${health.liquidity_score}`} />
              </div>
              {health.warnings.length > 0 && (
                <div className="mt-4 text-xs text-amber">
                  {health.warnings.slice(0, 3).map((w: string, i: number) => (
                    <div key={i} className="mb-1">• {w}</div>
                  ))}
                </div>
              )}
            </>
          )}
        </Card>

        <Card>
          <SectionHeader title="Cash Flow" sub="Total credit vs debit (mock data)" />
          {flow.length > 0 && (
            <div className="mt-4 space-y-4">
              {flow.map((m) => {
                const max = Math.max(m.credit, m.debit, 1);
                return (
                  <div key={m.month}>
                    <div className="flex justify-between text-xs text-text2 mb-1">
                      <span className="font-semibold text-text">{m.month}</span>
                      <span className={m.net >= 0 ? "text-green" : "text-red"}>
                        {inr0(m.net)}
                      </span>
                    </div>
                    <div className="flex gap-2 h-4">
                      <div className="flex-1 bg-card2 rounded relative overflow-hidden">
                        <div className="absolute inset-y-0 left-0 bg-blue rounded" style={{ width: `${(m.credit / max) * 100}%` }} />
                      </div>
                      <div className="flex-1 bg-card2 rounded relative overflow-hidden">
                        <div className="absolute inset-y-0 left-0 bg-red rounded" style={{ width: `${(m.debit / max) * 100}%` }} />
                      </div>
                    </div>
                    <div className="flex gap-2 text-[10px] text-muted mt-1">
                      <span className="flex-1">Credit {inr0(m.credit)}</span>
                      <span className="flex-1">Debit {inr0(m.debit)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Ask the AI", icon: "🤖", to: "advisor" },
          { label: "Loan Advisor", icon: "💰", to: "loans" },
          { label: "Market Data", icon: "📈", to: "markets" },
          { label: "Risk Alerts", icon: "⚠", to: "alerts" },
        ].map((a) => (
          <button key={a.to} onClick={() => goTo(a.to)} className="bg-card border border-border rounded-2xl p-4 text-left hover:border-blue/50 transition-colors">
            <div className="text-2xl">{a.icon}</div>
            <div className="text-sm font-semibold mt-2">{a.label}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-border py-1.5">
      <span className="text-muted">{label}</span>
      <span className="font-semibold text-text">{value}</span>
    </div>
  );
}
