import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Card, SectionHeader, Badge } from "../components/ui";
import { useSse } from "../hooks/useSse";

export default function ControlCenter() {
  const [agents, setAgents] = useState<any[]>([]);
  const [tools, setTools] = useState<any>(null);
  const [traceId, setTraceId] = useState<string>("");
  const [audit, setAudit] = useState<any[]>([]);
  const [liveEvents, setLiveEvents] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const { connected } = useSse((evt, data) => {
    if (["risk_alert", "financial_alert", "transaction_alert"].includes(evt)) {
      setLiveEvents((prev) => [{ ...data, event: evt }, ...prev].slice(0, 20));
    }
  });

  async function load() {
    const [a, t] = await Promise.all([api.agents(), api.tools()]);
    setAgents(a.agents);
    setTools(t);
  }

  useEffect(() => {
    load();
  }, []);

  async function runAgent() {
    setBusy(true);
    try {
      const res = await api.agentRoute(message);
      setResult(res);
      setTraceId(res.trace_id);
      const a = await api.audits(res.trace_id).catch(() => ({ audit: [] }));
      setAudit(a.audit || []);
    } catch (e: any) {
      setResult({ error: e.message });
    } finally {
      setBusy(false);
    }
  }

  async function viewAudit(id: string) {
    const a = await api.audits(id).catch(() => ({ audit: [] }));
    setAudit(a.audit || []);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <SectionHeader title="AI Control Center" sub="Multi-agent orchestration · live traces · governance" />
        <div className="flex items-center gap-2 text-xs">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-green" : "bg-red"}`} />
          {connected ? "SSE Live" : "Offline"}
        </div>
      </div>

      {/* Agent status */}
      <Card>
        <SectionHeader title="Agent Status" sub="Deterministic agent registry" />
        <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-3">
          {agents.map((a) => (
            <div key={a.name} className="border border-border rounded-xl p-3 bg-card2">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${a.status === "ready" ? "bg-green" : "bg-red"}`} />
                <span className="text-sm font-semibold">{a.name}</span>
              </div>
              <div className="mt-1 text-[11px] text-muted">{a.status}</div>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Multi-agent routing */}
        <Card>
          <SectionHeader title="Route a Request" sub="Cross-domain questions invoke multiple agents" />
          <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3}
            placeholder="e.g. Can I afford a 3 lakh loan while reaching my 2 lakh savings goal?"
            className="w-full bg-card2 border border-border rounded-xl px-3 py-2.5 text-sm outline-none focus:border-blue" />
          <button onClick={runAgent} disabled={busy}
            className="mt-3 px-5 py-2.5 rounded-xl bg-green text-bg font-bold disabled:opacity-50">
            {busy ? "Orchestrating…" : "Run Agents"}
          </button>

          {result && !result.error && (
            <div className="mt-4 space-y-2">
              <div className="text-xs text-muted">Agents:</div>
              <div className="flex flex-wrap gap-2">
                {(result.agents_used || []).map((a: string) => <Badge key={a} tone="green">{a}</Badge>)}
              </div>
              {result.risk?.risk_level && (
                <div className="text-sm">Risk: <Badge tone={result.risk.risk_level === "HIGH" || result.risk.risk_level === "CRITICAL" ? "red" : result.risk.risk_level === "MEDIUM" ? "amber" : "green"}>{result.risk.risk_level}</Badge> (score {result.risk.risk_score})</div>
              )}
              {result.governance?.requires_approval && (
                <div className="text-xs text-amber">⚠ Requires human approval · status {result.governance.status}</div>
              )}
              <div className="text-sm text-text2 whitespace-pre-wrap">{result.message}</div>
            </div>
          )}
          {result?.error && <div className="mt-4 text-xs text-red">{result.error}</div>}
        </Card>

        {/* Live events + trace viewer */}
        <Card>
          <SectionHeader title="Live Events" sub="SSE stream" />
          <div className="mt-3 max-h-56 overflow-y-auto space-y-1.5">
            {liveEvents.length === 0 && <div className="text-xs text-muted">Waiting for events…</div>}
            {liveEvents.map((e, i) => (
              <div key={i} className="border border-border rounded-lg p-2 bg-card2 text-xs">
                <span className="font-semibold">{e.event}</span> <span className="text-muted">{e.title || e.message || ""}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 border-t border-border pt-3">
            <SectionHeader title="Trace Viewer" sub="Every decision is traceable (UUID)" />
            <div className="mt-2 flex gap-2">
              <input value={traceId} onChange={(e) => setTraceId(e.target.value)}
                placeholder="TRACE-8f91c…" className="flex-1 bg-card2 border border-border rounded-lg px-3 py-2 text-xs outline-none focus:border-blue" />
              <button onClick={() => viewAudit(traceId)} className="px-3 rounded-lg bg-blue text-bg text-xs font-bold">View</button>
            </div>
            <div className="mt-3 space-y-1.5">
              {audit.length === 0 && <div className="text-xs text-muted">Run a request above to populate a trace.</div>}
              {audit.map((e: any, i: number) => (
                <div key={i} className="text-[11px] font-mono text-text2">
                  <span className="text-blue">{e.timestamp}</span> {e.operation} <span className="text-green">✓</span> {e.status}
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
