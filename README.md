# FinPilot — AI Finance Controller

**Phase 6 · Real-Time Multi-Agent Financial Control Center**

FinPilot turns a set of deterministic Python finance/market engines and MCP
servers into a single, unified platform. You no longer need to know which
command or engine is responsible — you just ask, and the system routes your
request to the right deterministic tools, collects *validated facts*, and has
**Gemini** narrate the answer. Gemini can **never** calculate anything itself.

```text
                         ┌──────────────────────────┐
                         │      FINPILOT UI         │
                         │ React + TypeScript       │
                         │ Tailwind CSS             │
                         └────────────┬─────────────┘
                                      │
                              REST + WebSocket/SSE
                                      │
                         ┌────────────▼─────────────┐
                         │   FASTAPI AI HOST        │
                         │ Unified Orchestrator     │
                         └────────────┬─────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
              BANK DOMAIN       CREDIT DOMAIN     MARKET DOMAIN
                    │                 │                 │
                    ▼                 ▼                 ▼
              Bank MCP          Loan Engine        Market MCP
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      │
                              VALIDATED FACTS
                                      │
                                      ▼
                              GEMINI NARRATOR
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                         ▼                         ▼
                    Text Response            Voice Response

                         ▲
                         │
                  Risk Observer
                         │
                        SSE
                         │
                         ▼
                  Real-time Alerts
                         +
                 Governance Layer
                         +
                   Trace Logging
                          +
                    Budget Guard
```

---

## Feature Documentation & Screenshots

> Every financial number (cash, health, loan affordability, DTI, risk) is computed by
> **deterministic, auditable Python engines** — the LLM (Gemini) only narrates; it never
> calculates. Real‑time risk alerts stream over **Server‑Sent Events (SSE)**.
>
> All screenshots below are real captures from the running app (`docs/screens/`), identified
> per page and placed next to the feature they demonstrate.

### Screenshot map

| # | File | Page / State | What it shows |
|---|------|--------------|---------------|
| 1 | `docs/screens/dashboard-1.png` | Dashboard | Financial Health, Cash Flow, nav rail, "System Online" |
| 2 | `docs/screens/dashboard-2.png` | Dashboard | Scrolled / alternate state |
| 3 | `docs/screens/trading-1.png` | Paper Trading | Market Realtime feed |
| 4 | `docs/screens/trading-2.png` | Paper Trading | Decision Trace (AI → rules engine) |
| 5 | `docs/screens/trading-3.png` | Paper Trading | Trace / Audit Chain |
| 6 | `docs/screens/markets-1.png` | Markets | Price, SMA trend, OHLC range, momentum |
| 7 | `docs/screens/advisor-1.png` | AI Advisor | Chat: "Compare HDFC and ICICI" + deterministic answer |
| 8 | `docs/screens/intelligence-1..9.png` | Intelligence | Health, forecasts, debt optimization, goals, digital twin, audit |
| 9 | `docs/screens/control-1.png` | Control Center | Agent status / Live Events |
| 10 | `docs/screens/control-2.png` | Control Center | Multi‑agent orchestration header |
| 11 | `docs/screens/control-3.png` | Control Center | Route a Request + Trace Viewer |
| 12 | `docs/screens/loans-1.png` | Loans | Single Loan + What‑if simulator |
| 13 | `docs/screens/loans-2.png` | Loans | Compare Offers (HDFC / ICICI) |
| 14 | `docs/screens/loans-3.png` | Loans | Simulator result (EMI, health %) |
| 15 | `docs/screens/transactions-1.png` | Transactions | Mock bank transactions (Aug 2026) |
| 16 | `docs/screens/alerts-1.png` | Risk Alerts | Demo: inject debit/credit → Live Events |
| 17 | `docs/screens/alerts-2.png` | Risk Alerts → Analyze Impact | Updated Cash, Health, Loan Affordability, warnings |
| 17 | `docs/screens/governance-1.png` | Governance | System status, Budget, Validation, MCP |

### Dashboard
![Dashboard](docs/screens/dashboard-1.png)
![Dashboard 2](docs/screens/dashboard-2.png)

The landing page is a single source of truth for the user's financial position. The
**Financial Health** card is produced by `health_engine.compute_health_score`, which blends
four weighted sub‑scores (cash, EMI burden, DTI, liquidity) into one 0–100 score and a
risk level — **never** calculated by the LLM. **Cash Flow** comes from
`finance_engine.compute_cash_position` (opening balances + credits − debits). The top bar shows
the live SSE connection dot and a running event counter.

