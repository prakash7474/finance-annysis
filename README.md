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
- **Total:** 249 tests.

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
