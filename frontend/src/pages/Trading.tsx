import { useEffect, useState, useRef, useCallback } from "react";
import { api, openVolatilityStream } from "../services/api";
import { Card, CardRaised, SectionHeader, Badge, StatCard, MonoValue } from "../components/ui";
import { inr, inr0 } from "../lib";

const SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"];
const ACCOUNTS = [
  { id: "ACC_CONSERVATIVE", label: "Rajesh — Conservative" },
  { id: "ACC_MODERATE", label: "Sneha — Moderate" },
  { id: "ACC_AGGRESSIVE", label: "Arjun — Aggressive" },
];

// ── Sparkline component ─────────────────────────────────────────────────
function Sparkline({ values, color = "#3DDC97", width = 120, height = 28 }: { values: number[]; color?: string; width?: number; height?: number }) {
  if (!values || values.length < 2) return <div style={{ width, height }} />;
  const mn = Math.min(...values);
  const mx = Math.max(...values);
  const span = (mx - mn) || 1;
  const step = width / (values.length - 1);
  const pts = values.map((v, i) => {
    const x = i * step;
    const y = height - 2 - ((v - mn) / span) * (height - 4);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const fillPts = `0,${height - 2} ${pts} ${width},${height - 2}`;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <polygon points={fillPts} fill={color} opacity={0.08} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── Volatility spike indicator ──────────────────────────────────────────
function SpikeIndicator({ spikes }: { spikes: { symbol: string; price: number; vol: number; time: string }[] }) {
  if (spikes.length === 0) return null;
  const latest = spikes[0];
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-amber/10 border border-amber/30 text-[11px]">
      <span className="status-dot reconnecting" style={{ background: "#D9A441", boxShadow: "0 0 6px #D9A441" }} />
      <span className="font-mono font-bold text-amber">VOLATILITY SPIKE</span>
      <span className="text-text2">{latest.symbol}</span>
      <MonoValue className="text-text2">{inr(latest.price)}</MonoValue>
      <span className="text-muted">vol {latest.vol}%</span>
    </div>
  );
}

// ── Decision trace stage ────────────────────────────────────────────────
function DecisionStage({
  label,
  content,
  delay,
  boost = false,
}: {
  label: string;
  content: React.ReactNode;
  delay: number;
  boost?: boolean;
}) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(t);
  }, [delay]);

  if (!visible) return null;
  return (
    <div className={`stage-reveal ${boost ? "override-boost" : ""}`} style={{ animationDelay: `${delay}ms` }}>
      <div className="border border-border rounded-lg p-3 bg-panel-raised">
        <div className="text-[10px] uppercase tracking-[0.15em] text-muted font-semibold">{label}</div>
        <div className="mt-1.5">{content}</div>
      </div>
    </div>
  );
}