### Paper Trading
![Paper Trading](docs/screens/trading-1.png)
![Paper Trading](docs/screens/trading-2.png)
![Paper Trading](docs/screens/trading-3.png)

A safe, simulated trading surface. **Market Realtime** subscribes to an accelerated replay feed
(`replay_engine`) and, when volatility crosses a threshold, publishes `volatility_spike` events
to the SSE stream. Every proposed order flows through a **Decision Trace**: the AI *proposes*,
but a deterministic **rules engine decides** (approve/reject). The **Trace / Audit Chain**
records market facts → proposal → rules → decision → order with a UUID so every action is
auditable. **No real orders are ever placed.**

### Markets
![Markets](docs/screens/markets-1.png)

Powered by the `market_engine` + `mock_market_adapter` (deterministic, seed 42). It shows the
latest price, an SMA trend line, a 20‑day OHLC range, and a momentum percentage for symbols like
RELIANCE / TCS / INFY. Because the adapter is seeded, the numbers are reproducible across runs.

### AI Advisor
![AI Advisor](docs/screens/advisor-1.png)

A conversational assistant. When you ask a question, the **Orchestrator** routes the intent to
the right deterministic tools (bank/finance/loan/market MCP or engines), collects **validated
facts**, and only then asks **Gemini to narrate** the answer. In the capture above the user asked
*"Compare HDFC and ICICI"* and received a deterministic loan‑offer comparison. The LLM never
computes the math itself.

### Intelligence
![Intelligence](docs/screens/intelligence-1.png)
![Intelligence](docs/screens/intelligence-2.png)
![Intelligence](docs/screens/intelligence-3.png)
![Intelligence](docs/screens/intelligence-4.png)
![Intelligence](docs/screens/intelligence-5.png)
![Intelligence](docs/screens/intelligence-6.png)
![Intelligence](docs/screens/intelligence-7.png)
![Intelligence](docs/screens/intelligence-8.png)
![Intelligence](docs/screens/intelligence-9.png)

The autonomous decision center. It surfaces:
- **Why this score** — the exact `health_engine` formula breakdown (transparent, never LLM‑calculated).
- **Cash‑Flow & Spending forecasts** — projections from `forecast_engine` (labeled "not a guarantee").
- **Debt Optimization** — re‑ranking of debts by total cost (deterministic).
- **Smart Alerts** — priority‑ordered risk alerts.
- **Goals** — progress derived from the current financial profile.
- **Market Watcher** — analysis only; never places trades.
- **AI Recommendations** — informational guidance; **human approval required** before any action.
- **Financial Digital Twin** — simulates changes (e.g., a raise or new loan) against a copy of the
  data; **the original data is never modified**.
- **Audit / Trace Viewer** — every decision is traceable to a UUID.

### Control Center
![Control Center](docs/screens/control-1.png)
![Control Center](docs/screens/control-2.png)
![Control Center](docs/screens/control-3.png)

The multi‑agent brain. It shows a deterministic **agent registry/status**, lets you **Route a
Request** (cross‑domain questions fan out to several agents), streams **Live Events** over SSE,
and provides a UUID‑keyed **Trace Viewer** so you can inspect exactly which agents ran and what
each returned.

### Loans
![Loans](docs/screens/loans-1.png)
![Loans](docs/screens/loans-2.png)
![Loans](docs/screens/loans-3.png)

**Loan Advisor** explains the true cost of borrowing before you commit:
- **Single Loan** — EMI (`loan_engine.calculate_emi`), total interest, processing fee,
  `emi_income_ratio` (DTI), and a risk level.
- **Compare Offers** — HDFC vs ICICI (and others) ranked by **total cost**, not just rate.
- **What‑if Simulator** — change income/EMI and watch EMI, DTI, risk, and health score update
  live (the third capture shows an EMI of ~₹9,964 and a health impact of ~40.3%).

### Transactions
![Transactions](docs/screens/transactions-1.png)

The raw ledger: mock bank transactions for August 2026 (credits, debits, EMIs). This is the
source data the finance and anomaly engines analyze.

### Governance
![Governance](docs/screens/governance-1.png)

Operational guardrails: **System Status** of every component, an operational **Budget** guard that
caps spend, **Validation** of Pydantic schemas / tool schemas / facts, and live **MCP server**
health. Governance ensures the autonomous features stay within safe, auditable bounds.

### "Fix the Market" — Risk Alerts Module
![Risk Alerts](docs/screens/alerts-1.png)
![Risk Alerts - Impact Analysis](docs/screens/alerts-2.png)

