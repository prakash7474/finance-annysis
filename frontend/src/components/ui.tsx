// Professional UI primitives — clean fintech surfaces, densities and badges.

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-card border border-border/70 rounded-xl p-5 shadow-card ${className}`}>{children}</div>
  );
}

export function CardRaised({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-panel-raised border border-border/70 rounded-xl p-5 shadow-card ${className}`}>{children}</div>
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
    <Card className="transition-all duration-200 hover:border-border/60 hover:shadow-card-hover">
      <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted">{label}</div>
      <div className={`mt-1.5 text-[26px] leading-none font-semibold tracking-tight ${accent} ${mono ? "font-mono tabular-nums" : ""}`}>
        {value}
      </div>
      {sub && <div className="mt-2 text-xs text-text2">{sub}</div>}
    </Card>
  );
}

export function SectionHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div>
      <h3 className="text-[15px] font-semibold text-text font-display tracking-tight">{title}</h3>
      {sub && <p className="text-xs text-muted mt-0.5">{sub}</p>}
    </div>
  );
}

export function Badge({ children, tone = "green" }: { children: React.ReactNode; tone?: string }) {
  const map: Record<string, string> = {
    green: "bg-green/10 text-green ring-1 ring-green/20",
    red: "bg-red/10 text-red ring-1 ring-red/20",
    amber: "bg-amber/10 text-amber ring-1 ring-amber/20",
    blue: "bg-blue/10 text-blue ring-1 ring-blue/20",
    violet: "bg-violet/10 text-violet ring-1 ring-violet/20",
    gray: "bg-card2 text-text2 ring-1 ring-border",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide px-2.5 py-0.5 rounded-full ${map[tone] || map.gray}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}

export function RiskBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className="mt-2 h-1.5 rounded-full bg-border/60 overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${pct}%`, background: "linear-gradient(90deg, #22C55E, #3B82F6)" }}
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
