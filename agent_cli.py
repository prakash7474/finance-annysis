"""
agent_cli.py - CLI agent for finance analysis.

Commands:
  cash-position    Show current cash position across all accounts
  monthly-summary  Show credit/debit summary for a date range
  emi-summary      Show EMI breakdown for a date range
  emi-ratio        Show EMI-to-income ratio
  category-summary Show spending breakdown by category
  loan-analysis    Analyze a single loan scenario
  compare-loans    Compare multiple loan offers
  price            Get latest stock price
  ohlc             Get OHLC history for a stock
  trend            Analyze trend vs SMA
  momentum         Analyze price momentum
"""

import argparse
import io
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import finance_engine as fe
import loan_engine as le
import market_engine as me

# Fix Windows console encoding for the rupee symbol (matches finance_chat.py/app.py)
try:
    if sys.platform == "win32" and hasattr(sys.stdout, "buffer") and not sys.stdout.closed:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.platform == "win32" and hasattr(sys.stderr, "buffer") and not sys.stderr.closed:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except (ValueError, AttributeError):
    pass


@asynccontextmanager
async def get_mcp_session(server_script: str = "bank_mcp_server.py"):
    """Create and connect an MCP session to a server.

    Used as an async context manager (avoids the anyio teardown bug that
    occurs when an async generator is closed mid-iteration via ``break``).
    """
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).parent / server_script)],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def _parse_tool_result(result):
    """Parse MCP tool result, handling both JSON string and JSON array formats."""
    text = result.content[0].text
    parsed = json.loads(text)
    # MCP v2 may return each list item as separate content items
    # But since we return JSON strings now, this handles both cases
    if isinstance(parsed, list):
        return parsed
    return [parsed]


def _parse_tool_result_flat(result):
    """Parse MCP tool result that returns a JSON string containing a list."""
    return json.loads(result.content[0].text)


async def cmd_cash_position(args):
    """Show current cash position across all accounts."""
    async with get_mcp_session() as session:
        accounts = await session.call_tool("get_accounts", {})
        accounts_list = _parse_tool_result_flat(accounts)
        transactions = _parse_tool_result_flat(
            await session.call_tool("get_transactions", {})
        )

        pos = fe.compute_cash_position(accounts_list, transactions)
        print(fe.format_cash_position(pos))


async def cmd_monthly_summary(args):
    """Show credit/debit summary for a date range."""
    async with get_mcp_session() as session:
        transactions = _parse_tool_result_flat(
            await session.call_tool("get_transactions", {
                "start_date": args.start_date,
                "end_date": args.end_date,
            })
        )

        summary = fe.summarize_credit_debit(transactions, args.start_date, args.end_date)
        print(fe.format_monthly_summary(summary))


async def cmd_emi_summary(args):
    """Show EMI breakdown for a date range."""
    async with get_mcp_session() as session:
        transactions = _parse_tool_result_flat(
            await session.call_tool("get_transactions", {
                "start_date": args.start_date,
                "end_date": args.end_date,
            })
        )

        emi_data = fe.detect_emis(transactions, args.start_date, args.end_date)
        print(fe.format_emi_summary(emi_data))


async def cmd_emi_ratio(args):
    """Show EMI-to-income ratio."""
    async with get_mcp_session() as session:
        transactions = _parse_tool_result_flat(
            await session.call_tool("get_transactions", {
                "start_date": args.start_date,
                "end_date": args.end_date,
            })
        )

        ratio_data = fe.compute_emi_income_ratio(transactions, args.start_date, args.end_date)
        print(f"EMI-to-Income Ratio ({args.start_date} to {args.end_date}):")
        print("-" * 40)
        print(f"  Total income:  {fe.format_inr(ratio_data['total_income'])}")
        print(f"  Total EMI:     {fe.format_inr(ratio_data['total_emi'])}")
        print(f"  EMI/Income:    {ratio_data['emi_income_ratio_pct']:.1f}%")
        print(f"  Status:        {'⚠️  STRESSED (>40%)' if ratio_data['is_stressed'] else '✅ Healthy'}")


async def cmd_category_summary(args):
    """Show spending breakdown by category."""
    async with get_mcp_session() as session:
        transactions = _parse_tool_result_flat(
            await session.call_tool("get_transactions", {
                "start_date": args.start_date,
                "end_date": args.end_date,
            })
        )

        cat_summary = fe.get_category_summary(transactions, args.start_date, args.end_date)
        print(f"Category Summary ({args.start_date} to {args.end_date}):")
        print("-" * 40)
        for cat, data in sorted(cat_summary["categories"].items(), key=lambda x: x[1]["total"], reverse=True):
            print(f"  {cat:<20} {fe.format_inr(data['total']):>15}  ({data['count']} txns)")