This module demonstrates the end‑to‑end real‑time risk pipeline:

1. **Inject a transaction** — `Inject ₹80,000 debit` or `Inject ₹60,000 credit` →
   `POST /api/events/inject`.
2. **RiskObserver** applies the transaction, recomputes the cash position, and runs deterministic
   anomaly detection (`large_debit`, `large_credit`, `liquidity_drop`, `emi_burden`,
   `unusual_spending`, `credit_utilization`).
3. Matching **risk alerts** are published to the `EventBus` and streamed to the browser over
   **SSE** (`GET /api/events`) as live "Live Events".
4. Click **Analyze Impact** on any event → `POST /api/events/analyze` recomputes:
   - **Updated Cash** (`snapshot.net_cash`)
   - **Health** score + risk level (`health.overall_score`, `health.risk_level`)
   - **Loan Affordability** for a ₹3L reference loan (`emi`, `dti`, `risk_level`)
   - Contextual **warnings** (liquidity breach, elevated DTI, etc.)

> Stability note: a prior bug made the observer re‑scan the *entire* transaction history on every
> inject, so the Nth inject emitted N alerts and flooded the UI. It now emits only alerts tied to
> the new transaction, and an `ErrorBoundary` prevents any single bad render from blanking the app.

### Architecture

```mermaid
flowchart LR
  U[Browser / React UI] -- REST + SSE --> API[FastAPI :8000]
  API --> OB[Orchestrator / Multi-Agent]
  API --> RO[RiskObserver + AnomalyDetector]
  API --> ENG[Engines: finance / health / loan / market / forecast]
  API --> BUS[(EventBus -> SSE)]
  OB --> MCP[MCP Servers: bank / market]
  ENG --> MOCK[(Mock data fallback)]
  BUS --> U
```

### Tech stack
- **Frontend**: React 18 + TypeScript + Vite + Tailwind + Framer Motion.
- **Backend**: FastAPI, async SSE, in‑memory `EventBus`, deterministic engines.
- **Data**: `DATA_SOURCE=mock` (default fallback) or `mcp` (live MCP servers). Every domain
  independently falls back to mock if its MCP server is unreachable.

### Quick Start

```bash
# Terminal 1 — API (auto-spawns/connects data layer)
python backend/main.py

# Terminal 2 — UI
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173`. Interactive docs: `http://127.0.0.1:8000/docs`.

### API summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health/component status |
| GET | `/api/events` | **SSE** real‑time risk alerts |
| POST | `/api/events/inject` | Inject a transaction (triggers RiskObserver) |
| POST | `/api/events/analyze` | Recompute cash/health/loan affordability |
| GET | `/api/finance/*` | cash‑position, health‑score, transactions, forecasts, goals, alerts |
| POST | `/api/loan/*` | analyze / compare loans |
| GET | `/api/market/*` | price / trend / momentum / range |
| POST | `/api/chat` | AI Advisor |
| POST | `/api/agents/route` | multi‑agent routing (Control Center) |

### Stability & recent fixes (root cause → resolution)

| # | Symptom | Root cause | Fix |
|---|---------|-----------|-----|
| 1 | Intermittent / consistent crash on inject; unresponsive Risk Alerts page | `RiskObserver.observe_transaction` re‑scanned the **entire growing transaction history** on every inject → event **fan‑out** (Nth inject emitted N alerts), flooding SSE and React state | Emit only alerts tied to the **new** transaction (`signal.txn_id == txn.txn_id`); state‑based signals stay bounded |
| 2 | Blank white screen after a crash | No React **Error Boundary** — any render exception unmounted the whole tree | Added `frontend/src/ErrorBoundary.tsx` and wrapped `<App/>` in `main.tsx` (recoverable "Try again / Reload" panel) |
| 3 | Impact Analysis (Updated Cash / Health / Loan Affordability) renders blank | Unhandled promise rejections in `inject`/`analyzeEvent`; `volatility_spike` events polluted "Live Events"; no placeholder/guards | `try/catch` + loading/error states; filtered `volatility_spike` out of relevant events; null‑safe rendering with a placeholder |
| 4 | "₹60,000 credit" actually injected a **debit** | `inject()` hardcoded `type: "DEBIT"` | Button now passes `type: "CREDIT"` |
| 5 | Unbounded SSE churn | `setEvents` appended without dedupe | Dedupe by `event_id` + cap at 40 |

### Troubleshooting
- **Backend unreachable** — start `python backend/main.py` on `127.0.0.1:8000`; Vite proxies
  `/api` and `/health`.
