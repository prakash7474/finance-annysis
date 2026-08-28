import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Card, SectionHeader, Badge } from "../components/ui";

export default function Governance() {
  const [health, setHealth] = useState<any>(null);
  const [traceId, setTraceId] = useState("—");
  const [budget, setBudget] = useState<any>(null);

  useEffect(() => {
    api.health().then(setHealth);
    setBudget({ tool_calls: 3, max_tool_calls: 8, estimated_cost_usd: 0.006, max_cost_usd: 0.05 });
  }, []);

  return (
    <div className="space-y-6">
      <SectionHeader title="Governance" sub="Telemetry · budget · validation" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <SectionHeader title="System Status" />
          <div className="mt-4 space-y-2">
            {health && Object.entries(health.services || {}).map(([name, s]: any) => (
              <div key={name} className="flex justify-between border-b border-border py-2 text-sm">
                <span className="text-text2">{name.replace(/_/g, " ").toUpperCase()}</span>
                <Badge tone={s.status === "online" || s.status === "configured" ? "green" : s.status === "mock" ? "blue" : "red"}>
                  {s.status}
                </Badge>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <SectionHeader title="Budget" sub="Operational budget guard" />
          {budget && (
            <div className="mt-4 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-text2">Tool Calls</span>
                <span className="font-semibold">{budget.tool_calls} / {budget.max_tool_calls}</span>
              </div>
              <div className="h-2 rounded-full bg-border overflow-hidden">
                <div className="h-full bg-green rounded-full" style={{ width: `${Math.min(100, (budget.tool_calls / budget.max_tool_calls) * 100)}%` }} />
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-text2">Estimated Cost</span>
                <span className="font-semibold">${budget.estimated_cost_usd} / ${budget.max_cost_usd}</span>
              </div>
              <div className="h-2 rounded-full bg-border overflow-hidden">
                <div className="h-full bg-blue rounded-full" style={{ width: `${Math.min(100, (budget.estimated_cost_usd / budget.max_cost_usd) * 100)}%` }} />
              </div>
            </div>
          )}
          <div className="mt-4 border-t border-border pt-3 text-xs">
            <div className="text-muted uppercase tracking-widest text-[10px]">Latest trace</div>
            <div className="mt-1 font-mono text-blue text-sm">{traceId}</div>
          </div>
        </Card>

        <Card>
          <SectionHeader title="Validation" sub="Pydantic · tool schema · facts" />
          <div className="mt-4 space-y-2 text-sm">
            {["Pydantic request schemas", "Tool input validation", "Facts validation", "Budget guard", "Trace propagation"].map((v) => (
              <div key={v} className="flex items-center gap-2 text-green">
                <span>✓</span> {v}
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <SectionHeader title="MCP Servers" />
          <div className="mt-4 space-y-2 text-sm">
            {["Bank", "Loan", "Market"].map((s) => (
              <div key={s} className="flex justify-between border-b border-border py-2">
                <span className="text-text2">{s} MCP</span>
                <Badge tone="green">online</Badge>
              </div>
            ))}
          </div>
          <div className="mt-3 text-xs text-text2">
            AI: <Badge tone="green">Gemini {health?.services?.gemini?.status}</Badge>
          </div>
        </Card>
      </div>
    </div>
  );
}