async def cmd_loan_analysis(args):
    """Analyze a single loan scenario with risk assessment."""
    result = le.assess_loan_risk(
        principal=args.amount,
        annual_rate_pct=args.rate,
        tenure_months=args.tenure_months,
        monthly_income=args.monthly_income,
        existing_monthly_emi=args.existing_emi,
        processing_fee_pct=args.processing_fee_pct,
    )
    print(f"Loan: {fe.format_inr(args.amount)} at {args.rate}% for {args.tenure_months} months")
    print(f"Income: {fe.format_inr(args.monthly_income)}/month | Existing EMI: {fe.format_inr(args.existing_emi)}/month")
    print()
    print(le.format_loan_analysis(result))


async def cmd_price(args):
    """Get latest stock price."""
    async with get_mcp_session("market_mcp_server.py") as session:
        result = _parse_tool_result_flat(
            await session.call_tool("get_price", {"symbol": args.symbol})
        )
        print(me.format_price(result["symbol"], result["price"]))


async def cmd_ohlc(args):
    """Get OHLC history for a stock."""
    async with get_mcp_session("market_mcp_server.py") as session:
        result = _parse_tool_result_flat(
            await session.call_tool("get_ohlc", {"symbol": args.symbol, "days": args.days})
        )
        print(me.format_ohlc_table(result["bars"], result["symbol"], last_n=min(args.days, 15)))
        print(f"  Total bars: {result['count']}")


async def cmd_trend(args):
    """Analyze trend vs SMA."""
    async with get_mcp_session("market_mcp_server.py") as session:
        days_needed = max(args.sma_days * 2, 60)
        result = _parse_tool_result_flat(
            await session.call_tool("get_ohlc", {"symbol": args.symbol, "days": days_needed})
        )
        trend = me.detect_trend_vs_sma(result["bars"], sma_days=args.sma_days)
        print(me.format_trend(args.symbol, trend))


async def cmd_momentum(args):
    """Analyze price momentum."""
    async with get_mcp_session("market_mcp_server.py") as session:
        days_needed = args.lookback_days + 5
        result = _parse_tool_result_flat(
            await session.call_tool("get_ohlc", {"symbol": args.symbol, "days": days_needed})
        )
        mom = me.compute_momentum(result["bars"], lookback_days=args.lookback_days)
        print(me.format_momentum(args.symbol, mom))


async def cmd_compare_loans(args):
    """Compare loan offers from mock data."""
    async with get_mcp_session() as session:
        offers_raw = _parse_tool_result_flat(
            await session.call_tool("get_loan_offers", {})
        )

        # Filter to specific banks if requested
        if args.banks:
            bank_list = [b.strip().upper() for b in args.banks.split(",")]
            offers_raw = [
                o for o in offers_raw
                if any(bank in o["bank"].upper() for bank in bank_list)
            ]

        if not offers_raw:
            print("No loan offers found matching your criteria.")
            return

        results = le.compare_loan_offers(
            principal=args.amount,
            offers=offers_raw,
            monthly_income=args.monthly_income,
            existing_monthly_emi=args.existing_emi,
        )

        print(le.format_loan_comparison(results, args.amount, args.monthly_income, args.existing_emi))


# ──────────────────────────────────────────────────────────────────────────────
# Phase 5 - Autonomous Financial Intelligence CLI commands
# ──────────────────────────────────────────────────────────────────────────────

async def _fetch_bank_data():
    async with get_mcp_session() as session:
        accounts = _parse_tool_result_flat(await session.call_tool("get_accounts", {}))
        transactions = _parse_tool_result_flat(await session.call_tool("get_transactions", {}))
        offers = _parse_tool_result_flat(await session.call_tool("get_loan_offers", {}))
    return accounts, transactions, offers


from intelligence import compute_phase5_facts  # noqa: E402
from models.scenario_models import ScenarioInput  # noqa: E402
from digital_twin import simulate_financial_scenario  # noqa: E402
from models.financial_models import FinancialSnapshot  # noqa: E402


