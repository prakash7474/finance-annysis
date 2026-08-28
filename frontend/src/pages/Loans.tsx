import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Card, SectionHeader, Badge, StatCard } from "../components/ui";
import { inr, inr0, riskTone } from "../lib";

export default function Loans() {
  const [amount, setAmount] = useState(300000);
  const [rate, setRate] = useState(12.0);
  const [tenure, setTenure] = useState(36);
  const [income, setIncome] = useState(80000);
  const [existingEmi, setExistingEmi] = useState(22300);
  const [result, setResult] = useState<any>(null);
  const [compare, setCompare] = useState<any>(null);
  const [salaryDrop, setSalaryDrop] = useState(0);
  const [scenario, setScenario] = useState<any>(null);

  function analyze() {
    api
      .analyzeLoan({ amount, rate, tenure_months: tenure, monthly_income: income, existing_emi: existingEmi })
      .then(setResult)
      .catch((e) => setResult({ error: e.message }));
  }

  function compareFn() {
    api
      .compareLoans({ amount, monthly_income: income, existing_emi: existingEmi })
      .then(setCompare)
      .catch((e) => setCompare({ error: e.message }));
  }

  function runScenario() {
    api
      .scenario({
        loan_amount: amount,
        tenure_months: tenure,
        rate,
        monthly_income: income,
        existing_emi: existingEmi,
        salary_change_percent: salaryDrop,
        net_cash: 0,
      })
      .then(setScenario)
      .catch((e) => setScenario({ error: e.message }));
  }

  return (
    <div className="space-y-6">
      <SectionHeader title="Loan Advisor" sub="Understand the true cost of borrowing before you commit." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Single loan */}
        <Card>
          <SectionHeader title="Single Loan" />
          <div className="mt-4 grid grid-cols-2 gap-4">
            <Num id="amount" label="Loan Amount (₹)" value={amount} set={setAmount} step={10000} />
            <Num id="rate" label="Interest Rate (%)" value={rate} set={setRate} step={0.5} />
            <Num id="tenure" label="Tenure (months)" value={tenure} set={setTenure} step={1} />
            <Num id="income" label="Monthly Income (₹)" value={income} set={setIncome} step={5000} />
            <Num id="emi" label="Existing EMI (₹)" value={existingEmi} set={setExistingEmi} step={1000} />
          </div>
          <button onClick={analyze} className="mt-5 w-full py-3 rounded-xl bg-green text-bg font-bold">
            Analyze Loan →
          </button>

          {result && !result.error && (
            <div className="mt-5 grid grid-cols-2 gap-3">
              <StatCard label="Monthly EMI" value={inr0(result.emi)} accent="text-green" />
              <StatCard label="Total Interest" value={inr0(result.total_interest)} accent="text-amber" />
              <StatCard label="Total Cost" value={inr0(result.total_cost)} />
              <StatCard label="EMI / Income" value={`${(result.emi_income_ratio * 100).toFixed(1)}%`} />
              <div className="col-span-2">
                <Badge tone={riskTone(result.risk_level)}>{result.risk_level} RISK</Badge>
                <div className="mt-3 space-y-1 text-xs text-text2">
                  {result.risk_flags.map((f: any, i: number) => (
                    <div key={i}>• {f.message}</div>
                  ))}
                </div>
              </div>
            </div>
          )}
          {result?.error && <div className="mt-4 text-xs text-red">{result.error}</div>}
        </Card>

        {/* Compare */}
        <Card>
          <SectionHeader title="Compare Offers" sub="Ranked by total cost" />
          <button onClick={compareFn} className="mt-4 w-full py-3 rounded-xl bg-blue text-bg font-bold">
            Compare Offers
          </button>
          {compare && !compare.error && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-muted text-left">
                    <th className="py-2">Bank</th>
                    <th className="py-2">Rate</th>
                    <th className="py-2">Tenure</th>
                    <th className="py-2">EMI</th>
                    <th className="py-2">Total</th>
                    <th className="py-2">Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {compare.offers.map((o: any) => (
                    <tr key={o.offer_id} className="border-t border-border">
                      <td className="py-2 font-semibold">{o.bank}</td>
                      <td className="py-2">{o.interest_rate}%</td>
                      <td className="py-2">{o.tenure_months}m</td>
                      <td className="py-2">{inr0(o.emi)}</td>
                      <td className="py-2">{inr0(o.total_cost)}</td>
                      <td className="py-2">
                        <Badge tone={riskTone(o.risk_level)}>{o.risk_level}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {compare.best_by_cost && (
                <div className="mt-3 text-xs text-green">Best by total cost: {compare.best_by_cost.bank} ({inr0(compare.best_by_cost.total_cost)})</div>
              )}
            </div>
          )}
          {compare?.error && <div className="mt-4 text-xs text-red">{compare.error}</div>}
        </Card>
      </div>

      {/* What-if */}
      <Card>
        <SectionHeader title="What-if Simulator" sub="Salary change impact on EMI, DTI, risk and health" />
        <div className="mt-4 flex flex-wrap items-end gap-4">
          <div>
            <div className="text-[11px] text-muted uppercase tracking-widest">Salary change</div>
            <div className="flex items-center gap-2">
              <input type="range" min={-30} max={10} value={salaryDrop} onChange={(e) => setSalaryDrop(Number(e.target.value))} className="w-40 accent-green" />
              <span className={`text-sm font-bold ${salaryDrop < 0 ? "text-red" : "text-green"}`}>{salaryDrop}%</span>
            </div>
          </div>
          <button onClick={runScenario} className="px-5 py-3 rounded-xl bg-green text-bg font-bold">
            Run Simulation
          </button>
        </div>

        {scenario && !scenario.error && (
          <div className="mt-5 grid grid-cols-2 gap-4">
            <div className="bg-card2 rounded-xl p-4">
              <div className="text-[11px] uppercase tracking-widest text-muted">Current</div>
              <CompareRows cur={scenario.current} />
            </div>
            <div className="bg-card2 rounded-xl p-4 border border-blue/30">
              <div className="text-[11px] uppercase tracking-widest text-blue">Scenario</div>
              <CompareRows cur={scenario.scenario} />
            </div>
          </div>
        )}
        {scenario?.error && <div className="mt-4 text-xs text-red">{scenario.error}</div>}
      </Card>
    </div>
  );
}

function Num({ id, label, value, set, step }: { id: string; label: string; value: number; set: (n: number) => void; step: number }) {
  return (
    <div>
      <label className="block text-[11px] text-muted uppercase tracking-widest mb-1">{label}</label>
      <input
        id={id}
        type="number"
        value={value}
        onChange={(e) => set(Number(e.target.value))}
        step={step}
        className="w-full bg-card2 border border-border rounded-xl px-3 py-2.5 text-sm outline-none focus:border-blue"
      />
    </div>
  );
}

function CompareRows({ cur }: { cur: any }) {
  const rows = [
    ["Income", inr0(cur.monthly_income)],
    ["EMI", inr0(cur.emi)],
    ["DTI", cur.dti_ratio != null ? `${(cur.dti_ratio * 100).toFixed(1)}%` : "—"],
    ["Risk", cur.risk],
    ["Health", cur.health_score != null ? `${cur.health_score}/100` : "—"],
  ];
  return (
    <div className="mt-2 space-y-1.5 text-sm">
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between">
          <span className="text-text2">{k}</span>
          <span className="font-semibold text-text">{v}</span>
        </div>
      ))}
    </div>
  );
}