- **MCP servers unavailable** — backend auto‑falls back to mock; finance/market keep working.
- **Gemini not answering** — check `GEMINI_API_KEY`; a deterministic narrator always answers.
- **App shows a recoverable error** — use "Try again"; a stack‑free message is shown (no blank
  screen).

---

## Architecture

The **LLM is never the financial calculation engine.** The flow is:

```text
Financial Data
  → Continuous Analysis (anomaly / forecast / debt)
  → Risk & Scenario Simulation (Digital Twin)
  → Recommendation Engine
  → Human Approval
  → Audit Trail
  → Gemini narrator (explains the facts only)
```

**Phase 5** adds an autonomous intelligence layer on top of Phase 4:

- **Engines (deterministic)** — `anomaly_engine` (statistical deviation),
  `forecast_engine` (cash-flow + spending), `goal_engine`, `health_engine`
  (Phase-5 score), `debt_optimizer`, `digital_twin` (scenario simulator),
  `portfolio_watcher`, `recommendation_engine`, `alert_engine`, `approval_engine`,
  `audit_logger`.
- **`intelligence.py`** — one deterministic assembly function that wires every
  Phase 5 engine to the bank data; reused by the FastAPI layer, the CLI, the MCP
  server and the tests (a single source of truth).
- **Pydantic models** in `models/` (`financial_models`, `alert_models`,
  `recommendation_models`, `scenario_models`).
- **Human approval layer** — recommendations are `PENDING → APPROVED | REJECTED |
  EXPIRED`; nothing is ever auto-executed, and `execute()` only runs on an
  approved recommendation.
- **Audit system** — every decision records `trace_id / decision_id / operation /
  facts / recommendation / approval_status / execution_status`.
- **MCP** — `mcp_servers/intelligence_mcp_server.py` exposes Phase 5 tools and
  read-only resources.
- **SSE** — `financial_alert` events pushed to the frontend.

### Architecture (Phase 4 base) — unchanged

- **Orchestrator** (`backend/orchestrator/orchestrator.py`) — the central
  Mediator: receives the request, creates `trace_id / request_id / session_id`,
  routes the intent, discovers tools, validates inputs, invokes deterministic
  tools under a **budget guard**, aggregates **Facts**, sends them to the
  **Gemini narrator**, and returns the response + audit trail.
- **Tool Registry** (`tool_registry.py`) — one discoverable place where every
  backend capability is registered (name, domain, server, executor). Routing
  never hard-codes a tool.
- **Deterministic Engines** (`finance_engine`, `loan_engine`, `market_engine`,
  `health_engine`, `scenario_engine`) — all arithmetic lives here.
- **Data Layer** (`data_layer.py`) — talks to the **MCP servers** (bank /
  market) with an automatic **mock fallback**, so finance keeps working even if
  the market MCP is down.
- **Governance** — operational budget guard, trace/audit logging, Pydantic
  validation, rate limiting.
- **Observers** — `risk_observer` + `anomaly_detector` monitor transactions and
  push **SSE** risk alerts to the UI.
- **Sessions** — in-memory session/context store (swappable for Redis/PG).

The repo keeps Phase 1–3 code intact and backward-compatible. `engines/` are
thin re-exports of the root engine modules, and `mcp_servers/` are standalone,
runnable servers used by the backend.

## Project Layout

```text
backend/                FASTAPI host: main, config, api/, orchestrator/,
                        governance/, observers/, schemas/
mcp_servers/            standalone bank / market / loan MCP servers
engines/                re-exports of the deterministic engines
data/                   mock market reference data
frontend/               React + TS + Tailwind UI (Vite)
tests/                  unit / api / orchestrator / governance / integration / e2e
health_engine.py        deterministic financial health score
scenario_engine.py      deterministic what-if simulator
```

## Installation

```bash
# Python
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

## Environment Variables

Copy `.env.example` → `.env` and fill in your Gemini key:

```bash
cp .env.example .env
# edit GEMINI_API_KEY=your_key_here
```

Key variables:

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | — | Gemini API key (**server-side only**) |
| `GEMINI_MODEL` | `gemini-3.6-flash` | narrator model |
| `DATA_SOURCE` | `mcp` | `mcp` (use servers) or `mock` (offline fallback) |
| `MCP_TRANSPORT` | `stdio` | `stdio` (backend auto-spawns servers) or `sse` |
| `BANK/MARKET_MCP_URL` | `http://127.0.0.1:900N/sse` | SSE endpoints |
| `BUDGET_MAX_TOOL_CALLS` | `8` | max tools per request |
| `BUDGET_MAX_COST_USD` | `0.05` | max estimated cost per request |
| `RISK_*` | various | risk observer thresholds |
| `APP_PORT` | `8000` | backend port |