def _print_phase5_header(title: str):
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def cmd_health(args):
    """Show Financial Health Score."""
    accounts, transactions, offers = await _fetch_bank_data()
    facts = compute_phase5_facts(accounts, transactions, offers)
    h = facts["health"]
    _print_phase5_header("FINANCIAL HEALTH")
    print(f"  Score:            {h['score']} / 100")
    print(f"  Status:           {h['status']}")
    print(f"  Liquidity score:  {h['liquidity_score']}")
    print(f"  Debt score:       {h['debt_score']}")
    print(f"  Expense score:    {h['expense_score']}")
    print(f"  Savings score:    {h['savings_score']}")
    print(f"  DTI:              {facts['dti'] * 100:.1f}%")
    for r in h["reasons"]:
        print(f"    - {r}")


async def cmd_anomalies(args):
    """Detect transaction anomalies."""
    accounts, transactions, offers = await _fetch_bank_data()
    facts = compute_phase5_facts(accounts, transactions, offers)
    _print_phase5_header("TRANSACTION ANOMALIES")
    if not facts["anomalies"]:
        print("  No anomalies detected.")
    for a in facts["anomalies"]:
        print(f"  [{a['severity']}] {a['category']} : {a['amount']:,.2f} vs expected {a['expected_amount']:,.2f}")
        print(f"         {a['reason']}")


async def cmd_cash_forecast(args):
    """Project cash flow."""
    accounts, transactions, offers = await _fetch_bank_data()
    facts = compute_phase5_facts(accounts, transactions, offers, forecast_days=args.days)
    f = facts["forecast"]
    _print_phase5_header(f"CASH-FLOW FORECAST ({args.days} days)")
    print(f"  Projected balance: {fe.format_inr(f['projected_balance'])}")
    print(f"  Projected income:  {fe.format_inr(f['projected_income'])}")
    print(f"  Projected expenses:{fe.format_inr(f['projected_expenses'])}")
    print(f"  Projected EMI:     {fe.format_inr(f['projected_emi'])}")
    print(f"  Confidence:        {f['confidence']}")
    print(f"  Risk level:        {f['risk_level']}")
    print("  (Forecast - not a guarantee)")


async def cmd_spending_forecast(args):
    """Project spending by category."""
    accounts, transactions, offers = await _fetch_bank_data()
    facts = compute_phase5_facts(accounts, transactions, offers)
    _print_phase5_header("SPENDING FORECAST")
    for s in facts["spending"][:12]:
        print(f"  {s['category']:<16} {fe.format_inr(s['projected_amount']):>16}  (risk {s['risk_level']})")


async def cmd_goal(args):
    """Plan a financial goal."""
    accounts, transactions, offers = await _fetch_bank_data()
    facts = compute_phase5_facts(accounts, transactions, offers)
    from goal_engine import plan_financial_goal

    goal = plan_financial_goal(
        target_amount=args.target,
        current_saved_amount=args.current or 0,
        months_remaining=args.months,
        monthly_income=facts['monthly_income'],
        monthly_expenses=facts['monthly_expenses'],
        monthly_emi=facts['existing_emi'],
        name=args.name,
    )
    _print_phase5_header("FINANCIAL GOAL")
    print(f"  Goal:             {goal.name}")
    print(f"  Target:           {fe.format_inr(goal.target_amount)}")
    print(f"  Current savings:  {fe.format_inr(goal.current_saved_amount)}")
    print(f"  Remaining:        {fe.format_inr(goal.remaining_amount)}")
    print(f"  Months left:      {goal.months_remaining}")
    print(f"  Required monthly: {fe.format_inr(goal.required_monthly_saving)}")
    print(f"  Saving capacity:  {fe.format_inr(goal.current_saving_capacity)}")
    print(f"  Monthly shortfall:{fe.format_inr(goal.monthly_shortfall)}")
    print(f"  Status:           {goal.status}")


async def cmd_debt_optimization(args):
    """Rank debt repayment."""
    accounts, transactions, offers = await _fetch_bank_data()
    facts = compute_phase5_facts(accounts, transactions, offers)
    _print_phase5_header("DEBT OPTIMIZATION")
    for r in facts["debt"]:
        print(f"  #{r['priority']} {r['bank']:<16} emi {fe.format_inr(r['monthly_emi'])}  "
              f"interest {fe.format_inr(r['estimated_interest'])}  dti {r['dti_impact'] * 100:.1f}%")
        print(f"       strategy={r['strategy']} reasons={r['reason_codes']}")


