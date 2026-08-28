// Small reusable UI primitives.

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-card border border-border rounded-2xl p-5 ${className}`}>{children}</div>
  );
}

export function StatCard({
  label,
  value,
  sub,
  accent = "text-text",
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <Card className="transition-transform hover:-translate-y-0.5">
      <div className="text-[11px] uppercase tracking-widest text-muted font-semibold">{label}</div>
      <div className={`mt-2 text-2xl font-bold ${accent}`}>{value}</div>
      {sub && <div className="mt-2 text-xs text-text2">{sub}</div>}
    </Card>
  );
}

export function SectionHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div>
      <h3 className="text-lg font-semibold text-text">{title}</h3>
      {sub && <p className="text-xs text-muted mt-1">{sub}</p>}
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
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide px-3 py-1 rounded-full ${map[tone] || map.gray}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}

export function RiskBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className="mt-3 h-2 rounded-full bg-border overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${pct}%`, background: "linear-gradient(90deg, #19C37D, #5B8DEF)" }}
      />
    </div>
  );
}
