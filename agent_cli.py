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
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import finance_engine as fe
import loan_engine as le
import market_engine as me


async def get_mcp_session(server_script: str = "bank_mcp_server.py"):
    """Create and connect an MCP session to a server."""
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
    async for session in get_mcp_session():
        accounts = await session.call_tool("get_accounts", {})
        accounts_list = _parse_tool_result_flat(accounts)
        transactions = _parse_tool_result_flat(
            await session.call_tool("get_transactions", {})
        )

        pos = fe.compute_cash_position(accounts_list, transactions)
        print(fe.format_cash_position(pos))
        break


async def cmd_monthly_summary(args):
    """Show credit/debit summary for a date range."""
    async for session in get_mcp_session():
        transactions = _parse_tool_result_flat(
            await session.call_tool("get_transactions", {
                "start_date": args.start_date,
                "end_date": args.end_date,
            })
        )

        summary = fe.summarize_credit_debit(transactions, args.start_date, args.end_date)
        print(fe.format_monthly_summary(summary))
        break


async def cmd_emi_summary(args):
    """Show EMI breakdown for a date range."""
    async for session in get_mcp_session():
        transactions = _parse_tool_result_flat(
            await session.call_tool("get_transactions", {
                "start_date": args.start_date,
                "end_date": args.end_date,
            })
        )

        emi_data = fe.detect_emis(transactions, args.start_date, args.end_date)
        print(fe.format_emi_summary(emi_data))
        break


async def cmd_emi_ratio(args):
    """Show EMI-to-income ratio."""
    async for session in get_mcp_session():
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
        break


async def cmd_category_summary(args):
    """Show spending breakdown by category."""
    async for session in get_mcp_session():
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
        break


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
    async for session in get_mcp_session("market_mcp_server.py"):
        result = _parse_tool_result_flat(
            await session.call_tool("get_price", {"symbol": args.symbol})
        )
        print(me.format_price(result["symbol"], result["price"]))
        break


async def cmd_ohlc(args):
    """Get OHLC history for a stock."""
    async for session in get_mcp_session("market_mcp_server.py"):
        result = _parse_tool_result_flat(
            await session.call_tool("get_ohlc", {"symbol": args.symbol, "days": args.days})
        )
        print(me.format_ohlc_table(result["bars"], result["symbol"], last_n=min(args.days, 15)))
        print(f"  Total bars: {result['count']}")
        break


async def cmd_trend(args):
    """Analyze trend vs SMA."""
    async for session in get_mcp_session("market_mcp_server.py"):
        days_needed = max(args.sma_days * 2, 60)
        result = _parse_tool_result_flat(
            await session.call_tool("get_ohlc", {"symbol": args.symbol, "days": days_needed})
        )
        trend = me.detect_trend_vs_sma(result["bars"], sma_days=args.sma_days)
        print(me.format_trend(args.symbol, trend))
        break


async def cmd_momentum(args):
    """Analyze price momentum."""
    async for session in get_mcp_session("market_mcp_server.py"):
        days_needed = args.lookback_days + 5
        result = _parse_tool_result_flat(
            await session.call_tool("get_ohlc", {"symbol": args.symbol, "days": days_needed})
        )
        mom = me.compute_momentum(result["bars"], lookback_days=args.lookback_days)
        print(me.format_momentum(args.symbol, mom))
        break


async def cmd_compare_loans(args):
    """Compare loan offers from mock data."""
    async for session in get_mcp_session():
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
            break

        results = le.compare_loan_offers(
            principal=args.amount,
            offers=offers_raw,
            monthly_income=args.monthly_income,
            existing_monthly_emi=args.existing_emi,
        )

        print(le.format_loan_comparison(results, args.amount, args.monthly_income, args.existing_emi))
        break


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
    }
    await handlers[args.command](args)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