async def cmd_scenario(args):
    """Run the Digital Twin scenario simulator."""
    accounts, transactions, offers = await _fetch_bank_data()
    facts = compute_phase5_facts(accounts, transactions, offers)
    snapshot = FinancialSnapshot(**facts["snapshot"])
    scenario = ScenarioInput(
        salary_change_percentage=args.salary_change,
        expense_change_percentage=args.expense_change,
        new_loan_amount=args.loan_amount,
        new_loan_rate=args.loan_rate,
        new_loan_tenure=args.loan_tenure,
    )
    result = simulate_financial_scenario(snapshot, scenario).model_dump()
    _print_phase5_header("FINANCIAL DIGITAL TWIN - SCENARIO")
    cur, sim = result["baseline"], result["simulated"]
    print(f"  {'':<16}{'CURRENT':>16}{'SCENARIO':>18}")
    print(f"  {'Income':<16}{cur['monthly_income']:>16,.2f}{sim['monthly_income']:>18,.2f}")
    print(f"  {'Expenses':<16}{cur['monthly_expenses']:>16,.2f}{sim['monthly_expenses']:>18,.2f}")
    print(f"  {'EMI':<16}{cur['new_emi']:>16,.2f}{sim['new_emi']:>18,.2f}")
    print(f"  {'DTI':<16}{cur['dti'] * 100:>15.1f}%{sim['dti'] * 100:>17.1f}%")
    print(f"  {'Cash flow':<16}{cur['cash_flow']:>16,.2f}{sim['cash_flow']:>18,.2f}")
    print(f"  {'Health':<16}{cur['health_score']:>16,.1f}{sim['health_score']:>18,.1f}")
    print(f"  {'Risk':<16}{cur['risk_level']:>16}{sim['risk_level']:>18}")
    print("  Recommendations:")
    for r in result["recommendations"]:
        print(f"    - {r}")


async def cmd_alerts(args):
    """Show smart financial alerts."""
    accounts, transactions, offers = await _fetch_bank_data()
    facts = compute_phase5_facts(accounts, transactions, offers)
    _print_phase5_header("FINANCIAL ALERTS")
    if not facts["alerts"]:
        print("  No active alerts.")
    for a in facts["alerts"]:
        print(f"  [{a['severity']}] {a['title']} - {a['description']}")


async def cmd_recommendations(args):
    """Show recommendations."""
    accounts, transactions, offers = await _fetch_bank_data()
    facts = compute_phase5_facts(accounts, transactions, offers)
    _print_phase5_header("AI RECOMMENDATIONS")
    for r in facts["recommendations"]:
        flag = "[APPROVAL]" if r["requires_approval"] else "[INFO]"
        print(f"  #{r['priority']} {flag} {r['title']}")
        print(f"       reasons={r['reason_codes']} confidence={r['confidence']}")


