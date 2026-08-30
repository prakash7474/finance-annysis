import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../services/api";
import { Card, SectionHeader, Badge, RiskBar, StatCard } from "../components/ui";
import { AnimatedNumber, Check, Reveal, RevealItem, Stagger } from "../motion";
import { inr, inr0, riskTone } from "../lib";

const TABS = ["Health", "Forecast", "Goals", "Debt", "Watcher", "Recommendations", "Simulator", "Alerts", "Audit"];

export default function Intelligence() {
  const [tab, setTab] = useState("Health");
  const [facts, setFacts] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [sim, setSim] = useState<any>(null);
  const [recs, setRecs] = useState<any[]>([]);
  const [ai, setAi] = useState<string>("");

  async function reload() {
    setLoading(true);
    try {
      const [health, anomalies, cashf, spendf, goals, debt, alerts, recommendations] = await Promise.all([
        api.financeHealth(),
        api.anomalies(),
        api.cashForecast(30),
        api.spendingForecast(30),
        api.goals(),
        api.debt(),
        api.financialAlerts(),
        api.recommendations(),
      ]);
      setFacts({
        health, anomalies: anomalies.anomalies, forecast: cashf, spending: spendf.spending,
        goals: goals.goals, debt: debt.debt, alerts: alerts.alerts,
      });
      setRecs(recommendations.recommendations);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function runScenario(payload: any) {
    const res = await api.runScenario(payload);
    setSim(res);
  }

  async function narrate() {
    const res = await api.narrateIntelligence("Summarise my financial health.");
    setAi(res.message);
  }

  if (loading && !facts) {
    return <div className="text-text2 animate-pulse">Loading intelligence…</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <SectionHeader title="Intelligence" sub="Autonomous financial intelligence & decision center" />
        <button onClick={reload} className="text-xs px-3 py-2 rounded-lg bg-card border border-border hover:border-blue">
          Reload
        </button>
      </div>

      {/* Tab bar */}
      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-xl text-sm font-semibold ${tab === t ? "bg-green/15 text-green" : "bg-card border border-border text-text2 hover:text-text"}`}>
            {t}
          </button>
        ))}
      </div>

      {tab === "Health" && facts?.health && (
        <Reveal className="grid lg:grid-cols-3 gap-6">
          <Card>
            <StatCard label="Health Score"
              value={<AnimatedNumber value={facts.health.score} flash format={(v) => `${Math.round(v)}/100`} />}
              accent={facts.health.score >= 70 ? "text-green" : facts.health.score >= 50 ? "text-amber" : "text-red"} />
            <RiskBar score={facts.health.score} />
            <div className="mt-4"><Badge tone={riskTone(facts.health.status)}>{facts.health.status}</Badge></div>
            <div className="mt-4 space-y-1.5 text-xs">
              <Row k="Liquidity" v={`${facts.health.liquidity_score}`} />
              <Row k="Debt" v={`${facts.health.debt_score}`} />
              <Row k="Expense" v={`${facts.health.expense_score}`} />
              <Row k="Savings" v={`${facts.health.savings_score}`} />
            </div>
          </Card>
          <Card className="lg:col-span-2">
            <SectionHeader title="Why this score" sub="Deterministic formula, never Gemini-calculated" />
            <div className="mt-4 grid grid-cols-2 gap-3">
              <StatCard label="Net Cash" value={inr0(facts.health.net_cash)} accent="text-green" />
              <StatCard label="Monthly Income" value={inr0(facts.health.monthly_income)} />
              <StatCard label="Monthly Expenses" value={inr0(facts.health.monthly_expenses)} />
              <StatCard label="DTI" value={`${(facts.health.dti * 100).toFixed(1)}%`} accent="text-amber" />
            </div>
            <div className="mt-4 space-y-1">
              {(facts.health.reasons || []).map((r: string, i: number) => (
                <div key={i} className="text-xs text-amber">• {r}</div>
              ))}
            </div>
            <button onClick={narrate} className="mt-4 px-4 py-2 rounded-lg bg-blue text-bg text-sm font-bold">✨ AI Explain</button>
            {ai && <div className="mt-3 text-sm text-text2 whitespace-pre-wrap">{ai}</div>}
          </Card>
        </Reveal>
      )}

      {tab === "Forecast" && facts?.forecast && (
        <div className="space-y-6">
          <Card>
            <SectionHeader title="Cash-Flow Forecast" sub="Projection, not a guarantee" />
            <div className="flex flex-wrap gap-2 my-3">
              {[7, 14, 30, 60, 90].map((d) => (
                <button key={d} onClick={() => setDays(d)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold ${days === d ? "bg-green/20 text-green" : "bg-card border border-border"}`}>
                  {d}d
                </button>
              ))}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Projected Balance" value={inr0(facts.forecast.projected_balance)} accent="text-green" />
              <StatCard label="Projected Income" value={inr0(facts.forecast.projected_income)} />
              <StatCard label="Projected Expenses" value={inr0(facts.forecast.projected_expenses)} accent="text-red" />
              <StatCard label="Projected EMI" value={inr0(facts.forecast.projected_emi)} accent="text-amber" />
            </div>
            <div className="mt-3">
              <Badge tone={riskTone(facts.forecast.risk_level)}>{facts.forecast.risk_level} risk</Badge>
              <span className="ml-3 text-xs text-muted">confidence {facts.forecast.confidence}</span>
            </div>
          </Card>
          <Card>
            <SectionHeader title="Spending Forecast" sub="Per category" />
            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
              {(facts.spending || []).slice(0, 12).map((s: any) => (
                <div key={s.category} className="flex justify-between border-b border-border py-2 text-sm">
                  <span>{s.category}</span>
                  <span className="font-semibold text-text">{inr0(s.projected_amount)}
                    <span className="ml-2 text-xs text-muted">{s.risk_level}</span>
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {tab === "Goals" && (
        <GoalsTab facts={facts} onReload={reload} />
      )}

      {tab === "Debt" && facts?.debt && (
        <Card>
          <SectionHeader title="Debt Optimization" sub="Ranked by total cost (deterministic)" />
          <div className="mt-3 space-y-2">
            {(facts.debt || []).map((d: any) => (
              <div key={d.loan_id} className="border border-border rounded-xl p-3 bg-card2">
                <div className="flex justify-between">
                  <span className="font-semibold">#{d.priority} {d.bank}</span>
                  <Badge tone="amber">{d.strategy}</Badge>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                  <Mini k="EMI" v={inr0(d.monthly_emi)} />
                  <Mini k="Interest" v={inr0(d.estimated_interest)} />
                  <Mini k="DTI impact" v={`${(d.dti_impact * 100).toFixed(1)}%`} />
                </div>
                <div className="mt-2 text-[11px] text-muted">{d.reason_codes.join(" · ")}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {tab === "Watcher" && <WatcherTab />}

      {tab === "Recommendations" && (
        <RecommendationsTab recs={recs} setRecs={setRecs} />
      )}

      {tab === "Simulator" && <SimulatorTab onRun={runScenario} sim={sim} />}

      {tab === "Alerts" && (
        <Card>
          <SectionHeader title="Smart Alerts" sub="Priority-ordered" />
          <div className="mt-3 space-y-2">
            {(facts?.alerts || []).map((a: any, i: number) => (
              <div key={i} className="border border-border rounded-xl p-3 bg-card2 flex items-start gap-3">
                <Badge tone={a.severity === "HIGH" || a.severity === "CRITICAL" ? "red" : a.severity === "MEDIUM" ? "amber" : "blue"}>
                  {a.severity}
                </Badge>
                <div>
                  <div className="text-sm font-semibold">{a.title}</div>
                  <div className="text-xs text-text2 mt-0.5">{a.description}</div>
                  {a.recommended_action && <div className="text-[11px] text-blue mt-1">→ {a.recommended_action}</div>}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {tab === "Audit" && <AuditTab />}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return <div className="flex justify-between border-b border-border py-1"><span className="text-muted">{k}</span><span className="font-semibold">{v}</span></div>;
}
function Mini({ k, v }: { k: string; v: string }) {
  return <div className="bg-card border border-border rounded-lg p-2"><div className="text-[10px] uppercase text-muted">{k}</div><div className="font-semibold mt-0.5">{v}</div></div>;
}

function GoalsTab({ facts, onReload }: { facts: any; onReload: () => void }) {
  const [target, setTarget] = useState(200000);
  const [months, setMonths] = useState(8);
  const [current, setCurrent] = useState(40000);
  const [created, setCreated] = useState<any>(null);

  async function create() {
    const res = await api.createGoal({ target_amount: target, months_remaining: months, current_saved_amount: current });
    setCreated(res);
    onReload();
  }

  return (
    <div className="space-y-6">
      <Card>
        <SectionHeader title="New Goal" />
        <div className="mt-3 grid grid-cols-3 gap-3">
          <Field label="Target (₹)" value={target} set={setTarget} step={10000} />
          <Field label="Months" value={months} set={setMonths} step={1} />
          <Field label="Current saved (₹)" value={current} set={setCurrent} step={5000} />
        </div>
        <button onClick={create} className="mt-4 px-5 py-2.5 rounded-xl bg-green text-bg font-bold">Create Goal</button>
        {created && (
          <Stagger className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            <RevealItem>
              <StatCard label="Required / mo" accent="text-green"
                value={<AnimatedNumber value={created.required_monthly_saving} flash format={(v) => inr0(v)} />} />
            </RevealItem>
            <RevealItem>
              <StatCard label="Capacity / mo"
                value={<AnimatedNumber value={created.current_saving_capacity} flash format={(v) => inr0(v)} />} />
            </RevealItem>
            <RevealItem>
              <StatCard label="Shortfall / mo" accent="text-red"
                value={<AnimatedNumber value={created.monthly_shortfall} flash format={(v) => inr0(v)} />} />
            </RevealItem>
            <RevealItem>
              <StatCard label="Status" value={created.status} />
            </RevealItem>
          </Stagger>
        )}
      </Card>
      <Card>
        <SectionHeader title="Goals" sub="From current financial profile" />
        <div className="mt-3 space-y-2">
          {(facts?.goals || []).map((g: any) => (
            <div key={g.goal_id} className="border border-border rounded-xl p-3 bg-card2">
              <div className="flex justify-between">
                <span className="font-semibold">{g.name}</span>
                <Badge tone={g.status === "COMPLETED" ? "green" : g.status === "SHORTFALL" ? "red" : "blue"}>{g.status}</Badge>
              </div>
              <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                <Mini k="Target" v={inr0(g.target_amount)} />
                <Mini k="Remaining" v={inr0(g.remaining_amount)} />
                <Mini k="Required / mo" v={inr0(g.required_monthly_saving)} />
                <Mini k="Shortfall / mo" v={inr0(g.monthly_shortfall)} />
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function Field({ label, value, set, step }: { label: string; value: number; set: (n: number) => void; step: number }) {
  return (
    <div>
      <label className="block text-[11px] text-muted uppercase tracking-widest mb-1">{label}</label>
      <input type="number" value={value} onChange={(e) => set(Number(e.target.value))} step={step}
        className="w-full bg-card2 border border-border rounded-xl px-3 py-2.5 text-sm outline-none focus:border-blue" />
    </div>
  );
}

function WatcherTab() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    (async () => {
      const [p, t, m] = await Promise.all([
        api.marketPrice("RELIANCE"), api.marketTrend("RELIANCE"), api.marketMomentum("RELIANCE"),
      ]);
      const [p2, t2] = await Promise.all([api.marketPrice("TCS"), api.marketTrend("TCS")]);
      setData({ reliance: { p, t, m }, tcs: { p: p2, t: t2 } });
    })();
  }, []);
  if (!data) return <div className="text-text2 animate-pulse">Loading watcher…</div>;
  const rows = [
    ["RELIANCE", data.reliance.p.price, data.reliance.t.trend, data.reliance.m.momentum_pct],
    ["TCS", data.tcs.p.price, data.tcs.t.trend, null],
  ];
  return (
    <Card>
      <SectionHeader title="Market Watcher" sub="Analysis only - never places trades" />
      <table className="w-full text-sm mt-3">
        <thead>
          <tr className="text-muted text-left">
            <th className="py-2">Symbol</th><th className="py-2">Price</th><th className="py-2">Trend</th><th className="py-2">Momentum</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([s, price, trend, mom]) => (
            <tr key={s} className="border-t border-border">
              <td className="py-2 font-semibold">{s}</td>
              <td className="py-2">{inr(price)}</td>
              <td className="py-2"><Badge tone={riskTone(trend === "UPTREND" ? "HEALTHY" : trend === "DOWNTREND" ? "HIGH" : "MODERATE")}>{trend}</Badge></td>
              <td className="py-2">{mom != null ? `${mom >= 0 ? "+" : ""}${mom.toFixed(2)}%` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function RecommendationsTab({ recs, setRecs }: { recs: any[]; setRecs: (r: any[]) => void }) {
  async function act(rec: any, action: "approve" | "reject") {
    const res = action === "approve"
      ? await api.approveRecommendation(rec.recommendation_id)
      : await api.rejectRecommendation(rec.recommendation_id);
    setRecs(recs.map((r) => r.recommendation_id === rec.recommendation_id ? { ...r, status: res.status } : r));
  }
  return (
    <Card>
      <SectionHeader title="AI Recommendations" sub="Informational guidance - human approval required before any action" />
      <div className="mt-3 space-y-3">
        {recs.map((r: any) => (
          <motion.div
            key={r.recommendation_id}
            animate={{ borderColor: r.status === "APPROVED" ? "#1a3a2a" : r.status === "REJECTED" ? "#3a1a20" : "var(--border)" }}
            transition={{ duration: 0.35 }}
            className="border rounded-xl p-3 bg-card2"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold inline-flex items-center gap-2">
                #{r.priority} {r.title}
                {r.status === "APPROVED" && <span className="text-green"><Check /></span>}
                {r.status === "REJECTED" && <span className="text-red">✕</span>}
              </span>
              <Badge tone={r.status === "APPROVED" ? "green" : r.status === "REJECTED" ? "red" : r.requires_approval ? "amber" : "blue"}>
                {r.status}
              </Badge>
            </div>
            <div className="mt-1 text-[11px] text-muted">
              {r.reason_codes.join(" · ")} · confidence {r.confidence}
            </div>
            {r.requires_approval && r.status === "PENDING" && (
              <div className="mt-3 flex gap-2">
                <button onClick={() => act(r, "approve")} className="px-4 py-2 rounded-lg bg-green text-bg text-sm font-bold">Approve</button>
                <button onClick={() => act(r, "reject")} className="px-4 py-2 rounded-lg bg-red text-white text-sm font-bold">Reject</button>
              </div>
            )}
          </motion.div>
        ))}
      </div>
    </Card>
  );
}

function SimulatorTab({ onRun, sim }: { onRun: (p: any) => void; sim: any }) {
  const [salary, setSalary] = useState(-10);
  const [expense, setExpense] = useState(15);
  const [loan, setLoan] = useState(200000);
  function run() {
    onRun({ salary_change_percentage: salary, expense_change_percentage: expense, new_loan_amount: loan, new_loan_rate: 12, new_loan_tenure: 36 });
  }
  return (
    <Card>
      <SectionHeader title="Financial Digital Twin" sub="Simulates changes; original data is never modified" />
      <div className="mt-3 grid grid-cols-3 gap-3">
        <div>
          <label className="text-[11px] text-muted uppercase tracking-widest">Salary change</label>
          <div className="flex items-center gap-2 mt-1">
            <input type="range" min={-30} max={20} value={salary} onChange={(e) => setSalary(Number(e.target.value))} className="w-full accent-green" />
            <span className={`text-sm font-bold ${salary < 0 ? "text-red" : "text-green"}`}>{salary}%</span>
          </div>
        </div>
        <div>
          <label className="text-[11px] text-muted uppercase tracking-widest">Expense change</label>
          <div className="flex items-center gap-2 mt-1">
            <input type="range" min={-20} max={40} value={expense} onChange={(e) => setExpense(Number(e.target.value))} className="w-full accent-amber" />
            <span className={`text-sm font-bold ${expense > 0 ? "text-red" : "text-green"}`}>{expense}%</span>
          </div>
        </div>
        <Field label="New loan (₹)" value={loan} set={setLoan} step={10000} />
      </div>
      <button onClick={run} className="mt-4 px-6 py-2.5 rounded-xl bg-blue text-bg font-bold">Simulate</button>

      <AnimatePresence mode="wait">
        {sim && (
          <motion.div key={sim.scenario_id || Math.random()}
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.35, ease: [0, 0, 0.2, 1] }}
            className="mt-5 grid grid-cols-2 gap-4">
            <div className="bg-card2 rounded-xl p-4">
              <div className="text-[11px] uppercase tracking-widest text-muted">Current</div>
              <SimRows s={sim.baseline} />
            </div>
            <div className="bg-card2 rounded-xl p-4 border border-blue/30">
              <div className="text-[11px] uppercase tracking-widest text-blue">Simulated</div>
              <SimRows s={sim.simulated} />
            </div>
            <div className="col-span-2">
              <div className="text-xs font-bold mb-2">Recommendations</div>
              {(sim.recommendations || []).map((r: string, i: number) => (
                <div key={i} className="text-xs text-text2 mb-1">• {r}</div>
              ))}
              <Reveal delay={0.1} className="mt-3 text-[10px] text-muted">
                simulated — original data unchanged
              </Reveal>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

function SimRows({ s }: { s: any }) {
  const rows = [
    ["Income", inr0(s.monthly_income)],
    ["Expenses", inr0(s.monthly_expenses)],
    ["EMI", inr0(s.new_emi)],
    ["DTI", s.dti != null ? `${(s.dti * 100).toFixed(1)}%` : "—"],
    ["Cash flow", inr0(s.cash_flow)],
    ["Health", s.health_score != null ? `${s.health_score}/100` : "—"],
    ["Risk", s.risk_level || "—"],
  ];
  return <div className="mt-2 space-y-1.5 text-sm">{rows.map(([k, v]) => (
    <div key={k} className="flex justify-between"><span className="text-text2">{k}</span><span className="font-semibold text-text">{v}</span></div>
  ))}</div>;
}

function AuditTab() {
  const [trace, setTrace] = useState("");
  const [data, setData] = useState<any>(null);
  async function load(id: string) {
    setData(await api.audit(id).catch(() => ({ audit: [{ operation: "not found" }] })));
  }
  useEffect(() => {
    load(trace || "sample");
  }, [trace]);
  return (
    <Card>
      <SectionHeader title="Audit / Trace Viewer" sub="Every decision is traceable" />
      <div className="mt-3 flex gap-2">
        <input value={trace} onChange={(e) => setTrace(e.target.value)} placeholder="trace_id (e.g. run a scenario, then paste its trace_id)"
          className="flex-1 bg-card2 border border-border rounded-xl px-3 py-2 text-sm outline-none focus:border-blue" />
        <button onClick={() => load(trace)} className="px-4 rounded-xl bg-blue text-bg text-sm font-bold">View</button>
      </div>
      <div className="mt-3 space-y-2">
        {(data?.audit || []).map((e: any, i: number) => (
          <div key={i} className="border border-border rounded-xl p-3 bg-card2 text-xs">
            <div className="flex justify-between">
              <span className="font-semibold">{e.operation}</span>
              <span>{e.status} · {e.timestamp}</span>
            </div>
            <div className="mt-1 text-muted">{e.decision_id} · trace {e.trace_id}</div>
            {e.approval_status && <div className="mt-1 text-green">approval: {e.approval_status} · execution: {e.execution_status}</div>}
          </div>
        ))}
      </div>
    </Card>
  );
}
