# FinPilot — AI Finance Controller

**Phase 4 · Unified AI Finance Controller Platform**

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
User
  → Intent / Tool Selection (deterministic router)
  → Python deterministic engine
  → Validated structured Facts
  → Gemini narrator (explains the facts only)
  → Response
```

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
- **Phase 4:** 104 new tests across unit / api / orchestrator / governance /
  integration / e2e.
- **Total:** 142 tests.

Test layers cover: engines, health score, scenario engine, budget guard, Pydantic
schema rejection, intent routing, tool-registry discoverability, anomaly
detection, tracing/audit, the FastAPI endpoints (`/health`, `/api/chat`,
`/api/scenario`, `/api/events`), the orchestrator (finance/loan/market/
multi-domain/invalid/budget-exceeded), security (no keys leaked, bad input
rejected), the canonical multi-domain integration flow, and an 8-step end-to-end
demo. Tests run offline using the mock data source + fallback narrator.

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

> FinPilot provides analytical insights, not guaranteed financial advice.
> For demo & educational purposes only.
