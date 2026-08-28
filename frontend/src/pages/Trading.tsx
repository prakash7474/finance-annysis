import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Card, SectionHeader, Badge, StatCard } from "../components/ui";
import { inr, inr0 } from "../lib";

const SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"];
const ACCOUNTS = [
  { id: "ACC_CONSERVATIVE", label: "Rajesh — Conservative" },
  { id: "ACC_MODERATE", label: "Sneha — Moderate" },
  { id: "ACC_AGGRESSIVE", label: "Arjun — Aggressive" },
];

export default function Trading() {
  const [accountId, setAccountId] = useState("ACC_CONSERVATIVE");
  const [symbol, setSymbol] = useState("RELIANCE");
  const [account, setAccount] = useState<any>(null);
  const [quote, setQuote] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [order, setOrder] = useState<any>(null);
  const [trace, setTrace] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);

  async function load() {
    const [acc, qt] = await Promise.all([api.tradingAccount(accountId), api.marketLatest(symbol)]);    setAccount(acc);
    setQuote(qt);
  }

  useEffect(() => {
    load();
    // auto-refresh market tick
    const t = setInterval(() => {
      api.marketLatest(symbol).then(setQuote);
    }, 1500);
    return () => clearInterval(t);
  }, [accountId, symbol]);

  async function propose(override = false) {
    setBusy(true);
    try {
      const res = await api.allocate({ account_id: accountId, symbol, override_limits: override });
      setResult(res);
      setTrace(await api.tradingTraceId(res.trace_id).then((r) => r.audit || []));
    } catch (e: any) {
      setResult({ error: e.message });
    } finally {
      setBusy(false);
    }
  }

  async function executeDecision() {
    if (!result || result.decision.status === "REJECTED") return;
    const qty = result.decision.final_quantity;
    if (qty <= 0) return;
    try {
      const res = await api.placePaperOrder({ account_id: accountId, symbol, side: "BUY", quantity: qty });
      setOrder(res);
      load();
    } catch (e: any) {
      setOrder({ error: e.message });
    }
  }

  const riskTone = (p: string) => (p === "conservative" ? "green" : p === "aggressive" ? "red" : "amber");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <SectionHeader title="AI Trading Allocation" sub="Rules engine has final say over the AI — PAPER TRADING ONLY (simulated, no real money)" />
        <Badge tone="amber">Paper Trading — Simulated</Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Market + account */}
        <div className="space-y-6">
          <Card>
            <SectionHeader title="Market Realtime (replay)" sub="Accelerated feed — simulated" />
            <div className="mt-3 flex flex-wrap gap-2">
              {SYMBOLS.map((s) => (
                <button key={s} onClick={() => setSymbol(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold ${symbol === s ? "bg-blue/20 text-blue" : "bg-card border border-border"}`}>
                  {s}
                </button>
              ))}
            </div>
            {quote && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <StatCard label="Price" value={inr(quote.price)} accent="text-green" />
                <StatCard label="20D SMA" value={quote.sma ? inr(quote.sma) : "—"} />
                <StatCard label="Trend" value={quote.trend || "—"} />
                <StatCard label="Realized Vol" value={quote.realized_volatility != null ? `${quote.realized_volatility}%` : "—"} />
              </div>
            )}
          </Card>

          <Card>
            <SectionHeader title="Account" sub="Mocked demo accounts (paper)" />
            <div className="mt-3 flex flex-wrap gap-2">
              {ACCOUNTS.map((a) => (
                <button key={a.id} onClick={() => setAccountId(a.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold ${accountId === a.id ? "bg-green/20 text-green" : "bg-card border border-border"}`}>
                  {a.label}
                </button>
              ))}
            </div>
            {account && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <StatCard label="Cash" value={inr0(account.cash_balance)} />
                <StatCard label="Portfolio" value={inr0(account.portfolio_value)} />
                <div className="col-span-2 flex items-center gap-2">
                  <span className="text-xs text-muted">Risk profile:</span>
                  <Badge tone={riskTone(account.risk_profile)}>{account.risk_profile}</Badge>
                </div>
                <div className="col-span-2 space-y-1 text-xs">
                  {(account.holdings || []).map((h: any) => (
                    <div key={h.symbol} className="flex justify-between border-b border-border py-1">
                      <span>{h.symbol}</span><span>{h.quantity} @ {inr(h.avg_price)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Allocation decision */}
        <Card>
          <SectionHeader title="Stage 1 → Stage 2" sub="AI proposes · rules engine decides" />
          <div className="mt-3 flex flex-wrap gap-2">
            <button onClick={() => propose(false)} disabled={busy} className="px-5 py-2.5 rounded-xl bg-green text-bg font-bold disabled:opacity-50">
              Propose Allocation
            </button>
            <button onClick={() => propose(true)} disabled={busy} className="px-5 py-2.5 rounded-xl bg-red text-white font-bold disabled:opacity-50">
              Try to Override Limits
            </button>
          </div>
          <div className="mt-2 text-[11px] text-muted">"Ignore the limits / go all-in" is still blocked by the rules engine.</div>

          {result && !result.error && (
            <div className="mt-4 space-y-3">
              <div className="border border-border rounded-xl p-3 bg-card2">
                <div className="text-[11px] uppercase tracking-widest text-muted">AI Proposal (Stage 1)</div>
                <div className="mt-2 text-sm">{result.proposal.symbol} {result.proposal.side} · {result.proposal.proposed_quantity} sh</div>
                <div className="text-xs text-text2 mt-1">confidence {result.proposal.confidence} · {result.proposal.rationale}</div>
              </div>
              <div className="border border-amber/30 rounded-xl p-3 bg-card2">
                <div className="text-[11px] uppercase tracking-widest text-amber">Rules Engine (Stage 2)</div>
                <div className="mt-2 text-sm font-semibold">
                  {result.decision.status} — {result.decision.reason}
                </div>
                <div className="mt-2 space-y-1">
                  {(result.decision.rules || []).map((r: any, i: number) => (
                    <div key={i} className="text-xs flex items-center gap-2">
                      <span className={r.passed ? "text-green" : "text-red"}>{r.passed ? "✓" : "✗"}</span>
                      <span className="text-text2">{r.message}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-2 text-xs">
                  Final size: <span className="font-bold">{result.decision.final_quantity}</span> sh
                  ({inr(result.decision.final_value)}) <Badge tone={result.decision.status === "EXECUTE" ? "green" : result.decision.status === "RESIZED" ? "amber" : "red"}>{result.decision.status}</Badge>
                </div>
              </div>
              {result.decision.status !== "REJECTED" && (
                <button onClick={executeDecision} className="px-5 py-2.5 rounded-xl bg-blue text-bg font-bold">
                  Place Paper Order
                </button>
              )}
            </div>
          )}
          {result?.error && <div className="mt-3 text-xs text-red">{result.error}</div>}

          {order && !order.error && (
            <div className="mt-4 border border-green/30 rounded-xl p-3 bg-card2 text-sm">
              <div className="font-semibold text-green">Paper order {order.order.status}</div>
              <div className="text-xs text-text2 mt-1">
                {order.order.symbol} {order.order.side} {order.order.quantity} @ {inr(order.order.fill_price)}
                (slippage {order.order.slippage_pct * 100}%)
              </div>
              <div className="text-xs text-text2">Remaining cash: {inr0(order.snapshot.cash_balance)}</div>
            </div>
          )}
          {order?.error && <div className="mt-3 text-xs text-red">{order.error}</div>}
        </Card>
      </div>

      {/* Trace */}
      <Card>
        <SectionHeader title="Trace / Audit Chain" sub="market facts → proposal → rules → decision → order (Phase 5)" />
        <div className="mt-3 space-y-2">
          {trace.length === 0 && <div className="text-xs text-muted">Run a proposal to populate the trace.</div>}
          {trace.map((e: any, i: number) => (
            <div key={i} className="border border-border rounded-lg p-3 bg-card2 text-xs">
              <div className="flex justify-between">
                <span className="font-semibold">{e.operation}</span>
                <span className="text-muted">{e.timestamp} · {e.status}</span>
              </div>
              <div className="mt-1 text-muted font-mono">{e.decision_id} · trace {e.trace_id}</div>
              {e.facts && Object.keys(e.facts).length > 0 && (
                <pre className="mt-2 text-[10px] text-text2 overflow-x-auto">{JSON.stringify(e.facts, null, 1).slice(0, 900)}</pre>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
