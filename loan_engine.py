"""
loan_engine.py - Loan math, risk assessment, and offer comparison.

Pure Python functions; no MCP or I/O logic.
"""

from typing import Any


def calculate_emi(principal: float, annual_rate_pct: float, tenure_months: int) -> float:
    """
    EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    r = monthly interest rate (decimal)
    """
    if tenure_months <= 0:
        return 0.0
    r = (annual_rate_pct / 12.0) / 100.0
    n = tenure_months
    if r == 0:
        return principal / n
    factor = (1 + r) ** n
    emi = principal * r * factor / (factor - 1)
    return emi


def total_interest_and_cost(
    principal: float,
    annual_rate_pct: float,
    tenure_months: int,
    processing_fee_pct: float = 0.0,
) -> dict[str, float]:
    """Compute EMI, total interest, and total cost including fees."""
    emi = calculate_emi(principal, annual_rate_pct, tenure_months)
    total_payment = emi * tenure_months
    total_interest = total_payment - principal
    processing_fee = principal * (processing_fee_pct / 100.0)
    total_cost = total_payment + processing_fee

    return {
        "emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
        "processing_fee": round(processing_fee, 2),
        "total_cost": round(total_cost, 2),
    }


def assess_loan_risk(
    principal: float,
    annual_rate_pct: float,
    tenure_months: int,
    monthly_income: float,
    existing_monthly_emi: float = 0.0,
    processing_fee_pct: float = 0.0,
) -> dict[str, Any]:
    """Assess loan risk based on EMI burden, interest rate, and tenure."""
    metrics = total_interest_and_cost(principal, annual_rate_pct, tenure_months, processing_fee_pct)
    emi = metrics["emi"]
    total_emi_burden = emi + existing_monthly_emi
    emi_income_ratio = total_emi_burden / monthly_income if monthly_income > 0 else float("inf")

    risk_flags: list[dict[str, str]] = []

    # Rule 1: EMI/income ratio
    if emi_income_ratio > 0.5:
        risk_flags.append({
            "code": "HIGH_EMI_INCOME_RATIO",
            "message": f"Total EMI burden is {emi_income_ratio*100:.1f}% of monthly income (>50%).",
            "severity": "HIGH",
        })
    elif emi_income_ratio > 0.4:
        risk_flags.append({
            "code": "MODERATE_EMI_INCOME_RATIO",
            "message": f"Total EMI burden is {emi_income_ratio*100:.1f}% of monthly income (40-50%).",
            "severity": "MEDIUM",
        })

    # Rule 2: High interest rate
    if annual_rate_pct >= 14:
        risk_flags.append({
            "code": "HIGH_INTEREST_RATE",
            "message": f"Interest rate {annual_rate_pct:.2f}% is high compared to typical personal loans.",
            "severity": "MEDIUM",
        })
    elif annual_rate_pct >= 12:
        risk_flags.append({
            "code": "MODERATE_INTEREST_RATE",
            "message": f"Interest rate {annual_rate_pct:.2f}% is moderate; consider negotiating or comparing offers.",
            "severity": "LOW",
        })

    # Rule 3: Short tenure stress
    if tenure_months <= 12 and emi_income_ratio > 0.35:
        risk_flags.append({
            "code": "SHORT_TENURE_HIGH_BURDEN",
            "message": "Short tenure with relatively high EMI burden; check cash flow comfort.",
            "severity": "MEDIUM",
        })

    risk_level = "LOW"
    if any(f["severity"] == "HIGH" for f in risk_flags):
        risk_level = "HIGH"
    elif any(f["severity"] == "MEDIUM" for f in risk_flags):
        risk_level = "MEDIUM"

    return {
        "emi": round(emi, 2),
        "total_cost": metrics["total_cost"],
        "total_interest": metrics["total_interest"],
        "processing_fee": metrics["processing_fee"],
        "emi_income_ratio": round(emi_income_ratio, 4),
        "risk_level": risk_level,
        "risk_flags": risk_flags,
    }


