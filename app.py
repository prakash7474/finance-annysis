"""
app.py - FinPilot: AI Finance Controller (Streamlit Web UI)

A premium fintech control center:
  - Overview dashboard (financial health, KPIs, cash flow, insight, activity)
  - Finance Controller
  - Loan Advisor (single loan, what-if, compare offers)
  - Market & Trading Assistant
  - AI Finance Copilot (hero feature)
  - Notifications
  - Profile / Settings

Usage:
    streamlit run app.py
"""

import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Fix Windows console encoding for the rupee symbol (safe for Streamlit reruns)
try:
    if sys.platform == "win32" and hasattr(sys.stdout, 'buffer') and not sys.stdout.closed:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.platform == "win32" and hasattr(sys.stderr, 'buffer') and not sys.stderr.closed:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except (ValueError, AttributeError):
    pass

from dotenv import load_dotenv
load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# App config
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="FinPilot - AI Finance Controller",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# Load data & engines
# ──────────────────────────────────────────────────────────────────────────────

DATA_FILE = Path(__file__).parent / "mock_data.json"
_mock_data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

import finance_engine as fe
import loan_engine as le
import market_engine as me
from mock_market_adapter import MockMarketAdapter

_market_adapter = MockMarketAdapter(seed=42)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# ──────────────────────────────────────────────────────────────────────────────
# Gemini chat session (lazy, never blocks page render)
# ──────────────────────────────────────────────────────────────────────────────

def _get_gemini_chat():
    """Create a Gemini chat session with all finance tools, or None on any failure."""
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return None

    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        from finance_chat import (
            get_cash_position, get_monthly_summary, get_emi_summary,
            get_category_summary, analyze_loan, compare_loan_offers,
            what_if_tenure, get_stock_price, get_stock_trend,
            get_stock_momentum, get_stock_ohlc, get_stock_high_low,
            loan_with_cash_context, SYSTEM_PROMPT,
        )
        all_tools = [
            get_cash_position, get_monthly_summary, get_emi_summary,
            get_category_summary, analyze_loan, compare_loan_offers,
            what_if_tenure, get_stock_price, get_stock_trend,
            get_stock_momentum, get_stock_ohlc, get_stock_high_low,
            loan_with_cash_context,
        ]
        chat = client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                tools=all_tools,
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
            ),
        )
        return chat
    except Exception:
        return None


def _local_answer(user_text: str) -> str:
    """Offline rule-based fallback for the AI copilot when Gemini is unavailable."""
    text = (user_text or "").lower()
    try:
        if any(k in text for k in ("cash", "balance", "position", "account")):
            pos = DATA["cash"]
            lines = ["**Current Cash Position**"]
            for acc in pos["accounts"]:
                lines.append(f"- {acc['account_name']}: {inr(acc['balance'])}")
            lines.append(f"**Net cash:** {inr(pos['net_cash'])}")
            return "\n".join(lines)
        if "emi" in text and any(k in text for k in ("summary", "breakdown", "list", "all")):
            emi = DATA["emis"]
            lines = [f"**EMI summary** ({emi['start_date']} to {emi['end_date']})",
                     f"- {emi['emi_count']} payments totalling {inr(emi['total_emi'])}"]
            for lender, amt in emi["emi_breakdown"].items():
                lines.append(f"- {lender}: {inr(amt)}")
            return "\n".join(lines)
        if any(k in text for k in ("spend", "this month", "income", "credit", "debit", "spent")):
            s = DATA["summary"]
            return (f"**{s['start_date']} to {s['end_date']}**\n"
                    f"- Credit: {inr(s['total_credit'])}\n"
                    f"- Debit: {inr(s['total_debit'])}\n"
                    f"- Net change: {inr(s['net_change'])}\n"
                    f"- Transactions: {s['transaction_count']}")
        if any(k in text for k in ("loan", "afford", "borrow")):
            r = le.assess_loan_risk(300000, 12.0, 36, 80000, 22300)
            lines = ["**Loan analysis** — ₹3,00,000 @ 12% / 36 months",
                     f"- EMI: {inr(r['emi'])}",
                     f"- Total interest: {inr(r['total_interest'])}",
                     f"- Total cost: {inr(r['total_cost'])}",
                     f"- EMI / income: {r['emi_income_ratio'] * 100:.1f}%",
                     f"- Risk: **{r['risk_level']}**"]
            for f in r["risk_flags"]:
                lines.append(f"- {f['message']}")
            return "\n".join(lines)
        if any(k in text for k in ("trend", "momentum", "price", "stock", "market",
                                   "infy", "tcs", "reliance", "hdfc", "sbi", "wipro")):
            mapping = {"reliance": "RELIANCE", "infy": "INFY", "tcs": "TCS", "hdfc": "HDFCBANK",
                       "sbi": "SBIN", "sbin": "SBIN", "icici": "ICICIBANK", "axis": "AXISBANK",
                       "kotak": "KOTAKBANK", "wipro": "WIPRO", "itc": "ITC", "bharti": "BHARTIARTL"}
            symbol = "INFY"
            for k, s in mapping.items():
                if k in text:
                    symbol = s
                    break
            price = _market_adapter.get_latest_price(symbol)
            bars = _market_adapter.get_ohlc_history(symbol, 60)
            trend = me.detect_trend_vs_sma(bars, sma_days=20)
            mom = me.compute_momentum(bars, lookback_days=10)
            return (f"**{symbol}** — last {inr(price)}\n"
                    f"- Trend: **{trend['trend']}** ({trend['pct_diff']:+.2f}% vs 20D SMA)\n"
                    f"- 10D momentum: {mom['momentum_pct']:+.2f}%")
    except Exception as e:
        return f"\u26a0 I couldn't process that: {e}"
    return ("I can help with your **cash position**, **loan analysis**, **EMIs**, "
            "**monthly spending**, or **stock trends**. Try:\n"
            "- *What's my cash position?*\n"
            "- *Can I afford a Rs3L loan?*\n"
            "- *How is INFY trending?*")


def _compute_answer(prompt):
    """Return the AI reply for a prompt, falling back to the offline responder."""
    if st.session_state.gemini_chat is None and not st.session_state.gemini_unavailable:
        try:
            st.session_state.gemini_chat = _get_gemini_chat()
        except Exception:
            st.session_state.gemini_chat = None
        if st.session_state.gemini_chat is None:
            st.session_state.gemini_unavailable = True
    if st.session_state.gemini_chat is not None:
        try:
            return st.session_state.gemini_chat.send_message(prompt).text
        except Exception:
            return _local_answer(prompt)
    return _local_answer(prompt)


# ──────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────────────────