## Backend Setup

```bash
# Simplest (auto-spawns its own stdio MCP servers)
python backend/main.py
```

or run servers yourself over SSE:

```bash
python mcp_servers/bank_mcp_server.py --sse --port 9001
python mcp_servers/market_mcp_server.py --sse --port 9002
```

then set `MCP_TRANSPORT=sse` in `.env` and start the backend.

## MCP Setup

Standalone servers run over **stdio** by default, or **SSE** with
`--sse --port N`. The backend connects to them (auto-spawned stdio or remote
SSE) and falls back to deterministic mock data when a server is unavailable.
Phase 5 adds `mcp_servers/intelligence_mcp_server.py` (port 9004) exposing
tools — `detect_transaction_anomalies`, `forecast_cash_flow`,
`forecast_spending`, `calculate_financial_health`, `plan_financial_goal`,
`optimize_debt`, `simulate_financial_scenario`, `get_financial_alerts`,
`get_recommendations` — and read-only resources — `finance://health/current`,
`finance://forecast/cashflow`, `finance://forecast/spending`,
`finance://alerts`, `finance://recommendations`, `finance://goals`,
`finance://digital-twin/current`.

## Frontend Setup

```bash
cd frontend && npm install && npm run dev
# http://localhost:5173  (Vite proxies /api and /health to the backend)
```

## Testing

```bash
python -m pytest -q
```

- **Existing (Phase 1–3):** 38 tests pass (`test_loan_engine.py`,
  `test_market_engine.py`) — unchanged and backward-compatible.
- **Phase 4:** 104 tests (unified orchestrator, governance, SSE, API, security,
  integration, e2e).
- **Phase 5:** 73 tests (`test_anomaly_engine`, `test_forecast_engine`,
  `test_goal_engine`, `test_health_engine_phase5`, `test_debt_optimizer`,
  `test_digital_twin`, `test_recommendation_engine`, `test_alert_engine`,
  `test_approval_engine`, `test_api_phase5`).
- **Phase 6:** 34 tests (`test_agents`, `test_mcp_client`, `test_event_bus`,
  `test_governance`, `test_voice_session`, `test_api_phase6`).
- **Trading add-on:** 38 tests (`test_replay_engine`, `test_accounts_provider`,
  `test_allocation_engine`, `test_demat_engine`, `test_api_trading`).
- **Total:** 287 tests.

Phase 5 test coverage includes: anomaly detection (normal/large/category/
zero-negative), forecasting (deterministic, 7/30-day, no-data, missing income),
goal planning (target/shortfall/completed/invalid), health scoring (excellent/
moderate/critical, DTI & liquidity thresholds), debt ranking (all five
strategies), Digital Twin (salary/expense/loan/combined + **original data
unchanged**), recommendations (DTI/liquidity/goal-shortfall), alerts
(priority ordering), approval (pending→approved/rejected, no double-approval,
rejected cannot execute), SSE emit, and the full Phase 5 API surface. Tests run
offline (mock data + fallback narrator).

## API Documentation

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | service & MCP status (no secrets) |
| `POST` | `/api/chat` | unified AI chat (multi-turn, returns facts + tools + risk) |
| `POST` | `/api/scenario` | what-if simulator |
| `POST` | `/api/loan/analyze` | single loan analysis |
| `POST` | `/api/loan/compare` | compare offers |
| `GET` | `/api/finance/cash-position` | cash position |
| `GET` | `/api/finance/monthly-summary` | credit/debit summary |
| `GET` | `/api/finance/emi-summary` | EMI breakdown |
| `GET` | `/api/finance/emi-ratio` | EMI-to-income ratio |
| `GET` | `/api/finance/category-summary` | spending by category |
| `GET` | `/api/finance/health-score` | financial health score |
| `GET` | `/api/finance/transactions` | transaction list |
| `GET` | `/api/market/price` | latest price |
| `GET` | `/api/market/trend` | trend vs SMA |
| `GET` | `/api/market/momentum` | momentum |
| `GET` | `/api/market/ohlc` | OHLC history |
| `GET` | `/api/market/range` | high/low range |
| `GET` | `/api/events` | **SSE** real-time risk alerts |
| `POST` | `/api/events/inject` | inject a transaction (demo) |
| `POST` | `/api/events/analyze` | recompute impact after an alert |
| `POST` | `/api/voice/*` | pluggable voice abstraction (text fallback) |