async def main():
    parser = argparse.ArgumentParser(
        description="Finance Controller CLI - Query your mock bank data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agent_cli.py cash-position
  python agent_cli.py monthly-summary --start-date 2026-08-01 --end-date 2026-08-31
  python agent_cli.py emi-summary --start-date 2026-07-01 --end-date 2026-08-31
  python agent_cli.py emi-ratio --start-date 2026-08-01 --end-date 2026-08-31
  python agent_cli.py category-summary --start-date 2026-08-01 --end-date 2026-08-31
  python agent_cli.py loan-analysis --amount 300000 --rate 12.0 --tenure-months 36 --monthly-income 80000
  python agent_cli.py compare-loans --amount 200000 --monthly-income 80000 --existing-emi 22300
  python agent_cli.py price --symbol RELIANCE
  python agent_cli.py ohlc --symbol INFY --days 30
  python agent_cli.py trend --symbol INFY --sma-days 20
  python agent_cli.py momentum --symbol TCS --lookback-days 10
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # cash-position
    subparsers.add_parser("cash-position", help="Show current cash position")

    # monthly-summary
    ms = subparsers.add_parser("monthly-summary", help="Show credit/debit summary")
    ms.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    ms.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")

    # emi-summary
    es = subparsers.add_parser("emi-summary", help="Show EMI breakdown")
    es.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    es.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")

    # emi-ratio
    er = subparsers.add_parser("emi-ratio", help="Show EMI-to-income ratio")
    er.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    er.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")

    # category-summary
    cs = subparsers.add_parser("category-summary", help="Show spending by category")
    cs.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    cs.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")

    # loan-analysis
    la = subparsers.add_parser("loan-analysis", help="Analyze a single loan scenario")
    la.add_argument("--amount", type=float, required=True, help="Loan amount in INR")
    la.add_argument("--rate", type=float, required=True, help="Annual interest rate (%%)")
    la.add_argument("--tenure-months", type=int, required=True, help="Tenure in months")
    la.add_argument("--monthly-income", type=float, required=True, help="Monthly income in INR")
    la.add_argument("--existing-emi", type=float, default=0.0, help="Existing monthly EMI (default: 0)")
    la.add_argument("--processing-fee-pct", type=float, default=0.0, help="Processing fee %% (default: 0)")

    # compare-loans
    cl = subparsers.add_parser("compare-loans", help="Compare loan offers from mock data")
    cl.add_argument("--amount", type=float, required=True, help="Loan amount in INR")
    cl.add_argument("--monthly-income", type=float, required=True, help="Monthly income in INR")
    cl.add_argument("--existing-emi", type=float, default=0.0, help="Existing monthly EMI (default: 0)")
    cl.add_argument("--banks", type=str, default=None, help="Comma-separated bank names to filter (e.g., HDFC,ICICI)")

    # price
    pr = subparsers.add_parser("price", help="Get latest stock price")
    pr.add_argument("--symbol", type=str, required=True, help="Stock symbol (e.g., RELIANCE, INFY)")

    # ohlc
    oc = subparsers.add_parser("ohlc", help="Get OHLC history")
    oc.add_argument("--symbol", type=str, required=True, help="Stock symbol")
    oc.add_argument("--days", type=int, default=30, help="Number of days (default: 30)")

    # trend
    tr = subparsers.add_parser("trend", help="Analyze trend vs SMA")
    tr.add_argument("--symbol", type=str, required=True, help="Stock symbol")
    tr.add_argument("--sma-days", type=int, default=20, help="SMA window in days (default: 20)")

    # momentum
    mo = subparsers.add_parser("momentum", help="Analyze price momentum")
    mo.add_argument("--symbol", type=str, required=True, help="Stock symbol")
    mo.add_argument("--lookback-days", type=int, default=10, help="Momentum lookback (default: 10)")

    # ── Phase 5 commands ──────────────────────────────────────────────────────
    h = subparsers.add_parser("health", help="Show financial health score")
    an = subparsers.add_parser("anomalies", help="Detect transaction anomalies")
    cf = subparsers.add_parser("cash-forecast", help="Project cash flow")
    cf.add_argument("--days", type=int, default=30, help="Forecast horizon (7/14/30/60/90)")
    sf = subparsers.add_parser("spending-forecast", help="Project spending by category")
    g = subparsers.add_parser("goal", help="Plan a financial goal")
    g.add_argument("--target", type=float, required=True, help="Target amount")
    g.add_argument("--months", type=int, required=True, help="Months remaining")
    g.add_argument("--current", type=float, default=0.0, help="Current saved amount")
    g.add_argument("--name", type=str, default="Savings Goal", help="Goal name")
    db = subparsers.add_parser("debt-optimization", help="Rank debt repayment")
    sc = subparsers.add_parser("scenario", help="Run the Digital Twin simulator")
    sc.add_argument("--salary-change", type=float, default=0.0, help="Salary change percent")
    sc.add_argument("--expense-change", type=float, default=0.0, help="Expense change percent")
    sc.add_argument("--loan-amount", type=float, default=0.0, help="New loan amount")
    sc.add_argument("--loan-rate", type=float, default=12.0, help="New loan rate")
    sc.add_argument("--loan-tenure", type=int, default=36, help="New loan tenure")
    al = subparsers.add_parser("alerts", help="Show financial alerts")
    rc = subparsers.add_parser("recommendations", help="Show recommendations")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    import asyncio
    handlers = {
        "cash-position": cmd_cash_position,
        "monthly-summary": cmd_monthly_summary,
        "emi-summary": cmd_emi_summary,
        "emi-ratio": cmd_emi_ratio,
        "category-summary": cmd_category_summary,
        "loan-analysis": cmd_loan_analysis,
        "compare-loans": cmd_compare_loans,
        "price": cmd_price,
        "ohlc": cmd_ohlc,
        "trend": cmd_trend,
        "momentum": cmd_momentum,
        "health": cmd_health,
        "anomalies": cmd_anomalies,
        "cash-forecast": cmd_cash_forecast,
        "spending-forecast": cmd_spending_forecast,
        "goal": cmd_goal,
        "debt-optimization": cmd_debt_optimization,
        "scenario": cmd_scenario,
        "alerts": cmd_alerts,
        "recommendations": cmd_recommendations,
    }
    await handlers[args.command](args)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
