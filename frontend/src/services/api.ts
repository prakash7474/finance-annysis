// API + SSE client for the FinPilot backend.

const BASE = ""; // Vite proxies /api and /health to 127.0.0.1:8000

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.message || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => request<import("../types").HealthResponse>("/health"),

  cashPosition: () => request<import("../types").CashPosition>("/api/finance/cash-position"),
  monthlySummary: (start = "2026-08-01", end = "2026-08-31") =>
    request<import("../types").MonthlySummary>(`/api/finance/monthly-summary?start_date=${start}&end_date=${end}`),
  emiSummary: () => request<import("../types").EmiSummary>("/api/finance/emi-summary"),
  healthScore: () => request<import("../types").FinancialHealthResult>("/api/finance/health-score"),

  analyzeLoan: (body: any) => request<import("../types").LoanResult>("/api/loan/analyze", { method: "POST", body: JSON.stringify(body) }),
  compareLoans: (body: any) => request<import("../types").LoanComparisonResult>("/api/loan/compare", { method: "POST", body: JSON.stringify(body) }),
  scenario: (body: any) => request<import("../types").ScenarioResult>("/api/scenario", { method: "POST", body: JSON.stringify(body) }),

  marketPrice: (symbol: string) => request<import("../types").MarketQuote>(`/api/market/price?symbol=${symbol}`),
  marketTrend: (symbol: string, sma = 20) => request<import("../types").TrendResult>(`/api/market/trend?symbol=${symbol}&sma_days=${sma}`),
  marketMomentum: (symbol: string, look = 10) => request<import("../types").MomentumResult>(`/api/market/momentum?symbol=${symbol}&lookback_days=${look}`),
  marketRange: (symbol: string, days = 20) => request<any>(`/api/market/range?symbol=${symbol}&days=${days}`),

  chat: (message: string, session_id?: string) =>
    request<import("../types").ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id }),
    }),

  injectTxn: (body: any) =>
    request<any>("/api/events/inject", { method: "POST", body: JSON.stringify(body) }),
  analyzeEvent: (body: any) =>
    request<any>("/api/events/analyze", { method: "POST", body: JSON.stringify(body) }),
  recentEvents: () => request<{ events: import("../types").RiskEvent[] }>("/api/events/recent"),
  transactions: () =>
    request<{ transactions: import("../types").Transaction[] }>("/api/finance/transactions").then((r) => r.transactions),

  voiceStart: () => request<{ session_id: string; mode: string }>("/api/voice/start-session", { method: "POST" }),
  voiceSend: (session_id: string, audio: string) =>
    request<any>("/api/voice/send-audio", { method: "POST", body: JSON.stringify({ session_id, audio }) }),

  // ── Phase 5 intelligence ──────────────────────────────────────────────────
  financeHealth: () => request<any>("/api/finance/health"),
  anomalies: () => request<{ anomalies: any[] }>("/api/finance/anomalies"),
  cashForecast: (days = 30) => request<any>(`/api/finance/forecast/cashflow?days=${days}`),
  spendingForecast: (days = 30) => request<any>(`/api/finance/forecast/spending?days=${days}`),
  goals: () => request<any>("/api/finance/goals"),
  createGoal: (body: any) => request<any>("/api/finance/goals", { method: "POST", body: JSON.stringify(body) }),
  runScenario: (body: any) => request<any>("/api/finance/scenario", { method: "POST", body: JSON.stringify(body) }),
  debt: () => request<any>("/api/finance/debt"),
  financialAlerts: () => request<any>("/api/finance/alerts"),
  recommendations: () => request<any>("/api/finance/recommendations"),
  approveRecommendation: (id: string) =>
    request<any>(`/api/finance/recommendations/${id}/approve`, { method: "POST" }),
  rejectRecommendation: (id: string) =>
    request<any>(`/api/finance/recommendations/${id}/reject`, { method: "POST" }),
  audit: (traceId: string) => request<any>(`/api/finance/audit/${traceId}`),
  emitAlerts: () => request<any>("/api/finance/alerts/emit", { method: "POST" }),
  narrateIntelligence: (message: string) =>
    request<any>("/api/finance/narrate", { method: "POST", body: JSON.stringify({ message }) }),

  // ── Phase 6 multi-agent ──────────────────────────────────────────────────
  agents: () => request<any>("/api/agents"),
  tools: () => request<any>("/api/tools"),
  agentRoute: (message: string, session_id?: string) =>
    request<any>("/api/agents/route", { method: "POST", body: JSON.stringify({ message, session_id }) }),
  audits: (traceId: string) => request<any>(`/api/audit/${traceId}`),
};

export function openEventSource(onEvent: (event: string, data: any) => void): EventSource {
  const es = new EventSource(`${BASE}/api/events`);
  es.onopen = () => onEvent("connected", {});
  ["risk_alert", "transaction_alert", "system_alert", "loan_risk_changed", "tool_step", "health"].forEach(
    (name) => {
      es.addEventListener(name, (raw: any) => {
        try {
          onEvent(name, JSON.parse(raw.data));
        } catch {
          onEvent(name, raw.data);
        }
      });
    }
  );
  es.onerror = () => onEvent("error", {});
  return es;
}
