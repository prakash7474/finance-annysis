# AI Finance Controller - Phase 1 + 2 + 3

Mock Bank Data + Finance Controller + Loan Advisor + Market Data using MCP.

## Overview

This project implements an AI finance controller that:
- Connects to a mock bank via MCP
- Ingests 79 synthetic transactions across 2 accounts
- Computes cash position, credit/debit summaries, and EMI breakdowns
- Analyzes loan scenarios with EMI calculation and risk assessment
- Compares multiple loan offers with cost and risk ranking
- Fetches stock prices, OHLC data, and computes SMA/trend/momentum
- Answers finance and market queries via CLI + AI chatbot

## Architecture

```
agent_cli.py              ← CLI, connects to both MCP servers
    ↓
bank_mcp_server.py        ← Bank MCP (accounts, transactions)
market_mcp_server.py      ← Market MCP (prices, OHLC, news)
    ↓
mock_data.json            ← 79 transactions, 2 accounts, 4 loans
finance_engine.py         ← Finance analysis (Phase 1)
loan_engine.py            ← Loan math & risk (Phase 2)
market_engine.py          ← SMA, trend, momentum (Phase 3)
mock_market_adapter.py    ← Deterministic mock market data
loan_advisor_chat.py      ← Gemini AI chatbot
```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import finance_engine; import mcp; print('OK')"
```

## Usage

### Cash Position
```bash
python agent_cli.py cash-position
```

Output:
```
Cash Position:
----------------------------------------
  HDFC Savings (ACC001): ₹109,936.50
  ICICI Credit Card (ACC002): ₹-15,122.00
----------------------------------------
  Net cash: ₹94,814.50
```

### Monthly Summary
```bash
python agent_cli.py monthly-summary --start-date 2026-08-01 --end-date 2026-08-31
```

Output:
```
Summary (2026-08-01 to 2026-08-31):
----------------------------------------
  Total credit:  ₹122,625.00
  Total debit:   ₹169,594.00
  Net change:    -₹46,969.00
  Transactions:  42
```

### EMI Summary
```bash
python agent_cli.py emi-summary --start-date 2026-08-01 --end-date 2026-08-31
```

Output:
```
EMI Summary (2026-08-01 to 2026-08-31):
----------------------------------------
  2026-08-02 | EMI - HDFC PERSONAL LOAN | ₹12,500.00
  2026-08-03 | EMI - ICICI PERSONAL LOAN | ₹9,800.00
  2026-08-08 | EMI - SBI HOUSING LOAN | ₹15,200.00
  2026-08-14 | EMI - HDFC PERSONAL LOAN | ₹12,500.00
  2026-08-14 | EMI - ICICI PERSONAL LOAN | ₹9,800.00
  2026-08-19 | EMI - SBI HOUSING LOAN | ₹15,200.00
  2026-08-25 | EMI - HDFC PERSONAL LOAN | ₹12,500.00
  2026-08-25 | EMI - ICICI PERSONAL LOAN | ₹9,800.00
----------------------------------------
  Total EMI: ₹97,300.00

  Breakdown by lender:
    HDFC PERSONAL LOAN: ₹37,500.00
    ICICI PERSONAL LOAN: ₹29,400.00
    SBI HOUSING LOAN: ₹30,400.00
```

### EMI-to-Income Ratio
```bash
python agent_cli.py emi-ratio --start-date 2026-08-01 --end-date 2026-08-31
```

### Category Summary
```bash
python agent_cli.py category-summary --start-date 2026-08-01 --end-date 2026-08-31
```

### Loan Analysis (Phase 2)
```bash
python agent_cli.py loan-analysis --amount 300000 --rate 12.0 --tenure-months 36 --monthly-income 80000
```

Output:
```
Loan: Rs.300,000.00 at 12.0% for 36 months
Income: Rs.80,000.00/month | Existing EMI: Rs.0.00/month

