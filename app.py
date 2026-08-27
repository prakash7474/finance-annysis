"""
app.py - FinPilot: AI Finance Controller (Streamlit Web UI)

A premium fintech web interface with sidebar navigation:
  - Home dashboard
  - Finance Controller (Phase 1)
  - Loan Advisor (Phase 2)
  - Market & Trading (Phase 3)
  - AI Finance Chat (Phase 4)
  - Notifications
  - Profile / Settings

Usage:
    streamlit run app.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Fix Windows encoding (safe for Streamlit reruns)
import io
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
    layout="centered",
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

# ──────────────────────────────────────────────────────────────────────────────
# Gemini client (lazy init for chat)
# ──────────────────────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


def _get_gemini_chat():
    """Create a Gemini chat session with all finance tools."""
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return None

    client = genai.Client(api_key=GEMINI_API_KEY)

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
        model="gemini-3.6-flash",
        config=types.GenerateContentConfig(
            tools=all_tools,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
        ),
    )
    return chat


# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────


def fmt_inr(amount: float) -> str:
    """Format amount in Indian Rupee style."""
    if amount < 0:
        return f"\u20b9{abs(amount):,.2f}"
    return f"\u20b9{amount:,.2f}"


def fmt_inr_short(amount: float) -> str:
    """Short INR format for cards."""
    if abs(amount) >= 100_000:
        return f"\u20b9{amount / 100_000:.2f}L"
    if abs(amount) >= 1_000:
        return f"\u20b9{amount / 1_000:.1f}K"
    return f"\u20b9{amount:.0f}"


# ──────────────────────────────────────────────────────────────────────────────
# Pre-compute all data
# ──────────────────────────────────────────────────────────────────────────────


def _load_all_data():
    """Load and compute all data for the app."""
    accounts = _mock_data["accounts"]
    transactions = _mock_data["transactions"]
    loan_offers = _mock_data["loan_offers"]

    cash = fe.compute_cash_position(accounts, transactions)

    today = datetime.now()
    month_start = today.replace(day=1).strftime("%Y-%m-%d")
    month_end = today.strftime("%Y-%m-%d")
    summary = fe.summarize_credit_debit(transactions, month_start, month_end)
    emis = fe.detect_emis(transactions, month_start, month_end)
    categories = fe.get_category_summary(transactions, month_start, month_end)
    recent_txns = sorted(transactions, key=lambda t: t["date"], reverse=True)[:5]

    return {
        "cash": cash,
        "summary": summary,
        "emis": emis,
        "categories": categories,
        "recent_txns": recent_txns,
        "loan_offers": loan_offers,
        "month_start": month_start,
        "month_end": month_end,
        "accounts": accounts,
        "transactions": transactions,
    }


DATA = _load_all_data()

# Pre-compute daily cash flow (used across pages)
daily = {}
for t in DATA["transactions"]:
    d = t["date"]
    daily[d] = daily.get(d, 0) + (t["amount"] if t["type"] == "CREDIT" else -t["amount"])

net_cash = DATA["cash"]["net_cash"]
total_emi = DATA["emis"]["total_emi"]

# ──────────────────────────────────────────────────────────────────────────────
# Custom CSS — dark fintech theme
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Global dark background */
.stApp { background: #080c24; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0e27 0%, #0f1332 100%);
    border-right: 1px solid rgba(0,200,255,0.08);
}
section[data-testid="stSidebar"] .stMarkdown p { color: #8892b0; }
section[data-testid="stSidebar"] hr { border-color: rgba(0,200,255,0.1); }

/* Cards */
.fin-card {
    background: rgba(15, 19, 50, 0.85);
    border: 1px solid rgba(0, 200, 255, 0.12);
    border-radius: 18px;
    padding: 22px;
    color: white;
    transition: transform 0.2s, border-color 0.2s;
}
.fin-card:hover {
    transform: scale(1.015);
    border-color: rgba(0, 200, 255, 0.3);
}

/* KPI card */
.kpi-card {
    background: rgba(15, 19, 50, 0.85);
    border: 1px solid rgba(0, 200, 255, 0.12);
    border-radius: 16px;
    padding: 20px;
    color: white;
    text-align: center;
    transition: transform 0.2s;
}
.kpi-card:hover { transform: scale(1.02); border-color: rgba(0,200,255,0.3); }
.kpi-label { font-size: 11px; color: #8892b0; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
.kpi-value { font-size: 24px; font-weight: 700; color: #00c8ff; }
.kpi-value.positive { color: #00e676; }
.kpi-value.negative { color: #ff5252; }
.kpi-value.warning { color: #ffab00; }
.kpi-sub { font-size: 11px; color: #8892b0; margin-top: 6px; }

/* Cash card */
.cash-card {
    background: linear-gradient(135deg, #0f1332 0%, #1a1f4e 60%, #0f1332 100%);
    border: 1px solid rgba(0,200,255,0.2);
    border-radius: 20px;
    padding: 28px;
    color: white;
    position: relative;
    overflow: hidden;
}
.cash-card::before {
    content: '';
    position: absolute;
    top: -50%; right: -50%;
    width: 100%; height: 100%;
    background: radial-gradient(circle, rgba(0,200,255,0.06) 0%, transparent 70%);
    pointer-events: none;
}
.cash-label { font-size: 13px; color: #8892b0; text-transform: uppercase; letter-spacing: 1px; }
.cash-amount { font-size: 36px; font-weight: 800; color: #00c8ff; margin: 8px 0; }
.cash-change { font-size: 14px; color: #00e676; font-weight: 600; }

/* Feature card */
.feature-card {
    background: rgba(15, 19, 50, 0.85);
    border: 1px solid rgba(0, 200, 255, 0.12);
    border-radius: 18px;
    padding: 24px;
    color: white;
    transition: all 0.25s;
    cursor: default;
}
.feature-card:hover {
    transform: scale(1.03);
    border-color: rgba(0,200,255,0.35);
    box-shadow: 0 8px 30px rgba(0,200,255,0.08);
}
.feature-icon { font-size: 32px; margin-bottom: 10px; }
.feature-title { font-size: 16px; font-weight: 700; color: #e0e6ed; margin-bottom: 6px; }
.feature-desc { font-size: 12px; color: #8892b0; line-height: 1.5; }

/* Transaction row */
.txn-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 13px 16px;
    background: rgba(15, 19, 50, 0.6);
    border: 1px solid rgba(0, 200, 255, 0.08);
    border-radius: 14px;
    margin-bottom: 8px;
    color: white;
    transition: transform 0.15s;
}
.txn-row:hover { transform: scale(1.01); border-color: rgba(0,200,255,0.2); }
.txn-icon {
    width: 38px; height: 38px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 17px; margin-right: 12px; flex-shrink: 0;
}
.txn-icon.credit { background: rgba(0,230,118,0.15); }
.txn-icon.debit { background: rgba(255,82,82,0.15); }
.txn-info { flex: 1; }
.txn-name { font-size: 13px; font-weight: 600; color: #e0e6ed; }
.txn-date { font-size: 11px; color: #8892b0; margin-top: 2px; }
.txn-amount { font-size: 14px; font-weight: 700; }
.txn-amount.credit { color: #00e676; }
.txn-amount.debit { color: #ff5252; }

/* Risk badge */
.risk-badge { display: inline-block; padding: 5px 14px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
.risk-badge.low { background: rgba(0,230,118,0.15); color: #00e676; border: 1px solid rgba(0,230,118,0.3); }
.risk-badge.medium { background: rgba(255,171,0,0.15); color: #ffab00; border: 1px solid rgba(255,171,0,0.3); }
.risk-badge.high { background: rgba(255,82,82,0.15); color: #ff5252; border: 1px solid rgba(255,82,82,0.3); }

/* Offer card */
.offer-card {
    background: rgba(15, 19, 50, 0.85);
    border: 1px solid rgba(0, 200, 255, 0.12);
    border-radius: 18px;
    padding: 22px;
    color: white;
    margin-bottom: 14px;
    transition: transform 0.2s;
}
.offer-card:hover { transform: scale(1.01); border-color: rgba(0,200,255,0.25); }
.offer-card.best { border-color: rgba(0,230,118,0.4); box-shadow: 0 0 24px rgba(0,230,118,0.08); }
.offer-bank { font-size: 18px; font-weight: 700; color: #00c8ff; }
.offer-kpi { font-size: 20px; font-weight: 700; color: #e0e6ed; margin-top: 8px; }
.offer-kpi-label { font-size: 10px; color: #8892b0; text-transform: uppercase; letter-spacing: 0.5px; }
.best-badge { background: linear-gradient(135deg, #00e676, #00c8ff); color: #0a0e27; font-size: 10px; font-weight: 800; padding: 4px 10px; border-radius: 6px; text-transform: uppercase; }

/* Stock header */
.stock-header {
    background: linear-gradient(135deg, #0f1332 0%, #1a1f4e 100%);
    border: 1px solid rgba(0,200,255,0.2);
    border-radius: 20px;
    padding: 26px;
    color: white;
}
.stock-symbol { font-size: 30px; font-weight: 800; color: #00c8ff; }
.stock-price { font-size: 26px; font-weight: 700; color: white; margin: 4px 0; }
.stock-change { font-size: 15px; font-weight: 600; }
.stock-change.up { color: #00e676; }
.stock-change.down { color: #ff5252; }
.trend-badge { display: inline-block; padding: 5px 12px; border-radius: 8px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
.trend-badge.uptrend { background: rgba(0,230,118,0.15); color: #00e676; }
.trend-badge.downtrend { background: rgba(255,82,82,0.15); color: #ff5252; }
.trend-badge.neutral { background: rgba(255,171,0,0.15); color: #ffab00; }

/* Chat bubbles */
.chat-user {
    background: linear-gradient(135deg, #1a1f4e, #2a2f6e);
    border: 1px solid rgba(123,97,255,0.25);
    border-radius: 18px 18px 4px 18px;
    padding: 14px 18px; color: white;
    margin-left: 40px; margin-bottom: 12px;
    font-size: 14px; max-width: 85%; float: right;
}
.chat-ai {
    background: rgba(15,19,50,0.9);
    border: 1px solid rgba(0,200,255,0.15);
    border-radius: 18px 18px 18px 4px;
    padding: 14px 18px; color: #e0e6ed;
    margin-right: 40px; margin-bottom: 12px;
    font-size: 14px; line-height: 1.6; max-width: 85%;
}
.chat-ai strong { color: #00c8ff; }

/* AI status dot */
.ai-dot { width: 8px; height: 8px; border-radius: 50%; background: #00e676; display: inline-block; animation: pulse 2s infinite; margin-right: 6px; }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

/* Section title */
.section-title { font-size: 17px; font-weight: 700; color: #e0e6ed; margin: 22px 0 12px 0; }

/* Notification card */
.notif-card {
    background: rgba(15,19,50,0.85);
    border: 1px solid rgba(0,200,255,0.12);
    border-radius: 16px;
    padding: 18px 20px;
    color: white;
    margin-bottom: 10px;
    transition: transform 0.15s;
}
.notif-card:hover { transform: scale(1.01); border-color: rgba(0,200,255,0.25); }
.notif-card.unread { border-left: 3px solid #00c8ff; }
.notif-icon { width: 40px; height: 40px; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; font-size: 18px; margin-right: 14px; }
.notif-icon.finance { background: rgba(0,200,255,0.12); }
.notif-icon.loan { background: rgba(123,97,255,0.12); }
.notif-icon.market { background: rgba(0,230,118,0.12); }
.notif-icon.alert { background: rgba(255,171,0,0.12); }

/* Profile section */
.profile-header {
    background: linear-gradient(135deg, #0f1332 0%, #1a1f4e 100%);
    border: 1px solid rgba(0,200,255,0.2);
    border-radius: 20px;
    padding: 32px;
    color: white;
    text-align: center;
}
.profile-avatar { width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, #00c8ff, #7b61ff); display: flex; align-items: center; justify-content: center; font-size: 32px; margin: 0 auto 14px; }
.profile-name { font-size: 22px; font-weight: 700; color: #e0e6ed; }
.profile-role { font-size: 13px; color: #8892b0; margin-top: 4px; }
.settings-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 20px;
    background: rgba(15,19,50,0.7);
    border: 1px solid rgba(0,200,255,0.1);
    border-radius: 14px;
    color: white;
    margin-bottom: 8px;
    transition: transform 0.15s;
}
.settings-row:hover { transform: scale(1.01); border-color: rgba(0,200,255,0.2); }
.settings-label { font-size: 14px; font-weight: 600; color: #e0e6ed; }
.settings-sub { font-size: 12px; color: #8892b0; margin-top: 2px; }
.settings-arrow { color: #8892b0; font-size: 18px; }

/* Action button */
.action-btn {
    background: rgba(15,19,50,0.85);
    border: 1px solid rgba(0,200,255,0.15);
    border-radius: 16px; padding: 18px;
    text-align: center; color: white;
    transition: all 0.2s;
}
.action-btn:hover { border-color: #00c8ff; background: rgba(0,200,255,0.08); transform: scale(1.02); }
.action-icon { font-size: 26px; margin-bottom: 8px; }
.action-label { font-size: 12px; font-weight: 600; color: #e0e6ed; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: rgba(15,19,50,0.6); border-radius: 14px; padding: 4px; gap: 4px; }
.stTabs [data-baseweb="tab"] { background: transparent; border-radius: 10px; color: #8892b0; font-weight: 600; font-size: 13px; padding: 10px 18px; border: none; }
.stTabs [aria-selected="true"] { background: rgba(0,200,255,0.12) !important; color: #00c8ff !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,200,255,0.2); border-radius: 3px; }

/* Hide defaults */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
.stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 20px 0;">
        <div style="display:flex; align-items:center; gap:10px;">
            <div style="font-size:28px;">📈</div>
            <div>
                <div style="font-size:20px; font-weight:800; background:linear-gradient(90deg,#00c8ff,#7b61ff); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">FinPilot</div>
                <div style="font-size:9px; color:#8892b0; letter-spacing:1.5px;">AI FINANCE CONTROLLER</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["🏠 Home", "💼 Finance Controller", "💰 Loan Advisor", "📈 Market & Trading", "💬 AI Finance Chat", "🔔 Notifications", "👤 Profile"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Context strip in sidebar
    net_cash = DATA["cash"]["net_cash"]
    total_emi = DATA["emis"]["total_emi"]
    st.markdown(f"""
    <div style="padding: 4px 0;">
        <div style="font-size:10px; color:#8892b0; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">Context</div>
        <div style="background:rgba(0,200,255,0.06); border:1px solid rgba(0,200,255,0.1); border-radius:10px; padding:10px 12px; margin-bottom:6px;">
            <div style="font-size:10px; color:#8892b0;">CASH</div>
            <div style="font-size:14px; font-weight:700; color:#00c8ff;">{fmt_inr_short(net_cash)}</div>
        </div>
        <div style="background:rgba(255,171,0,0.06); border:1px solid rgba(255,171,0,0.1); border-radius:10px; padding:10px 12px; margin-bottom:6px;">
            <div style="font-size:10px; color:#8892b0;">EMI</div>
            <div style="font-size:14px; font-weight:700; color:#ffab00;">{fmt_inr_short(total_emi)}</div>
        </div>
        <div style="background:rgba(123,97,255,0.06); border:1px solid rgba(123,97,255,0.1); border-radius:10px; padding:10px 12px;">
            <div style="font-size:10px; color:#8892b0;">LOAN OFFERS</div>
            <div style="font-size:14px; font-weight:700; color:#7b61ff;">{len(DATA['loan_offers'])} available</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; font-size:10px; color:#3a3f5c;'>"
        "For demo/educational purposes only.<br>Not financial advice."
        "</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════════════════════════════════════

