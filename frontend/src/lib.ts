export function inr(amount: number): string {
  if (amount === null || amount === undefined) return "—";
  const sign = amount < 0 ? "-" : "";
  const a = Math.abs(amount);
  const [intPart, dec] = a.toFixed(2).split(".");
  const digits = intPart.replace(/,/g, "");
  let grouped = intPart;
  if (digits.length > 3) {
    const last3 = digits.slice(-3);
    const rest = digits.slice(0, -3);
    const groups: string[] = [];
    let r = rest;
    while (r.length > 2) {
      groups.unshift(r.slice(-2));
      r = r.slice(0, -2);
    }
    groups.unshift(r);
    grouped = groups.join(",") + "," + last3;
  }
  return `${sign}₹${grouped}.${dec}`;
}

export function inr0(amount: number): string {
  if (amount === null || amount === undefined) return "—";
  return inr(Math.round(amount));
}

export function pct(value: number): string {
  if (value === null || value === undefined) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function riskTone(level: string): string {
  const map: Record<string, string> = {
    HEALTHY: "green",
    LOW: "green",
    MODERATE: "amber",
    HIGH: "red",
    CRITICAL: "red",
  };
  return map[level] || "gray";
}