// ── Main Trading page ───────────────────────────────────────────────────
export default function Trading() {
  const [accountId, setAccountId] = useState("ACC_CONSERVATIVE");
  const [symbol, setSymbol] = useState("RELIANCE");
  const [account, setAccount] = useState<any>(null);
  const [quote, setQuote] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [order, setOrder] = useState<any>(null);
  const [trace, setTrace] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [overrideUsed, setOverrideUsed] = useState(false);
  const [feedStatus, setFeedStatus] = useState<"connected" | "reconnecting" | "error">("connected");
  const [priceHistory, setPriceHistory] = useState<number[]>([]);
  const [priceFlash, setPriceFlash] = useState<"up" | "down" | null>(null);
  const [spikes, setSpikes] = useState<{ symbol: string; price: number; vol: number; time: string }[]>([]);
  const prevPrice = useRef<number | null>(null);

  // Subscribe to volatility_spike SSE events for real-time sparkline updates
  useEffect(() => {
    const es = openVolatilityStream((data) => {
      if (data.symbol === symbol && data.price) {
        // Add spike price to sparkline
        setPriceHistory((prev) => [...prev.slice(-30), data.price]);
        setPriceFlash("up"); // spikes are upward
        setTimeout(() => setPriceFlash(null), 800);
        prevPrice.current = data.price;

        // Track spike events
        setSpikes((prev) => [
          { symbol: data.symbol, price: data.price, vol: data.realized_volatility, time: new Date().toLocaleTimeString() },
          ...prev.slice(0, 5),
        ]);
      }
    });
    return () => es.close();
  }, [symbol]);

  async function load() {
    try {
      const [acc, qt] = await Promise.all([api.tradingAccount(accountId), api.marketLatest(symbol)]);
      setAccount(acc);
      setQuote(qt);
      setFeedStatus("connected");
      // Track price history for sparkline
      if (qt?.price) {
        setPriceHistory((prev) => [...prev.slice(-30), qt.price]);
        // Flash on price change
        if (prevPrice.current !== null && qt.price !== prevPrice.current) {
          setPriceFlash(qt.price > prevPrice.current ? "up" : "down");
          setTimeout(() => setPriceFlash(null), 800);
        }
        prevPrice.current = qt.price;
      }
    } catch {
      setFeedStatus("error");
    }
  }

  useEffect(() => {
    load();
    // Polling as fallback (SSE provides real-time spikes, polling fills gaps)
    const t = setInterval(() => {
      api.marketLatest(symbol).then((qt) => {
        setQuote(qt);
        setFeedStatus("connected");
        if (qt?.price) {
          setPriceHistory((prev) => [...prev.slice(-30), qt.price]);
          if (prevPrice.current !== null && qt.price !== prevPrice.current) {
            setPriceFlash(qt.price > prevPrice.current ? "up" : "down");
            setTimeout(() => setPriceFlash(null), 800);
          }
          prevPrice.current = qt.price;
        }
      }).catch(() => setFeedStatus("reconnecting"));
    }, 1500);
    return () => clearInterval(t);
  }, [accountId, symbol]);

  async function propose(override = false) {
    setBusy(true);
    setOverrideUsed(override);
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
  const hasRuleOverride = result?.adjusted_for?.length > 0;

  return (
    <div className="space-y-4">
      {/* ── Top strip: Account snapshot ──────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Cash" value={account ? inr0(account.cash_balance) : "—"} mono />
        <StatCard label="Portfolio" value={account ? inr0(account.portfolio_value) : "—"} mono />
        <StatCard label="Price" value={quote ? inr(quote.price) : "—"} mono accent={
          priceFlash === "up" ? "price-flash-up text-green" : priceFlash === "down" ? "price-flash-down text-red" : "text-text"
        } />
        <StatCard label="Trend" value={quote?.trend || "—"} />
      </div>

      {/* ── Volatility spike indicator ──────────────────────────────────── */}
      <SpikeIndicator spikes={spikes} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ── Left: Market panel ──────────────────────────────────────────── */}
        <div className="space-y-4">
          {/* Market data panel */}
          <Card>
            <SectionHeader title="Market Realtime" sub="Accelerated feed — simulated" />
            {/* Symbol selector */}
            <div className="mt-2 flex flex-wrap gap-1.5">
              {SYMBOLS.map((s) => (
                <button
                  key={s}
                  onClick={() => setSymbol(s)}
                  className={`px-2.5 py-1 rounded text-[11px] font-mono font-bold transition-colors ${
                    symbol === s ? "bg-green/15 text-green border border-green/30" : "bg-panel-raised border border-border text-text2 hover:text-text"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
            {/* Feed status */}
            {feedStatus !== "connected" && (
              <div className="mt-2 flex items-center gap-2 text-[11px] text-amber">
                <span className="status-dot reconnecting" />
                Feed {feedStatus === "reconnecting" ? "reconnecting…" : "disconnected — retrying"}
              </div>
            )}
            {/* Price display */}
            {quote && (
              <div className="mt-3 grid grid-cols-2 gap-2">
                <div className="bg-panel-raised rounded-lg p-3 border border-border">
                  <div className="text-[9px] uppercase tracking-widest text-muted">20D SMA</div>
                  <MonoValue className="text-lg font-bold text-text mt-1">{quote.sma ? inr(quote.sma) : "—"}</MonoValue>
                </div>
                <div className="bg-panel-raised rounded-lg p-3 border border-border">
                  <div className="text-[9px] uppercase tracking-widest text-muted">Realized Vol</div>
                  <MonoValue className="text-lg font-bold text-text mt-1">
                    {quote.realized_volatility != null ? `${quote.realized_volatility}%` : "—"}
                  </MonoValue>
                </div>
              </div>
            )}
            {/* Sparkline */}
            {priceHistory.length >= 2 && (
              <div className="mt-3 bg-panel-raised rounded-lg p-3 border border-border">
                <div className="text-[9px] uppercase tracking-widest text-muted mb-2">Price History</div>
                <Sparkline values={priceHistory} color={priceFlash === "down" ? "#E85D5D" : "#3DDC97"} />
              </div>
            )}
          </Card>

          {/* Account panel */}
          <Card>
            <SectionHeader title="Account" sub="Mocked demo accounts (paper)" />
            <div className="mt-2 flex flex-wrap gap-1.5">
              {ACCOUNTS.map((a) => (
                <button
                  key={a.id}
                  onClick={() => setAccountId(a.id)}
                  className={`px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
                    accountId === a.id ? "bg-green/15 text-green border border-green/30" : "bg-panel-raised border border-border text-text2 hover:text-text"
                  }`}
                >
                  {a.label}
                </button>
              ))}
            </div>
            {account && (
              <div className="mt-2 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-muted">Risk:</span>
                  <Badge tone={riskTone(account.risk_profile)}>{account.risk_profile}</Badge>
                </div>
                {/* Holdings table */}
                {account.holdings?.length > 0 && (
                  <div className="bg-panel-raised rounded border border-border overflow-hidden">
                    <table className="w-full text-[11px]">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="text-left py-1.5 px-2 text-muted font-semibold uppercase tracking-wider">Symbol</th>
                          <th className="text-right py-1.5 px-2 text-muted font-semibold">Qty</th>
                          <th className="text-right py-1.5 px-2 text-muted font-semibold">Avg Price</th>
                        </tr>
                      </thead>
                      <tbody>
                        {account.holdings.map((h: any) => (
                          <tr key={h.symbol} className="border-b border-border/50 last:border-0">
                            <td className="py-1.5 px-2 font-mono font-semibold text-text">{h.symbol}</td>
                            <td className="py-1.5 px-2 text-right font-mono text-text2">{h.quantity}</td>
                            <td className="py-1.5 px-2 text-right font-mono text-text2">{inr(h.avg_price)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>

        {/* ── Right: Decision trace panel ─────────────────────────────────── */}
        <CardRaised className={hasRuleOverride ? "rule-pulse" : ""}>
          <SectionHeader title="Decision Trace" sub="AI proposes → rules engine decides" />
          {/* Action buttons */}
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              onClick={() => propose(false)}
              disabled={busy}
              className="px-4 py-2 rounded-lg bg-green text-bg text-xs font-bold disabled:opacity-50 transition-colors"
            >
              {busy ? "Processing…" : "Propose Allocation"}
            </button>
            <button
              onClick={() => propose(true)}
              disabled={busy}
              className="px-4 py-2 rounded-lg bg-red/90 text-white text-xs font-bold disabled:opacity-50 transition-colors"
            >
              Try Override Limits
            </button>
          </div>
          <div className="mt-1 text-[10px] text-muted italic">
            "Ignore the limits" is still blocked by the rules engine.
          </div>

          {/* Empty state */}
          {!result && !busy && (
            <div className="mt-6 text-center py-8">
              <div className="text-2xl mb-2 opacity-30">📊</div>
              <div className="text-xs text-muted">Run a proposal to see the decision trace.</div>
              <div className="text-[10px] text-muted mt-1">The AI proposes, the rules engine decides.</div>
            </div>
          )}

          {/* Loading state */}
          {busy && (
            <div className="mt-4 text-center py-6">
              <div className="text-xs text-text2 font-semibold">Running allocation pipeline…</div>
              <div className="mt-2 flex justify-center gap-1">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="w-1.5 h-1.5 rounded-full bg-green animate-pulse" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          )}

          {/* Error state */}
          {result?.error && (
            <div className="mt-3 bg-red/10 border border-red/30 rounded-lg p-3 text-xs text-red">
              {result.error}
            </div>
          )}

          {/* Decision stages with staggered reveal */}
          {result && !result.error && (
            <div className="mt-3 space-y-2">
              {/* Stage 1: AI Proposal */}
              <DecisionStage
                label="Stage 1 — AI Proposal"
                delay={0}
                content={
                  <div>
                    <div className="flex items-center gap-2 text-sm">
                      <MonoValue className="font-bold text-text">{result.proposal.symbol}</MonoValue>
                      <span className="text-text2">{result.proposal.side}</span>
                      <MonoValue className="font-bold text-green">{result.proposal.proposed_quantity} sh</MonoValue>
                    </div>
                    <div className="text-[11px] text-text2 mt-1">
                      confidence <Badge tone={result.proposal.confidence === "HIGH" ? "green" : result.proposal.confidence === "MEDIUM" ? "amber" : "red"}>
                        {result.proposal.confidence}
                      </Badge>
                    </div>
                    <div className="text-[11px] text-muted mt-1">{result.proposal.rationale}</div>
                  </div>
                }
              />

              {/* Stage 2: Rules Engine */}
              <DecisionStage
                label="Stage 2 — Rules Engine"
                delay={200}
                boost={overrideUsed}
                content={
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-bold ${hasRuleOverride ? "text-amber" : "text-green"}`}>
                        {result.decision.status}
                      </span>
                      <span className="text-text2 text-xs">—</span>
                      <span className="text-xs text-text2">{result.decision.reason}</span>
                    </div>
                    {/* Rule results */}
                    <div className="mt-2 space-y-1">
                      {(result.decision.rules || []).map((r: any, i: number) => (
                        <div key={i} className="flex items-start gap-1.5 text-[11px]">
                          <span className={r.passed ? "text-green" : "text-amber"}>
                            {r.passed ? "✓" : "✗"}
                          </span>
                          <span className="text-text2">{r.message}</span>
                        </div>
                      ))}
                    </div>
                    {/* Final size */}
                    <div className="mt-2 pt-2 border-t border-border text-xs">
                      <span className="text-muted">Final: </span>
                      <MonoValue className="font-bold text-text">{result.decision.final_quantity}</MonoValue>
                      <span className="text-text2"> sh</span>
                      <MonoValue className="text-text2 ml-2">({inr(result.decision.final_value)})</MonoValue>
                      <Badge tone={result.decision.status === "EXECUTE" ? "green" : result.decision.status === "RESIZED" ? "amber" : "red"}>
                        {result.decision.status}
                      </Badge>
                    </div>
                  </div>
                }
              />

              {/* Execute button */}
              {result.decision.status !== "REJECTED" && (
                <DecisionStage
                  label="Stage 3 — Execution"
                  delay={400}
                  content={
                    <div>
                      {order ? (
                        order.error ? (
                          <div className="text-xs text-red">{order.error}</div>
                        ) : (
                          <div className="bg-green/10 border border-green/30 rounded-lg p-3 insert-flash">
                            <div className="text-xs font-bold text-green">Order {order.order.status}</div>
                            <div className="text-[11px] text-text2 mt-1 font-mono">
                              {order.order.symbol} {order.order.side} {order.order.quantity} @ <MonoValue>{inr(order.order.fill_price)}</MonoValue>
                              <span className="text-muted ml-2">(slippage {order.order.slippage_pct * 100}%)</span>
                            </div>
                            <div className="text-[11px] text-text2 mt-1">
                              Remaining cash: <MonoValue>{inr0(order.snapshot.cash_balance)}</MonoValue>
                            </div>
                          </div>
                        )
                      ) : (
                        <button
                          onClick={executeDecision}
                          className="px-4 py-2 rounded-lg bg-green text-bg text-xs font-bold transition-colors"
                        >
                          Place Paper Order
                        </button>
                      )}
                    </div>
                  }
                />
              )}
            </div>
          )}
        </CardRaised>
      </div>

      {/* ── Order/holdings ledger ──────────────────────────────────────────── */}
      <Card>
        <SectionHeader title="Trace / Audit Chain" sub="market facts → proposal → rules → decision → order" />
        <div className="mt-2 space-y-1.5">
          {trace.length === 0 && (
            <div className="text-[11px] text-muted py-3 text-center">
              Run a proposal to populate the trace chain.
            </div>
          )}
          {trace.map((e: any, i: number) => (
            <div
              key={i}
              className="row-insert border border-border rounded-lg p-2.5 bg-panel-raised text-[11px]"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <div className="flex justify-between items-center">
                <span className="font-semibold text-text font-mono">{e.operation}</span>
                <span className="text-muted font-mono text-[10px]">{e.timestamp?.split("T")[1]?.slice(0, 8)} · {e.status}</span>
              </div>
              <div className="mt-0.5 text-[10px] text-muted font-mono">
                {e.decision_id} · trace {e.trace_id}
              </div>
              {e.facts && Object.keys(e.facts).length > 0 && (
                <pre className="mt-1.5 text-[9px] text-text2 overflow-x-auto font-mono leading-relaxed max-h-24 overflow-y-auto">
                  {JSON.stringify(e.facts, null, 1).slice(0, 600)}
                </pre>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
