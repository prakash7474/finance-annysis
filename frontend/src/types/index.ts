// Shared TypeScript types mirroring the backend Pydantic schemas.

export interface AccountBalance {
  account_id: string;
  account_name: string;
  account_type: string;
  balance: number;
}

export interface CashPosition {
  accounts: AccountBalance[];
  net_cash: number;
}

export interface MonthlySummary {
  start_date: string;
  end_date: string;
  total_credit: number;
  total_debit: number;
  net_change: number;
  transaction_count: number;
}

export interface EmiSummary {
  start_date: string;
  end_date: string;
  total_emi: number;
  emi_count: number;
  emi_breakdown: Record<string, number>;
}

export interface FinancialHealthResult {
  cash_score: number;
  emi_score: number;
  dti_score: number;
  liquidity_score: number;
  overall_score: number;
  risk_level: string;
  warnings: string[];
  dti_ratio?: number | null;
  cash_months?: number | null;
}

export interface LoanResult {
  emi: number;
  total_interest: number;
  total_cost: number;
  processing_fee: number;
  emi_income_ratio: number;
  risk_level: string;
  risk_flags: { code: string; message: string; severity: string }[];
}

export interface LoanOffer {
  offer_id: string;
  bank: string;
  product: string;
  interest_rate: number;
  tenure_months: number;
  emi: number;
  total_cost: number;
  total_interest: number;
  risk_level: string;
  rank: number;
  is_best_cost?: boolean;
  is_lowest_risk?: boolean;
}

export interface LoanComparisonResult {
  amount: number;
  monthly_income: number;
  existing_emi: number;
  offers: LoanOffer[];
  best_by_cost?: LoanOffer | null;
  lowest_risk?: LoanOffer | null;
}

export interface MarketQuote {
  symbol: string;
  price: number;
}

export interface TrendResult {
  latest_close: number | null;
  sma: number | null;
  trend: string;
  pct_diff: number | null;
}

export interface MomentumResult {
  momentum_pct: number;
  lookback_days: number;
  older_close: number;
  latest_close: number;
}

export interface ScenarioResult {
  current: Record<string, any>;
  scenario: Record<string, any>;
  delta: Record<string, any>;
}

export interface ChatResponse {
  success: boolean;
  session_id?: string;
  request_id?: string;
  trace_id?: string;
  message: string;
  intent?: string;
  tools_used: string[];
  facts: Record<string, any>;
  risk: Record<string, any>;
  error_code?: string | null;
  narrator?: string;
}

export interface RiskEvent {
  event: string;
  event_id: string;
  severity: string;
  account_id?: string;
  account_name?: string;
  message: string;
  category?: string;
  amount?: number;
  balance_after?: number;
  timestamp?: string;
  data?: Record<string, any>;
}

export interface HealthResponse {
  status: string;
  services: Record<string, { name: string; status: string }>;
  version?: string;
}

export interface Transaction {
  txn_id: string;
  account_id: string;
  date: string;
  description: string;
  amount: number;
  type: string;
  category: string;
}