**Phase 5 intelligence APIs:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/finance/health` | financial health score (deterministic) |
| `GET` | `/api/finance/anomalies` | transaction anomalies |
| `GET` | `/api/finance/forecast/cashflow?days=30` | cash-flow forecast |
| `GET` | `/api/finance/forecast/spending` | spending forecast |
| `GET` | `/api/finance/goals` | list goals |
| `POST` | `/api/finance/goals` | create a goal |
| `POST` | `/api/finance/scenario` | Digital Twin scenario | 
| `GET` | `/api/finance/debt` | debt optimization ranking |
| `GET` | `/api/finance/alerts` | priority-ordered smart alerts |
| `GET` | `/api/finance/recommendations` | recommendations |
| `POST` | `/api/finance/recommendations/{id}/approve` | human approve |
| `POST` | `/api/finance/recommendations/{id}/reject` | human reject |
| `GET` | `/api/finance/audit/{trace_id}` | audit trail |
| `POST` | `/api/finance/alerts/emit` | push alerts to the SSE stream |
| `POST` | `/api/finance/narrate` | Gemini/fallback narration of Phase 5 facts |

Interactive OpenAPI docs: `http://127.0.0.1:8000/docs`.

## Demo Workflow (5 minutes)

**Simplest startup (auto-spawns MCP servers):**

```bash
# Terminal 1                 # Terminal 2
python backend/main.py       cd frontend && npm run dev
```

**4-terminal variant (SSE MCP servers):**

```bash
# Terminal 1                    Terminal 2
python backend/main.py          python mcp_servers/bank_mcp_server.py --sse --port 9001
# Terminal 3                    Terminal 4
python mcp_servers/market_mcp_server.py --sse --port 9002
cd frontend && npm run dev
```

> If you run the 4-terminal variant, set `MCP_TRANSPORT=sse` in `.env`.

Then:

1. **Dashboard** opens with FinPilot + *System Online*, cash, income, EMI and a
   Financial Health card.
2. **AI Advisor:** ask *“What is my current cash position?”* → Bank MCP →
   Finance Engine → Facts → Gemini → answer.
3. Ask *“Can I afford a ₹300,000 loan for 36 months?”* → cash + income + existing
   EMI + loan + DTI + risk.
4. *“What if I reduce the loan to ₹200,000?”* → new deterministic DTI/risk.
5. *“Compare HDFC and ICICI.”* → deterministic comparison table.
6. *“How is RELIANCE performing?”* → price, SMA, trend, momentum.
7. **Risk Alerts:** click *Inject ₹80,000 debit* → Risk Observer → SSE →
   dashboard alert.
8. Click *Analyze Impact* → updated cash, health, loan affordability, warning.

## Troubleshooting

- **Gemini not answering** — check `GEMINI_API_KEY` in `.env`. FinPilot always
  falls back to a deterministic narrator, and finance tools keep working.
- **MCP servers unavailable** — the backend auto-falls back to mock data; finance
  and market features continue to function.
- **`₹` shows garbled in the CLI** — run with `PYTHONIOENCODING=utf-8` (the CLI
  wraps stdout in UTF-8 automatically on Windows).
- **Frontend can't reach the backend** — make sure the backend runs on
  `127.0.0.1:8000`; Vite proxies `/api` and `/health` to it.
- **Tests** — run offline by default (mock + fallback narrator); they never call
  Gemini or require MCP servers.

## Phase 6 — Multi-Agent Control Center

Phase 6 turns the platform into a unified multi-agent financial control system
reusing the Phase 4/5 engines and MCP servers.

```text
USER ─ Web Chat / Voice ─▶ ORCHESTRATOR (Mediator)
                              │
   ┌────────────┬────────────┼─────────────┐
   ▼            ▼            ▼             ▼
BANK_AGENT   LOAN_AGENT  MARKET_AGENT  FINANCE_AGENT  (run in parallel)
   └────────────┴────────────┼─────────────┘
                             ▼
                        RISK_AGENT
                             ▼
                     GOVERNANCE_AGENT  (budget · safety · approval)
                             ▼
                 FINANCE_NARRATOR (Gemini / fallback)
                             ▼
   RECOMMENDATION ─▶ HUMAN APPROVAL ─▶ AUDIT LOG ─▶ FINAL RESPONSE
```