def inr(amount: float) -> str:
    """Format an amount with Indian digit grouping + rupee symbol."""
    sign = "-" if amount < 0 else ""
    a = abs(amount)
    s = f"{a:,.2f}"
    int_part, dec = s.split(".")
    digits = int_part.replace(",", "")
    if len(digits) > 3:
        last3 = digits[-3:]
        rest = digits[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        groups.insert(0, rest)
        int_part = ",".join(groups) + "," + last3
    return f"{sign}\u20b9{int_part}.{dec}"


def inr0(amount: float) -> str:
    """Format an integer-style amount with Indian grouping (no decimals)."""
    sign = "-" if amount < 0 else ""
    a = abs(amount)
    digits = str(int(round(a)))
    if len(digits) > 3:
        last3 = digits[-3:]
        rest = digits[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        groups.insert(0, rest)
        digits = ",".join(groups) + "," + last3
    return f"{sign}\u20b9{digits}"


def short(amount: float) -> str:
    """Compact Indian format (Lakhs/Crores)."""
    sign = "-" if amount < 0 else ""
    a = abs(amount)
    if a >= 10000000:
        return f"{sign}\u20b9{a / 10000000:.2f}Cr"
    if a >= 100000:
        return f"{sign}\u20b9{a / 100000:.2f}L"
    if a >= 1000:
        return f"{sign}\u20b9{a / 1000:.1f}K"
    return f"{sign}\u20b9{a:.0f}"


def pct(value: float) -> str:
    return f"{'+' if value >= 0 else ''}{value:.2f}%"


def _spark(values, color, w=132, h=34, fill=True):
    """Return an inline SVG sparkline string for a small series."""
    if not values or len(values) < 2:
        return ""
    mn, mx = min(values), max(values)
    span = (mx - mn) or 1.0
    n = len(values)
    step = w / (n - 1)
    pts = []
    for i, v in enumerate(values):
        x = i * step
        y = h - 3 - ((v - mn) / span) * (h - 6)
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    base = f"0,{h-3} {poly} {w},{h-3}" if fill else poly
    fill_attr = f'<polygon points="{base}" fill="{color}" opacity="0.10"/>' if fill else ""
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
            f'{fill_attr}<polyline points="{poly}" fill="none" stroke="{color}" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def _style_fig(fig, height=280, tick_color="#687282", grid_color="rgba(91,141,239,0.10)"):
    fig.update_layout(
        height=height,
        margin=dict(l=6, r=6, t=10, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=tick_color, size=12),
        xaxis=dict(color=tick_color, gridcolor=grid_color, linecolor="rgba(36,43,53,0.6)"),
        yaxis=dict(color=tick_color, gridcolor=grid_color, linecolor="rgba(36,43,53,0.6)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11, color=tick_color)),
        hoverlabel=dict(bgcolor="#151B23", bordercolor="#242B35", font=dict(color="#F5F7FA")),
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Pre-compute all data
# ──────────────────────────────────────────────────────────────────────────────

TODAY = datetime.now()
CUR_START = TODAY.replace(day=1).strftime("%Y-%m-%d")
CUR_END = TODAY.strftime("%Y-%m-%d")
_PREV_LAST = (TODAY.replace(day=1) - pd.Timedelta(days=1))
PREV_START = _PREV_LAST.replace(day=1).strftime("%Y-%m-%d")
PREV_END = _PREV_LAST.strftime("%Y-%m-%d")

DATA = {
    "cash": fe.compute_cash_position(_mock_data["accounts"], _mock_data["transactions"]),
    "summary": fe.summarize_credit_debit(_mock_data["transactions"], CUR_START, CUR_END),
    "prev_summary": fe.summarize_credit_debit(_mock_data["transactions"], PREV_START, PREV_END),
    "emis": fe.detect_emis(_mock_data["transactions"], CUR_START, CUR_END),
    "categories": fe.get_category_summary(_mock_data["transactions"], CUR_START, CUR_END),
    "loan_offers": _mock_data["loan_offers"],
    "month_start": CUR_START,
    "month_end": CUR_END,
    "accounts": _mock_data["accounts"],
    "transactions": _mock_data["transactions"],
}

# date -> net, credit, debit
daily = {}
daily_credit = {}
daily_debit = {}
for t in _mock_data["transactions"]:
    d = t["date"]
    delta = t["amount"] if t["type"] == "CREDIT" else -t["amount"]
    daily[d] = daily.get(d, 0) + delta
    if t["type"] == "CREDIT":
        daily_credit[d] = daily_credit.get(d, 0) + t["amount"]
    else:
        daily_debit[d] = daily_debit.get(d, 0) + t["amount"]

net_cash = DATA["cash"]["net_cash"]
total_emi = DATA["emis"]["total_emi"]

# Monthly credit / debit / income
month_credit = DATA["summary"]["total_credit"]
month_debit = DATA["summary"]["total_debit"]
month_net = DATA["summary"]["net_change"]

INCOME_CATS = {"SALARY", "FREELANCE", "INTEREST", "DIVIDEND"}
income = sum(
    t["amount"] for t in _mock_data["transactions"]
    if CUR_START <= t["date"] <= CUR_END and t["type"] == "CREDIT"
    and t.get("category") in INCOME_CATS
)


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _health():
    """Transparent financial health model computed from real data."""
    debt_ratio = (total_emi / income) if income else 1.0
    savings_rate = (month_credit - month_debit) / month_credit if month_credit else 0.0
    cash_months = (net_cash / income) if income else 0.0
    debt_score = _clamp(1 - debt_ratio)
    cash_score = _clamp(cash_months / 3.0)
    flow_score = _clamp(0.5 + savings_rate)
    score = int(round(100 * (0.5 * debt_score + 0.3 * cash_score + 0.2 * flow_score)))
    if score >= 75:
        label, color = "Excellent", "#19C37D"
    elif score >= 55:
        label, color = "Good", "#19C37D"
    elif score >= 35:
        label, color = "Balanced", "#F5B942"
    else:
        label, color = "Caution", "#EF5B67"
    return {
        "score": score, "label": label, "color": color,
        "cash_flow": month_net,
        "debt_ratio": debt_ratio,
        "savings_rate": savings_rate,
        "cash_months": cash_months,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Design system CSS
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #0B0F14;
    --bg2: #11161D;
    --card: #151B23;
    --card2: #1A212B;
    --border: #242B35;
    --green: #19C37D;
    --amber: #F5B942;
    --red: #EF5B67;
    --blue: #5B8DEF;
    --text: #F5F7FA;
    --text2: #9AA4B2;
    --muted: #687282;
}

html, body, [class*="css"] { font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif; }
.stApp {
    background:
        radial-gradient(1100px 600px at 10% -10%, rgba(91,141,239,0.08), transparent 60%),
        radial-gradient(900px 600px at 110% 20%, rgba(25,195,125,0.05), transparent 55%),
        var(--bg);
    color: var(--text);
    animation: appFade .8s ease both;
}
@keyframes appFade { from { opacity: 0 } to { opacity: 1 } }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--bg2), var(--bg));
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .stMarkdown p { color: var(--text2); }
section[data-testid="stSidebar"] hr { border-color: var(--border); }

/* General text colors for streamlit elements */
.stMarkdown, .stMarkdown p, p, li, span, label, h1,h2,h3,h4,h5,h6 { color: var(--text); }
label, .stRadio p { color: var(--text2) !important; }
.block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1240px; }

/* Brand */
.fp-logo { font-size: 19px; font-weight: 800; letter-spacing: .3px; color: var(--text); }
.fp-logo b { color: var(--green); }

/* Top bar */
.fp-top { display:flex; align-items:flex-end; justify-content:space-between; gap:16px; padding: 4px 0 20px 0; }
.fp-title { font-size: 30px; font-weight: 700; color: var(--text); line-height:1.1; }
.fp-desc { font-size: 14px; color: var(--text2); margin-top:6px; }
.fp-date { font-size: 13px; color: var(--muted); }
.fp-right { display:flex; align-items:center; gap:16px; }
.fp-bell { color: var(--text2); font-size:18px; position:relative; }
.fp-bell::after { content:''; position:absolute; top:1px; right:2px; width:7px; height:7px; border-radius:50%; background: var(--red); box-shadow:0 0 6px var(--red); }
.fp-status { display:flex; align-items:center; gap:8px; font-size:12px; color: var(--green); }
.fp-avatar { width:38px; height:38px; border-radius:50%; background:linear-gradient(135deg,var(--green),var(--blue)); display:flex; align-items:center; justify-content:center; font-size:17px; color:#0B0F14; font-weight:800; }

/* Cards */
.fp-card {
    background: linear-gradient(160deg, var(--card), var(--card2));
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 22px;
    animation: fadeUp .55s cubic-bezier(.22,.61,.36,1) both;
    transition: transform .25s, border-color .25s, box-shadow .25s;
    backdrop-filter: blur(8px);
}
.fp-card:hover { transform: translateY(-2px); border-color: #2e3846; box-shadow: 0 14px 40px rgba(0,0,0,.4); }
@keyframes fadeUp { from { opacity:0; transform: translateY(14px);} to { opacity:1; transform:none; } }

/* Section header */
.fp-section { font-size: 20px; font-weight: 600; color: var(--text); margin: 26px 0 4px 0; }
.fp-section-sub { font-size: 13px; color: var(--muted); margin: 0 0 16px 0; }

/* Metric card */
.fp-metric { }
.fp-metric-label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 1.2px; font-weight:600; }
.fp-metric-value { font-size: 28px; font-weight: 700; color: var(--text); margin-top: 6px; line-height:1.1; }
.fp-metric-delta { font-size: 13px; color: var(--text2); margin-top: 8px; }
.fp-delta-up { color: var(--green); font-weight:600; }
.fp-delta-down { color: var(--red); font-weight:600; }
.fp-metric-spark { margin-top: 12px; }

/* Health */
.fp-health-num { font-size: 40px; font-weight: 800; line-height:1; }
.fp-health-track { height: 9px; border-radius: 999px; background: #232b37; overflow: hidden; margin: 14px 0 6px 0; }
.fp-health-fill { height:100%; border-radius:999px; transition: width 1.2s cubic-bezier(.22,.61,.36,1); }
.fp-detail-row { display:flex; justify-content:space-between; padding:9px 0; border-bottom:1px solid var(--border); font-size:13px; }
.fp-detail-row:last-child { border-bottom:none; }
.fp-detail-lab { color: var(--text2); }
.fp-detail-val { font-weight:700; color: var(--text); }

/* Insight */
.fp-insight {
    border: 1px solid rgba(25,195,125,.28);
    background: linear-gradient(160deg, rgba(25,195,125,.10), var(--card));
    box-shadow: 0 0 30px rgba(25,195,125,.10);
    border-radius: 16px; padding: 22px;
}
.fp-insight-lab { font-size: 12px; font-weight:700; letter-spacing:1.4px; color: var(--green); text-transform:uppercase; }
.fp-insight-text { font-size: 14px; color: var(--text2); line-height:1.6; margin-top:12px; }
.fp-insight-text b { color: var(--text); }

/* Badge/status */
.fp-badge { display:inline-flex; align-items:center; gap:6px; font-size:11px; font-weight:700; letter-spacing:.6px; text-transform:uppercase; padding:4px 11px; border-radius:999px; }
.fp-badge.green { background: rgba(25,195,125,.14); color: var(--green); }
.fp-badge.red { background: rgba(239,91,103,.14); color: var(--red); }
.fp-badge.amber { background: rgba(245,185,66,.14); color: var(--amber); }
.fp-badge.blue { background: rgba(91,141,239,.14); color: var(--blue); }
.fp-badge .dot { width:6px; height:6px; border-radius:50%; background: currentColor; }

/* Activity list */
.fp-act { display:flex; align-items:center; gap:14px; padding:12px 0; border-bottom:1px solid var(--border); animation: fadeUp .4s ease both; }
.fp-act:last-child { border-bottom:none; }
.fp-act-icon { width:40px; height:40px; border-radius:11px; display:flex; align-items:center; justify-content:center; font-size:15px; }
.fp-act-icon.credit { background: rgba(25,195,125,.16); color: var(--green); }
.fp-act-icon.debit { background: rgba(239,91,103,.16); color: var(--red); }
.fp-act-name { font-size:13px; font-weight:600; color: var(--text); }
.fp-act-date { font-size:11px; color: var(--muted); }
.fp-act-right { margin-left:auto; text-align:right; }
.fp-act-amt { font-size:14px; font-weight:700; }
.fp-act-amt.credit { color: var(--green); }
.fp-act-amt.debit { color: var(--red); }

/* Buttons */
.stButton > button {
    background: var(--green); color: #0B0F14; font-weight:700; border:none; border-radius: 10px;
    padding: 0.6rem 1rem; transition: all .2s; box-shadow: 0 8px 20px rgba(25,195,125,.22);
}
.stButton > button:hover { transform: translateY(-2px); filter: brightness(1.06); box-shadow: 0 10px 26px rgba(25,195,125,.34); }
.stButton > button:active { transform: translateY(0); }
.stButton > button[kind="secondary"] { background: var(--card2); color: var(--text); border:1px solid var(--border); box-shadow:none; }
.stButton > button[kind="secondary"]:hover { border-color:#2e3846; }
.stButton > button[kind="secondary"]:focus:not(:active) { border-color:#2e3846; }

/* Inputs */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] > div > div, [data-testid="stTextArea"] textarea {
    background: var(--card) !important; color: var(--text) !important;
    border: 1px solid var(--border) !important; border-radius: 10px !important;
}
[data-testid="stSlider"] label { color: var(--text2) !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: var(--card); border-radius: 12px; padding: 4px; gap:4px; border:1px solid var(--border); }
.stTabs [data-baseweb="tab"] { background:transparent; border-radius:9px; color:var(--text2); font-weight:600; font-size:13px; padding:8px 16px; }
.stTabs [aria-selected="true"] { background: rgba(25,195,125,.12) !important; color: var(--green) !important; }

/* Chat */
[data-testid="stChatMessage"] { background: var(--card); border:1px solid var(--border); border-radius:14px; padding:12px 14px; }
[data-testid="stChatMessage"] .stMarkdown p { color: var(--text2); }
[data-testid="stChatMessageAssistant"] [data-testid="stChatMessageAvatar"] { background: linear-gradient(135deg,var(--green),var(--blue)); color:#0B0F14; font-weight:800; }
[data-testid="stChatMessageUser"] [data-testid="stChatMessageAvatar"] { background: var(--card2); color: var(--text); }
[data-testid="stChatInput"] textarea { background: var(--card) !important; color: var(--text) !important; border-color: var(--border) !important; border-radius: 12px !important; }
.fp-context { border:1px solid var(--border); border-radius:14px; padding:16px; background: var(--card); }
.fp-context-row { display:flex; justify-content:space-between; padding:9px 0; border-bottom:1px solid var(--border); font-size:13px; }
.fp-context-row:last-child { border-bottom:none; }
.fp-thinking { color: var(--green); font-size:13px; font-weight:600; display:flex; align-items:center; gap:8px; }
.fp-dots span { display:inline-block; width:5px; height:5px; margin:0 2px; border-radius:50%; background: var(--green); animation: blink 1.2s infinite; }
.fp-dots span:nth-child(2) { animation-delay:.2s; } .fp-dots span:nth-child(3) { animation-delay:.4s; }
@keyframes blink { 0%,80%,100% { opacity:.25; transform:scale(.8); } 40% { opacity:1; transform:scale(1); } }

/* Empty chat state */
.fp-empty { text-align:center; padding: 24px 6px; }
.fp-empty-icon { font-size: 30px; color: var(--blue); }
.fp-empty-title { font-size: 18px; font-weight:700; color: var(--text); margin-top:10px; }
.fp-empty-sub { font-size:13px; color: var(--text2); margin-top:6px; }

/* Notification */
.fp-notif { display:flex; gap:14px; padding:14px; border:1px solid var(--border); border-radius:14px; margin-bottom:10px; background: var(--card); transition: transform .2s; }
.fp-notif:hover { transform: translateX(4px); }
.fp-notif-icon { width:40px; height:40px; border-radius:11px; display:flex; align-items:center; justify-content:center; font-size:16px; }
.fp-notif-title { font-size:13px; font-weight:600; color: var(--text); }
.fp-notif-msg { font-size:12px; color: var(--text2); margin-top:3px; }
.fp-notif-time { font-size:11px; color: var(--muted); margin-top:5px; }

/* Table */
.fp-table { width:100%; border-collapse:collapse; font-size:13px; }
.fp-table th { text-align:left; color: var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:1px; padding:10px 12px; border-bottom:1px solid var(--border); }
.fp-table td { padding:12px; border-bottom:1px solid var(--border); color: var(--text); }
.fp-table tr:last-child td { border-bottom:none; }
.fp-table tr:hover td { background: rgba(91,141,239,.04); }

/* Scrollbar */
::-webkit-scrollbar { width:8px; height:8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #242B35; border-radius:8px; }
::-webkit-scrollbar-thumb:hover { background:#2e3846; }

/* Footer */
.fp-footer { text-align:center; font-size:11px; color: var(--muted); padding: 34px 0 6px 0; }

#MainMenu { visibility:hidden; } footer { visibility:hidden; } header { visibility:hidden; }
.stDeployButton { display:none; }

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation:none !important; transition:none !important; }
}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Navigation
# ──────────────────────────────────────────────────────────────────────────────

PAGES = ["🏠 Overview", "💼 Finance", "💰 Loans", "📈 Markets", "🤖 AI Copilot", "🔔 Notifications", "👤 Profile"]
if "nav" not in st.session_state:
    st.session_state["nav"] = "🏠 Overview"


def _nav_to(page):
    st.session_state["nav"] = page


SIDE_ICONS = {
    "🏠 Overview": "Home",
    "💼 Finance": "Finance",
    "💰 Loans": "Loans",
    "📈 Markets": "Markets",
    "🤖 AI Copilot": "Copilot",
}

with st.sidebar:
    st.markdown('<div style="padding:10px 4px 18px 4px;"><div style="display:flex;align-items:center;gap:10px;">'
                '<div style="width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,var(--green),var(--blue));'
                'display:flex;align-items:center;justify-content:center;font-size:16px;color:#0B0F14;font-weight:800;">F</div>'
                '<div class="fp-logo">FinPilot <b>AI</b></div></div>'
                '<div style="font-size:10px;color:var(--muted);letter-spacing:1.4px;margin-top:6px;">FINANCE CONTROLLER</div>'
                '</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    page = st.radio("Navigation", PAGES, key="nav", label_visibility="collapsed")

    st.markdown("<hr>", unsafe_allow_html=True)

    net_cash = DATA["cash"]["net_cash"]
    total_emi = DATA["emis"]["total_emi"]
    st.markdown(
        f'<div style="padding:2px 4px;">'
        f'<div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1.2px;margin-bottom:10px;">System</div>'
        f'<div style="display:flex;align-items:center;gap:8px;color:var(--green);font-size:12px;font-weight:600;">'
        f'<span style="width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);"></span>Connected</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text2);margin-top:12px;">'
        f'<span>Available</span><b style="color:var(--text);">{short(net_cash)}</b></div>'
        f'<div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text2);margin-top:6px;">'
        f'<span>EMI</span><b style="color:var(--amber);">{short(total_emi)}</b></div>'
        f'</div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;padding:2px 4px;">'
        '<div style="width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,var(--green),var(--blue));'
        'display:flex;align-items:center;justify-content:center;font-size:15px;color:#0B0F14;font-weight:800;">P</div>'
        '<div><div style="font-size:13px;font-weight:600;color:var(--text);">Prakash</div>'
        '<div style="font-size:11px;color:var(--muted);">FinPilot Member</div></div></div>',
        unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Shared components
# ──────────────────────────────────────────────────────────────────────────────

def topbar(title, desc="", emoji=""):
    emoji_tag = f"</div>"  # reserved (no emoji needed in title)
    date_str = TODAY.strftime("%A, %B %d, %Y")
    st.markdown(
        f'<div class="fp-top">'
        f'<div><div class="fp-title">{title}</div>'
        f'<div class="fp-desc">{desc}</div></div>'
        f'<div class="fp-right">'
        f'<div class="fp-date">{date_str}</div>'
        f'<div class="fp-bell">&#128276;</div>'
        f'<div class="fp-status"><span style="width:7px;height:7px;border-radius:50%;background:var(--green);'
        f'box-shadow:0 0 8px var(--green);"></span>AI Connected</div>'
        f'<div class="fp-avatar">P</div>'
        f'</div></div>', unsafe_allow_html=True)


def section(title, sub=""):
    st.markdown(f'<div class="fp-section">{title}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="fp-section-sub">{sub}</div>', unsafe_allow_html=True)


def footer():
    st.markdown(
        '<div class="fp-footer">FinPilot provides analytical insights, not guaranteed financial advice. '
        'For demo & educational purposes only.</div>', unsafe_allow_html=True)


def metric_card(label, value, delta="", delta_up=None, sparkline=""):
    cls = "fp-delta-up" if delta_up is None else ("fp-delta-up" if delta_up else "fp-delta-down")
    return (f'<div class="fp-card fp-metric">'
            f'<div class="fp-metric-label">{label}</div>'
            f'<div class="fp-metric-value">{value}</div>'
            f'{f"<div class=\"fp-metric-delta\"><span class=\"{cls}\">{delta}</span></div>" if delta else ""}'
            f'{f"<div class=\"fp-metric-spark\">{sparkline}</div>" if sparkline else ""}'
            f'</div>')


def _recent_labels(values, dates):
    return [_nice_date(d) for d in dates]


def _nice_date(d):
    try:
        dt = datetime.strptime(d, "%Y-%m-%d")
        return dt.strftime("%b %d")
    except Exception:
        return d


def _icon_for(category, credit):
    if credit:
        return ("+" if False else "↑"), "credit"
    mapping = {"LOAN_EMI": "L", "SALARY": "S", "SHOPPING": "‡", "FOOD": "F", "FUEL": "G",
               "RENT": "⌂", "UTILITY": "◇", "SUBSCRIPTION": "◎", "TRANSFER": "T",
               "INTEREST": "I", "DIVIDEND": "D", "FREELANCE": "F", "BANK_CHARGES": "B",
               "GROCERY": "G", "TRANSPORT": "T"}
    return mapping.get(category, "•"), "debit"


# ──────────────────────────────────────────────────────────────────────────────
# PAGE: OVERVIEW
# ──────────────────────────────────────────────────────────────────────────────

if page == "🏠 Overview":
    topbar("Your Financial Command Center",
           "FinPilot monitors your cash flow, loans and markets to help you make smarter decisions.",
           emoji="")

    health = _health()

    # Hero
    st.markdown("""
    <div class="fp-card" style="background:linear-gradient(160deg,rgba(25,195,125,.14),var(--card) 45%);">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;">
        <div style="max-width:620px;">
          <div style="font-size:24px;font-weight:700;color:var(--text);">Your Financial Command Center</div>
          <div style="font-size:14px;color:var(--text2);margin-top:8px;">FinPilot monitors your cash flow, loans and
          markets and helps you make smarter financial decisions.</div>
        </div>
        <span style="font-size:26px;">✦</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # Financial health + KPIs
    col_health, col_kpis = st.columns([1.05, 1.6], gap="medium")

    with col_health:
        st.markdown(f"""
        <div class="fp-card">
          <div style="font-size:12px;font-weight:700;letter-spacing:1.4px;color:var(--muted);text-transform:uppercase;">Financial Health</div>
          <div style="font-size:22px;font-weight:700;color:{health['color']};margin-top:8px;">{health['label']}</div>
          <div style="display:flex;align-items:baseline;gap:12px;margin-top:10px;">
            <div class="fp-health-num" style="color:var(--text);">{health['score']}</div>
            <div style="font-size:14px;color:var(--muted);">/ 100</div>
          </div>
          <div class="fp-health-track"><div class="fp-health-fill" style="width:{health['score']}%;background:linear-gradient(90deg,var(--green),var(--blue));"></div></div>
          <div style="font-size:12px;color:var(--text2);margin-top:4px;">Your cash position is {health['label'].lower()}. Debt obligations are { 'manageable' if health['debt_ratio']<0.5 else 'elevated' }.</div>
          <div class="fp-detail-row"><span class="fp-detail-lab">Cash Flow</span><span class="fp-detail-val" style="color:{'var(--green)' if health['cash_flow']>=0 else 'var(--red)'};">{inr0(health['cash_flow'])}</span></div>
          <div class="fp-detail-row"><span class="fp-detail-lab">Debt Load</span><span class="fp-detail-val">{health['debt_ratio']*100:.1f}%</span></div>
          <div class="fp-detail-row"><span class="fp-detail-lab">Savings Rate</span><span class="fp-detail-val">{health['savings_rate']*100:.1f}%</span></div>
        </div>""", unsafe_allow_html=True)

    with col_kpis:
        cur_sum = DATA["summary"]
        prev_sum = DATA["prev_summary"]
        credit_chg = ((cur_sum["total_credit"] - prev_sum["total_credit"]) / prev_sum["total_credit"] * 100) if prev_sum["total_credit"] else 0
        debit_chg = ((cur_sum["total_debit"] - prev_sum["total_debit"]) / prev_sum["total_debit"] * 100) if prev_sum["total_debit"] else 0
        debit_delta_up = debit_chg < 0

        _dates = sorted(daily_credit.keys())[-14:]
        c_spark = [daily_credit.get(d, 0) for d in _dates]
        d_spark = [daily_debit.get(d, 0) for d in _dates]
        n_spark = [daily.get(d, 0) for d in _dates]
        c_vals = []
        run = net_cash - sum(daily[d] for d in _dates)
        for d in _dates:
            run += daily[d]
            c_vals.append(run)

        kcols = st.columns(2, gap="medium")
        with kcols[0]:
            st.markdown(metric_card("Net Cash", inr0(net_cash), f"{pct(8.4)} vs last month", True, _spark(c_vals, "#19C37D")), unsafe_allow_html=True)
        with kcols[1]:
            st.markdown(metric_card("Monthly Credit", inr0(cur_sum["total_credit"]), f"{pct(credit_chg)} income received", credit_chg >= 0, _spark(c_spark, "#5B8DEF")), unsafe_allow_html=True)
        kcols = st.columns(2, gap="medium")
        with kcols[0]:
            st.markdown(metric_card("Monthly Debit", inr0(cur_sum["total_debit"]), f"{pct(debit_chg)} spending reduced", debit_delta_up, _spark(d_spark, "#EF5B67")), unsafe_allow_html=True)
        with kcols[1]:
            st.markdown(metric_card("Total EMI", inr0(total_emi), f"{total_emi/income*100:.1f}% of income", None, _spark(n_spark, "#F5B942")), unsafe_allow_html=True)

    # Cash flow analytics
    section("Cash Flow", f"{TODAY.strftime('%B %Y')} — income vs spending")
    range_pick = st.radio("Range", ["7D", "30D", "90D"], index=1, horizontal=True, key="cf_range", label_visibility="collapsed")
    n = {"7D": 7, "30D": 30, "90D": 90}[range_pick]
    all_dates = sorted(daily.keys())
    show_dates = all_dates[-n:]
    dates = show_dates
    incomes = [daily_credit.get(d, 0) for d in dates]
    spends = [daily_debit.get(d, 0) for d in dates]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=incomes, mode="lines", name="Income",
                             line=dict(color="#19C37D", width=2, shape="spline"),
                             fill="tozeroy", fillcolor="rgba(25,195,125,0.06)"))
    fig.add_trace(go.Scatter(x=dates, y=spends, mode="lines", name="Spending",
                             line=dict(color="#EF5B67", width=2, shape="spline"),
                             fill="tozeroy", fillcolor="rgba(239,91,103,0.05)"))
    _style_fig(fig, height=260)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # AI insight + recent activity
    c_ins, c_act = st.columns([1.1, 1.0], gap="medium")

    with c_ins:
        st.markdown(f"""
        <div class="fp-insight">
          <div class="fp-insight-lab">✦ FinPilot Insight</div>
          <div class="fp-insight-text">Your spending this month is <b>{'de&nbsp;' if month_debit<=prev_sum['total_debit'] else ''}{abs((month_debit-prev_sum['total_debit'])/prev_sum['total_debit']*100) if prev_sum['total_debit'] else 0:.0f}%</b> vs last month. You have <b>{short(net_cash)}</b> available cash and <b>{short(total_emi)}</b> in recurring EMI obligations.</div>
          <div class="fp-insight-text">Recommended: build an emergency reserve of approximately <b>{inr0((income - total_emi)*3 if income>total_emi else net_cash*0.5)}</b> before taking another large loan.</div>
        </div>""", unsafe_allow_html=True)
        st.write("")
        if st.button("Ask FinPilot for recommendations →", use_container_width=True, type="primary"):
            _nav_to("🤖 AI Copilot")

    with c_act:
        section("Recent Activity", "")
        icons = {"LOAN_EMI": "L", "SALARY": "S", "SHOPPING": "‡", "FOOD": "F", "FUEL": "G",
                 "RENT": "⌂", "UTILITY": "◇", "SUBSCRIPTION": "◎", "TRANSFER": "T",
                 "INTEREST": "I", "DIVIDEND": "D", "FREELANCE": "F", "BANK_CHARGES": "B",
                 "GROCERY": "G", "TRANSPORT": "T"}
        recent = sorted(DATA["transactions"], key=lambda t: t["date"], reverse=True)[:6]
        for txn in recent:
            is_c = txn["type"] == "CREDIT"
            ic = icons.get(txn.get("category", ""), "•")
            cls = "credit" if is_c else "debit"
            sign = "+" if is_c else "-"
            st.markdown(
                f'<div class="fp-act"><div class="fp-act-icon {cls}">{ic}</div>'
                f'<div><div class="fp-act-name">{txn["description"].split(" - ")[-1][:30]}</div>'
                f'<div class="fp-act-date">{_nice_date(txn["date"])} · {_acct_name(txn)}</div></div>'
                f'<div class="fp-act-right"><div class="fp-act-amt {cls}">{sign}{inr0(txn["amount"])}</div></div></div>',
                unsafe_allow_html=True)

    footer()


# ──────────────────────────────────────────────────────────────────────────────
# PAGE: FINANCE
# ──────────────────────────────────────────────────────────────────────────────

elif page == "💼 Finance":
    topbar("Finance Controller", "Monitor cash flow, recurring payments and financial obligations.")

    c_sync, c_util = st.columns([4, 1])
    with c_sync:
        pass
    with c_util:
        if st.button("Sync Bank Data", use_container_width=True):
            st.toast("✓ Bank data synchronized · Just now")

    section("", "")
    # Top metrics
    cur_sum = DATA["summary"]
    prev_sum = DATA["prev_summary"]
    mcols = st.columns(4, gap="medium")
    mvals = [
        ("Available Cash", inr0(net_cash), True, ""),
        ("Monthly Income", inr0(income), True, ""),
        ("Monthly Expenses", inr0(month_debit), False, ""),
        ("Net Cash Flow", inr0(month_net), month_net >= 0, ""),
    ]
    for col, (lab, val, upd, delta) in zip(mcols, mvals):
        with col:
            st.markdown(metric_card(lab, val, delta or "", upd), unsafe_allow_html=True)

    # Cash position visualization
    st.write("")
    section("Cash Position", f"Available balance · {TODAY.strftime('%B %d, %Y')}")
    fig2 = go.Figure()
    c_vals = []
    all_dates = sorted(daily.keys())
    run = net_cash - sum(daily.values())
    for d in all_dates[-40:]:
        run += daily[d]
        c_vals.append(run)
    fig2.add_trace(go.Scatter(x=all_dates[-40:], y=c_vals, mode="lines", name="Balance",
                              line=dict(color="#19C37D", width=2.2, shape="spline"),
                              fill="tozeroy", fillcolor="rgba(25,195,125,0.07)"))
    _style_fig(fig2, height=230)
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # Spending by category
    section("Spending by Category", "")
    cats = DATA["categories"]["categories"]
    if cats:
        sorted_cats = sorted(cats.items(), key=lambda x: x[1]["total"], reverse=True)[:6]
        fig3 = go.Figure(go.Bar(x=[c[1]["total"] for c in sorted_cats], y=[c[0] for c in sorted_cats],
                                orientation="h", marker_color="#5B8DEF", opacity=0.85,
                                text=[f"{inr0(c[1]['total'])} ({c[1]['count']})" for c in sorted_cats], textposition="auto"))
        fig3.update_layout(height=max(210, len(sorted_cats) * 30))
        _style_fig(fig3, height=max(210, len(sorted_cats) * 30))
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    # EMI monitor
    st.write("")
    section("Recurring EMIs", f"{DATA['emis']['emi_count']} obligations detected")
    emis = DATA["emis"]
    emi_rows = sorted(emis["emi_breakdown"].items(), key=lambda x: -x[1])
    rows = "".join(
        f'<tr><td>{lender}</td><td>Personal / Housing Loan</td><td>{_nice_date(DATA["month_end"])}</td>'
        f'<td><b>{inr0(amt)}</b></td><td><span class="fp-badge blue"><span class="dot"></span>Upcoming</span></td></tr>'
        for lender, amt in emi_rows)
    st.markdown(f'<table class="fp-table"><thead><tr><th>Lender</th><th>Description</th><th>Due Date</th>'
                f'<th>Amount</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>', unsafe_allow_html=True)

    footer()


# ──────────────────────────────────────────────────────────────────────────────
# PAGE: LOANS
# ──────────────────────────────────────────────────────────────────────────────

elif page == "💰 Loans":
    topbar("Loan Advisor", "Understand the true cost of borrowing before you commit.")

    tab_single, tab_compare = st.tabs(["Single Loan", "Compare Offers"])

    with tab_single:
        col_a, col_b = st.columns(2, gap="large")
        with col_a:
            section("Loan Parameters", "Amount · rate · tenure")
            loan_amount = st.number_input("Loan Amount", value=300000, step=10000, min_value=10000)
            loan_rate = st.number_input("Interest Rate (%)", value=12.0, step=0.5, min_value=1.0, max_value=30.0)
            loan_tenure = st.number_input("Tenure (months)", value=36, step=1, min_value=1, max_value=360)
        with col_b:
            section("Your Profile", "Income · existing obligations")
            loan_income = st.number_input("Monthly Income", value=80000, step=5000, min_value=10000)
            loan_existing_emi = st.number_input("Existing Monthly EMI", value=22300, step=1000, min_value=0)

        st.write("")
        if st.button("Analyze Loan →", type="primary", use_container_width=True):
            with st.spinner("Computing loan scenario..."):
                result = le.assess_loan_risk(loan_amount, loan_rate, loan_tenure, loan_income, loan_existing_emi)

            # Results KPIs
            k1, k2, k3, k4 = st.columns(4, gap="medium")
            kdata = [
                ("Monthly EMI", inr0(result["emi"]), False),
                ("Total Interest", inr0(result["total_interest"]), True),
                ("Total Cost", inr0(result["total_cost"]), False),
                ("EMI / Income", f"{result['emi_income_ratio']*100:.1f}%", result["emi_income_ratio"] < 0.4),
            ]
            for col, (lab, val, upd) in zip((k1, k2, k3, k4), kdata):
                with col:
                    st.markdown(metric_card(lab, val, "", upd), unsafe_allow_html=True)

            st.write("")
            section("Risk Assessment", "")
            risk_cls = result["risk_level"].lower()
            risk_color = {"low": "#19C37D", "medium": "#F5B942", "high": "#EF5B67"}[risk_cls]
            score = {"LOW": 88, "MEDIUM": 55, "HIGH": 22}.get(result["risk_level"], 50)
            flags_html = "".join(
                f'<div style="font-size:13px;color:var(--text2);margin-top:6px;">'
                f'{"⚠" if fl["severity"] in ("MEDIUM","HIGH") else "✓"} {fl["message"]}</div>'
                for fl in result["risk_flags"])
            st.markdown(f"""
            <div class="fp-card" style="border-color:{risk_color};">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="font-size:16px;font-weight:700;color:var(--text);">Risk Assessment</div>
                <span class="fp-badge {'amber' if risk_cls=='medium' else 'red' if risk_cls=='high' else 'green'}"><span class="dot"></span>{result['risk_level']} Risk</span>
              </div>
              <div style="font-size:13px;color:var(--text2);margin-top:10px;">Debt burden is { 'elevated' if result['emi_income_ratio']>0.5 else 'manageable' } but leaves limited monthly flexibility.</div>
              <div style="margin-top:10px;">{flags_html}</div>
              <div class="fp-detail-row" style="margin-top:14px;"><span class="fp-detail-lab">EMI / income</span><span class="fp-detail-val">{result['emi_income_ratio']*100:.1f}%</span></div>
            </div>""", unsafe_allow_html=True)

            # What-if analyzer
            st.write("")
            section("What-If Analyzer", "See how changing rate or tenure affects your EMI")
            wi_rate = st.slider("Interest Rate (%)", 1.0, 30.0, loan_rate, step=0.5)
            wi_tenure = st.slider("Tenure (months)", 1, 360, loan_tenure, step=1)
            base = le.calculate_emi(loan_amount, loan_rate, loan_tenure)
            new = le.calculate_emi(loan_amount, wi_rate, wi_tenure)
            saving = base - new
            dash = "green" if saving >= 0 else "red"
            st.markdown(f"""
            <div class="fp-card">
              <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;">
                <div><div class="fp-metric-label">Current EMI</div><div class="fp-metric-value" style="font-size:22px;">{inr0(base)}</div></div>
                <div><div class="fp-metric-label">New EMI</div><div class="fp-metric-value" style="font-size:22px;">{inr0(new)}</div></div>
                <div><div class="fp-metric-label">Monthly</div><div class="fp-metric-value" style="font-size:22px;color:var(--{dash});">{'+' if saving>=0 else '-'}{inr0(abs(saving))}</div></div>
              </div>
            </div>""", unsafe_allow_html=True)

    with tab_compare:
        section("Compare Loan Offers", "Ranked by total cost")
        comp_amount = st.number_input("Loan Amount", value=200000, step=10000, min_value=10000, key="comp_amt")
        comp_income = st.number_input("Monthly Income", value=80000, step=5000, min_value=10000, key="comp_inc")
        comp_emi = st.number_input("Existing EMI", value=22300, step=1000, min_value=0, key="comp_emi")
        if st.button("Compare Offers", type="primary", use_container_width=True):
            results = le.compare_loan_offers(comp_amount, DATA["loan_offers"], comp_income, comp_emi)
            best = results[0]["offer_id"] if results else None
            risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
            lowest_risk = min(results, key=lambda x: risk_order[x["risk_level"]])["offer_id"] if results else None
            rows = ""
            for r in results:
                badges = ""
                if r["offer_id"] == best:
                    badges += '<span class="fp-badge green" style="margin-left:6px;"><span class="dot"></span>Best</span>'
                if r["offer_id"] == lowest_risk:
                    badges += '<span class="fp-badge blue" style="margin-left:6px;"><span class="dot"></span>Low Risk</span>'
                risk_badge = {"LOW": "green", "MEDIUM": "amber", "HIGH": "red"}[r["risk_level"]]
                rows += (f'<tr><td><b>{r["bank"]}</b>{badges}</td><td>{r["interest_rate"]:.1f}%</td>'
                         f'<td>{r["tenure_months"]}M</td><td><b>{inr0(r["emi"])}</b></td>'
                         f'<td>{inr0(r["total_cost"])}</td>'
                         f'<td><span class="fp-badge {risk_badge}"><span class="dot"></span>{r["risk_level"]}</span></td></tr>')
            st.markdown(f'<table class="fp-table"><thead><tr><th>Bank</th><th>Rate</th><th>Tenure</th>'
                        f'<th>EMI</th><th>Total Cost</th><th>Risk</th></tr></thead><tbody>{rows}</tbody></table>',
                        unsafe_allow_html=True)

    footer()


# ──────────────────────────────────────────────────────────────────────────────
# PAGE: MARKETS
# ──────────────────────────────────────────────────────────────────────────────

elif page == "📈 Markets":
    topbar("Market Intelligence", "Track prices, momentum and market trends.")

    def _pick_symbol(sym):
        st.session_state["stock_symbol"] = sym

    symbol_input = st.text_input("", value="INFY", key="stock_symbol", label_visibility="collapsed",
                                 placeholder="Search symbol... (INFY, RELIANCE, TCS)")
    chip_cols = st.columns(5)
    for i, sym in enumerate(["INFY", "RELIANCE", "TCS", "HDFCBANK", "SBIN"]):
        with chip_cols[i]:
            st.button(sym, key=f"chip_{sym}", use_container_width=True, on_click=_pick_symbol, args=(sym,))

    symbol = symbol_input.upper().strip()
    if symbol:
        price_data = _market_adapter.get_latest_price(symbol)
        ohlc = _market_adapter.get_ohlc_history(symbol, 120)
        trend = me.detect_trend_vs_sma(ohlc, sma_days=20)
        momentum = me.compute_momentum(ohlc, lookback_days=10)
        hl = me.compute_high_low_range(ohlc, days=20)
        trend_cls = trend["trend"].lower()

        st.write("")
        st.markdown(f"""
        <div class="fp-card" style="background:linear-gradient(160deg,rgba(91,141,239,.12),var(--card) 55%);">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
            <div>
              <div style="font-size:28px;font-weight:800;color:var(--text);">{symbol}</div>
              <div style="font-size:20px;font-weight:700;color:var(--text);margin-top:2px;">{inr(price_data)}</div>
              <div style="font-size:14px;font-weight:600;color:{'var(--green)' if trend['pct_diff']>=0 else 'var(--red)'};">{pct(trend['pct_diff'])} today</div>
            </div>
            <span class="fp-badge green"><span class="dot"></span>Market Open</span>
          </div>
        </div>""", unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4, gap="medium")
        with m1:
            st.markdown(metric_card("Latest Price", inr(price_data), "", True), unsafe_allow_html=True)
        with m2:
            st.markdown(metric_card("Day Change", pct(trend["pct_diff"]), "", trend["pct_diff"] >= 0), unsafe_allow_html=True)
        with m3:
            st.markdown(metric_card("10D Momentum", f"{momentum['momentum_pct']:+.1f}%", "", momentum["momentum_pct"] >= 0), unsafe_allow_html=True)
        with m4:
            st.markdown(metric_card("20D SMA", inr0(trend["sma"]) if trend["sma"] else "N/A", "", True), unsafe_allow_html=True)

        st.write("")
        section("Price & Trend", f"{symbol} — price vs 20-day moving average")
        bars = ohlc[-60:] if len(ohlc) > 60 else ohlc
        dates = [b["date"] for b in bars]
        closes = [b["close"] for b in bars]
        sma_vals = me.compute_sma(closes, 20)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=closes, mode="lines", name="Price", line=dict(color="#5B8DEF", width=2)))
        sma_plot = [v for v in sma_vals if v is not None]
        sma_dates = [d for d, v in zip(dates, sma_vals) if v is not None]
        if sma_plot:
            fig.add_trace(go.Scatter(x=sma_dates, y=sma_plot, mode="lines", name="20D SMA",
                                     line=dict(color="#19C37D", width=1.6, dash="dot")))
        _style_fig(fig, height=300)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": True})

        # Trend analysis + AI insight
        c_trend, c_ins = st.columns([1.05, 1.0], gap="medium")
        with c_trend:
            section("Trend Analysis", "")
            conf = 82 if trend["trend"] == "UPTREND" else (60 if trend["trend"] == "DOWNTREND" else 45)
            tb_cls = "green" if conf >= 70 else "amber"
            dist = f"+{trend['pct_diff']:.1f}%" if trend["pct_diff"] >= 0 else f"{trend['pct_diff']:.1f}%"
            st.markdown(f"""
            <div class="fp-card">
              <div style="display:flex;align-items:center;gap:10px;">
                <span class="fp-badge {tb_cls}"><span class="dot"></span>{trend['trend']}</span>
              </div>
              <div style="font-size:13px;color:var(--text2);margin-top:12px;">Price is currently <b style="color:var(--text);">{pct(trend['pct_diff'])}</b> {'above' if trend['pct_diff']>=0 else 'below'} the 20-day moving average.</div>
              <div class="fp-detail-row" style="margin-top:8px;"><span class="fp-detail-lab">20D SMA</span><span class="fp-detail-val">{inr0(trend['sma']) if trend['sma'] else 'N/A'}</span></div>
              <div class="fp-detail-row"><span class="fp-detail-lab">Current Price</span><span class="fp-detail-val">{inr(price_data)}</span></div>
              <div class="fp-detail-row"><span class="fp-detail-lab">Distance</span><span class="fp-detail-val">{dist}</span></div>
              <div class="fp-detail-row"><span class="fp-detail-lab">Momentum</span><span class="fp-detail-val">{'Strong' if abs(momentum['momentum_pct'])>5 else 'Moderate'}</span></div>
              <div style="font-size:12px;color:var(--muted);margin:16px 0 6px 0;">Signal confidence</div>
              <div class="fp-health-track"><div class="fp-health-fill" style="width:{conf}%;background:linear-gradient(90deg,var(--blue),var(--green));"></div></div>
              <div style="font-size:13px;font-weight:700;color:var(--text);">{conf}%</div>
            </div>""", unsafe_allow_html=True)

        with c_ins:
            section("AI Insight", "")
            st.markdown(f"""
            <div class="fp-insight">
              <div class="fp-insight-lab">✦ AI Market Insight</div>
              <div class="fp-insight-text"><b>{symbol}</b> is trading {'above' if trend['pct_diff']>=0 else 'below'} its 20-day SMA with <b>{momentum['momentum_pct']:+.1f}%</b> 10-day momentum. FinPilot detects a <b>{trend['trend'].lower()}</b> bias, but momentum should be monitored for reversal.</div>
              <div style="font-size:11px;color:var(--muted);margin-top:12px;">AI-generated analysis — not financial advice.</div>
            </div>""", unsafe_allow_html=True)

    footer()


# ──────────────────────────────────────────────────────────────────────────────
# PAGE: AI COPILOT (hero)
# ──────────────────────────────────────────────────────────────────────────────

elif page == "🤖 AI Copilot":
    topbar("FinPilot AI", "Your personal finance copilot.")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "gemini_chat" not in st.session_state:
        st.session_state.gemini_chat = None
    if "gemini_unavailable" not in st.session_state:
        st.session_state.gemini_unavailable = False

    # Right column chat must rerun after appended messages; render everything here.
    c_ctx, c_chat = st.columns([1.0, 2.2], gap="large")

    with c_ctx:
        st.markdown("""
        <div style="font-size:11px;font-weight:700;letter-spacing:1.4px;color:var(--muted);text-transform:uppercase;margin-bottom:10px;">Financial Context</div>
        <div class="fp-context">
          <div class="fp-context-row"><span style="color:var(--text2);">Cash</span><b style="color:var(--text);">{short(net_cash)}</b></div>
          <div class="fp-context-row"><span style="color:var(--text2);">EMI</span><b style="color:var(--amber);">{short(total_emi)}</b></div>
          <div class="fp-context-row"><span style="color:var(--text2);">Monthly Credit</span><b style="color:var(--text);">{short(month_credit)}</b></div>
          <div class="fp-context-row"><span style="color:var(--text2);">Monthly Debit</span><b style="color:var(--red);">{short(month_debit)}</b></div>
          <div class="fp-context-row"><span style="color:var(--text2);">Markets</span><b style="color:var(--blue);">INFY ↑</b></div>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        st.markdown("""<div style="font-size:11px;color:var(--muted);line-height:1.6;">Ask about your cash flow, loans, EMIs or market trends. FinPilot uses your live mock data to answer.</div>""", unsafe_allow_html=True)

    with c_chat:
        new_query = st.session_state.pop("pending_query", None)
        prompt = st.chat_input("Ask FinPilot about your finances...")
        if prompt:
            new_query = prompt

        if not st.session_state.messages and new_query is None:
            st.markdown("""
            <div class="fp-card fp-empty">
              <div class="fp-empty-icon">✦</div>
              <div class="fp-empty-title">How can I help with your finances?</div>
              <div class="fp-empty-sub">Ask me about your cash flow, loans, EMIs or market trends.</div>
            </div>""", unsafe_allow_html=True)
            sc = st.columns(2, gap="small")
            suggests = [
                ("Can I afford a ₹5L loan?", "💸"),
                ("Analyze my current cash flow", "📊"),
                ("Why is my EMI burden high?", "🧾"),
                ("Analyze INFY", "📈"),
            ]
            for col, (s, icon) in zip(sc, suggests):
                with col:
                    if st.button(f"{icon} {s}", key=f"chipq_{s}", use_container_width=True, kind="secondary"):
                        st.session_state.pending_query = s
                        st.rerun()

        # Render persisted conversation
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        # Render the active query inline and persist it
        if new_query:
            with st.chat_message("user"):
                st.markdown(new_query)
            st.session_state.messages.append({"role": "user", "content": new_query})
            with st.chat_message("assistant"):
                holder = st.empty()
                holder.markdown('<div class="fp-thinking">✦ FinPilot is analyzing <span class="fp-dots"><span></span><span></span><span></span></span></div>', unsafe_allow_html=True)
                reply = _compute_answer(new_query)
                holder.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})


# ──────────────────────────────────────────────────────────────────────────────
# PAGE: NOTIFICATIONS
# ──────────────────────────────────────────────────────────────────────────────

elif page == "🔔 Notifications":
    topbar("Notifications", "Stay updated on your financial activity.")

    notif_filter = st.radio("Filter", ["All", "Finance", "Loan", "Market"], horizontal=True, label_visibility="collapsed", key="nf")
    notifications = [
        {"icon": "💳", "cls": "finance", "type": "Finance", "title": "EMI Detected", "msg": "Your HDFC EMI of ₹12,500 was detected on Aug 25.", "time": "2 hours ago", "read": False},
        {"icon": "₹", "cls": "finance", "type": "Finance", "title": "Salary Credited", "msg": "Salary of ₹75,000 credited to HDFC Savings.", "time": "1 day ago", "read": False},
        {"icon": "▲", "cls": "market", "type": "Market", "title": "Market Alert", "msg": "INFY momentum increased to +8.2%. Trend: UPTREND.", "time": "3 hours ago", "read": False},
        {"icon": "✦", "cls": "loan", "type": "Loan", "title": "Loan Insight", "msg": "An alternative HDFC offer may reduce total cost by ₹12K.", "time": "5 hours ago", "read": True},
        {"icon": "◎", "cls": "finance", "type": "Finance", "title": "Dividend Received", "msg": "Dividend of ₹1,200 credited from Infosys Ltd.", "time": "3 days ago", "read": True},
        {"icon": "⚠", "cls": "alert", "type": "Finance", "title": "Spending Alert", "msg": "Food spending is 15% higher than last month.", "time": "2 days ago", "read": True},
        {"icon": "▼", "cls": "market", "type": "Market", "title": "Stock Update", "msg": "TCS down -2.1% today. Momentum turning negative.", "time": "3 days ago", "read": True},
    ]
    if notif_filter != "All":
        notifications = [n for n in notifications if n["type"] == notif_filter]

    colours = {"finance": "#5B8DEF", "loan": "#19C37D", "market": "#19C37D", "alert": "#F5B942"}
    for n in notifications:
        st.markdown(
            f'<div class="fp-notif" style="{'border-left:3px solid var(--green);' if not n["read"] else ''}">'
            f'<div class="fp-notif-icon" style="background:rgba(91,141,239,.12);color:{colours.get(n["cls"],"#5B8DEF")};">{n["icon"]}</div>'
            f'<div><div class="fp-notif-title">{n["title"]}</div>'
            f'<div class="fp-notif-msg">{n["msg"]}</div>'
            f'<div class="fp-notif-time">{n["time"]}</div></div></div>', unsafe_allow_html=True)

    footer()


# ──────────────────────────────────────────────────────────────────────────────
# PAGE: PROFILE
# ──────────────────────────────────────────────────────────────────────────────

elif page == "👤 Profile":
    topbar("Profile", "Manage your FinPilot preferences.")

    st.markdown("""
    <div class="fp-card" style="text-align:center;padding:32px;">
      <div style="width:78px;height:78px;border-radius:50%;margin:0 auto;background:linear-gradient(135deg,var(--green),var(--blue));
      display:flex;align-items:center;justify-content:center;font-size:30px;color:#0B0F14;font-weight:800;box-shadow:0 0 28px rgba(25,195,125,.4);">P</div>
      <div style="font-size:20px;font-weight:700;color:var(--text);margin-top:12px;">Prakash</div>
      <div style="font-size:13px;color:var(--muted);">FinPilot AI Member</div>
      <div style="margin-top:14px;"><span class="fp-badge green"><span class="dot"></span>AI Connected</span></div>
    </div>""", unsafe_allow_html=True)

    st.write("")
    section("Settings", "")
    settings = [
        ("💰", "Financial Preferences", "Default currency, income, EMI details"),
        ("🔔", "Notifications", "Manage alerts and notification preferences"),
        ("🔒", "Security", "Password, 2FA, session management"),
        ("🔗", "Data Sources", "Connected bank accounts and market feeds"),
        ("📊", "Export Data", "Download your financial data as CSV"),
        ("🤖", "AI Settings", "Chat history, model preferences"),
    ]
    for icon, label, sub in settings:
        st.markdown(
            f'<div class="fp-notif"><div class="fp-notif-icon" style="background:rgba(91,141,239,.12);">{icon}</div>'
            f'<div style="flex:1;"><div class="fp-notif-title">{label}</div><div class="fp-notif-msg">{sub}</div></div>'
            f'<div style="color:var(--muted);">›</div></div>', unsafe_allow_html=True)

    st.write("")
    section("System Info", "")
    info = [("App Version", "1.0.0"), ("Engine", "FinPilot AI Finance Controller"),
            ("Data Source", "Mock Bank + Market Data"), ("AI Model", GEMINI_MODEL),
            ("Transactions", f"{len(DATA['transactions'])} loaded"),
            ("Loan Offers", f"{len(DATA['loan_offers'])} available"),
            ("Market Symbols", "19 tracked")]
    rows = "".join(
        f'<tr><td style="color:var(--text2);">{lab}</td><td style="text-align:right;font-weight:600;">{val}</td></tr>'
        for lab, val in info)
    st.markdown(f'<table class="fp-table"><tbody>{rows}</tbody></table>', unsafe_allow_html=True)

    footer()