def compare_loan_offers(
    principal: float,
    offers: list[dict],
    monthly_income: float,
    existing_monthly_emi: float = 0.0,
) -> list[dict]:
    """
    Compare multiple loan offers and return scored results sorted by total cost.

    Each offer should have: offer_id, bank, interest_rate, tenure_months,
    and optionally processing_fee_pct.
    """
    results = []
    for o in offers:
        rate = o["interest_rate"]
        tenure = o["tenure_months"]
        proc_fee = o.get("processing_fee_pct", 0.0)

        risk = assess_loan_risk(
            principal=principal,
            annual_rate_pct=rate,
            tenure_months=tenure,
            monthly_income=monthly_income,
            existing_monthly_emi=existing_monthly_emi,
            processing_fee_pct=proc_fee,
        )

        results.append({
            "offer_id": o["offer_id"],
            "bank": o["bank"],
            "product": o.get("product", "Loan"),
            "interest_rate": rate,
            "tenure_months": tenure,
            "processing_fee_pct": proc_fee,
            "emi": risk["emi"],
            "total_cost": risk["total_cost"],
            "total_interest": risk["total_interest"],
            "processing_fee": risk["processing_fee"],
            "emi_income_ratio": risk["emi_income_ratio"],
            "risk_level": risk["risk_level"],
            "risk_flags": risk["risk_flags"],
        })

    # Sort by total_cost ascending
    results.sort(key=lambda x: x["total_cost"])
    return results


def calculate_dti(
    monthly_income: float,
    existing_monthly_emi: float = 0.0,
    new_monthly_emi: float = 0.0,
) -> float | None:
    """
    Compute the Debt-To-Income ratio as a decimal.

    DTI = (existing_emi + new_emi) / monthly_income

    Returns None when monthly income is not positive.
    """
    if monthly_income <= 0:
        return None
    return (existing_monthly_emi + new_monthly_emi) / monthly_income


# ──────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────────────────

def _format_inr(amount: float) -> str:
    """Format amount in Indian Rupee style."""
    if amount < 0:
        return f"-Rs.{abs(amount):,.2f}"
    return f"Rs.{amount:,.2f}"


def format_loan_analysis(result: dict) -> str:
    """Pretty-print single loan analysis."""
    lines = [
        "Loan Analysis:",
        "-" * 50,
        f"  EMI:                {_format_inr(result['emi'])}",
        f"  Total interest:     {_format_inr(result['total_interest'])}",
        f"  Processing fee:     {_format_inr(result['processing_fee'])}",
        f"  Total cost:         {_format_inr(result['total_cost'])}",
        f"  EMI / income ratio: {result['emi_income_ratio']*100:.1f}%",
        "",
        f"  Risk level: {result['risk_level']}",
    ]

    if result["risk_flags"]:
        lines.append("  Flags:")
        for f in result["risk_flags"]:
            lines.append(f"    [{f['severity']}] {f['message']}")
    else:
        lines.append("  No risk flags.")

    # Suggestion
    lines.append("")
    if result["risk_level"] == "HIGH":
        lines.append("  Suggestion: This loan carries significant risk. Consider a lower amount,")
        lines.append("  longer tenure, or a lower interest rate before proceeding.")
    elif result["risk_level"] == "MEDIUM":
        lines.append("  Suggestion: Moderate risk. Compare with other offers or consider")
        lines.append("  extending tenure to reduce EMI burden.")
    else:
        lines.append("  Suggestion: Low risk. This loan appears manageable for your income.")

    return "\n".join(lines)


def format_loan_comparison(results: list[dict], principal: float, income: float, existing_emi: float) -> str:
    """Pretty-print loan comparison table."""
    lines = [
        f"Loan Comparison for {_format_inr(principal)}",
        f"Income: {_format_inr(income)}/month | Existing EMI: {_format_inr(existing_emi)}/month",
        "-" * 80,
        f"{'Rank':<5} {'Bank':<15} {'Rate':<8} {'Tenure':<8} {'EMI':<14} {'Total Cost':<16} {'Risk':<8}",
        "-" * 80,
    ]

    for i, r in enumerate(results, 1):
        risk_marker = {"LOW": "OK", "MEDIUM": "~", "HIGH": "!!"}.get(r["risk_level"], "?")
        lines.append(
            f"{i:<5} {r['bank']:<15} {r['interest_rate']:<8.2f} "
            f"{r['tenure_months']:<8} {_format_inr(r['emi']):<14} "
            f"{_format_inr(r['total_cost']):<16} {risk_marker} {r['risk_level']}"
        )

    lines.append("-" * 80)

    if results:
        best_cost = min(results, key=lambda x: x["total_cost"])
        lowest_risk = min(results, key=lambda x: {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[x["risk_level"]])

        lines.append(f"Best by total cost:  {best_cost['bank']} ({_format_inr(best_cost['total_cost'])})")
        lines.append(f"Lowest risk option:  {lowest_risk['bank']} (risk: {lowest_risk['risk_level']})")

        if best_cost["offer_id"] != lowest_risk["offer_id"]:
            lines.append("")
            lines.append("Note: The cheapest option differs from the lowest-risk option.")
            lines.append("Consider your risk appetite when choosing.")

    return "\n".join(lines)