- **Agents** (`backend/agents/`) — `base_agent` + `bank_agent`, `loan_agent`,
  `market_agent`, `finance_agent`, `risk_agent`, `governance_agent`. Each agent
  returns structured data and never mutates global state.
- **MultiAgentOrchestrator** — routes by intent, runs independent agents in
  parallel via `asyncio.gather`, then risk → governance, applies the operational
  budget, and narrates.
- **MCPClientManager** — central connection/discovery/invoke for MCP servers
  (tool + resource discovery, no hard-coded calls).
- **Events** (`backend/events/`) — async event bus + `risk_observer` publishing
  `transaction.created`, `financial_alert`, `dti.high`, `cash.low`, …
- **Governance** (`backend/governance/`) — `budget_tracker` (max tool calls /
  execution time / cost, `SafetyBudgetExceeded`, loop-limit guard),
  `approval_engine`, `audit_logger` re-exports.
- **Voice** (`backend/voice/`) — `VoiceSession` with streaming + **interruption**,
  over a WebSocket; goes through the same governance/risk path as text.
- **AI** (`backend/ai/finance_narrator.py`) — Gemini narrator with `temperature=0`
  and a staged system prompt; deterministic fallback.

**Phase 6 endpoints:** `GET /api/agents` · `POST /api/agents/route` ·
`GET /api/tools` · `GET /api/audit/{trace_id}` · `WebSocket /api/voice`
(in addition to all Phase 4/5 endpoints).

## Phase 5 Demo (Autonomous Intelligence)

After the Phase 4 demo, on the **Intelligence** screen (or via CLI):

- **Scenario A — Health:** Dashboard/Intelligence shows cash, income, expenses,
  EMI, DTI and the deterministic Financial Health Score.
- **Scenario B — Anomaly:** Refresh intel (or `anomalies`) → an unusual
  transaction is flagged; `POST /api/finance/alerts/emit` pushes
  `financial_alert` events over SSE.
- **Scenario C — Cash Forecast:** Pick `7/14/30/60/90` days → projected
  balance / income / expenses / EMI / risk.
- **Scenario D — Goal:** Enter target ₹200,000 over 8 months → required saving,
  capacity and shortfall.
- **Scenario E — Digital Twin:** Salary `-10%`, Expenses `+15%`, new loan
  ₹200,000 → SIMULATE → new EMI/DTI/cash-flow/health/risk/recommendations;
  original data unchanged.
- **Scenario F — Recommendation:** Approve / Reject a pending recommendation; a
  recommendation is never executed without approval (`execute` works only on
  `APPROVED`).

**Phase 5 CLI commands:**

```bash
python agent_cli.py health
python agent_cli.py anomalies
python agent_cli.py cash-forecast --days 30
python agent_cli.py spending-forecast
python agent_cli.py goal --target 200000 --months 8
python agent_cli.py debt-optimization
python agent_cli.py scenario --salary-change -10 --expense-change 15 --loan-amount 200000
python agent_cli.py alerts
python agent_cli.py recommendations
```

## AI Trading Allocation Add-On (Paper Trading — Simulated)

Centerpiece: **the AI proposes a trade, the deterministic Rules Engine visibly
overrides or blocks it, and everything is traced.** There is **no real broker
connection and no real money** — stated explicitly, not hidden.

```text
Market Realtime MCP (accelerated replay)   →  volatility_spike (SSE)
Mocked Account Snapshot (conservative/moderate/aggressive)
        ↓
Stage 1  AI Proposer  →  TradeProposal { symbol, side, qty, rationale, confidence }
        ↓
Stage 2  Rules Engine (deterministic, NOT prompt-based)
         • max % position per risk profile
         • cash floor the agent can never trade below
         • daily-loss circuit breaker
         → resize / reject; logs original proposal, rule, final size
        ↓
FinalAllocationDecision  →  Demat MCP (PAPER ONLY)
        ↓
Paper order fills at tick + 0.1% slippage  →  mocked snapshot updated
        ↓
Trace log (market facts → proposal → rules → decision → order)  →  UI trace panel
```

- **Replay feed** (`replay_engine.py`): deterministic, scripted series with a
  baked-in price jump; `compute_sma`, `compute_realized_volatility`,
  `classify_trend`, and a reliable `volatility_spike` event (fires at a known
  cursor, looped so the demo never stalls).
- **Accounts** (`accounts_provider.py`): 3 mocked demo accounts with distinct
  risk profiles; unknown id → `ACCOUNT_NOT_LINKED`.
- **Rules engine** (`allocation_engine.py`): caps by risk profile, cash floor,
  circuit breaker; resizes/rejects and records the reason.
