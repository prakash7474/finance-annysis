import { useState } from "react";
import { api } from "../services/api";
import { Card, SectionHeader, StatCard, Badge } from "../components/ui";
import { inr, pct, riskTone } from "../lib";

const SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN", "WIPRO"];

export default function Markets() {
  const [symbol, setSymbol] = useState("RELIANCE");
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  async function load(sym: string) {
    setSymbol(sym);
    setError("");
    try {
      const [price, trend, mom, range] = await Promise.all([
        api.marketPrice(sym),
        api.marketTrend(sym, 20),
        api.marketMomentum(sym, 10),
        api.marketRange(sym, 20),
      ]);
      setData({ symbol: sym, price, trend, mom, range });
    } catch (e: any) {
      setError(e.message || "No market data found");
      setData(null);
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeader title="Market Data" sub="Deterministic mock market adapter (seed 42)" />
      <div className="flex flex-wrap gap-2">
        {SYMBOLS.map((s) => (
          <button
            key={s}
            onClick={() => load(s)}
            className={`px-4 py-2 rounded-xl text-sm font-bold ${symbol === s ? "bg-blue/20 text-blue" : "bg-card border border-border text-text2 hover:text-text"}`}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <StatCard label="Current Price" value={data ? inr(data.price.price) : "—"} accent="text-green" />
        <StatCard label="20D SMA" value={data && data.trend.sma != null ? inr(data.trend.sma) : "—"} />
        <StatCard
          label="Momentum (10D)"
          value={data ? `${(data.mom.momentum_pct >= 0 ? "+" : "")}${data.mom.momentum_pct.toFixed(2)}%` : "—"}
          accent={data && data.mom.momentum_pct >= 0 ? "text-green" : "text-red"}
        />
      </div>

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card>
            <SectionHeader title="Trend" />
            <div className="mt-4">
              <Badge tone={riskTone(data.trend.trend === "UPTREND" ? "HEALTHY" : data.trend.trend === "DOWNTREND" ? "HIGH" : "MODERATE")}>
                {data.trend.trend}
              </Badge>
              <div className="mt-3 text-xs text-text2">
                Latest close {inr(data.trend.latest_close)}
                <br />
                {data.trend.pct_diff != null ? `${pct(data.trend.pct_diff)} vs 20D SMA` : "insufficient data"}
              </div>
            </div>
          </Card>
          <Card>
            <SectionHeader title="OHLC Range (20D)" />
            <div className="mt-4 space-y-1.5 text-sm">
              <Row k="High" v={inr(data.range.high)} />
              <Row k="Low" v={inr(data.range.low)} />
              <Row k="Range" v={`${data.range.range_pct.toFixed(2)}%`} />
              <Row k="Days" v={`${data.range.days}`} />
            </div>
          </Card>
          <Card>
            <SectionHeader title="Momentum" />
            <div className="mt-4 space-y-1.5 text-sm">
              <Row k="Older close" v={inr(data.mom.older_close)} />
              <Row k="Latest close" v={inr(data.mom.latest_close)} />
              <Row k="Change" v={`${pct(data.mom.momentum_pct)}`} accent={data.mom.momentum_pct >= 0 ? "text-green" : "text-red"} />
            </div>
          </Card>
        </div>
      )}

      {error && (
        <Card>
          <div className="text-sm text-red">MARKET_DATA_NOT_FOUND · {error}</div>
        </Card>
      )}
    </div>
  );
}

function Row({ k, v, accent = "text-text" }: { k: string; v: string; accent?: string }) {
  return (
    <div className="flex justify-between border-b border-border py-1.5">
      <span className="text-text2">{k}</span>
      <span className={`font-semibold ${accent}`}>{v}</span>
    </div>
  );
}