if page == "🏠 Home":
    # Title + tagline
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <div style="font-size: 32px; font-weight: 800; background: linear-gradient(90deg, #00c8ff, #7b61ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            FinPilot — AI Finance Controller
        </div>
        <div style="font-size: 15px; color: #8892b0; margin-top: 6px;">
            Run the books, analyze loans, and track markets — all in one AI agent.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KPI row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Transactions</div><div class="kpi-value">{len(DATA['transactions'])}</div><div class="kpi-sub">processed</div></div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label">EMIs Detected</div><div class="kpi-value warning">{DATA['emis']['emi_count']}</div><div class="kpi-sub">recurring</div></div>""", unsafe_allow_html=True)
    with k3:
        st.markdown("""<div class="kpi-card"><div class="kpi-label">Loan Scenarios</div><div class="kpi-value">4</div><div class="kpi-sub">analyzed</div></div>""", unsafe_allow_html=True)
    with k4:
        st.markdown("""<div class="kpi-card"><div class="kpi-label">Stocks Tracked</div><div class="kpi-value">19</div><div class="kpi-sub">symbols</div></div>""", unsafe_allow_html=True)

    # Feature cards
    st.markdown('<div class="section-title">Capabilities</div>', unsafe_allow_html=True)
    fc1, fc2, fc3, fc4 = st.columns(4)
    features = [
        ("💼", "Finance Controller", "Cash position, credit/debit summary, EMI detection."),
        ("💰", "Loan Advisor", "EMI calculator, total cost, risk flags, offer comparison."),
        ("📈", "Market & Trading", "Prices, OHLC charts, SMA trend, momentum."),
        ("💬", "AI Finance Chat", "Ask anything about your finances, loans, and stocks."),
    ]
    for col, (icon, title, desc) in zip([fc1, fc2, fc3, fc4], features):
        with col:
            st.markdown(f"""<div class="feature-card"><div class="feature-icon">{icon}</div><div class="feature-title">{title}</div><div class="feature-desc">{desc}</div></div>""", unsafe_allow_html=True)

    # Cash position
    st.markdown('<div class="section-title">Net Cash Position</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="cash-card">
        <div class="cash-label">Available Balance</div>
        <div class="cash-amount">{fmt_inr(net_cash)}</div>
        <div class="cash-change">+8.4% this month</div>
    </div>
    """, unsafe_allow_html=True)

    # Mini cash chart
    if daily:
        sorted_dates = sorted(daily.keys())[-15:]
        cumulative = []
        running = net_cash - sum(daily[d] for d in sorted(daily.keys()))
        for d in sorted_dates:
            running += daily[d]
            cumulative.append(round(running, 2))
        fig_cash = go.Figure()
        fig_cash.add_trace(go.Scatter(x=sorted_dates, y=cumulative, mode="lines+markers",
            line=dict(color="#00c8ff", width=2, shape="spline"), marker=dict(size=4),
            fill="tozeroy", fillcolor="rgba(0,200,255,0.05)"))
        fig_cash.update_layout(height=130, margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False), yaxis=dict(visible=False, showgrid=False), showlegend=False)
        st.plotly_chart(fig_cash, use_container_width=True)

    # Recent transactions
    st.markdown('<div class="section-title">Recent Activity</div>', unsafe_allow_html=True)
    icons = {"LOAN_EMI": "L", "SALARY": "S", "SHOPPING": "$", "FOOD": "F",
             "FUEL": "G", "RENT": "R", "UTILITY": "U", "SUBSCRIPTION": "S",
             "TRANSFER": "T", "INTEREST": "I", "DIVIDEND": "D",
             "FREELANCE": "F", "BANK_CHARGES": "B", "GROCERY": "G", "TRANSPORT": "T"}
    for txn in DATA["recent_txns"][:5]:
        is_credit = txn["type"] == "CREDIT"
        icon = icons.get(txn.get("category", ""), "X")
        icon_cls = "credit" if is_credit else "debit"
        sign = "+" if is_credit else "-"
        st.markdown(f"""<div class="txn-row"><div style="display:flex; align-items:center;"><div class="txn-icon {icon_cls}">{icon}</div><div class="txn-info"><div class="txn-name">{txn['description'].split(' - ')[-1][:35]}</div><div class="txn-date">{txn['date']}</div></div></div><div class="txn-amount {icon_cls}">{sign}{fmt_inr(txn['amount'])}</div></div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: FINANCE CONTROLLER
# ══════════════════════════════════════════════════════════════════════════════

elif page == "💼 Finance Controller":
    st.markdown("""<div style="margin-bottom:20px;"><div style="font-size:26px; font-weight:800; color:#e0e6ed;">💼 Finance Controller</div><div style="font-size:13px; color:#8892b0; margin-top:4px;">Your financial activity at a glance</div></div>""", unsafe_allow_html=True)

    # Date filter
    date_filter = st.selectbox("Date Range", ["This Month", "Last 30 Days", "Last 90 Days"], index=0, label_visibility="collapsed")
    if date_filter == "This Month":
        start_d, end_d = DATA["month_start"], DATA["month_end"]
    elif date_filter == "Last 30 Days":
        end_d = datetime.now().strftime("%Y-%m-%d")
        start_d = (datetime.now() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    else:
        end_d = datetime.now().strftime("%Y-%m-%d")
        start_d = (datetime.now() - pd.Timedelta(days=90)).strftime("%Y-%m-%d")

    summary_f = fe.summarize_credit_debit(DATA["transactions"], start_d, end_d)
    emis_f = fe.detect_emis(DATA["transactions"], start_d, end_d)

    # KPI row
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Net Cash</div><div class="kpi-value">{fmt_inr(net_cash)}</div><div class="kpi-sub">Available balance</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Total Credit</div><div class="kpi-value positive">{fmt_inr(summary_f['total_credit'])}</div><div class="kpi-sub">{summary_f['transaction_count']} transactions</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Total Debit</div><div class="kpi-value negative">{fmt_inr(summary_f['total_debit'])}</div><div class="kpi-sub">Net: {fmt_inr(summary_f['net_change'])}</div></div>""", unsafe_allow_html=True)

    # Cash flow chart
    st.markdown('<div class="section-title">Cash Flow</div>', unsafe_allow_html=True)
    chart_dates = sorted(daily.keys())[-20:]
    if chart_dates:
        vals = [daily[d] for d in chart_dates]
        fig_flow = go.Figure()
        fig_flow.add_trace(go.Bar(x=chart_dates, y=vals, marker_color=["#00e676" if v >= 0 else "#ff5252" for v in vals], opacity=0.8))
        fig_flow.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(color="#8892b0", gridcolor="rgba(0,200,255,0.05)"),
            yaxis=dict(color="#8892b0", gridcolor="rgba(0,200,255,0.05)"), showlegend=False)
        st.plotly_chart(fig_flow, use_container_width=True)

    # EMI detection
    st.markdown(f"""<div class="section-title">Detected EMIs</div><div style="font-size:12px; color:#8892b0; margin-bottom:12px;">{emis_f['emi_count']} recurring payments in this period</div>""", unsafe_allow_html=True)
    for lender, amt in emis_f["emi_breakdown"].items():
        st.markdown(f"""<div class="txn-row"><div style="display:flex; align-items:center;"><div class="txn-icon debit">\ud83c\udfe6</div><div class="txn-info"><div class="txn-name">{lender}</div><div class="txn-date">{start_d} to {end_d}</div></div></div><div class="txn-amount debit">{fmt_inr(amt)}</div></div>""", unsafe_allow_html=True)

    # Spending by category
    st.markdown('<div class="section-title">Spending by Category</div>', unsafe_allow_html=True)
    cats = DATA["categories"]["categories"]
    if cats:
        sorted_cats = sorted(cats.items(), key=lambda x: x[1]["total"], reverse=True)
        fig_cat = go.Figure(go.Bar(x=[c[1]["total"] for c in sorted_cats], y=[c[0] for c in sorted_cats],
            orientation="h", marker_color="#00c8ff", opacity=0.8,
            text=[f"{fmt_inr(c[1]['total'])} ({c[1]['count']})" for c in sorted_cats], textposition="auto"))
        fig_cat.update_layout(height=max(200, len(sorted_cats) * 28), margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(color="#8892b0", gridcolor="rgba(0,200,255,0.05)"),
            yaxis=dict(color="#8892b0", autorange="reversed"), showlegend=False)
        st.plotly_chart(fig_cat, use_container_width=True)

    # All transactions (expandable)
    with st.expander("All Transactions", expanded=False):
        for txn in sorted(DATA["transactions"], key=lambda t: t["date"], reverse=True):
            is_credit = txn["type"] == "CREDIT"
            sign = "+" if is_credit else "-"
            color = "#00e676" if is_credit else "#ff5252"
            st.markdown(f"<div style='display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,200,255,0.05);color:#e0e6ed;font-size:13px;'><span>{txn['date']} &nbsp; {txn['description'][:40]}</span><span style='color:{color};font-weight:600;'>{sign}{fmt_inr(txn['amount'])}</span></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: LOAN ADVISOR
# ══════════════════════════════════════════════════════════════════════════════

elif page == "💰 Loan Advisor":
    st.markdown("""<div style="margin-bottom:20px;"><div style="font-size:26px; font-weight:800; color:#e0e6ed;">💰 Loan Advisor</div><div style="font-size:13px; color:#8892b0; margin-top:4px;">Make smarter borrowing decisions</div></div>""", unsafe_allow_html=True)

    tab_single, tab_compare = st.tabs(["📋 Single Loan Analysis", "⚖️ Compare Offers"])

    with tab_single:
        st.markdown('<div class="section-title">Loan Parameters</div>', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            loan_amount = st.number_input("Loan Amount (\u20b9)", value=300000, step=10000, min_value=10000)
            loan_rate = st.number_input("Interest Rate (%)", value=12.0, step=0.5, min_value=1.0, max_value=30.0)
            loan_tenure = st.number_input("Tenure (months)", value=36, step=1, min_value=1, max_value=360)
        with col_b:
            loan_income = st.number_input("Monthly Income (\u20b9)", value=80000, step=5000, min_value=10000)
            loan_existing_emi = st.number_input("Existing Monthly EMI (\u20b9)", value=22300, step=1000, min_value=0)

        if st.button("Analyze Loan", use_container_width=True, type="primary"):
            with st.spinner("Computing loan scenario..."):
                result = le.assess_loan_risk(loan_amount, loan_rate, loan_tenure, loan_income, loan_existing_emi)

            # KPI row
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f"""<div class="kpi-card"><div class="kpi-label">EMI</div><div class="kpi-value">{fmt_inr(result['emi'])}</div></div>""", unsafe_allow_html=True)
            with k2:
                st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Total Interest</div><div class="kpi-value negative">{fmt_inr(result['total_interest'])}</div></div>""", unsafe_allow_html=True)
            with k3:
                st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Total Cost</div><div class="kpi-value">{fmt_inr(result['total_cost'])}</div></div>""", unsafe_allow_html=True)
            with k4:
                ratio_pct = result["emi_income_ratio"] * 100
                ratio_cls = "positive" if ratio_pct < 40 else "warning" if ratio_pct < 50 else "negative"
                st.markdown(f"""<div class="kpi-card"><div class="kpi-label">EMI / Income</div><div class="kpi-value {ratio_cls}">{ratio_pct:.1f}%</div></div>""", unsafe_allow_html=True)

            # Risk assessment
            risk_cls = result["risk_level"].lower()
            st.markdown(f"""
            <div class="fin-card" style="margin-top:16px;">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">
                    <div style="font-size:16px; font-weight:700;">AI Risk Assessment</div>
                    <span class="risk-badge {risk_cls}">{result['risk_level']} RISK</span>
                </div>
                <div style="display:flex; gap:8px; margin-bottom:14px;">
                    <div style="flex:1; height:8px; border-radius:4px; background:rgba(0,230,118,0.2);"></div>
                    <div style="flex:1; height:8px; border-radius:4px; background:rgba(255,171,0,0.2);"></div>
                    <div style="flex:1; height:8px; border-radius:4px; background:rgba(255,82,82,0.2);"></div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:10px; color:#8892b0; margin-bottom:16px;">
                    <span>LOW</span><span>MEDIUM</span><span>HIGH</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Risk flags
            if result["risk_flags"]:
                for flag in result["risk_flags"]:
                    severity_icon = "\u26a0\ufe0f" if flag["severity"] in ("MEDIUM", "HIGH") else "\u2713"
                    st.markdown(f"""<div style="padding:10px 14px; background:rgba(15,19,50,0.6); border:1px solid rgba(0,200,255,0.08); border-radius:10px; margin-bottom:6px; font-size:13px; color:#e0e6ed;">{severity_icon} {flag['message']}</div>""", unsafe_allow_html=True)

            # Suggestion
            if result["risk_level"] == "HIGH":
                suggestion = "This loan carries significant risk. Consider a lower amount, longer tenure, or lower interest rate."
            elif result["risk_level"] == "MEDIUM":
                suggestion = "Moderate risk. Compare with other offers or consider extending tenure to reduce EMI burden."
            else:
                suggestion = "Low risk. This loan appears manageable for your income."
            st.markdown(f"""<div style="padding:14px 18px; background:rgba(0,200,255,0.06); border:1px solid rgba(0,200,255,0.15); border-radius:14px; margin-top:12px; font-size:13px; color:#e0e6ed;"><strong>AI Suggestion:</strong> {suggestion}</div>""", unsafe_allow_html=True)

    with tab_compare:
        st.markdown('<div class="section-title">Compare Loan Offers</div>', unsafe_allow_html=True)
        comp_amount = st.number_input("Loan Amount (\u20b9)", value=200000, step=10000, min_value=10000, key="comp_amt")
        comp_income = st.number_input("Monthly Income (\u20b9)", value=80000, step=5000, min_value=10000, key="comp_inc")
        comp_emi = st.number_input("Existing EMI (\u20b9)", value=22300, step=1000, min_value=0, key="comp_emi")

        if st.button("Compare Offers", use_container_width=True, type="primary", key="comp_btn"):
            with st.spinner("Comparing offers..."):
                results = le.compare_loan_offers(comp_amount, DATA["loan_offers"], comp_income, comp_emi)

            best_id = results[0]["offer_id"] if results else None
            risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
            lowest_risk_id = min(results, key=lambda x: risk_order[x["risk_level"]])["offer_id"] if results else None

            for i, r in enumerate(results):
                is_best = r["offer_id"] == best_id
                is_lowest_risk = r["offer_id"] == lowest_risk_id
                risk_cls = r["risk_level"].lower()
                card_cls = "offer-card best" if is_best else "offer-card"

                badge = ""
                if is_best:
                    badge = '<span class="best-badge">BEST VALUE</span> '
                elif is_lowest_risk:
                    badge = '<span style="background:rgba(0,230,118,0.15); color:#00e676; font-size:10px; font-weight:700; padding:4px 10px; border-radius:6px; text-transform:uppercase;">LOWEST RISK</span> '

                st.markdown(f"""
                <div class="{card_cls}">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <div>
                            <div class="offer-bank">{r['bank']}</div>
                            <div style="font-size:12px; color:#8892b0;">{r.get('product', 'Loan')} &bull; {r['interest_rate']}% &bull; {r['tenure_months']} months</div>
                        </div>
                        <div>{badge}<span class="risk-badge {risk_cls}">{r['risk_level']}</span></div>
                    </div>
                    <div style="display:flex; gap:16px;">
                        <div><div class="offer-kpi-label">EMI</div><div class="offer-kpi">{fmt_inr(r['emi'])}</div></div>
                        <div><div class="offer-kpi-label">Total Cost</div><div class="offer-kpi">{fmt_inr(r['total_cost'])}</div></div>
                        <div><div class="offer-kpi-label">Interest</div><div class="offer-kpi">{fmt_inr(r['total_interest'])}</div></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MARKET & TRADING
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📈 Market & Trading":
    st.markdown("""<div style="margin-bottom:20px;"><div style="font-size:26px; font-weight:800; color:#e0e6ed;">📈 Market & Trading</div><div style="font-size:13px; color:#8892b0; margin-top:4px;">Real-time stock analysis powered by AI</div></div>""", unsafe_allow_html=True)

    # Symbol input + chips
    symbol_input = st.text_input("Stock symbol", value="INFY", label_visibility="collapsed", placeholder="Enter stock symbol (e.g., INFY, RELIANCE, TCS)")
    chip_cols = st.columns(5)
    for i, sym in enumerate(["INFY", "RELIANCE", "TCS", "HDFCBANK", "SBIN"]):
        with chip_cols[i]:
            if st.button(sym, key=f"chip_{sym}", use_container_width=True):
                symbol_input = sym

    symbol = symbol_input.upper().strip()

    if symbol:
        price_data = _market_adapter.get_latest_price(symbol)
        ohlc_data = _market_adapter.get_ohlc_history(symbol, 60)
        trend = me.detect_trend_vs_sma(ohlc_data, sma_days=20)
        momentum = me.compute_momentum(ohlc_data, lookback_days=10)
        hl_range = me.compute_high_low_range(ohlc_data, days=20)

        # Stock header
        trend_cls = trend["trend"].lower()
        trend_emoji = {"uptrend": "\u2191", "downtrend": "\u2193", "neutral": "\u2192"}.get(trend_cls, "?")
        chg_pct = trend.get("pct_diff", 0)
        chg_cls = "up" if chg_pct >= 0 else "down"
        chg_sign = "+" if chg_pct >= 0 else ""

        st.markdown(f"""
        <div class="stock-header">
            <div class="stock-symbol">{symbol}</div>
            <div class="stock-price">{fmt_inr(price_data)}</div>
            <div class="stock-change {chg_cls}">{chg_sign}{chg_pct:.2f}%</div>
            <div style="margin-top:8px;"><span class="trend-badge {trend_cls}">{trend_emoji} {trend['trend']}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # KPIs
        st.markdown('<div class="section-title">Key Metrics</div>', unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            mom_cls = "positive" if momentum["momentum_pct"] >= 0 else "negative"
            st.markdown(f"""<div class="kpi-card"><div class="kpi-label">10D Momentum</div><div class="kpi-value {mom_cls}">{'+' if momentum['momentum_pct'] >= 0 else ''}{momentum['momentum_pct']:.1f}%</div></div>""", unsafe_allow_html=True)
        with m2:
            sma_val = fmt_inr(trend["sma"]) if trend["sma"] else "N/A"
            st.markdown(f"""<div class="kpi-card"><div class="kpi-label">20D SMA</div><div class="kpi-value">{sma_val}</div></div>""", unsafe_allow_html=True)
        with m3:
            pvs_cls = "positive" if chg_pct >= 0 else "negative"
            st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Price vs SMA</div><div class="kpi-value {pvs_cls}">{chg_sign}{chg_pct:.2f}%</div></div>""", unsafe_allow_html=True)
        with m4:
            st.markdown(f"""<div class="kpi-card"><div class="kpi-label">20D Range</div><div class="kpi-value">{hl_range['range_pct']:.1f}%</div><div class="kpi-sub">{fmt_inr(hl_range['low'])} - {fmt_inr(hl_range['high'])}</div></div>""", unsafe_allow_html=True)

        # Chart
        st.markdown(f'<div class="section-title">{symbol} - 30 Day Chart</div>', unsafe_allow_html=True)
        chart_bars = ohlc_data[-30:] if len(ohlc_data) > 30 else ohlc_data
        dates = [b["date"] for b in chart_bars]
        closes = [b["close"] for b in chart_bars]
        sma_vals = me.compute_sma(closes, 20)

        fig_stock = go.Figure()
        fig_stock.add_trace(go.Scatter(x=dates, y=closes, mode="lines", name="Price", line=dict(color="#00c8ff", width=2)))
        sma_plot = [v for v in sma_vals if v is not None]
        sma_dates = [d for d, v in zip(dates, sma_vals) if v is not None]
        if sma_plot:
            fig_stock.add_trace(go.Scatter(x=sma_dates, y=sma_plot, mode="lines", name="20D SMA", line=dict(color="#ffab00", width=1.5, dash="dot")))
        fig_stock.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(color="#8892b0", gridcolor="rgba(0,200,255,0.05)"),
            yaxis=dict(color="#8892b0", gridcolor="rgba(0,200,255,0.05)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11, color="#8892b0")))
        st.plotly_chart(fig_stock, use_container_width=True)

        # AI insight
        explanations = {
            "UPTREND": f"{symbol} is trading above its 20-day moving average with positive momentum, indicating bullish short-term behavior.",
            "DOWNTREND": f"{symbol} is trading below its 20-day moving average, suggesting bearish pressure.",
            "NEUTRAL": f"{symbol} is trading near its 20-day moving average with no clear directional bias.",
        }
        st.markdown(f"""
        <div style="background:linear-gradient(135deg, rgba(0,200,255,0.08), rgba(123,97,255,0.08)); border:1px solid rgba(0,200,255,0.2); border-radius:18px; padding:22px; margin-top:16px;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
                <span style="font-size:18px;">🤖</span>
                <span style="font-size:15px; font-weight:700; color:#e0e6ed;">AI Market Analysis</span>
            </div>
            <div style="display:flex; gap:10px; margin-bottom:14px; flex-wrap:wrap;">
                <div style="background:rgba(0,230,118,0.1); border:1px solid rgba(0,230,118,0.25); border-radius:10px; padding:10px 16px;">
                    <div style="font-size:10px; color:#8892b0;">STATUS</div>
                    <div style="font-size:14px; font-weight:700; color:#00e676;">{trend['trend']}</div>
                </div>
                <div style="background:rgba(0,200,255,0.1); border:1px solid rgba(0,200,255,0.25); border-radius:10px; padding:10px 16px;">
                    <div style="font-size:10px; color:#8892b0;">MOMENTUM</div>
                    <div style="font-size:14px; font-weight:700; color:#00c8ff;">{'+' if momentum['momentum_pct'] >= 0 else ''}{momentum['momentum_pct']:.1f}%</div>
                </div>
                <div style="background:rgba(123,97,255,0.1); border:1px solid rgba(123,97,255,0.25); border-radius:10px; padding:10px 16px;">
                    <div style="font-size:10px; color:#8892b0;">PRICE vs SMA</div>
                    <div style="font-size:14px; font-weight:700; color:#7b61ff;">{chg_sign}{chg_pct:.2f}%</div>
                </div>
            </div>
            <div style="font-size:14px; color:#e0e6ed; line-height:1.6;">{explanations.get(trend['trend'], '')}</div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: AI FINANCE CHAT
# ══════════════════════════════════════════════════════════════════════════════

elif page == "💬 AI Finance Chat":
    st.markdown("""<div style="margin-bottom:16px;"><div style="font-size:26px; font-weight:800; color:#e0e6ed;">💬 AI Finance Chat</div><div style="font-size:13px; color:#8892b0; margin-top:4px;"><span class="ai-dot"></span> Online &mdash; Your unified financial copilot</div></div>""", unsafe_allow_html=True)

    # Context strip
    st.markdown(f"""
    <div style="display:flex; gap:10px; margin-bottom:18px; overflow-x:auto; padding:4px 0;">
        <div style="background:rgba(0,200,255,0.08); border:1px solid rgba(0,200,255,0.15); border-radius:12px; padding:10px 16px; white-space:nowrap;">
            <div style="font-size:10px; color:#8892b0;">CASH</div>
            <div style="font-size:14px; font-weight:700; color:#00c8ff;">{fmt_inr_short(net_cash)}</div>
        </div>
        <div style="background:rgba(255,171,0,0.08); border:1px solid rgba(255,171,0,0.15); border-radius:12px; padding:10px 16px; white-space:nowrap;">
            <div style="font-size:10px; color:#8892b0;">EMI</div>
            <div style="font-size:14px; font-weight:700; color:#ffab00;">{fmt_inr_short(total_emi)}</div>
        </div>
        <div style="background:rgba(123,97,255,0.08); border:1px solid rgba(123,97,255,0.15); border-radius:12px; padding:10px 16px; white-space:nowrap;">
            <div style="font-size:10px; color:#8892b0;">OFFERS</div>
            <div style="font-size:14px; font-weight:700; color:#7b61ff;">{len(DATA['loan_offers'])}</div>
        </div>
        <div style="background:rgba(0,230,118,0.08); border:1px solid rgba(0,230,118,0.15); border-radius:12px; padding:10px 16px; white-space:nowrap;">
            <div style="font-size:10px; color:#8892b0;">MONTH</div>
            <div style="font-size:14px; font-weight:700; color:#00e676;">{DATA['month_end'][:7]}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Init messages
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "gemini_chat" not in st.session_state:
        st.session_state.gemini_chat = None

    if not st.session_state.messages:
        st.session_state.messages.append({"role": "assistant", "content": "**Hi! I am your FinPilot AI.**\n\nI can help you understand your finances, compare loans, and analyze markets.\n\nTry asking:\n- *What is my current cash position?*\n- *Can I afford a Rs.3L loan?*\n- *How is INFY trending?*"})
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🔔 Notifications":
    st.markdown("""<div style="margin-bottom:20px;"><div style="font-size:26px; font-weight:800; color:#e0e6ed;">🔔 Notifications</div><div style="font-size:13px; color:#8892b0; margin-top:4px;">Stay updated on your financial activity</div></div>""", unsafe_allow_html=True)

    # Filter tabs
    notif_filter = st.radio("Filter", ["All", "Finance", "Loan", "Market"], horizontal=True, label_visibility="collapsed")

    notifications = [
        {"icon": "\ud83d\udcb3", "icon_cls": "finance", "type": "Finance", "title": "EMI Detected", "message": "Your HDFC EMI of ₹12,500 was detected on Aug 25.", "time": "2 hours ago", "unread": True},
        {"icon": "\ud83d\udcb0", "icon_cls": "finance", "type": "Finance", "title": "Salary Credited", "message": "Salary of ₹75,000 credited to HDFC Savings.", "time": "1 day ago", "unread": True},
        {"icon": "\ud83c\udfc8", "icon_cls": "market", "type": "Market", "title": "Market Alert", "message": "INFY momentum increased to +8.2%. Trend: UPTREND.", "time": "3 hours ago", "unread": True},
        {"icon": "\ud83d\udca1", "icon_cls": "loan", "type": "Loan", "title": "Loan Insight", "message": "An alternative loan offer from HDFC may reduce total cost by ₹12K.", "time": "5 hours ago", "unread": False},
        {"icon": "\ud83d\udcb3", "icon_cls": "finance", "type": "Finance", "title": "EMI Detected", "message": "Your ICICI EMI of ₹9,800 was detected on Aug 25.", "time": "2 hours ago", "unread": False},
        {"icon": "\ud83d\udcc9", "icon_cls": "market", "type": "Market", "title": "Stock Update", "message": "RELIANCE closed at ₹2,478.50 (+1.2%). SMA crossover detected.", "time": "1 day ago", "unread": False},
        {"icon": "\u26a0\ufe0f", "icon_cls": "alert", "type": "Finance", "title": "Spending Alert", "message": "Food spending is 15% higher than last month.", "time": "2 days ago", "unread": False},
        {"icon": "\ud83d\udcb0", "icon_cls": "finance", "type": "Finance", "title": "Dividend Received", "message": "Dividend of ₹1,200 credited from Infosys Ltd.", "time": "3 days ago", "unread": False},
        {"icon": "\ud83c\udfc8", "icon_cls": "market", "type": "Market", "title": "Market Alert", "message": "TCS down -2.1% today. Momentum turning negative.", "time": "3 days ago", "unread": False},
        {"icon": "\ud83d\udca1", "icon_cls": "loan", "type": "Loan", "title": "Loan Reminder", "message": "Your SBI Housing Loan EMI of ₹15,200 is due on Aug 31.", "time": "4 days ago", "unread": False},
    ]

    if notif_filter != "All":
        notifications = [n for n in notifications if n["type"] == notif_filter]

    for n in notifications:
        unread_cls = "notif-card unread" if n["unread"] else "notif-card"
        unread_dot = '<div style="width:8px; height:8px; border-radius:50%; background:#00c8ff; margin-left:8px;"></div>' if n["unread"] else ""
        st.markdown(f"""
        <div class="{unread_cls}">
            <div style="display:flex; align-items:center;">
                <div class="notif-icon {n['icon_cls']}">{n['icon']}</div>
                <div style="flex:1;">
                    <div style="display:flex; align-items:center;">
                        <div style="font-size:14px; font-weight:600; color:#e0e6ed;">{n['title']}</div>
                        {unread_dot}
                    </div>
                    <div style="font-size:12px; color:#8892b0; margin-top:2px;">{n['message']}</div>
                    <div style="font-size:11px; color:#3a3f5c; margin-top:4px;">{n['time']}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PROFILE / SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "👤 Profile":
    st.markdown("""<div style="margin-bottom:20px;"><div style="font-size:26px; font-weight:800; color:#e0e6ed;">👤 Profile</div><div style="font-size:13px; color:#8892b0; margin-top:4px;">Manage your FinPilot preferences</div></div>""", unsafe_allow_html=True)

    # Profile header
    st.markdown("""
    <div class="profile-header">
        <div class="profile-avatar">👤</div>
        <div class="profile-name">Demo User</div>
        <div class="profile-role">FinPilot AI Member</div>
        <div style="margin-top:12px;">
            <span class="ai-dot"></span>
            <span style="font-size:12px; color:#00e676; font-weight:600;">AI Online</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title" style="margin-top:24px;">Settings</div>', unsafe_allow_html=True)

    settings = [
        ("💰", "Financial Preferences", "Default currency, income, EMI details"),
        ("🔔", "Notifications", "Manage alerts and notification preferences"),
        ("🔒", "Security", "Password, 2FA, session management"),
        ("🔗", "Data Sources", "Connected bank accounts and market feeds"),
        ("📊", "Export Data", "Download your financial data as CSV"),
        ("🤖", "AI Settings", "Chat history, model preferences"),
        ("ℹ️", "About FinPilot", "Version 1.0.0 — AI Finance Controller"),
    ]

    for icon, label, sub in settings:
        st.markdown(f"""
        <div class="settings-row">
            <div style="display:flex; align-items:center; gap:12px;">
                <span style="font-size:20px;">{icon}</span>
                <div>
                    <div class="settings-label">{label}</div>
                    <div class="settings-sub">{sub}</div>
                </div>
            </div>
            <span class="settings-arrow">\u203a</span>
        </div>
        """, unsafe_allow_html=True)

    # System info
    st.markdown('<div class="section-title" style="margin-top:24px;">System Info</div>', unsafe_allow_html=True)
    info_items = [
        ("App Version", "1.0.0"),
        ("Engine", "FinPilot AI Finance Controller"),
        ("Data Source", "Mock Bank + Market Data"),
        ("AI Model", "Gemini 3.6 Flash"),
        ("Transactions", f"{len(DATA['transactions'])} loaded"),
        ("Loan Offers", f"{len(DATA['loan_offers'])} available"),
        ("Market Symbols", "19 tracked"),
    ]
    for label, value in info_items:
        st.markdown(f"""<div style="display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid rgba(0,200,255,0.05); font-size:13px;">
            <span style="color:#8892b0;">{label}</span>
            <span style="color:#e0e6ed; font-weight:600;">{value}</span>
        </div>""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="text-align:center; padding:30px 0 10px 0; color:#3a3f5c; font-size:11px;">
    FinPilot AI Finance Controller — Hackathon Demo<br>
    Powered by Gemini AI • Mock Data for Demonstration<br>
    For educational purposes only. Not financial advice.
</div>
""", unsafe_allow_html=True)