- **Demat engine** (`demat_engine.py`): paper-only fill at current tick + 0.1%
  slippage; updates the mocked snapshot; rejects orders that exceed cash
  (defence in depth). No live-mode code path.
- **Endpoints:** `GET /api/trading/accounts` · `GET /api/trading/accounts/{id}` ·
  `GET /api/trading/market/{symbol}/latest|ohlc|sma|volatility` ·
  `GET /api/trading/trend/{symbol}` · `POST /api/trading/allocate` ·
  `POST /api/trading/orders` · `GET /api/trading/orders/{id}` ·
  `GET /api/trading/trace` · `GET /api/trading/trace/{trace_id}`.
- **MCP servers:** `market_realtime_mcp_server.py` (9005),
  `governance_mcp_server.py` (9006), `demat_mcp_server.py` (9007).
- **Demo beat:** ask the AI to "go all in / ignore the limits" — the Rules Engine
  still resizes/blocks it. `POST /api/trading/allocate` (with or without
  `override_limits`) shows the visible override + `trace_id` chain.

> **Out of scope (stated to judges):** real bank/broker OAuth (replaced with
> mocked demo accounts), live order execution (paper mode only), full
> SEBI/compliance layer (shown as a roadmap slide with the trace log as
> evidence), voice/Gemini Live (cut). No real money moves.

## UI Motion System

The frontend animates like live instrumentation (React + Framer Motion):
`frontend/src/motion.tsx` defines shared motion tokens + primitives
(`AnimatedNumber` spring count-up with old→new value-flash in mint/coral,
`PulseDot`, `ShimmerBar`, `Reveal`/`Stagger`, `TraceSteps`, `Toast`), and
`index.css` holds the CSS keyframes (decision pulse, price flash, row insert,
edge flash, voice pulse, mono-number highlight). The whole app is wrapped in
`<MotionConfig reducedMotion="user">` plus a global `prefers-reduced-motion`
CSS gate, so motion is skipped for that preference.

Cross-cutting rules it follows: numbers never hard-cut (always animate
old→new); **amber is reserved exclusively for AI-proposal-vs-rules-engine
override moments** (corruption/danger are coral; review/flag states use a
muted violet); the **"Paper trading — simulated"** disclosure is deliberately
never animated; trace/decision reveals honour real execution order or real
parallelism (never fake a sequential animation onto genuinely parallel agents).

## Phase 6 Demo (Multi-Agent + Voice)

- **Control Center** screen: agent status (`/api/agents`), tool discovery
  (`/api/tools`), a "Route a Request" box (cross-domain, multi-agent), a live
  event feed and a **trace viewer**.
- **Cross-domain:** "I want a ₹300,000 loan for 36 months. Can I afford it while
  reaching my ₹200,000 savings goal?" → finance/bank/loan/market agents run in
  parallel → risk → governance (`PENDING_APPROVAL`) → facts → Gemini → audit.
- **Voice:** connect a WebSocket client to `ws://127.0.0.1:8000/api/voice`; send
  `{"type":"audio","data":"What is my financial health?"}` → streamed reply; send
  `{"type":"interrupt"}` to stop and issue a new query. Voice uses the same
  governance/risk/audit path as text.

## Known Limitations (demo/prototype)

- Bank data, transactions and loan offers are **mock** (`mock_data.json`).
- Market data comes from a **deterministic mock adapter** (`seed=42`) that
  synthesises OHLC from symbol base prices; values vary with the report date but
  are deterministic for a given day. There is **no live market API**.
- Session/conversation state, rate limiting, event bus and alert retention are
  **in-memory** (swappable for Redis/Postgres).
- Voice is a **text-fallback abstraction** (Gemini Live can be plugged in
  without touching the orchestrator).
- The financial-health score and risk rules are **configurable heuristics**, not
  a production credit model.
- The narrator never computes numbers, but when Gemini is unavailable the
  deterministic fallback narrator is used.
- **Phase 5** forecasts are **projections** (labelled as such), anomaly detection
  is statistical (no ML), the Digital Twin is a **temporary simulation** (real
  data is never modified), recommendations are **informational**, and the
  approval layer is **simulated** (no real bank/payment connection).
- **Phase 6** is a **multi-agent advisory system**: agents never execute real
  transactions or trades, the voice layer is a **streaming text mock** (Gemini
  Live plugs in behind the same interface), and session/event/audit stores are
  **in-memory**.

> FinPilot provides analytical insights, not guaranteed financial advice.
> For demo & educational purposes only.
