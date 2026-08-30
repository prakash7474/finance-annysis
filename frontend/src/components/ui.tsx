// Instrument panel UI primitives — density and precision over ornament.

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-panel border border-border rounded-lg p-5 ${className}`}>{children}</div>
  );
}

export function CardRaised({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-panel-raised border border-border rounded-lg p-5 ${className}`}>{children}</div>
  );
}

export function StatCard({
  label,
  value,
  sub,
  accent = "text-text",
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  accent?: string;
  mono?: boolean;
}) {
  return (
    <Card className="transition-colors">
      <div className="text-[10px] uppercase tracking-[0.15em] text-muted font-semibold">{label}</div>
      <div className={`mt-1.5 text-xl font-bold ${accent} ${mono ? "font-mono" : ""}`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-text2">{sub}</div>}
    </Card>
  );
}

export function SectionHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-text font-display uppercase tracking-wider">{title}</h3>
      {sub && <p className="text-[11px] text-muted mt-0.5">{sub}</p>}
    </div>
  );
}

export function Badge({ children, tone = "green" }: { children: React.ReactNode; tone?: string }) {
  const map: Record<string, string> = {
    green: "bg-green/15 text-green",
    red: "bg-red/15 text-red",
    amber: "bg-amber/15 text-amber",
    blue: "bg-blue/15 text-blue",
    gray: "bg-card2 text-text2",
  };
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded ${map[tone] || map.gray}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}

export function RiskBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className="mt-2 h-1.5 rounded-full bg-border overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${pct}%`, background: "linear-gradient(90deg, #3DDC97, #5B8DEF)" }}
      />
    </div>
  );
}

export function MonoValue({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <span className={`font-mono tabular-nums ${className}`}>{children}</span>;
}

export function StatusDot({ status }: { status: "online" | "offline" | "reconnecting" }) {
  return <span className={`status-dot ${status}`} />;
}