Loan Analysis:
--------------------------------------------------
  EMI:                Rs.9,964.29
  Total interest:     Rs.58,714.55
  Processing fee:     Rs.0.00
  Total cost:         Rs.358,714.55
  EMI / income ratio: 12.5%

  Risk level: LOW
  Flags:
    [LOW] Interest rate 12.00% is moderate; consider negotiating or comparing offers.

  Suggestion: Low risk. This loan appears manageable for your income.
```

### Compare Loans (Phase 2)
```bash
python agent_cli.py compare-loans --amount 200000 --monthly-income 80000 --existing-emi 22300
```

Output:
```
Loan Comparison for Rs.200,000.00
Income: Rs.80,000.00/month | Existing EMI: Rs.22,300.00/month
--------------------------------------------------------------------------------
Rank  Bank            Rate     Tenure   EMI            Total Cost       Risk
--------------------------------------------------------------------------------
1     ICICI Bank      12.00    24       Rs.9,414.69    Rs.228,952.67    OK LOW
2     HDFC Bank       11.50    36       Rs.6,595.20    Rs.239,427.25    OK LOW
3     Axis Bank       9.00     60       Rs.4,151.67    Rs.253,100.26    OK LOW
4     SBI             8.50     240      Rs.1,735.65    Rs.417,555.15    OK LOW
--------------------------------------------------------------------------------
Best by total cost:  ICICI Bank (Rs.228,952.67)
Lowest risk option:  ICICI Bank (risk: LOW)
```

### Filter by Bank
```bash
python agent_cli.py compare-loans --amount 200000 --monthly-income 80000 --banks "HDFC,ICICI"
```

### Stock Price (Phase 3)
```bash
python agent_cli.py price --symbol RELIANCE
```

Output: `RELIANCE: Rs.2,428.42`

### OHLC History (Phase 3)
```bash
python agent_cli.py ohlc --symbol INFY --days 30
```

### Trend Analysis (Phase 3)
```bash
python agent_cli.py trend --symbol INFY --sma-days 20
```

Output:
```
Trend Analysis for INFY:
----------------------------------------
  Latest close:  Rs.1,564.21
  20-day SMA:    Rs.1,520.35
  Difference:   +2.88%
  Trend:        ^ UPTREND
```

### Momentum (Phase 3)
```bash
python agent_cli.py momentum --symbol TCS --lookback-days 10
```

Output:
```
Momentum for TCS:
----------------------------------------
  Lookback:     10 days
  Older close:  Rs.3,684.61
  Latest close: Rs.3,811.99
  Momentum:     +3.46%
  Signal:       Mild positive momentum
```

## Data

- **Accounts**: HDFC Savings (₹125,000 opening), ICICI Credit Card (₹15,000 opening)
- **Transactions**: 79 transactions covering July-August 2026
- **Categories**: Salary, Loan EMI, Food, Fuel, Shopping, Transport, Utility, Rent, etc.
- **Loan Offers**: HDFC Personal, ICICI Personal, SBI Home, Axis Car

### Loan Advisor Chat (Phase 2)
```bash
python loan_advisor_chat.py
```

Interactive AI chatbot powered by **Google Gemini** (gemini-3.6-flash) with automatic function calling. Asks questions like:
- "I want to take a 3 lakh loan at 12% for 36 months"
- "Compare HDFC vs ICICI for 2 lakh loan"
- "What if I extend tenure from 24 to 36 months?"
- "What's my cash position?"

The chatbot uses Gemini's AFC (Automatic Function Calling) to compute real EMI, risk, and comparisons using your `loan_engine.py` and `finance_engine.py`.

## Testing

```bash
# Run all tests (38 total)
python -m pytest test_loan_engine.py test_market_engine.py -v
```

### Loan Engine Tests (19)
- EMI calculation, total cost, risk assessment, offer comparison, formatting

### Market Engine Tests (19)
- SMA computation, trend detection (uptrend/downtrend/neutral)
- Momentum calculation, high/low range
- Mock adapter determinism and integration

## Roadmap

- [x] Phase 1: Mock bank data + basic finance controller
- [x] Phase 2: Loan advisor & what-if analysis
- [x] Phase 3: Market data MCP + trading assistant
- [ ] Phase 4: Unified finance chatbot
