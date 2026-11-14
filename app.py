"""OLIVER LESO | Equity Research Studio

Streamlit stock screener and portfolio risk dashboard using Yahoo Finance data.
Educational tool only; it is not investment advice.
"""
from __future__ import annotations

import json
import time
import uuid
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

import extra_streamlit_components as stx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# -----------------------------------------------------------------------------
# Page setup + visual identity
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="OLIVER LESO | Equity Research Studio",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

BG = "#0A0F1D"
PANEL = "#111A2E"
PANEL_2 = "#16223A"
BORDER = "#263552"
TEXT = "#EAF0FA"
MUTED = "#98A9C4"
ACCENT = "#54E1C1"
ACCENT_2 = "#8CA8FF"
GOLD = "#FFC66D"
RED = "#FF758F"
MAX_TICKERS = 35
MAX_COMPARE = 4
FETCH_TIMEOUT = 90
BASE_CURRENCIES = ["EUR", "USD", "CZK"]
CURRENCY_SYMBOL = {"EUR": "€", "USD": "$", "CZK": "Kč"}

st.markdown(
    f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
      :root {{ --bg:{BG}; --panel:{PANEL}; --panel2:{PANEL_2}; --border:{BORDER}; --text:{TEXT}; --muted:{MUTED}; --accent:{ACCENT}; }}
      html, body, [class*="css"] {{ font-family: 'Manrope', sans-serif; }}
      .stApp {{ background: radial-gradient(circle at 12% 0%, #172643 0, {BG} 38%), radial-gradient(circle at 100% 100%, #0f2a2c 0, transparent 40%); color: {TEXT}; }}
      [data-testid="stHeader"] {{ background: rgba(10,15,29,.85); }}
      [data-testid="stSidebar"] {{ background: linear-gradient(180deg, #101a2d 0%, #0b1222 100%); border-right: 1px solid {BORDER}; }}
      [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1,
      [data-testid="stSidebar"] h4, [data-testid="stSidebar"] summary {{ color: {TEXT}; }}
      [data-testid="stSidebar"] [data-testid="stExpander"] {{ border: 1px solid {BORDER}; border-radius: 12px; background: rgba(17,26,46,.6); }}
      h1, h2, h3 {{ letter-spacing: -0.03em; }}
      h1 {{ font-weight: 800 !important; }}
      .block-container {{ padding-top: 1.6rem; max-width: 1400px; }}
      .topbar {{ display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:10px 18px;
                 padding: 16px 22px; border:1px solid {BORDER}; border-radius:18px; margin: 2px 0 16px;
                 background: linear-gradient(115deg, rgba(26,45,73,.98), rgba(16,26,46,.96) 58%, rgba(18,47,57,.9)); }}
      .brand {{ font-size: 22px; font-weight: 800; color: {TEXT}; letter-spacing: -.02em; }}
      .brand span {{ color: {ACCENT}; }}
      .eyebrow {{ font: 500 11px 'DM Mono', monospace; letter-spacing: .18em; color: {ACCENT}; text-transform: uppercase; }}
      .snapshot {{ color: {MUTED}; font: 11px 'DM Mono', monospace; }}
      .chip {{ display:inline-block; border: 1px solid #2f4a6e; background: #132037; border-radius: 8px; padding: 3px 9px; margin: 2px 4px 2px 0; color: {ACCENT}; font: 12px 'DM Mono', monospace; }}
      .section-kicker {{ color: {ACCENT}; font: 500 11px 'DM Mono', monospace; text-transform: uppercase; letter-spacing: .14em; margin: 0 0 6px; }}
      .soft-card {{ border: 1px solid {BORDER}; background: linear-gradient(145deg, {PANEL}, #0f1729); border-radius: 15px; padding: 16px 17px; height: 100%; box-shadow: 0 8px 24px rgba(0,0,0,.18); }}
      .soft-label {{ color: {MUTED}; font: 11px 'DM Mono', monospace; letter-spacing: .08em; text-transform: uppercase; }}
      .soft-value {{ color: {TEXT}; font-size: 25px; font-weight: 800; margin: 8px 0 6px; letter-spacing: -.04em; }}
      .soft-note {{ color: {MUTED}; font-size: 12px; line-height: 1.5; }}
      .kpi-pill {{ display: inline-block; border: 1px solid; border-radius: 99px; padding: 3px 10px; font-size: 12px; font-weight: 600; margin-top: 4px; }}
      .info-box {{ border-left: 3px solid {ACCENT}; background: rgba(84,225,193,.07); border-radius: 0 10px 10px 0; padding: 11px 14px; color: #D5E4F4; line-height: 1.6; font-size: 13px; }}
      .warning-box {{ border-left: 3px solid {GOLD}; background: rgba(255,198,109,.07); border-radius: 0 10px 10px 0; padding: 11px 14px; color: #F0E2C7; line-height: 1.6; font-size: 13px; }}
      .small-muted {{ color: {MUTED}; font-size: 12px; line-height: 1.55; }}
      .mono {{ font-family: 'DM Mono', monospace; }}
      .swot-head {{ border:1px solid {BORDER};border-radius:15px;padding:14px 18px;background:linear-gradient(145deg,{PANEL},#0F1729);margin-bottom:12px; }}
      .stTabs [data-baseweb="tab-list"] {{ gap: 7px; border-bottom: 1px solid {BORDER}; flex-wrap: wrap; }}
      .stTabs [data-baseweb="tab"] {{ background: rgba(17,26,46,.65); border: 1px solid transparent; border-radius: 10px 10px 0 0; padding: 10px 15px; color: {MUTED}; }}
      .stTabs [aria-selected="true"] {{ background: #172640 !important; border-color: {BORDER} !important; color: {ACCENT} !important; }}
      div[data-testid="stMetric"] {{ border: 1px solid {BORDER}; padding: 14px 15px; border-radius: 14px; background: linear-gradient(145deg, {PANEL}, #0F1729); }}
      div[data-testid="stMetricLabel"] p {{ color: {MUTED} !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: .06em; }}
      div[data-testid="stMetricValue"] {{ color: {TEXT}; font-weight: 800; }}
      .stButton > button, .stDownloadButton > button, .stLinkButton > a {{ border-radius: 10px; border: 1px solid #3C5977; background: #172640; color: {TEXT}; font-weight: 700; }}
      .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
      div[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 12px; overflow: hidden; }}
      .news-card {{ border: 1px solid {BORDER}; border-radius: 12px; padding: 12px 14px; margin-bottom: 10px;
                    background: linear-gradient(145deg, {PANEL}, #0F1729); }}
      .news-title {{ color: {TEXT}; font-weight: 700; font-size: 14px; line-height: 1.4; }}
      .news-meta {{ color: {MUTED}; font: 11px 'DM Mono', monospace; margin-top: 4px; }}
      .news-summary {{ color: #C5D4E9; font-size: 12.5px; line-height: 1.55; margin-top: 6px; }}
      .chart-note {{ color: {MUTED}; font-size: 12px; line-height: 1.5; margin: -4px 0 14px; }}
      .desc-card {{ border: 1px solid {BORDER}; border-left: 4px solid {ACCENT}; border-radius: 14px; padding: 18px 22px;
                    background: linear-gradient(145deg, {PANEL}, #0F1729); color: #DCE7F7;
                    font-size: 15.5px; line-height: 1.8; margin: 8px 0 18px; box-shadow: 0 10px 28px rgba(0,0,0,.22); }}
      hr {{ border-color: {BORDER}; }}
      footer {{ visibility: hidden; }}
      @media (max-width: 720px) {{
        .block-container {{ padding-left: .8rem; padding-right: .8rem; }}
        .topbar {{ padding: 12px 14px; }}
        .brand {{ font-size: 18px; }}
        .soft-value {{ font-size: 20px; }}
        .stTabs [data-baseweb="tab"] {{ padding: 8px 10px; font-size: 12px; }}
        .news-title {{ font-size: 13px; }}
        .desc-card {{ font-size: 14px; padding: 14px 16px; }}
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def as_float(value: Any) -> float:
    """Convert an optional Yahoo Finance value into a finite float or NaN."""
    try:
        if value is None:
            return float("nan")
        value = float(value)
        return value if np.isfinite(value) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def get_info_value(info: dict[str, Any], key: str) -> float:
    return as_float(info.get(key))


def pct_change_over(close: pd.Series, trading_days: int) -> float:
    close = close.dropna()
    if len(close) <= trading_days:
        return float("nan")
    start = as_float(close.iloc[-trading_days - 1])
    end = as_float(close.iloc[-1])
    if not np.isfinite(start) or start == 0 or not np.isfinite(end):
        return float("nan")
    return (end / start - 1.0) * 100.0


def fmt_pct(value: Any, decimals: int = 2) -> str:
    value = as_float(value)
    return "—" if not np.isfinite(value) else f"{value:,.{decimals}f}%"


def fmt_pct_signed(value: Any, decimals: int = 2) -> str:
    value = as_float(value)
    return "—" if not np.isfinite(value) else f"{value:+,.{decimals}f}%"


def fmt_num(value: Any, decimals: int = 2) -> str:
    value = as_float(value)
    return "—" if not np.isfinite(value) else f"{value:,.{decimals}f}"


def pretty_large(value: Any) -> str:
    value = as_float(value)
    if not np.isfinite(value):
        return "—"
    absolute = abs(value)
    if absolute >= 1e12:
        return f"{value / 1e12:,.2f} T"
    if absolute >= 1e9:
        return f"{value / 1e9:,.2f} B"
    if absolute >= 1e6:
        return f"{value / 1e6:,.2f} M"
    return f"{value:,.0f}"


def safe_name(info: dict[str, Any], ticker: str) -> str:
    return str(info.get("shortName") or info.get("longName") or ticker)


def tone_for_sign(value: Any) -> str:
    """Vráti 'up' pre kladnú hodnotu, 'down' pre zápornú a 'neutral' pre chýbajúcu."""
    value = as_float(value)
    if not np.isfinite(value):
        return "neutral"
    return "up" if value >= 0 else "down"


def chart_note(text: str) -> None:
    """Krátke vysvetlenie pod grafom: čo ukazuje a na čo si dať pozor."""
    st.markdown(f"<div class='chart-note'>ℹ️ {html.escape(text)}</div>", unsafe_allow_html=True)


KEY_FUNDAMENTALS = ["P/E (TTM)", "Zisková marža (%)", "ROE (%)", "Rast tržieb (%)", "Debt/Equity"]


def missing_note(df: pd.DataFrame) -> str | None:
    """Vysvetlí, ktoré fundamentálne údaje Yahoo pre dané tituly nemá."""
    lines: list[str] = []
    for _, row in df.iterrows():
        missing = [k for k in KEY_FUNDAMENTALS if not np.isfinite(as_float(row.get(k)))]
        if missing:
            lines.append(f"{row['Ticker']}: chýba {', '.join(missing)}")
    if not lines:
        return None
    return (
        "Yahoo Finance pre niektoré tituly nemá všetky údaje. Je to bežné pri ETF, menších a zahraničných firmách "
        "a nejde o chybu aplikácie. Pomlčka znamená chýbajúci údaj, nie nulu. "
        + "; ".join(lines) + "."
    )


def make_plotly_dark(fig: go.Figure, height: int = 430) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Manrope, sans-serif"),
        height=height,
        margin=dict(l=12, r=12, t=60, b=80),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
        hoverlabel=dict(bgcolor=PANEL_2, font_color=TEXT),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=BORDER, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor="rgba(130,155,190,.13)", zeroline=False, linecolor=BORDER, tickfont=dict(color=MUTED))
    return fig


def metric_card(label: str, value: str, note: str) -> None:
    st.markdown(
        f"<div class='soft-card'><div class='soft-label'>{label}</div><div class='soft-value'>{value}</div><div class='soft-note'>{note}</div></div>",
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, note: str, tone: str = "neutral") -> None:
    """Karta s farebnou šípkou: zelená hore, červená dole, sivá bez šípky."""
    palette = {"up": ACCENT, "down": RED, "neutral": MUTED}
    arrows = {"up": "↑", "down": "↓", "neutral": "•"}
    color = palette.get(tone, MUTED)
    value_color = TEXT if tone == "neutral" else color
    st.markdown(
        f"""<div class='soft-card'>
          <div class='soft-label'>{label}</div>
          <div class='soft-value' style='color:{value_color}'>{value}</div>
          <span class='kpi-pill' style='color:{color};border-color:{color}88;background:{color}1A'>{arrows[tone]} {note}</span>
        </div>""",
        unsafe_allow_html=True,
    )


# Curated examples across the 11 main equity sectors, plus common broad-market ETFs.
# This is a starter universe, not an exhaustive list. ANY Yahoo Finance ticker can be added.
SECTOR_TICKERS = {
    "Information Technology": ["AAPL", "MSFT", "NVDA", "AMD", "AVGO", "ORCL", "CRM", "ADBE", "IBM", "NOW", "QCOM", "INTC", "MU", "CSCO", "TXN", "AMAT", "LRCX", "TSM", "ASML", "SAP.DE", "PLTR", "SHOP"],
    "Communication Services": ["GOOGL", "GOOG", "META", "NFLX", "DIS", "TMUS", "VZ", "T", "CHTR", "CMCSA", "SPOT", "TTD"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "BKNG", "TJX", "LULU", "MELI"],
    "Consumer Staples": ["COST", "WMT", "KO", "PEP", "PG", "CL", "KHC", "MDLZ", "EL", "KDP", "MO", "PM"],
    "Health Care": ["LLY", "NVO", "JNJ", "ABBV", "MRK", "PFE", "UNH", "ISRG", "ABT", "TMO", "DHR", "AMGN", "GILD", "BSX"],
    "Financials": ["JPM", "V", "MA", "BAC", "GS", "BRK-B", "MS", "C", "WFC", "AXP", "BLK", "SCHW", "PGR", "CB", "PYPL", "COIN"],
    "Industrials": ["CAT", "GE", "HON", "RTX", "LMT", "BA", "DE", "UPS", "FDX", "UNP", "ETN", "CMI", "PH", "WM", "CARR", "VRT", "UBER"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "OXY", "ENPH", "FSLR"],
    "Materials": ["LIN", "SHW", "APD", "FCX", "NEM", "NUE", "ECL", "DOW", "CTVA"],
    "Utilities": ["NEE", "SO", "DUK", "CEG", "VST", "XEL", "AEP", "EXC", "ETR"],
    "Real Estate": ["PLD", "AMT", "EQIX", "O", "SPG", "WELL", "PSA", "CCI", "VICI", "AVB"],
    "ETF & Indexy": ["SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "VT", "VWCE.DE", "CSPX.L", "EQQQ.DE", "^GSPC", "^IXIC", "^STOXX50E", "^FTSE"],
}
TICKER_TO_SECTOR = {
    ticker: sector
    for sector, sector_tickers in SECTOR_TICKERS.items()
    for ticker in sector_tickers
}
YAHOO_SECTOR_ALIASES = {
    "Technology": "Information Technology",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Financial Services": "Financials",
    "Healthcare": "Health Care",
    "Basic Materials": "Materials",
}

# Burzové prípony Yahoo Finance. Používajú sa, keď používateľ zadá holý symbol
# (napr. SAP alebo SIE), ktorý sa na Yahoo nenašiel.
EXCHANGE_SUFFIXES = [
    ".DE", ".AS", ".PA", ".L", ".MI", ".MC", ".SW", ".ST", ".OL", ".CO",
    ".HE", ".BR", ".VI", ".LS", ".WA", ".PR", ".KS", ".T", ".HK", ".TO", ".AX",
]


def canonical_sector(raw_sector: Any, ticker: str = "") -> str:
    raw = str(raw_sector or "").strip()
    if raw and raw.lower() not in {"unknown", "none", "nan", "n/a"}:
        return YAHOO_SECTOR_ALIASES.get(raw, raw)
    return TICKER_TO_SECTOR.get(ticker, "Neznámy")


def parse_symbols(raw: str) -> list[str]:
    """Split user input by comma, semicolon, space or newline; normalise to Yahoo symbols."""
    cleaned = re.sub(r"[;\s]+", ",", raw.replace("\n", ","))
    symbols = [s.strip().upper() for s in cleaned.split(",") if s.strip()]
    return list(dict.fromkeys(symbols))


def _has_history(ticker: str) -> bool:
    """Plain (necachovaná) kontrola, či Yahoo vracia cenovú históriu pre symbol."""
    try:
        hist = yf.Ticker(ticker).history(period="5d", interval="1d", auto_adjust=True, actions=False)
        return hist is not None and not hist.empty and "Close" in hist.columns
    except Exception:
        return False


@st.cache_data(ttl=3600, show_spinner=False)
def resolve_symbol(symbol: str) -> str | None:
    """Vráti prvý symbol, ktorý má cenovú históriu.

    Najprv sa skúsi zadaný symbol. Ak nemá dáta a nemá príponu, skúsia sa burzové prípony
    paralelne. Holý symbol môže existovať aj v USA (napr. SAP ako ADR), preto na presnú
    európsku burzu použi príponu, napr. SAP.DE.
    """
    symbol = symbol.strip().upper()
    if not symbol:
        return None
    if _has_history(symbol):
        return symbol
    if any(marker in symbol for marker in (".", "^", "=")):
        return None
    candidates = [symbol + suffix for suffix in EXCHANGE_SUFFIXES]
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(_has_history, candidates))
    for candidate, ok in zip(candidates, results):
        if ok:
            return candidate
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def search_yahoo(query: str) -> list[dict[str, str]]:
    """Vyhľadá firmy a ETF na Yahoo Finance podľa názvu alebo symbolu."""
    try:
        quotes = yf.Search(query, max_results=8).quotes or []
    except Exception:
        return []
    results: list[dict[str, str]] = []
    for quote in quotes:
        symbol = quote.get("symbol")
        if not symbol:
            continue
        results.append({
            "symbol": symbol,
            "name": quote.get("shortname") or quote.get("longname") or symbol,
            "exchange": quote.get("exchDisp") or quote.get("exchange") or "",
        })
    return results


# -----------------------------------------------------------------------------
# Market data: parallel fetch, currency conversion, timeouts
# -----------------------------------------------------------------------------
def _fetch_one(ticker: str, period: str) -> dict[str, Any]:
    """Stiahne históriu a informácie pre jeden ticker. Beží vo vlákne, preto nevolá st.*."""
    item: dict[str, Any] = {
        "ticker": ticker, "error": None, "info_error": False,
        "close": None, "high": None, "low": None, "info": {},
    }
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period=period, interval="1d", auto_adjust=True, actions=False)
    except Exception as exc:
        item["error"] = f"chyba pri načítaní ({type(exc).__name__})."
        return item
    if history is None or history.empty or "Close" not in history.columns:
        item["error"] = "Yahoo Finance nevrátil historické ceny."
        return item
    history = history.copy()
    if isinstance(history.index, pd.DatetimeIndex) and history.index.tz is not None:
        history.index = history.index.tz_localize(None)
    history = history[~history.index.duplicated(keep="last")].sort_index()
    close = pd.to_numeric(history["Close"], errors="coerce").dropna()
    if close.empty:
        item["error"] = "chýbajú použiteľné zatváracie ceny."
        return item
    item["close"] = close
    if "High" in history:
        item["high"] = pd.to_numeric(history["High"], errors="coerce")
    if "Low" in history:
        item["low"] = pd.to_numeric(history["Low"], errors="coerce")
    try:
        raw_info = stock.get_info()
        item["info"] = raw_info if isinstance(raw_info, dict) else {}
    except Exception:
        item["info_error"] = True
    return item


@st.cache_data(ttl=1800, show_spinner=False)
def load_fx_series(currency: str, base: str, period: str) -> pd.Series | None:
    """Denný kurz z meny `currency` do `base` (napr. USDEUR=X). Vracia None, ak sa nepodarí."""
    if currency == base:
        return None
    try:
        hist = yf.Ticker(f"{currency}{base}=X").history(period=period, interval="1d", auto_adjust=True, actions=False)
    except Exception:
        return None
    if hist is None or hist.empty or "Close" not in hist.columns:
        return None
    series = pd.to_numeric(hist["Close"], errors="coerce").dropna()
    if isinstance(series.index, pd.DatetimeIndex) and series.index.tz is not None:
        series.index = series.index.tz_localize(None)
    series = series[~series.index.duplicated(keep="last")].sort_index()
    return series if not series.empty else None


@st.cache_data(ttl=1800, show_spinner=False)
def load_market_data(tickers: tuple[str, ...], period: str, refresh_key: str, base: str):
    # `refresh_key` is deliberately part of the cache key. The refresh button changes it,
    # so the app fetches a fresh snapshot instead of reusing an older cached response.
    _ = refresh_key
    errors: list[str] = []
    raw: dict[str, dict[str, Any]] = {}

    executor = ThreadPoolExecutor(max_workers=min(8, max(1, len(tickers))))
    futures = {executor.submit(_fetch_one, ticker, period): ticker for ticker in tickers}
    try:
        for future in as_completed(futures, timeout=FETCH_TIMEOUT):
            ticker = futures[future]
            try:
                raw[ticker] = future.result()
            except Exception as exc:
                raw[ticker] = {"ticker": ticker, "error": f"chyba ({type(exc).__name__}).",
                               "info_error": False, "close": None, "high": None, "low": None, "info": {}}
    except FuturesTimeoutError:
        errors.append(f"Načítanie trvalo dlhšie ako {FETCH_TIMEOUT} s. Skús tlačidlo „Skúsiť načítať znova“.")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    closes: dict[str, pd.Series] = {}
    highs: dict[str, pd.Series] = {}
    lows: dict[str, pd.Series] = {}
    infos: dict[str, dict[str, Any]] = {}

    for ticker in tickers:
        item = raw.get(ticker)
        if item is None:
            infos[ticker] = {}
            errors.append(f"{ticker}: nestihol sa načítať.")
            continue
        if item["error"]:
            infos[ticker] = {}
            errors.append(f"{ticker}: {item['error']}")
            continue
        if item["info_error"]:
            errors.append(f"{ticker}: ceny sú načítané, no fundamentálne údaje nie sú dostupné.")

        info = dict(item["info"] or {})
        currency = str(info.get("currency") or "USD")
        scale = 1.0
        if currency == "GBp":  # britské ceny v pencoch
            currency, scale = "GBP", 0.01

        close = item["close"] * scale
        high = item["high"] * scale if item["high"] is not None else None
        low = item["low"] * scale if item["low"] is not None else None
        fx_last = 1.0
        price_currency = currency

        if currency != base:
            rate_series = load_fx_series(currency, base, period)
            if rate_series is None:
                errors.append(f"{ticker}: kurz {currency}/{base} sa nepodarilo načítať, ceny ostávajú v {currency}.")
            else:
                rate = rate_series.reindex(close.index, method="ffill").bfill()
                if rate.notna().any():
                    close = close * rate
                    if high is not None:
                        high = high.reindex(close.index) * rate
                    if low is not None:
                        low = low.reindex(close.index) * rate
                    fx_last = float(rate_series.dropna().iloc[-1])
                    price_currency = base

        info["_fx_last"] = fx_last
        info["_scale"] = scale
        info["_price_currency"] = price_currency
        infos[ticker] = info

        closes[ticker] = close.rename(ticker)
        if high is not None:
            highs[ticker] = high.rename(ticker)
        if low is not None:
            lows[ticker] = low.rename(ticker)

    def _stack(series_map: dict[str, pd.Series]) -> pd.DataFrame:
        return pd.concat(series_map.values(), axis=1).sort_index() if series_map else pd.DataFrame()

    fetched_at = pd.Timestamp.now(tz="Europe/Prague").strftime("%d.%m.%Y %H:%M:%S")
    return _stack(closes), _stack(highs), _stack(lows), pd.DataFrame(), infos, errors, fetched_at


def refresh_data() -> None:
    """Callback: vymaže cache a vynúti nové načítanie."""
    load_market_data.clear()
    st.session_state["_market_data_refresh_key"] = uuid.uuid4().hex


# -----------------------------------------------------------------------------
# Company news: fetch only the tickers currently selected by the user.
# -----------------------------------------------------------------------------
def clean_rss_text(value: Any, limit: int = 600) -> str:
    raw = html.unescape(str(value or ""))
    raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw[:limit].rstrip()


def parse_news_rss(url: str, ticker: str, fallback_source: str) -> list[dict[str, Any]]:
    """Read an RSS feed and normalise article metadata; never download article bodies."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=7) as response:
        payload = response.read(2_500_000)
    root = ET.fromstring(payload)
    found: list[dict[str, Any]] = []
    for item in root.findall(".//item")[:12]:
        title = clean_rss_text(item.findtext("title", ""), limit=300)
        link = (item.findtext("link", "") or "").strip()
        if not (link.startswith("https://") or link.startswith("http://")):
            continue
        description = clean_rss_text(item.findtext("description", ""), limit=800)
        source_element = item.find("source")
        publisher = clean_rss_text(source_element.text if source_element is not None else "", limit=100) or fallback_source
        raw_date = (item.findtext("pubDate", "") or "").strip()
        published_epoch = 0.0
        published_display = "Dátum neuvedený"
        published_iso = ""
        if raw_date:
            try:
                parsed = parsedate_to_datetime(raw_date)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                published_epoch = float(parsed.timestamp())
                local_time = pd.Timestamp(parsed).tz_convert("Europe/Prague")
                published_display = local_time.strftime("%d.%m.%Y %H:%M")
                published_iso = local_time.isoformat()
            except Exception:
                pass
        if title:
            found.append({
                "Ticker": ticker,
                "Title": title,
                "Summary": description,
                "URL": link,
                "Publisher": publisher,
                "Published display": published_display,
                "Published ISO": published_iso,
                "Published epoch": published_epoch,
                "Feed": fallback_source,
            })
    cutoff_epoch = pd.Timestamp.now(tz="UTC").timestamp() - 14 * 24 * 60 * 60
    found = [
        story for story in found
        if not story.get("Published epoch") or story["Published epoch"] >= cutoff_epoch
    ]
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for story in found:
        if story["URL"] not in seen:
            seen.add(story["URL"])
            unique.append(story)
    return unique


@st.cache_data(ttl=900, show_spinner=False)
def fetch_ticker_news(ticker: str, company_name: str, refresh_key: str) -> tuple[list[dict[str, Any]], str]:
    """Fetch up-to-date headlines for one selected symbol; 15-minute cache per ticker."""
    _ = refresh_key
    encoded_ticker = urllib.parse.quote(ticker, safe="")
    yahoo_url = (
        "https://feeds.finance.yahoo.com/rss/2.0/headline"
        f"?s={encoded_ticker}&region=US&lang=en-US"
    )
    try:
        yahoo_stories = parse_news_rss(yahoo_url, ticker, "Yahoo Finance")
        if yahoo_stories:
            return yahoo_stories[:8], "Yahoo Finance"
    except Exception:
        pass

    search_subject = f'"{company_name}" {ticker} stock when:7d'
    google_url = (
        "https://news.google.com/rss/search?q=" + urllib.parse.quote(search_subject)
        + "&hl=en-US&gl=US&ceid=US:en"
    )
    try:
        google_stories = parse_news_rss(google_url, ticker, "Google News")
        return google_stories[:8], ("Google News" if google_stories else "Bez dostupných správ")
    except Exception:
        return [], "News feed nedostupný"


def classify_news_signal(story: dict[str, Any]) -> tuple[str, str] | None:
    """Conservative keyword-based SWOT tagging of headline + RSS snippet (heuristic only)."""
    source_text = f"{story.get('Title', '')} {story.get('Summary', '')}".casefold()
    if not source_text.strip():
        return None

    rules: list[tuple[str, tuple[str, ...], str]] = [
        ("Hrozby", (
            "lawsuit", "antitrust", "investigation", "regulator", "regulatory", "recall",
            "data breach", "cyberattack", "fraud", "fine", "sanction", "tariff", "export ban",
            "export control", "downgrade", "probe", "cuts outlook", "cuts forecast", "cuts guidance",
            "weak demand", "court ruling", "security incident", "žaloba", "vyšetrovanie", "pokuta",
        ), "Titulok alebo krátky popis obsahuje výraz spájaný s právnym, regulačným alebo externým rizikom. Je to signál na preverenie, nie potvrdenie dopadu na firmu."),
        ("Slabé stránky", (
            "misses estimates", "missed estimates", "earnings miss", "revenue miss", "loss widens",
            "net loss", "layoffs", "layoff", "job cuts", "declining revenue", "revenue falls",
            "profit falls", "margin pressure", "slump", "slows down", "cuts jobs", "stock falls",
            "shares fall", "shares drop", "stock slides", "stock tumbles", "plunges", "klesajúce tržby",
            "pokles zisku", "prepúšťanie",
        ), "Mediálny text naznačuje slabšie výsledky alebo prevádzkový tlak. Treba overiť čísla, príčinu a to, či ide o jednorazový alebo dlhodobý problém."),
        ("Silné stránky", (
            "beats estimates", "beat estimates", "earnings beat", "profit rises", "revenue rises",
            "raises dividend", "share buyback", "strong results", "record profit", "record earnings",
            "record revenue", "raises guidance", "raises outlook", "raises forecast", "stock gains",
            "stock jumps", "stock rallies", "shares rise", "shares surge", "strong demand", "zvýšenie zisku",
        ), "Titulok naznačuje pozitívnu správu o výsledkoch alebo kapitálovej politike. Over, či ide o prekvapenie oproti očakávaniam a či už trh správu nezohľadnil v cene."),
        ("Príležitosti", (
            "partnership", "contract win", "wins contract", "wins deal", "approval", "product launch",
            "launches", "expansion", "acquisition", "acquires", "new product", "new market",
            "investment in", "orders surge", "demand growth", "strategic deal", "partnerstvo",
            "schválenie", "nový kontrakt",
        ), "Titulok môže signalizovať nový produkt, kontrakt, partnerstvo alebo trhovú príležitosť. Samotná správa nepotvrdzuje budúce tržby ani zisk."),
    ]
    for quadrant, keywords, rationale in rules:
        matched = next((word for word in keywords if word in source_text), None)
        if matched:
            return quadrant, rationale
    return None


def build_stock_metrics(
    tickers: list[str],
    prices: pd.DataFrame,
    highs: pd.DataFrame,
    lows: pd.DataFrame,
    volumes: pd.DataFrame,
    infos: dict[str, dict[str, Any]],
    benchmark_returns: pd.Series | None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for ticker in tickers:
        if ticker not in prices.columns:
            continue
        close = prices[ticker].dropna()
        if close.empty:
            continue
        current_price = as_float(close.iloc[-1])
        info = infos.get(ticker, {})
        daily_ret = close.pct_change(fill_method=None).dropna()
        annual_vol = float(daily_ret.std(ddof=1) * np.sqrt(252) * 100) if len(daily_ret) > 1 else np.nan

        high = highs[ticker].reindex(close.index) if ticker in highs.columns else close
        low = lows[ticker].reindex(close.index) if ticker in lows.columns else close
        prev_close = close.shift(1)
        tr = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
        ).max(axis=1, skipna=True)
        atr14 = as_float(tr.rolling(14, min_periods=14).mean().iloc[-1]) if len(tr) >= 14 else np.nan

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
        loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.mask((loss == 0) & (gain > 0), 100)
        rsi = rsi.mask((loss == 0) & (gain == 0), 50)
        current_rsi = as_float(rsi.iloc[-1]) if not rsi.empty else np.nan

        sma20 = as_float(close.rolling(20, min_periods=20).mean().iloc[-1]) if len(close) >= 20 else np.nan
        sma50 = as_float(close.rolling(50, min_periods=50).mean().iloc[-1]) if len(close) >= 50 else np.nan
        sma200 = as_float(close.rolling(200, min_periods=200).mean().iloc[-1]) if len(close) >= 200 else np.nan
        ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = as_float((macd_line - macd_signal).iloc[-1])

        rolling_year = close.tail(252)
        low_52w = as_float(rolling_year.min())
        high_52w = as_float(rolling_year.max())
        dd_series = close / close.cummax() - 1
        max_dd = as_float(dd_series.min() * 100)

        ret_1d = as_float(daily_ret.iloc[-1] * 100) if len(daily_ret) else np.nan
        ret_1m = pct_change_over(close, 21)
        ret_3m = pct_change_over(close, 63)
        ret_6m = pct_change_over(close, 126)
        ret_1y = pct_change_over(close, 252)

        beta = np.nan
        if benchmark_returns is not None and not benchmark_returns.empty:
            pair = pd.concat([daily_ret.rename("stock"), benchmark_returns.rename("benchmark")], axis=1).dropna()
            if len(pair) >= 30 and pair["benchmark"].var(ddof=1) > 0:
                beta = as_float(pair["stock"].cov(pair["benchmark"]) / pair["benchmark"].var(ddof=1))

        components: list[tuple[bool | None, int]] = [
            ((ret_3m > 0) if np.isfinite(ret_3m) else None, 25),
            ((ret_6m > 0) if np.isfinite(ret_6m) else None, 15),
            ((current_price > sma50) if np.isfinite(sma50) else None, 20),
            ((sma50 > sma200) if np.isfinite(sma50) and np.isfinite(sma200) else None, 20),
            ((50 <= current_rsi <= 70) if np.isfinite(current_rsi) else None, 20),
        ]
        available = sum(points for passed, points in components if passed is not None)
        earned = sum(points for passed, points in components if passed is True)
        tech_score = (earned / available * 100) if available else np.nan
        if np.isfinite(tech_score):
            signal = "Silnejšie signály" if tech_score >= 70 else ("Zmiešané signály" if tech_score >= 45 else "Slabšie signály")
        else:
            signal = "Málo dát"

        # Fundamenty z Yahoo sú v pôvodnej mene; kapitalizáciu a cieľovú cenu prepočítame rovnakým kurzom ako ceny.
        fx = as_float(info.get("_fx_last"))
        fx = fx if np.isfinite(fx) else 1.0
        scale = as_float(info.get("_scale"))
        scale = scale if np.isfinite(scale) else 1.0
        market_cap = get_info_value(info, "marketCap") * fx
        dividend_yield = get_info_value(info, "dividendYield")
        target_price = get_info_value(info, "targetMeanPrice") * fx * scale
        rows.append(
            {
                "Ticker": ticker,
                "Spoločnosť": safe_name(info, ticker),
                "Sektor": canonical_sector(info.get("sector"), ticker),
                "Odvetvie": info.get("industry") or "—",
                "Mena": info.get("_price_currency") or "USD",
                "Burza": info.get("exchange") or info.get("fullExchangeName") or "—",
                "Cena": current_price,
                "1D (%)": ret_1d,
                "1M (%)": ret_1m,
                "3M (%)": ret_3m,
                "6M (%)": ret_6m,
                "1Y (%)": ret_1y,
                "Volatilita (%)": annual_vol,
                "Max. prepad (%)": max_dd,
                "RSI (14)": current_rsi,
                "SMA 20": sma20,
                "SMA 50": sma50,
                "SMA 200": sma200,
                "MACD histogram": macd_hist,
                "ATR (14)": atr14,
                "52W minimum": low_52w,
                "52W maximum": high_52w,
                "Technické skóre": tech_score,
                "Technické signály": signal,
                "Beta vs. benchmark": beta,
                "Trhová kapitalizácia": market_cap,
                "P/E (TTM)": get_info_value(info, "trailingPE"),
                "Forward P/E": get_info_value(info, "forwardPE"),
                "P/B": get_info_value(info, "priceToBook"),
                "EV/EBITDA": get_info_value(info, "enterpriseToEbitda"),
                "Zisková marža (%)": get_info_value(info, "profitMargins") * 100,
                "ROE (%)": get_info_value(info, "returnOnEquity") * 100,
                "Rast tržieb (%)": get_info_value(info, "revenueGrowth") * 100,
                "Rast zisku (%)": get_info_value(info, "earningsGrowth") * 100,
                "Debt/Equity": get_info_value(info, "debtToEquity"),
                "Dividendový výnos (%)": dividend_yield * 100 if np.isfinite(dividend_yield) else np.nan,
                "EBITDA": get_info_value(info, "ebitda"),
                "Čistý zisk": get_info_value(info, "netIncomeToCommon"),
                "Tržby": get_info_value(info, "totalRevenue"),
                "EPS": get_info_value(info, "trailingEps"),
                "Analytický cieľ": target_price,
                "Počet analytikov": get_info_value(info, "numberOfAnalystOpinions"),
                "Potenciál k cieľu (%)": ((target_price / current_price - 1) * 100
                                             if current_price > 0 and np.isfinite(target_price) else np.nan),
            }
        )

    return pd.DataFrame(rows)


def build_swot(ticker: str, metrics: pd.DataFrame, infos: dict[str, dict[str, Any]]) -> dict[str, list[tuple[str, str]]]:
    """Create a rule-based SWOT from currently available Yahoo metrics (screening aid only)."""
    matched = metrics.loc[metrics["Ticker"] == ticker]
    if matched.empty:
        return {"Silné stránky": [], "Slabé stránky": [], "Príležitosti": [], "Hrozby": []}
    row = matched.iloc[0]
    sector = str(row.get("Sektor", "Neznámy"))
    financial_sector = sector == "Financials"

    def n(key: str) -> float:
        return as_float(row.get(key))

    strengths: list[tuple[str, str]] = []
    weaknesses: list[tuple[str, str]] = []
    opportunities: list[tuple[str, str]] = []
    threats: list[tuple[str, str]] = []

    margin, roe = n("Zisková marža (%)"), n("ROE (%)")
    sales_growth, earnings_growth = n("Rast tržieb (%)"), n("Rast zisku (%)")
    debt_equity, volatility = n("Debt/Equity"), n("Volatilita (%)")
    ret_1m, ret_3m, ret_6m, ret_1y = n("1M (%)"), n("3M (%)"), n("6M (%)"), n("1Y (%)")
    current_price, sma50, sma200 = n("Cena"), n("SMA 50"), n("SMA 200")
    rsi, max_dd, pe, forward_pe = n("RSI (14)"), n("Max. prepad (%)"), n("P/E (TTM)"), n("Forward P/E")
    dividend_yield = n("Dividendový výnos (%)")
    target_upside, analyst_count = n("Potenciál k cieľu (%)"), n("Počet analytikov")

    if np.isfinite(margin) and margin >= 15:
        strengths.append(("Vysoká zisková marža", f"Marža približne {margin:.2f} % naznačuje, že firma si z tržieb ponecháva významnú časť ako zisk. Porovnávaj ju s firmami v rovnakom odvetví."))
    elif np.isfinite(margin) and 0 < margin < 15:
        strengths.append(("Firma je zisková", f"Dostupná čistá marža je kladná ({margin:.2f} %), hoci jej kvalitu treba hodnotiť voči odvetvovým konkurentom."))
    if np.isfinite(roe) and roe >= 15:
        strengths.append(("Silná návratnosť vlastného imania", f"ROE je približne {roe:.2f} %. Môže to signalizovať účinné využívanie vlastného imania; pri vysokom dlhu alebo zápornom imaní môže byť ukazovateľ skreslený."))
    if np.isfinite(sales_growth) and sales_growth >= 10:
        strengths.append(("Rast tržieb", f"Yahoo Finance uvádza rast tržieb približne {sales_growth:.2f} %. Je to pozitívny signál dopytu, nie automaticky rastu budúceho zisku."))
    if np.isfinite(earnings_growth) and earnings_growth >= 10:
        strengths.append(("Rast zisku", f"Dostupný ukazovateľ rastu zisku je {earnings_growth:.2f} %. Skontroluj, či rast nie je spôsobený nízkou porovnávacou základňou alebo jednorazovou položkou."))
    if np.isfinite(ret_1y) and ret_1y > 10 and np.isfinite(current_price) and np.isfinite(sma200) and current_price > sma200:
        strengths.append(("Dlhodobejšie cenové momentum", f"Cena za posledný rok vzrástla o {ret_1y:.2f} % a je nad SMA 200. Ide o historický trendový signál, nie záruku pokračovania."))
    if not financial_sector and np.isfinite(debt_equity) and 0 <= debt_equity <= 60:
        strengths.append(("Relatívne nízky pomer dlhu k imaniu", f"Debt/Equity je približne {debt_equity:.2f}. Pomer a jeho definícia sa medzi sektormi líšia; tento prah je iba orientačný."))
    if np.isfinite(dividend_yield) and dividend_yield >= 2.5:
        strengths.append(("Dividendový výnos", f"Uvedený dividendový výnos je {dividend_yield:.2f} %. Výplata ani súčasná výška dividendy nie sú garantované."))

    if np.isfinite(margin) and margin < 0:
        weaknesses.append(("Záporná čistá marža", f"Dostupná čistá marža je {margin:.2f} %, čo signalizuje čistú stratu v sledovanom období."))
    elif np.isfinite(margin) and 0 <= margin < 5:
        weaknesses.append(("Nízka čistá marža", f"Marža je len {margin:.2f} %. Menší pokles tržieb alebo rast nákladov tak môže citeľnejšie zasiahnuť zisk; závisí to od odvetvia."))
    if np.isfinite(sales_growth) and sales_growth < 0:
        weaknesses.append(("Klesajúce tržby", f"Dostupný medziročný rast tržieb je {sales_growth:.2f} %. Skontroluj, či ide o dočasný výkyv alebo dlhodobejší problém."))
    if np.isfinite(earnings_growth) and earnings_growth < -5:
        weaknesses.append(("Pokles zisku", f"Dostupný rast zisku je {earnings_growth:.2f} %. Môže ísť o prevádzkový tlak, vyššie náklady alebo porovnávací efekt."))
    if np.isfinite(current_price) and np.isfinite(sma200) and current_price < sma200 and np.isfinite(ret_3m) and ret_3m < 0:
        weaknesses.append(("Slabší strednodobý technický trend", "Cena je pod SMA 200 a trojmesačný výnos je záporný. To opisuje historický vývoj, nie hodnotu firmy ako takej."))
    if not financial_sector and np.isfinite(debt_equity) and debt_equity > 150:
        weaknesses.append(("Vyšší pomer dlhu k vlastnému imaniu", f"Debt/Equity je približne {debt_equity:.2f}. Vysoká zadlženosť môže zvýšiť citlivosť na úrokové sadzby a pokles cash flow."))
    if np.isfinite(max_dd) and max_dd <= -35:
        weaknesses.append(("Veľký historický prepad", f"Maximálny prepad v načítanom cenovom období dosiahol {max_dd:.2f} %. Ukazuje, aký prudký pokles sa už v danom období stal."))

    if np.isfinite(target_upside) and target_upside >= 10:
        analyst_text = f"; počet analytikov v zdroji: {int(analyst_count)}" if np.isfinite(analyst_count) and analyst_count >= 0 else ""
        opportunities.append(("Priestor voči priemernému analytickému cieľu", f"Priemerný cenový cieľ je približne o {target_upside:.2f} % nad poslednou cenou{analyst_text}. Ide o konsenzus odhadov, nie spoľahlivú predpoveď."))
    if np.isfinite(sales_growth) and sales_growth >= 10 and (not np.isfinite(margin) or margin >= 0):
        opportunities.append(("Pokračovanie rastu tržieb", f"Tržby rastú o {sales_growth:.2f} %. Ďalšou vecou na sledovanie je, či firma dokáže rast premeniť na udržateľný zisk a cash flow."))
    if np.isfinite(pe) and np.isfinite(forward_pe) and pe > 0 and forward_pe > 0 and forward_pe < pe:
        opportunities.append(("Očakávaný budúci zisk v ocenení", f"Forward P/E ({forward_pe:.2f}) je nižšie než trailing P/E ({pe:.2f}), čo môže odrážať očakávaný rast zisku. Forward odhady sa môžu nenaplniť."))
    if np.isfinite(current_price) and np.isfinite(sma50) and np.isfinite(sma200) and sma50 < current_price < sma200:
        opportunities.append(("Možný krátkodobý obrat trendu", "Cena je nad SMA 50, ale stále pod SMA 200. Môže ísť o fázu zotavenia; na potvrdenie treba ďalšie dáta a kontext."))
    if np.isfinite(ret_1m) and np.isfinite(ret_3m) and ret_1m > 0 and ret_3m < 0:
        opportunities.append(("Zlepšenie krátkodobého momenta", f"Mesačný výnos je {ret_1m:.2f} %, zatiaľ čo trojmesačný zostáva {ret_3m:.2f} %. Môže ísť o začiatok zotavenia alebo iba krátky odraz."))

    if np.isfinite(volatility) and volatility >= 40:
        threats.append(("Vysoká volatilita", f"Ročná historická volatilita je {volatility:.2f} %. Hodnota investície môže výrazne kolísať oboma smermi."))
    if np.isfinite(max_dd) and max_dd <= -25:
        threats.append(("Riziko výrazného prepadu", f"V načítanom cenovom období bol pozorovaný maximálny prepad {max_dd:.2f} %. Historický prepad nie je maximálnou možnou budúcou stratou."))
    if np.isfinite(ret_3m) and ret_3m <= -10:
        threats.append(("Negatívne trojmesačné momentum", f"Trojmesačný výnos je {ret_3m:.2f} %. Trend môže odrážať zhoršené očakávania, ale aj dočasnú korekciu."))
    if np.isfinite(pe) and pe >= 35:
        threats.append(("Citlivosť na vysoké ocenenie", f"P/E (TTM) je približne {pe:.2f}. Pri vysokom ocenení môže byť cena citlivá na sklamanie v raste; primeranosť treba porovnať s podobnými firmami."))
    if not financial_sector and np.isfinite(debt_equity) and debt_equity > 150:
        threats.append(("Úrokové a refinančné riziko", f"Debt/Equity je približne {debt_equity:.2f}. Vysoký dlh môže zvýšiť náklady na financovanie a znížiť flexibilitu."))
    if np.isfinite(rsi) and rsi >= 70:
        threats.append(("Silno natiahnutý krátkodobý pohyb", f"RSI je {rsi:.2f}, čo sa často označuje ako prekúpené pásmo. Samo osebe to neznamená, že cena musí klesnúť."))
    if np.isfinite(earnings_growth) and earnings_growth < -10:
        threats.append(("Riziko pokračujúceho tlaku na zisk", f"Dostupný rast zisku je {earnings_growth:.2f} %. Over, či sa tlak premieta aj do cash flow a výhľadu firmy."))

    fallbacks = {
        "Silné stránky": (strengths, "Žiadny jednoduchý prah v dostupných údajoch sa nespustil. Neznamená to, že firma nemá silné stránky; prever aj výkazy a konkurenčnú pozíciu."),
        "Slabé stránky": (weaknesses, "Dostupné metriky neukázali jasný varovný signál podľa nastavených prahov. Skontroluj aj kvalitu cash flow a detailné výkazy."),
        "Príležitosti": (opportunities, "Z dostupných ukazovateľov sa nedá spoľahlivo pomenovať konkrétna príležitosť. Na to treba preskúmať stratégiu, trh, katalyzátory a aktuálne správy."),
        "Hrozby": (threats, "Žiadny z nastavených rizikových prahov sa nespustil. To neznamená, že neexistujú regulačné, konkurenčné alebo makroekonomické hrozby."),
    }
    result: dict[str, list[tuple[str, str]]] = {}
    for title, (items, fallback) in fallbacks.items():
        result[title] = items[:5] if items else [("Nedostatok zjavného signálu", fallback)]
    return result


def explain_score() -> None:
    st.markdown(
        """<div class='info-box'><b>Ako sa počíta technické skóre?</b><br>
        Je to transparentný indikátorový súčet, nie predpoveď budúcej ceny ani odporúčanie kúpiť/predať. Model sleduje kladný 3- a 6-mesačný výnos, cenu nad SMA 50, SMA 50 nad SMA 200 a RSI v pásme 50–70. Každá dostupná zložka má svoju váhu; ak pre niektorú zložku chýbajú historické dáta, skóre sa prepočíta len z dostupných zložiek.</div>""",
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# Session state and callbacks
# -----------------------------------------------------------------------------
DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMD", "TSM", "AVGO", "ORCL", "UBER", "PLTR", "JPM", "V", "COST"]
TICKER_UNIVERSE = list(dict.fromkeys(
    [ticker for sector_tickers in SECTOR_TICKERS.values() for ticker in sector_tickers]
    + DEFAULT_TICKERS + ["SHOP", "NVO", "LLY", "XOM", "CVX", "KO", "PEP", "HD", "BAC", "GS", "BRK-B"]
))
TICKER_PRESETS = {
    "Vlastný výber": DEFAULT_TICKERS,
    "Technológie a AI": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMD", "TSM", "AVGO", "ORCL", "PLTR", "MU"],
    "Veľké americké firmy": ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "JPM", "V", "MA", "COST", "WMT"],
    "ETF a trhové indexy": ["SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "VT", "VWCE.DE", "CSPX.L", "^GSPC"],
    "Dividendové a defenzívne": ["KO", "PEP", "WMT", "COST", "XOM", "CVX", "V", "JPM", "VOO", "VT"],
}

# --- Watchlist persistence (per browser, via cookie) -------------------------
WATCHLIST_COOKIE = "oliver_watchlist"
cookie_manager = stx.CookieManager(key="watchlist_cookies")

if "watchlist_restored" not in st.session_state:
    # Cookie sa do aplikácie načíta až v ďalšom behu, preto krátko počkáme.
    saved_raw = cookie_manager.get(WATCHLIST_COOKIE)
    if saved_raw is None and st.session_state.get("_cookie_wait", 0) < 5:
        st.session_state["_cookie_wait"] = st.session_state.get("_cookie_wait", 0) + 1
        time.sleep(0.3)
        st.rerun()
    if saved_raw:
        try:
            restored = [s for s in json.loads(urllib.parse.unquote(saved_raw)) if isinstance(s, str)]
            st.session_state["ticker_selection"] = restored[:MAX_TICKERS]
        except (ValueError, TypeError):
            pass  # poškodená cookie: ostanú predvolené tickery
    st.session_state["watchlist_restored"] = True

if "_market_data_refresh_key" not in st.session_state:
    st.session_state["_market_data_refresh_key"] = uuid.uuid4().hex
if "ticker_selection" not in st.session_state:
    st.session_state["ticker_selection"] = DEFAULT_TICKERS.copy()
if "_ticker_feedback" not in st.session_state:
    st.session_state["_ticker_feedback"] = None
if "compare_list" not in st.session_state:
    st.session_state["compare_list"] = ["AAPL", "MSFT"]
if "snapshot_log" not in st.session_state:
    st.session_state["snapshot_log"] = []


def add_custom_tickers() -> None:
    """Callback: resolve typed symbols (incl. EU suffixes) and add valid ones to the watchlist."""
    raw = st.session_state.get("custom_ticker_box", "")
    symbols = parse_symbols(raw)
    current = list(st.session_state.get("ticker_selection", []))
    added: list[str] = []
    rejected: list[str] = []
    for symbol in symbols:
        resolved = resolve_symbol(symbol)
        if resolved is None:
            rejected.append(symbol)
            continue
        if resolved in current or resolved in added:
            continue
        if len(current) + len(added) >= MAX_TICKERS:
            rejected.append(f"{symbol} (limit {MAX_TICKERS})")
            continue
        added.append(resolved)
    st.session_state["ticker_selection"] = current + added
    st.session_state["custom_ticker_box"] = ""
    st.session_state["_ticker_feedback"] = {"added": added, "rejected": rejected}


def add_searched_ticker(symbol: str) -> None:
    """Callback: add a ticker picked from the name search and clear the search box."""
    current = list(st.session_state.get("ticker_selection", []))
    if symbol not in current and len(current) < MAX_TICKERS:
        current.append(symbol)
        st.session_state["ticker_selection"] = current
    st.session_state["search_text"] = ""


def remove_all_tickers() -> None:
    st.session_state["ticker_selection"] = []
    st.session_state["_ticker_feedback"] = None


def add_compare(symbol: str) -> None:
    """Callback: add a firm to the comparison tab (can be outside the watchlist)."""
    current = list(st.session_state.get("compare_list", []))
    if symbol not in current and len(current) < MAX_COMPARE:
        current.append(symbol)
        st.session_state["compare_list"] = current
    st.session_state["compare_search"] = ""
    st.session_state["compare_symbol"] = ""
    st.session_state["compare_error"] = None


def add_compare_symbol() -> None:
    """Callback: resolve a typed symbol (e.g. SAP.DE or SAP) and add it to the comparison."""
    raw = str(st.session_state.get("compare_symbol", "")).strip()
    if not raw:
        return
    resolved = resolve_symbol(raw)
    if resolved:
        add_compare(resolved)
    else:
        st.session_state["compare_symbol"] = ""
        st.session_state["compare_error"] = raw


# -----------------------------------------------------------------------------
# Sidebar controls
# -----------------------------------------------------------------------------
st.sidebar.markdown("<div class='eyebrow'>Equity Research Studio</div>", unsafe_allow_html=True)
st.sidebar.title("Nastavenie analýzy")

with st.sidebar.expander("➕ Pridať ticker", expanded=False):
    st.caption(
        "Zadaj symbol z Yahoo Finance, napr. `NET`, `CSPX.L`. Holý európsky symbol "
        "(napr. `SIE`) sa skúsi s burzovými príponami automaticky. Na presnú burzu použi príponu, napr. `SAP.DE`."
    )
    st.text_input(
        "Ticker(y) na pridanie",
        key="custom_ticker_box",
        placeholder="Napr. NET, SAP.DE, SIE",
        on_change=add_custom_tickers,
    )
    st.button("Pridať ticker(y)", use_container_width=True, on_click=add_custom_tickers)

feedback = st.session_state.get("_ticker_feedback")
if feedback:
    if feedback["added"]:
        st.sidebar.success("Pridané: " + ", ".join(feedback["added"]))
    if feedback["rejected"]:
        st.sidebar.error("Nenašli sa dáta pre: " + ", ".join(feedback["rejected"]))

with st.sidebar.expander("🔎 Hľadať podľa názvu", expanded=False):
    st.caption("Napíš názov firmy alebo ETF, napríklad „Siemens“ alebo „MSCI World“, a vyber výsledok.")
    search_text = st.text_input("Hľadaný názov", key="search_text", placeholder="napr. Siemens")
    if search_text.strip():
        hits = search_yahoo(search_text.strip())
        if not hits:
            st.caption("Nič sa nenašlo. Skús iný názov alebo zadaj symbol priamo.")
        for hit in hits:
            label = f"{hit['symbol']} · {hit['name']}"
            if hit["exchange"]:
                label += f" ({hit['exchange']})"
            st.button(
                f"➕ {label}",
                key=f"add_{hit['symbol']}",
                use_container_width=True,
                on_click=add_searched_ticker,
                args=(hit["symbol"],),
            )

st.sidebar.markdown("#### Predvýbery")
preset_choice = st.sidebar.selectbox("Predvýber", list(TICKER_PRESETS.keys()), index=0,
                                     help="Predvýber nahradí aktuálny zoznam tickerov.")
if st.sidebar.button("Použiť predvýber", use_container_width=True):
    st.session_state["ticker_selection"] = TICKER_PRESETS[preset_choice].copy()
    st.session_state["_ticker_feedback"] = None
    st.rerun()

st.sidebar.markdown("#### Pridať sektor")
sector_watchlist = st.sidebar.multiselect(
    "Sektory na pridanie",
    options=list(SECTOR_TICKERS.keys()),
    key="sector_watchlist_picker",
    help="Pridá pripravenú skupinu sledovaných tickerov v zvolených sektoroch.",
)
if st.sidebar.button("Pridať tickery z vybraných sektorov", use_container_width=True):
    current = list(st.session_state.get("ticker_selection", []))
    additions = [ticker for sector in sector_watchlist for ticker in SECTOR_TICKERS.get(sector, [])]
    combined = list(dict.fromkeys(current + additions))
    if len(combined) > MAX_TICKERS:
        st.sidebar.warning(f"Výber by mal {len(combined)} tickerov. Limit je {MAX_TICKERS}; vyber menej sektorov.")
    else:
        st.session_state["ticker_selection"] = combined
        st.rerun()

st.sidebar.markdown("#### Aktuálny watchlist")
selection_options = list(dict.fromkeys(TICKER_UNIVERSE + st.session_state.get("ticker_selection", [])))
selected_tickers = st.sidebar.multiselect(
    "Sledované akcie / ETF",
    options=selection_options,
    key="ticker_selection",
    help="Odstráň ticker kliknutím na × alebo pridaj ďalšie z ponuky. Vlastné tickery sa ponechajú, aj keď nie sú v ponuke.",
)
if st.sidebar.button("🗑 Vymazať celý watchlist", use_container_width=True):
    remove_all_tickers()
    st.rerun()

tickers = list(dict.fromkeys([t.strip().upper() for t in selected_tickers if t.strip()]))
if len(tickers) > MAX_TICKERS:
    st.sidebar.warning(f"Pre rýchlejšie načítanie je limit {MAX_TICKERS} tickerov. Použije sa prvých {MAX_TICKERS}.")
    tickers = tickers[:MAX_TICKERS]
st.sidebar.caption(f"Aktuálny výber: **{len(tickers)} tickerov**")

# Uloženie watchlistu: zapisujeme len vtedy, keď sa zoznam oproti načítanému zmenil.
# Základ (baseline) sa nastaví pri prvom behu, takže predvolený zoznam sa nikdy neprepíše.
if st.session_state.get("watchlist_restored"):
    current_json = json.dumps(tickers)
    if "_last_saved_watchlist" not in st.session_state:
        st.session_state["_last_saved_watchlist"] = current_json
    elif st.session_state["_last_saved_watchlist"] != current_json:
        cookie_manager.set(
            WATCHLIST_COOKIE,
            urllib.parse.quote(current_json),
            expires_at=datetime.now() + timedelta(days=365),
            key="save_watchlist",
        )
        st.session_state["_last_saved_watchlist"] = current_json

with st.sidebar.expander("⚙️ Nastavenia modelu", expanded=False):
    base = st.selectbox(
        "Mena prepočtu",
        BASE_CURRENCIES,
        index=0,
        help="Všetky ceny sa prepočítajú do tejto meny kurzom z Yahoo Finance, aby sa dali porovnávať akcie z rôznych burz.",
    )
    base_sym = CURRENCY_SYMBOL.get(base, base)
    period = st.selectbox("Historické obdobie", ["1y", "2y", "5y", "10y", "max"], index=1,
                          help="Dlhšie obdobie pomáha pri SMA 200, drawdowne a porovnávaní cyklov.")
    benchmark = st.selectbox(
        "Porovnávací benchmark",
        ["SPY", "QQQ", "^GSPC", "^IXIC", "^STOXX50E", "^FTSE", "VWCE.DE"],
        index=0,
        help="Beta porovnáva citlivosť akcie na zvolený benchmark.",
    )
    capital = st.number_input(f"Modelový kapitál ({base_sym})", min_value=100.0, max_value=100_000_000.0, value=10_000.0, step=500.0)
    allocation_method = st.radio(
        "Model rozdelenia kapitálu",
        ["Rovnaká váha", "Inverzná volatilita"],
        help="Rovnaká váha rozdelí kapitál rovnomerne. Inverzná volatilita prideľuje väčšiu váhu menej volatilným titulom; nejde o plnú risk-parity optimalizáciu.",
    )
    risk_free = st.number_input("Bezriziková sadzba (% p. a.)", min_value=0.0, max_value=20.0, value=3.0, step=0.25)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<div class='small-muted'>Zdroj: Yahoo Finance cez yfinance. Ceny sú denné a nemusia byť real-time.</div>",
    unsafe_allow_html=True,
)
st.sidebar.button("↻ Načítať najnovšie dáta", use_container_width=True, on_click=refresh_data)

if not tickers:
    st.markdown(
        """<div class='topbar'><div><div class='eyebrow'>OLIVER LESO · PERSONAL MARKET INTELLIGENCE</div>
        <div class='brand'>Equity Research <span>Studio</span></div></div></div>""",
        unsafe_allow_html=True,
    )
    st.info("Watchlist je prázdny. V ľavom paneli pridaj aspoň jeden ticker, napríklad NET, AAPL alebo SAP.DE.")
    st.stop()

# -----------------------------------------------------------------------------
# Data loading (only for the tickers the user actually selected)
# -----------------------------------------------------------------------------
fetch_tickers = list(dict.fromkeys(tickers + [benchmark, "SPY", "^GSPC"]))
with st.spinner("Načítavam trhové dáta a počítam ukazovatele… Pri väčšom počte tickerov to môže chvíľu trvať."):
    prices_all, highs_all, lows_all, volumes_all, infos, data_errors, fetched_at = load_market_data(
        tuple(fetch_tickers), period, st.session_state["_market_data_refresh_key"], base
    )

valid_tickers = [t for t in tickers if t in prices_all.columns] if not prices_all.empty else []
if not valid_tickers:
    st.error("Nepodarilo sa načítať ceny zadaných tickerov. Skontroluj zápis tickerov a internetové pripojenie.")
    st.button("↻ Skúsiť načítať znova", on_click=refresh_data, use_container_width=True)
    if data_errors:
        with st.expander("Podrobnosti o načítaní", expanded=True):
            for issue in data_errors:
                st.write(f"- {issue}")
    st.stop()

for dependent_key in ("chart_ticker", "profile_ticker", "swot_ticker"):
    if st.session_state.get(dependent_key) not in valid_tickers:
        st.session_state.pop(dependent_key, None)
mc_selected_state = st.session_state.get("mc_compare_tickers")
if isinstance(mc_selected_state, list) and not set(mc_selected_state).issubset(set(valid_tickers)):
    st.session_state.pop("mc_compare_tickers", None)

benchmark_returns = None
if benchmark in prices_all.columns:
    benchmark_returns = prices_all[benchmark].pct_change(fill_method=None).dropna()
else:
    st.warning(f"Benchmark {benchmark} sa nepodarilo načítať. Beta nebude k dispozícii.")

metrics = build_stock_metrics(valid_tickers, prices_all, highs_all, lows_all, volumes_all, infos, benchmark_returns)
if metrics.empty:
    st.error("Dáta neobsahujú dostatok cien na výpočet ukazovateľov.")
    st.stop()

news_by_ticker: dict[str, list[dict[str, Any]]] = {}
news_status_by_ticker: dict[str, str] = {}
with st.spinner("Vyhľadávam najnovšie správy pre tvoje tickery…"):
    max_workers = min(8, max(1, len(valid_tickers)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(
                fetch_ticker_news,
                ticker,
                safe_name(infos.get(ticker, {}), ticker),
                st.session_state["_market_data_refresh_key"],
            ): ticker
            for ticker in valid_tickers
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                stories, status = future.result()
                news_by_ticker[ticker] = stories
                news_status_by_ticker[ticker] = status
            except Exception:
                news_by_ticker[ticker] = []
                news_status_by_ticker[ticker] = "News feed nedostupný"

all_selected_news = [story for ticker in valid_tickers for story in news_by_ticker.get(ticker, [])]
all_selected_news.sort(key=lambda story: float(story.get("Published epoch", 0) or 0), reverse=True)
news_signal_groups_by_ticker: dict[str, dict[str, list[dict[str, Any]]]] = {}
for news_ticker in valid_tickers:
    groups: dict[str, list[dict[str, Any]]] = {"Silné stránky": [], "Slabé stránky": [], "Príležitosti": [], "Hrozby": []}
    for story in news_by_ticker.get(news_ticker, []):
        classification = classify_news_signal(story)
        if classification:
            quadrant, rationale = classification
            story_with_signal = dict(story)
            story_with_signal["SWOT rationale"] = rationale
            groups[quadrant].append(story_with_signal)
    news_signal_groups_by_ticker[news_ticker] = groups

price_df = prices_all.reindex(columns=valid_tickers)
returns = price_df.pct_change(fill_method=None).dropna(how="all")

if data_errors:
    with st.expander(f"Poznámky pri načítaní dát ({len(data_errors)})"):
        st.markdown("Niektoré tickery alebo fundamentálne položky nemusia byť dostupné. Zvyšok aplikácie pracuje s dostupnými hodnotami.")
        for issue in data_errors:
            st.write(f"- {issue}")
        st.button("↻ Skúsiť načítať znova", on_click=refresh_data, key="retry_bottom")

# -----------------------------------------------------------------------------
# Header (kompaktný)
# -----------------------------------------------------------------------------
latest_date = price_df.dropna(how="all").index.max()
latest_text = latest_date.strftime("%d.%m.%Y") if pd.notna(latest_date) else "—"
st.markdown(
    f"""
    <div class='topbar'>
      <div>
        <div class='eyebrow'>OLIVER LESO · PERSONAL MARKET INTELLIGENCE</div>
        <div class='brand'>Equity Research <span>Studio</span></div>
      </div>
      <div class='snapshot'>Mena: {base} · Posledná cena: {latest_text} · snapshot {fetched_at}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 1. Čísla: karty + tabuľka watchlistu
# -----------------------------------------------------------------------------
cols = st.columns(4)
with cols[0]:
    metric_card("Sledované tituly", f"{len(valid_tickers)}", "Akcie a ETF s načítanou cenovou históriou")
with cols[1]:
    best = metrics.dropna(subset=["3M (%)"]).sort_values("3M (%)", ascending=False)
    best_text = f"{best.iloc[0]['Ticker']} {fmt_pct_signed(best.iloc[0]['3M (%)'])}" if not best.empty else "—"
    metric_card("Najlepší 3M výnos", best_text, "Z vybraného watchlistu")
with cols[2]:
    median_score = metrics["Technické skóre"].median()
    metric_card("Medián technického skóre", f"{median_score:.0f}/100" if np.isfinite(median_score) else "—", "Opis trendových signálov, nie prognóza výnosu")
with cols[3]:
    med_vol = metrics["Volatilita (%)"].median()
    metric_card("Medián volatility", fmt_pct(med_vol), "Ročná volatilita odhadnutá z denných výnosov")

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
st.markdown("### Prehľad watchlistu")
overview = metrics.sort_values("Technické skóre", ascending=False, na_position="last").copy()
for col in ["1D (%)", "1M (%)", "3M (%)", "6M (%)", "1Y (%)", "Volatilita (%)", "Technické skóre"]:
    overview[col] = pd.to_numeric(overview[col], errors="coerce")
display_cols = ["Ticker", "Spoločnosť", "Sektor", "Cena", "Mena", "1D (%)", "3M (%)", "6M (%)", "1Y (%)", "Volatilita (%)", "RSI (14)", "Technické skóre", "Technické signály"]
st.dataframe(
    overview[display_cols].style.format(
        {"Cena": "{:.2f}", "1D (%)": "{:+.2f}%", "3M (%)": "{:+.2f}%", "6M (%)": "{:+.2f}%", "1Y (%)": "{:+.2f}%", "Volatilita (%)": "{:.2f}%", "RSI (14)": "{:.2f}", "Technické skóre": "{:.2f}/100"},
        na_rep="—",
    ),
    use_container_width=True,
    hide_index=True,
)
st.caption(f"Ceny sú prepočítané do meny {base}. Dáta sú denné a môžu byť oneskorené. Historický výnos nezohľadňuje dane ani poplatky.")

note_overview = missing_note(metrics)
if note_overview:
    st.info(note_overview)

snap_col1, snap_col2 = st.columns([1, 1])
with snap_col1:
    st.download_button(
        "⬇ Stiahnuť snapshot (CSV)",
        data=overview[display_cols].to_csv(index=False).encode("utf-8-sig"),
        file_name=f"oliver_leso_snapshot_{datetime.now():%Y%m%d_%H%M}.csv",
        mime="text/csv",
        use_container_width=True,
    )
with snap_col2:
    if st.button("➕ Pridať snapshot do histórie", use_container_width=True):
        st.session_state["snapshot_log"].append({
            "Čas": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "Mena": base,
            "Počet tickerov": len(valid_tickers),
            "Medián skóre": round(float(median_score), 1) if np.isfinite(median_score) else None,
            "Medián 3M (%)": round(float(metrics["3M (%)"].median()), 2) if metrics["3M (%)"].notna().any() else None,
            "Medián volatility (%)": round(float(med_vol), 2) if np.isfinite(med_vol) else None,
        })
if st.session_state["snapshot_log"]:
    with st.expander(f"História snapshotov v tejto relácii ({len(st.session_state['snapshot_log'])})"):
        st.dataframe(pd.DataFrame(st.session_state["snapshot_log"]), use_container_width=True, hide_index=True)
        st.caption("História sa uchováva len v aktuálnej relácii. Po obnovení stránky sa stratí, preto si dôležité snapshoty stiahni ako CSV.")

# -----------------------------------------------------------------------------
# 2. Správy: rozbaliteľná sekcia
# -----------------------------------------------------------------------------
news_count = len(all_selected_news)
with st.expander(f"📰 Správy z watchlistu ({news_count})", expanded=False):
    if all_selected_news:
        ticker_filter = st.multiselect(
            "Filtrovať podľa tickeru",
            options=valid_tickers,
            default=[],
            key="news_ticker_filter",
            help="Ak nič nevyberieš, zobrazia sa správy pre všetky tickery.",
        )
        shown = [s for s in all_selected_news if not ticker_filter or s["Ticker"] in ticker_filter]
        if not shown:
            st.info("Pre zvolené tickery nie sú žiadne správy.")
        for idx, story in enumerate(shown[:30]):
            summary = story.get("Summary", "")
            summary_text = summary[:260] + ("…" if len(summary) > 260 else "")
            st.markdown(
                f"""<div class='news-card'>
                  <div class='news-meta'>{story['Ticker']} · {story.get('Publisher') or story.get('Feed', 'Zdroj')} · {story.get('Published display', 'Dátum neuvedený')}</div>
                  <div class='news-title'>{html.escape(story['Title'])}</div>
                  {f"<div class='news-summary'>{html.escape(summary_text)}</div>" if summary_text else ""}
                </div>""",
                unsafe_allow_html=True,
            )
            st.link_button("Otvoriť článok", story["URL"], key=f"news_open_{idx}_{story['Ticker']}")
    else:
        st.warning(
            "Pre aktuálne vybrané tickery sa nepodarilo načítať žiadne správy. "
            "Skús tlačidlo „Načítať najnovšie dáta“ alebo skontroluj pripojenie."
        )
    st.caption("Stav feedov: " + "; ".join(f"{t}: {news_status_by_ticker.get(t, 'neznámy stav')}" for t in valid_tickers))

# -----------------------------------------------------------------------------
# 3. Detailné záložky
# -----------------------------------------------------------------------------
tab_charts, tab_screener, tab_compare, tab_portfolio, tab_mc, tab_fundamentals, tab_swot, tab_glossary = st.tabs(
    ["↗ Grafy & technika", "⌕ Screener", "🆚 Porovnanie", "⛨ Portfólio & riziko", "🎲 Monte Carlo",
     "▤ Fundamenty", "◩ SWOT", "ⓘ Slovník"]
)

# -----------------------------------------------------------------------------
# TAB: charts and technical analysis
# -----------------------------------------------------------------------------
with tab_charts:
    st.markdown("<div class='section-kicker'>Price action</div>", unsafe_allow_html=True)
    st.subheader("Grafy, trendy a výkonnosť")

    perf_col = st.selectbox("Horizont výnosu", ["1D (%)", "1M (%)", "3M (%)", "6M (%)", "1Y (%)"], index=2, key="overview_perf")
    c1, c2 = st.columns([1.25, 1])
    with c1:
        chart_df = metrics[["Ticker", perf_col]].dropna().sort_values(perf_col)
        fig = px.bar(chart_df, x=perf_col, y="Ticker", orientation="h", color=perf_col,
                     color_continuous_scale=[RED, "#64748B", ACCENT], title=f"Výnos za zvolené obdobie · {perf_col.replace(' (%)', '')}")
        fig.update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title="Výnos (%)")
        fig.update_traces(texttemplate="%{x:+.2f}%", textposition="outside")
        lo, hi = float(chart_df[perf_col].min()), float(chart_df[perf_col].max())
        pad = max(abs(lo), abs(hi)) * 0.25 + 1
        fig.update_xaxes(range=[min(lo, 0) - pad, max(hi, 0) + pad])
        st.plotly_chart(make_plotly_dark(fig, 430), use_container_width=True)
        chart_note("Stĺpce ukazujú výnos za zvolené obdobie. Dlhšie obdobie zvyčajne znamená väčšie rozpätie hodnôt. Zelená je rast, červená pokles.")
    with c2:
        scatter_df = metrics.dropna(subset=["Volatilita (%)", "3M (%)"]).copy()
        if not scatter_df.empty:
            if scatter_df["Trhová kapitalizácia"].notna().any():
                scatter_df["Veľkosť bubliny"] = scatter_df["Trhová kapitalizácia"].fillna(scatter_df["Trhová kapitalizácia"].median())
            else:
                scatter_df["Veľkosť bubliny"] = 1.0
            fig = px.scatter(scatter_df, x="Volatilita (%)", y="3M (%)", hover_name="Ticker", size="Veľkosť bubliny",
                             size_max=36, color="Sektor", title="3-mesačný výnos a ročná volatilita")
            fig.update_layout(xaxis_title="Ročná volatilita (%)", yaxis_title="3M výnos (%)")
            st.plotly_chart(make_plotly_dark(fig, 430), use_container_width=True)
            chart_note("Veľkosť bubliny zodpovedá trhovej kapitalizácii. Vpravo sú tituly s väčším kolísaním, vyššie tie s lepším 3M výnosom. Ide o minulosť, nie o odporúčanie.")
        else:
            st.info("Na zostavenie grafu nie je dosť dát.")

    st.markdown("#### Detail ceny a indikátorov")
    chart_ticker = st.selectbox("Ticker", valid_tickers, key="chart_ticker")
    show_sma = st.multiselect("Kĺzavé priemery", ["SMA 20", "SMA 50", "SMA 200"], default=["SMA 50", "SMA 200"])

    close = price_df[chart_ticker].dropna()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=close.index, y=close.values, mode="lines", name="Cena (adjusted close)", line=dict(width=2.6, color=ACCENT)))
    for label, window, color in [("SMA 20", 20, ACCENT_2), ("SMA 50", 50, GOLD), ("SMA 200", 200, RED)]:
        if label in show_sma and len(close) >= window:
            sma = close.rolling(window).mean()
            fig.add_trace(go.Scatter(x=sma.index, y=sma.values, mode="lines", name=label, line=dict(width=1.5, color=color)))
    fig.update_layout(title=f"{chart_ticker} · upravená historická cena", xaxis_title="Dátum", yaxis_title=f"Cena ({base})")
    st.plotly_chart(make_plotly_dark(fig, 480), use_container_width=True)
    chart_note("Čiara je upravená historická cena vrátane dividend. Kĺzavé priemery vyhladzujú šum; ich prekríženie nezaručuje, že sa trend otočí.")

    ticker_row = metrics.loc[metrics["Ticker"] == chart_ticker].iloc[0]
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("RSI (14)", fmt_num(ticker_row["RSI (14)"], 2), "Nad 70: často prekúpené")
    k2.metric("MACD histogram", fmt_num(ticker_row["MACD histogram"], 3), "Nad nulou = kladný histogram")
    k3.metric("ATR (14)", fmt_num(ticker_row["ATR (14)"], 2), "Priemerný rozsah pohybu v cene")
    k4.metric("Od maxima 52W", fmt_pct((ticker_row["Cena"] / ticker_row["52W maximum"] - 1) * 100))
    k5.metric("Technické skóre", f"{ticker_row['Technické skóre']:.2f}/100" if np.isfinite(ticker_row["Technické skóre"]) else "—")

    with st.expander("Ako sa počíta technické skóre?"):
        explain_score()

    with st.expander("Kalkulačka veľkosti pozície"):
        st.caption(f"Kapitál zadávaj v mene {base}. Nezahŕňa poplatky, spread ani dane.")
        trade_defaults = {
            "entry": max(float(ticker_row["Cena"]), 0.01),
            "stop": max(float(ticker_row["Cena"]) * 0.94, 0.01),
            "target": max(float(ticker_row["Cena"]) * 1.12, 0.01),
        }
        tr1, tr2, tr3, tr4, tr5 = st.columns(5)
        with tr1:
            entry_price = st.number_input("Vstupná cena", min_value=0.01, max_value=1_000_000_000.0,
                                          value=round(trade_defaults["entry"], 2), step=0.01, key=f"entry_{chart_ticker}")
        with tr2:
            stop_price = st.number_input("Stop-loss cena", min_value=0.01, max_value=1_000_000_000.0,
                                         value=round(trade_defaults["stop"], 2), step=0.01, key=f"stop_{chart_ticker}")
        with tr3:
            target_price = st.number_input("Cieľová cena", min_value=0.01, max_value=1_000_000_000.0,
                                           value=round(trade_defaults["target"], 2), step=0.01, key=f"target_{chart_ticker}")
        with tr4:
            trade_capital = st.number_input(f"Kapitál ({base})", min_value=100.0, max_value=1_000_000_000.0,
                                            value=10_000.0, step=500.0, key=f"trade_capital_{chart_ticker}")
        with tr5:
            risk_budget_pct = st.number_input("Max. riziko kapitálu (%)", min_value=0.1, max_value=10.0,
                                              value=1.0, step=0.1, key=f"risk_pct_{chart_ticker}")

        risk_budget_amount = trade_capital * risk_budget_pct / 100
        unit_risk = entry_price - stop_price
        unit_reward = target_price - entry_price
        if unit_risk <= 0:
            st.error("Stop-loss musí byť nižšie než vstupná cena, aby sa dala vypočítať riziková veľkosť pozície.")
        elif unit_reward <= 0:
            st.warning("Cieľová cena je na alebo pod vstupom. Kalkulačka neukáže kladný pomer výnosu k riziku.")
        else:
            shares_by_risk = int(np.floor(risk_budget_amount / unit_risk))
            shares_by_capital = int(np.floor(trade_capital / entry_price))
            suggested_units = max(0, min(shares_by_risk, shares_by_capital))
            position_value = suggested_units * entry_price
            estimated_loss = suggested_units * unit_risk
            estimated_gain = suggested_units * unit_reward
            rr_ratio = unit_reward / unit_risk
            q1, q2, q3, q4, q5 = st.columns(5)
            q1.metric("Orientačný počet kusov", f"{suggested_units:,}", "Obmedzené rizikom aj kapitálom")
            q2.metric("Hodnota pozície", f"{position_value:,.2f} {base}", f"{position_value / trade_capital * 100:.2f}% kapitálu" if trade_capital > 0 else "—")
            q3.metric("Riziko pri stop-loss", f"{estimated_loss:,.2f} {base}", f"Limit: {risk_budget_amount:,.2f} {base}")
            q4.metric("Potenciálny zisk pri cieli", f"{estimated_gain:,.2f} {base}", "Hypotetický, pred nákladmi")
            q5.metric("Výnos : riziko", f"1 : {rr_ratio:.2f}", "Na jednu akciu")
            st.markdown("<div class='info-box'><b>Ako čítať kalkulačku:</b> Najprv určíš, koľko kapitálu si ochotný/á riskovať, potom vzdialenosť medzi vstupom a stop-lossom. Počet kusov sa vypočíta z tohto limitu a nikdy neprekročí zadaný kapitál. Stop-loss negarantuje vykonanie presne na zadanej cene, najmä pri cenových medzerách a nízkej likvidite.</div>", unsafe_allow_html=True)

    with st.expander("Porovnanie rastu cien na rovnakej báze"):
        compare_tickers = st.multiselect("Tickery na porovnanie", valid_tickers,
                                         default=valid_tickers[: min(4, len(valid_tickers))], key="compare_tickers")
        if compare_tickers:
            normalised = price_df[compare_tickers].dropna(how="all")
            normalised = normalised.apply(lambda s: s / s.dropna().iloc[0] * 100 if s.notna().any() else s)
            fig = px.line(normalised, x=normalised.index, y=normalised.columns, title="Vývoj ceny: prvá dostupná hodnota = 100")
            fig.update_layout(xaxis_title="Dátum", yaxis_title="Index (štart = 100)")
            st.plotly_chart(make_plotly_dark(fig, 420), use_container_width=True)
            chart_note("Všetky čiary začínajú na 100, takže ukazujú percentuálny vývoj, nie absolútnu cenu. Neukazujú počet kusov ani celkový výnos vrátane dividend.")

    with st.expander("Čo jednotlivé indikátory hovoria"):
        st.markdown("""
        - **RSI (14):** oscilátor od 0 do 100, ktorý porovnáva priemerné nedávne zisky a straty. Nad 70 sa často označuje ako prekúpené a pod 30 ako prepredané; nie je to samostatný signál na obchod.
        - **SMA 20/50/200:** jednoduché kĺzavé priemery za 20, 50 a 200 obchodných dní. Cena nad priemerom môže podporovať pohľad na rastúci trend, ale indikátor za cenou zaostáva.
        - **MACD histogram:** rozdiel medzi MACD čiarou a jej signálnou čiarou. Kladná hodnota znamená, že MACD je nad signálnou čiarou, nie že cena musí rásť.
        - **ATR (14):** priemerný skutočný denný rozsah pohybu za 14 dní. Meria veľkosť kolísania v menových jednotkách, nie smer.
        """)

# -----------------------------------------------------------------------------
# TAB: screener
# -----------------------------------------------------------------------------
with tab_screener:
    st.markdown("<div class='section-kicker'>Opportunity finder</div>", unsafe_allow_html=True)
    st.subheader("Nájdi tituly podľa vlastných kritérií")
    st.markdown("Nastav filtre a zoznam sa prepočíta. Filtre sú pomôcka na zúženie výberu, nie automatický pokyn na nákup.")

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        min_score = st.slider("Min. technické skóre", 0, 100, 0, 5)
    with f2:
        min_3m = st.slider("Min. 3M výnos (%)", -100, 150, -100, 5)
    with f3:
        max_vol = st.slider("Max. volatilita (% p. a.)", 10, 200, 120, 5)
    with f4:
        rsi_range = st.slider("RSI interval", 0, 100, (0, 100), 5)

    available_sectors = sorted(metrics["Sektor"].dropna().unique().tolist())
    sector_options = sorted(set(available_sectors) | set(SECTOR_TICKERS.keys()))
    selected_sectors = st.multiselect(
        "Sektory",
        sector_options,
        default=available_sectors,
        help="Ak vo vybranom sektore ešte nesleduješ žiadne akcie, pridaj ich v ľavom paneli.",
    )
    filtered = metrics.copy()
    filtered = filtered[filtered["Technické skóre"].fillna(-1) >= min_score]
    filtered = filtered[filtered["3M (%)"].fillna(-999) >= min_3m]
    filtered = filtered[filtered["Volatilita (%)"].fillna(999) <= max_vol]
    filtered = filtered[filtered["RSI (14)"].fillna(-1).between(rsi_range[0], rsi_range[1])]
    filtered = filtered[filtered["Sektor"].isin(selected_sectors)]

    a, b, c = st.columns(3)
    with a:
        metric_card("Výsledky filtra", str(len(filtered)), f"Z {len(metrics)} dostupných titulov")
    with b:
        avg_score = filtered["Technické skóre"].mean() if not filtered.empty else np.nan
        metric_card("Priemerné skóre", f"{avg_score:.2f}/100" if np.isfinite(avg_score) else "—", "Iba vyfiltrované tituly")
    with c:
        avg_vol = filtered["Volatilita (%)"].mean() if not filtered.empty else np.nan
        metric_card("Priemerná volatilita", fmt_pct(avg_vol), "Ročná, vypočítaná z denných výnosov")

    screener_cols = ["Ticker", "Spoločnosť", "Sektor", "Cena", "Mena", "3M (%)", "6M (%)", "1Y (%)", "Volatilita (%)", "RSI (14)", "P/E (TTM)", "Technické skóre", "Technické signály"]
    if filtered.empty:
        st.warning("Tomuto nastaveniu nevyhovuje žiadny ticker. Uvoľni jeden alebo viac filtrov.")
    else:
        filtered_display = filtered[screener_cols].sort_values("Technické skóre", ascending=False, na_position="last")
        st.dataframe(
            filtered_display.style.format(
                {"Cena": "{:.2f}", "3M (%)": "{:+.2f}%", "6M (%)": "{:+.2f}%", "1Y (%)": "{:+.2f}%", "Volatilita (%)": "{:.2f}%", "RSI (14)": "{:.2f}", "P/E (TTM)": "{:.2f}", "Technické skóre": "{:.2f}/100"},
                na_rep="—",
            ), use_container_width=True, hide_index=True
        )
        st.download_button("⬇ Stiahnuť výsledky do CSV", data=filtered_display.to_csv(index=False).encode("utf-8-sig"),
                           file_name="oliver_leso_stock_screener.csv", mime="text/csv")

    with st.expander("Ako si nastaviť filtre? Príklady"):
        st.markdown("""
        - **Momentum:** min. 3M výnos 0 %, technické skóre 60+.
        - **Konzervatívnejší výber:** nižší limit volatility; neznamená to nulové riziko.
        - **Technické ochladenie:** RSI napríklad 30–60; RSI pod 30 sa často označuje ako prepredané, ale môže zostať nízke aj počas silného poklesu.
        - **Fundamentálne hľadanie:** použi kartu Fundamenty a porovnávaj P/E, ziskovú maržu, ROE, zadlženie a rast; jednotlivý ukazovateľ nikdy nehodnoť izolovane.
        """)

# -----------------------------------------------------------------------------
# TAB: porovnanie ľubovoľných firiem
# -----------------------------------------------------------------------------
with tab_compare:
    st.markdown("<div class='section-kicker'>Compare any firm</div>", unsafe_allow_html=True)
    st.subheader("Porovnanie ľubovoľných firiem")
    st.markdown(
        "Pridaj až 4 firmy hľadaním podľa názvu alebo zadaním symbolu. Nemusia byť vo watchliste "
        "a nemusia byť na americkej burze. Aplikácia ukáže ich čísla vedľa seba a vysvetlí ich. "
        "Nehodnotí, ktorá firma je lepšia, a nepredpovedá vývoj ceny."
    )

    cmp_left, cmp_right = st.columns([1.4, 1])
    with cmp_left:
        st.text_input("Hľadať firmu alebo ETF podľa názvu", key="compare_search", placeholder="napr. Siemens, Allianz, Samsung")
        compare_query = str(st.session_state.get("compare_search", "")).strip()
        if compare_query:
            cmp_hits = search_yahoo(compare_query)
            if not cmp_hits:
                st.caption("Nič sa nenašlo. Skús iný názov alebo symbol vpravo.")
            for hit in cmp_hits:
                label = f"{hit['symbol']} · {hit['name']}"
                if hit["exchange"]:
                    label += f" ({hit['exchange']})"
                st.button(
                    f"➕ {label}",
                    key=f"cmp_hit_{hit['symbol']}",
                    use_container_width=True,
                    on_click=add_compare,
                    args=(hit["symbol"],),
                )
    with cmp_right:
        st.text_input("Alebo zadaj symbol", key="compare_symbol", placeholder="napr. SAP.DE alebo SIE",
                      on_change=add_compare_symbol)
        st.button("Pridať symbol", use_container_width=True, on_click=add_compare_symbol)
        if st.session_state.get("compare_error"):
            st.error(f"Pre symbol „{st.session_state['compare_error']}“ sa nenašli dáta. Skús príponu burzy, napr. .DE alebo .AS.")

    compare_options = list(dict.fromkeys(st.session_state.get("compare_list", []) + TICKER_UNIVERSE))
    compare_list = st.multiselect(
        "Firmy na porovnanie (max. 4)",
        options=compare_options,
        key="compare_list",
        max_selections=MAX_COMPARE,
        help="Odstrániš firmu kliknutím na ×.",
    )

    if len(compare_list) < 2:
        st.info("Vyber aspoň dve firmy na porovnanie.")
    else:
        with st.spinner("Načítavam dáta pre porovnanie…"):
            cmp_prices, cmp_highs, cmp_lows, cmp_volumes, cmp_infos, cmp_errors, _ = load_market_data(
                tuple(compare_list), period, st.session_state["_market_data_refresh_key"], base
            )
        cmp_valid = [t for t in compare_list if t in cmp_prices.columns] if not cmp_prices.empty else []
        if len(cmp_valid) < 2:
            st.warning("Pre aspoň dve zvolené firmy sa nepodarilo načítať ceny. Skús iné symboly alebo zadaj príponu burzy.")
            st.button("↻ Skúsiť načítať znova", on_click=refresh_data, key="retry_compare")
        else:
            cmp_metrics = build_stock_metrics(cmp_valid, cmp_prices, cmp_highs, cmp_lows, cmp_volumes, cmp_infos, benchmark_returns)
            cmp_names = {t: safe_name(cmp_infos.get(t, {}), t) for t in cmp_valid}
            st.markdown("#### Firmy vedľa seba")
            st.caption(f"Všetky ceny sú prepočítané do meny {base}, takže sa dajú porovnávať. Výnosy a pomery nezávisia od meny.")

            cmp_numeric = {
                "Cena": "Cena",
                "1Y (%)": "Výnos za 1 rok (%)",
                "3M (%)": "Výnos za 3 mesiace (%)",
                "Volatilita (%)": "Ročná volatilita (%)",
                "Max. prepad (%)": "Max. prepad (%)",
                "Technické skóre": "Technické skóre (0–100)",
                "P/E (TTM)": "P/E (TTM)",
                "Forward P/E": "Forward P/E",
                "Zisková marža (%)": "Zisková marža (%)",
                "ROE (%)": "ROE (%)",
                "Rast tržieb (%)": "Rast tržieb (%)",
                "Debt/Equity": "Debt/Equity",
                "Dividendový výnos (%)": "Dividendový výnos (%)",
                "Beta vs. benchmark": "Beta voči benchmarku",
                "Trhová kapitalizácia": "Trhová kapitalizácia",
            }
            cmp_table = cmp_metrics.set_index("Ticker")[list(cmp_numeric.keys())]
            cmp_table.columns = list(cmp_numeric.values())
            cmp_table = cmp_table.T.apply(pd.to_numeric, errors="coerce")
            cmp_table.columns = [cmp_names[t] for t in cmp_table.columns]
            st.dataframe(cmp_table.style.format("{:,.2f}", na_rep="—"), use_container_width=True)

            note_cmp = missing_note(cmp_metrics)
            if note_cmp:
                st.info(note_cmp)

            norm = cmp_prices[cmp_valid].dropna(how="all")
            norm = norm.apply(lambda s: s / s.dropna().iloc[0] * 100 if s.notna().any() else s)
            fig = px.line(norm, x=norm.index, y=norm.columns, title="Vývoj ceny: prvá dostupná hodnota = 100")
            fig.update_layout(xaxis_title="Dátum", yaxis_title="Index (štart = 100)")
            st.plotly_chart(make_plotly_dark(fig, 460), use_container_width=True)
            chart_note("Všetky firmy začínajú na 100, takže vidíš, kto ako rástol alebo klesal od rovnakého štartu. Neberie do úvahy dividendy ani poplatky.")

            st.markdown("<div class='info-box'><b>Ako čítať porovnanie:</b> Každé číslo má iný význam. Vyššia historická výnosnosť bola často spojená s vyšším kolísaním. Vysoké P/E môže znamenať vysoké očakávania trhu. Marža a ROE sa dajú porovnávať hlavne v rámci rovnakého odvetvia. Porovnanie nevyhlasuje víťaza a nepredpovedá budúce výnosy.</div>", unsafe_allow_html=True)

            with st.expander("Čo jednotlivé ukazovatele znamenajú"):
                st.markdown("""
                - **Výnos za 1 rok a 3 mesiace:** zmena ceny v minulosti, nie záruka budúceho vývoja.
                - **Volatilita a max. prepad:** ako veľmi cena kolísala a aký hlboký pokles už firma zažila. Pomáha odhadnúť, či by si takýto pokles zvládol.
                - **P/E a Forward P/E:** koľko trh platí za jednotku zisku. Forward P/E používa odhad budúceho zisku, ktorý sa nemusí naplniť.
                - **Zisková marža a ROE:** ako efektívne firma mení tržby a vlastný kapitál na zisk. Závisia od odvetvia.
                - **Rast tržieb:** ako sa tržby menili, nie či budú rásť.
                - **Debt/Equity:** koľko dlhu firma používa. Vyšší dlh zvyšuje citlivosť na horšie podmienky.
                - **Dividendový výnos:** dividenda voči cene. Vysoký výnos môže sprevádzať pokles ceny.
                - **Beta:** citlivosť na benchmark v minulosti.
                - **Trhová kapitalizácia:** približná trhová hodnota firmy. Väčšia firma nie je automaticky bezpečnejšia.
                """)

            with st.expander("Otázky, ktoré si môžeš položiť pri každej firme"):
                st.markdown("""
                1. Z čoho firma zarába a je to závislé na jednom produkte, zákazníkovi alebo regióne?
                2. Prečo sa jej čísla líšia od konkurencie, napríklad marža alebo dlh?
                3. Čo by muselo nastať, aby sa tvoja investičná téza ukázala ako nesprávna?
                4. Sú údaje z oficiálnych výkazov firmy, alebo len z jedného zdroja?
                5. Ako by firma prežila pokles trhu o 30 %?
                """)

            if cmp_errors:
                with st.expander(f"Poznámky k načítaniu ({len(cmp_errors)})"):
                    for issue in cmp_errors:
                        st.write(f"- {issue}")

# -----------------------------------------------------------------------------
# TAB: portfolio construction and risk
# -----------------------------------------------------------------------------
with tab_portfolio:
    st.markdown("<div class='section-kicker'>Portfolio laboratory</div>", unsafe_allow_html=True)
    st.subheader("Model rozdelenia kapitálu a rizikový profil")
    asset_vol = metrics.set_index("Ticker")["Volatilita (%)"].reindex(valid_tickers) / 100.0
    if allocation_method == "Rovnaká váha":
        weight_series = pd.Series(1 / len(valid_tickers), index=valid_tickers, dtype=float)
    else:
        inv_vol = 1 / asset_vol.replace(0, np.nan)
        inv_vol = inv_vol.replace([np.inf, -np.inf], np.nan).fillna(0)
        if inv_vol.sum() <= 0:
            weight_series = pd.Series(1 / len(valid_tickers), index=valid_tickers, dtype=float)
        else:
            weight_series = inv_vol / inv_vol.sum()

    portfolio_returns_df = returns.reindex(columns=valid_tickers).fillna(0)
    portfolio_returns = portfolio_returns_df.dot(weight_series).dropna()
    growth = (1 + portfolio_returns).cumprod()
    daily_vol = as_float(portfolio_returns.std(ddof=1)) if len(portfolio_returns) > 1 else np.nan
    annual_vol = daily_vol * np.sqrt(252) if np.isfinite(daily_vol) else np.nan
    annual_mean = as_float(portfolio_returns.mean() * 252) if len(portfolio_returns) else np.nan
    annualized_return = (float(growth.iloc[-1]) ** (252 / len(portfolio_returns)) - 1) if len(portfolio_returns) > 1 and growth.iloc[-1] > 0 else np.nan
    sharpe = (annual_mean - risk_free / 100) / annual_vol if np.isfinite(annual_vol) and annual_vol > 0 else np.nan
    max_drawdown_port = as_float((growth / growth.cummax() - 1).min() * 100) if not growth.empty else np.nan
    daily_q05 = as_float(portfolio_returns.quantile(0.05)) if len(portfolio_returns) else np.nan
    worst_days = portfolio_returns[portfolio_returns <= daily_q05] if np.isfinite(daily_q05) else pd.Series(dtype=float)
    cvar_daily = as_float(worst_days.mean()) if len(worst_days) else np.nan
    var_eur = max(0.0, -daily_q05 * capital) if np.isfinite(daily_q05) else np.nan
    cvar_eur = max(0.0, -cvar_daily * capital) if np.isfinite(cvar_daily) else np.nan
    hhi = float(np.sum((weight_series * 100) ** 2))
    effective_positions = 1 / float(np.sum(weight_series ** 2)) if float(np.sum(weight_series ** 2)) > 0 else np.nan

    p1, p2, p3, p4 = st.columns(4)
    with p1:
        kpi_card("Modelovaný kapitál", f"{capital:,.2f} {base_sym}", allocation_method, "neutral")
    with p2:
        kpi_card("Ročná volatilita", fmt_pct(annual_vol * 100 if np.isfinite(annual_vol) else np.nan),
                 "Kolísanie portfólia", "neutral")
    with p3:
        kpi_card("Sharpe ratio", fmt_num(sharpe, 2), f"Bezriziková sadzba: {risk_free:.2f}%", tone_for_sign(sharpe))
    with p4:
        kpi_card("Historický max. prepad", fmt_pct(max_drawdown_port),
                 "Najväčší pokles od vrcholu", "down" if np.isfinite(max_drawdown_port) and max_drawdown_port < 0 else "neutral")

    p5, p6, p7, p8 = st.columns(4)
    with p5:
        kpi_card("Historický CAGR", fmt_pct(annualized_return * 100 if np.isfinite(annualized_return) else np.nan),
                 "Ročný zložený výnos", tone_for_sign(annualized_return))
    with p6:
        kpi_card("VaR 95 % / 1 deň", f"{var_eur:,.2f} {base_sym}" if np.isfinite(var_eur) else "—",
                 "Historický odhad z 5. percentilu", "down" if np.isfinite(var_eur) else "neutral")
    with p7:
        kpi_card("CVaR 95 % / 1 deň", f"{cvar_eur:,.2f} {base_sym}" if np.isfinite(cvar_eur) else "—",
                 "Priemerná strata v najhorších 5 % dní", "down" if np.isfinite(cvar_eur) else "neutral")
    with p8:
        kpi_card("Efektívny počet pozícií", f"{effective_positions:.2f}" if np.isfinite(effective_positions) else "—",
                 f"HHI: {hhi:,.2f} (váhy v % na druhú)", "neutral")

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("#### Rozdelenie kapitálu")
        allocation = pd.DataFrame({
            "Ticker": valid_tickers,
            "Váha (%)": [weight_series[t] * 100 for t in valid_tickers],
            f"Modelovaná investícia ({base})": [weight_series[t] * capital for t in valid_tickers],
            "Volatilita (%)": [asset_vol.get(t, np.nan) * 100 for t in valid_tickers],
        }).sort_values("Váha (%)", ascending=False)
        st.dataframe(allocation.style.format({"Váha (%)": "{:.2f}%", f"Modelovaná investícia ({base})": "{:,.2f}", "Volatilita (%)": "{:.2f}%"}, na_rep="—"),
                     use_container_width=True, hide_index=True)
        st.download_button("⬇ Stiahnuť model alokácie", allocation.to_csv(index=False).encode("utf-8-sig"),
                           file_name="oliver_leso_portfolio_allocation.csv", mime="text/csv")
        fig = px.pie(allocation, names="Ticker", values=f"Modelovaná investícia ({base})", hole=0.62,
                     title="Modelová alokácia")
        fig.update_traces(textposition="inside", textinfo="label+percent")
        st.plotly_chart(make_plotly_dark(fig, 390), use_container_width=True)
        chart_note("Ukazuje, aký podiel kapitálu pripadá na jednotlivé tituly podľa zvoleného modelu. Rovnaká váha ignoruje rozdiel v riziku.")
    with c2:
        st.markdown("#### Historický vývoj modelového portfólia")
        if not growth.empty:
            cumulative = (growth - 1) * 100
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=cumulative.index, y=cumulative.values, mode="lines", name="Portfólio",
                                     line=dict(color=ACCENT, width=2.5), fill="tozeroy", fillcolor="rgba(84,225,193,.08)"))
            fig.update_layout(title="Kumulatívny modelový výnos", xaxis_title="Dátum", yaxis_title="Výnos (%)")
            st.plotly_chart(make_plotly_dark(fig, 390), use_container_width=True)
            chart_note("Kumulatívny výnos modelu za zvolené obdobie. Najväčší prepad od vrcholu je v kartách vyššie, pretože ukazuje, aký hlboký pokles model zažil.")
        corr = returns.reindex(columns=valid_tickers).corr()
        if len(valid_tickers) > 1 and not corr.empty:
            st.markdown("#### Korelácia výnosov")
            fig_corr = px.imshow(corr, text_auto=".2f", zmin=-1, zmax=1, color_continuous_scale="RdBu_r", aspect="auto")
            fig_corr.update_layout(coloraxis_colorbar=dict(title="Korelácia"))
            st.plotly_chart(make_plotly_dark(fig_corr, max(330, len(valid_tickers) * 28)), use_container_width=True)
            chart_note("Blízko +1 sa tituly v minulosti pohybovali spolu, takže sa navzájom slabo diverzifikujú. Nízke alebo záporné hodnoty znamenajú lepšiu diverzifikáciu. Korelácie sa v krízach často zvyšujú.")

    st.markdown("<div class='info-box'><b>Ako čítať portfóliové riziko:</b> Ročná volatilita odhaduje veľkosť bežných výkyvov, max drawdown ukazuje najväčší pozorovaný prepad od vrcholu, VaR približuje hranicu zlého dňa a CVaR priemernú stratu v najhorších 5 % dní. Každá metrika opisuje iný aspekt rizika, preto ich čítaj spolu.</div>", unsafe_allow_html=True)
    st.markdown("<div class='warning-box'><b>Limit modelu:</b> Inverzná volatilita nie je plná risk parity. Neoptimalizuje korelácie a nezaručuje rovnaký príspevok každého aktíva k riziku. Historické metriky nepredpovedajú budúce straty a výsledok nemusí zahŕňať dividendy, poplatky, dane ani menové konverzie.</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB: Monte Carlo (vlastná záložka)
# -----------------------------------------------------------------------------
with tab_mc:
    st.markdown("<div class='section-kicker'>Scenario simulation</div>", unsafe_allow_html=True)
    st.subheader("Monte Carlo: možné scenáre, nie predpoveď")
    st.markdown(
        "Simulácia opakovane náhodne vyberá historické denné výnosy a skladá z nich veľa možných ciest hodnoty. "
        "Výsledok ukazuje rozpätie možností na základe minulosti, nie to, čo sa stane."
    )

    m1, m2 = st.columns(2)
    with m1:
        mc_days = st.slider("Simulačný horizont (obchodné dni)", 21, 756, 252, 21)
    with m2:
        mc_sims = st.select_slider("Počet simulácií", options=[250, 500, 1000, 2000, 4000], value=1000)

    sp500_ticker = "SPY" if "SPY" in prices_all.columns else ("^GSPC" if "^GSPC" in prices_all.columns else None)
    sp500_returns = (prices_all[sp500_ticker].pct_change(fill_method=None).dropna()
                     if sp500_ticker else pd.Series(dtype=float))
    rng = np.random.default_rng(2026)
    historical = portfolio_returns.replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype=float)
    historical = historical[np.isfinite(historical) & (historical > -1)]
    sp500_historical = sp500_returns.replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype=float)
    sp500_historical = sp500_historical[np.isfinite(sp500_historical) & (sp500_historical > -1)]

    if len(historical) >= 20:
        sampled = rng.choice(historical, size=(mc_days, mc_sims), replace=True)
        simulated_paths = capital * np.cumprod(1 + sampled, axis=0)
        final_values = simulated_paths[-1, :]
        x_days = np.arange(1, mc_days + 1)
        low_band = np.percentile(simulated_paths, 5, axis=1)
        high_band = np.percentile(simulated_paths, 95, axis=1)
        median_path = np.median(simulated_paths, axis=1)

        st.markdown("#### Portfólio: rozpätie scenárov")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_days, y=high_band, mode="lines", line=dict(width=0), showlegend=False, name="95. percentil portfólia"))
        fig.add_trace(go.Scatter(x=x_days, y=low_band, mode="lines", line=dict(width=0), fill="tonexty",
                                 fillcolor="rgba(140,168,255,.15)", name="Portfólio · rozpätie 5.–95. percentil"))
        for j in range(min(60, mc_sims)):
            fig.add_trace(go.Scatter(x=x_days, y=simulated_paths[:, j], mode="lines", line=dict(color="rgba(84,225,193,.12)", width=1), showlegend=False))
        fig.add_trace(go.Scatter(x=x_days, y=median_path, mode="lines", line=dict(color=ACCENT, width=3), name="Portfólio · medián"))

        sp500_final_values = np.array([])
        sp500_median_path = None
        if len(sp500_historical) >= 20:
            sp500_sampled = rng.choice(sp500_historical, size=(mc_days, mc_sims), replace=True)
            sp500_paths = capital * np.cumprod(1 + sp500_sampled, axis=0)
            sp500_final_values = sp500_paths[-1, :]
            sp500_median_path = np.median(sp500_paths, axis=1)
            fig.add_trace(go.Scatter(x=x_days, y=sp500_median_path, mode="lines",
                                     line=dict(color=GOLD, width=3, dash="dash"), name=f"S&P 500 · medián ({sp500_ticker})"))
        else:
            st.warning("S&P 500 benchmark nemá dosť historických výnosov na simuláciu.")

        fig.update_layout(title=f"Monte Carlo porovnanie · {mc_sims:,} ciest · {mc_days} obchodných dní",
                          xaxis_title="Obchodný deň", yaxis_title=f"Modelová hodnota ({base})")
        st.plotly_chart(make_plotly_dark(fig, 460), use_container_width=True)
        chart_note("Tieňovaná oblasť je rozpätie 5.–95. percentilu simulácií, čiara je medián. Ukazuje, čo sa v minulých scenároch dialo, nie čo sa stane.")
        st.caption(f"Každý model začína rovnakým kapitálom {capital:,.2f} {base_sym}. S&P 500 je reprezentovaný {sp500_ticker or 'nedostupným benchmarkom'}.")

        q05, q50, q95 = np.percentile(final_values, [5, 50, 95])
        if len(sp500_final_values):
            sp_q50 = float(np.percentile(sp500_final_values, 50))
            diff_q50 = q50 - sp_q50
            qcols = st.columns(5)
            with qcols[0]:
                kpi_card("Portfólio · 5. percentil", f"{q05:,.2f} {base_sym}", fmt_pct_signed((q05 / capital - 1) * 100), tone_for_sign(q05 - capital))
            with qcols[1]:
                kpi_card("Portfólio · medián", f"{q50:,.2f} {base_sym}", fmt_pct_signed((q50 / capital - 1) * 100), tone_for_sign(q50 - capital))
            with qcols[2]:
                kpi_card("S&P 500 · medián", f"{sp_q50:,.2f} {base_sym}", fmt_pct_signed((sp_q50 / capital - 1) * 100), tone_for_sign(sp_q50 - capital))
            with qcols[3]:
                kpi_card("Rozdiel mediánov", f"{diff_q50:+,.2f} {base_sym}", "Portfólio mínus S&P 500", tone_for_sign(diff_q50))
            with qcols[4]:
                kpi_card("Portfólio · 95. percentil", f"{q95:,.2f} {base_sym}", fmt_pct_signed((q95 / capital - 1) * 100), tone_for_sign(q95 - capital))
        else:
            qcols = st.columns(3)
            with qcols[0]:
                kpi_card("Slabší scenár · 5. percentil", f"{q05:,.2f} {base_sym}", fmt_pct_signed((q05 / capital - 1) * 100), tone_for_sign(q05 - capital))
            with qcols[1]:
                kpi_card("Medián simulácií", f"{q50:,.2f} {base_sym}", fmt_pct_signed((q50 / capital - 1) * 100), tone_for_sign(q50 - capital))
            with qcols[2]:
                kpi_card("Silnejší scenár · 95. percentil", f"{q95:,.2f} {base_sym}", fmt_pct_signed((q95 / capital - 1) * 100), tone_for_sign(q95 - capital))

        st.markdown("#### Medián každej vybranej akcie oproti S&P 500")
        st.caption("Každá čiara samostatne modeluje investíciu celého zadaného kapitálu do jednej akcie. Nejde o vážené portfólio.")
        compare_mc_tickers = st.multiselect(
            "Akcie zahrnuté do porovnania",
            options=valid_tickers,
            default=valid_tickers,
            key="mc_compare_tickers",
            help="Predvolene sú zahrnuté všetky načítané akcie a ETF. Odznačením zúžiš graf, ak je príliš hustý.",
        )
        fig_compare = go.Figure()
        summary_rows: list[dict[str, Any]] = []
        if len(sp500_historical) >= 20:
            summary_rows.append({
                "Ticker": "S&P 500",
                f"Medián hodnoty ({base})": float(np.percentile(sp500_final_values, 50)) if len(sp500_final_values) else np.nan,
                "Medián výnosu (%)": (float(np.percentile(sp500_final_values, 50)) / capital - 1) * 100 if len(sp500_final_values) else np.nan,
                f"5. percentil ({base})": float(np.percentile(sp500_final_values, 5)) if len(sp500_final_values) else np.nan,
                f"95. percentil ({base})": float(np.percentile(sp500_final_values, 95)) if len(sp500_final_values) else np.nan,
                "Simulácie končiace stratou (%)": float(np.mean(sp500_final_values < capital) * 100) if len(sp500_final_values) else np.nan,
            })
            fig_compare.add_trace(go.Scatter(x=x_days, y=sp500_median_path, mode="lines",
                                             line=dict(color=GOLD, width=3.5, dash="dash"), name=f"S&P 500 ({sp500_ticker})"))

        palette = [ACCENT, ACCENT_2, "#FF9E80", "#DDA0DD", "#69D2E7", "#C3E88D", "#FF8FAB", "#B8C0FF", "#F4A261"]
        for idx, ticker in enumerate(compare_mc_tickers):
            if ticker not in prices_all.columns:
                continue
            ticker_returns = prices_all[ticker].pct_change(fill_method=None).dropna().to_numpy(dtype=float)
            ticker_returns = ticker_returns[np.isfinite(ticker_returns) & (ticker_returns > -1)]
            if len(ticker_returns) < 20:
                continue
            ticker_sampled = rng.choice(ticker_returns, size=(mc_days, mc_sims), replace=True)
            ticker_paths = capital * np.cumprod(1 + ticker_sampled, axis=0)
            ticker_median = np.median(ticker_paths, axis=1)
            ticker_final = ticker_paths[-1, :]
            fig_compare.add_trace(go.Scatter(x=x_days, y=ticker_median, mode="lines",
                                             line=dict(color=palette[idx % len(palette)], width=1.8), name=ticker))
            summary_rows.append({
                "Ticker": ticker,
                f"Medián hodnoty ({base})": float(np.percentile(ticker_final, 50)),
                "Medián výnosu (%)": (float(np.percentile(ticker_final, 50)) / capital - 1) * 100,
                f"5. percentil ({base})": float(np.percentile(ticker_final, 5)),
                f"95. percentil ({base})": float(np.percentile(ticker_final, 95)),
                "Simulácie končiace stratou (%)": float(np.mean(ticker_final < capital) * 100),
            })
        fig_compare.update_layout(title="Mediánová cesta: jednotlivé tickery vs. S&P 500",
                                  xaxis_title="Obchodný deň", yaxis_title=f"Modelová hodnota ({base})")
        st.plotly_chart(make_plotly_dark(fig_compare, 500), use_container_width=True)
        chart_note("Každá čiara ukazuje medián scenárov pre jednu akciu, zlatá prerušovaná čiara je S&P 500. Porovnanie vychádza z minulých výnosov, takže nezachytáva budúce zmeny trhu.")
        if summary_rows:
            summary_df = pd.DataFrame(summary_rows).sort_values("Medián výnosu (%)", ascending=False, na_position="last")
            st.markdown("#### Porovnávacia tabuľka výsledkov")
            st.dataframe(summary_df.style.format({
                f"Medián hodnoty ({base})": "{:,.2f}", "Medián výnosu (%)": "{:+.2f}%",
                f"5. percentil ({base})": "{:,.2f}", f"95. percentil ({base})": "{:,.2f}",
                "Simulácie končiace stratou (%)": "{:.2f}%",
            }, na_rep="—"), use_container_width=True, hide_index=True)
            st.download_button("⬇ Stiahnuť Monte Carlo porovnanie do CSV",
                               data=summary_df.to_csv(index=False).encode("utf-8-sig"),
                               file_name="oliver_leso_monte_carlo_comparison.csv", mime="text/csv")
        st.markdown("<div class='warning-box'><b>Ako interpretovať:</b> Medián je prostredná hodnota nasimulovaných scenárov, nie predpoveď. S&P 500 slúži ako porovnávací benchmark. Individuálne akcie sú simulované samostatne, takže druhý graf neuchováva historické korelácie medzi akciami. Model nezachytáva spoľahlivo zmenu trhového režimu, budúce nečakané udalosti, poplatky, dane ani menové konverzie.</div>", unsafe_allow_html=True)
    else:
        st.warning("Na Monte Carlo simuláciu je potrebných aspoň 20 dostupných historických denných výnosov portfólia.")

# -----------------------------------------------------------------------------
# TAB: fundamentals
# -----------------------------------------------------------------------------
with tab_fundamentals:
    st.markdown("<div class='section-kicker'>Business quality</div>", unsafe_allow_html=True)
    st.subheader("Fundamenty a valuácia spoločností")
    st.markdown("Údaje pochádzajú z dostupných polí Yahoo Finance. Pomlčka znamená chýbajúcu hodnotu, nie nulu.")

    fundamental_cols = ["Ticker", "Spoločnosť", "Sektor", "Trhová kapitalizácia", "P/E (TTM)", "Forward P/E", "P/B", "EV/EBITDA", "Zisková marža (%)", "ROE (%)", "Rast tržieb (%)", "Rast zisku (%)", "Debt/Equity", "Dividendový výnos (%)"]
    fundamental_view = metrics[fundamental_cols].copy()
    st.dataframe(
        fundamental_view.style.format({
            "Trhová kapitalizácia": lambda v: pretty_large(v),
            "P/E (TTM)": "{:.2f}", "Forward P/E": "{:.2f}", "P/B": "{:.2f}", "EV/EBITDA": "{:.2f}",
            "Zisková marža (%)": "{:.2f}%", "ROE (%)": "{:.2f}%", "Rast tržieb (%)": "{:+.2f}%", "Rast zisku (%)": "{:+.2f}%", "Debt/Equity": "{:.2f}", "Dividendový výnos (%)": "{:.2f}%",
        }, na_rep="—"), use_container_width=True, hide_index=True
    )
    note_fund = missing_note(metrics)
    if note_fund:
        st.info(note_fund)
    st.download_button("⬇ Stiahnuť fundamenty do CSV", data=fundamental_view.to_csv(index=False).encode("utf-8-sig"),
                       file_name="oliver_leso_fundamentals.csv", mime="text/csv")

    st.markdown("#### Porovnanie vybraného ukazovateľa")
    fcol1, fcol2 = st.columns([1, 2])
    with fcol1:
        fundamental_metric = st.selectbox("Ukazovateľ", ["P/E (TTM)", "Forward P/E", "P/B", "EV/EBITDA", "Zisková marža (%)", "ROE (%)", "Rast tržieb (%)", "Rast zisku (%)", "Debt/Equity", "Dividendový výnos (%)"], index=0)
    with fcol2:
        fund_data = metrics[["Ticker", fundamental_metric]].dropna().sort_values(fundamental_metric)
        fig = px.bar(fund_data, x="Ticker", y=fundamental_metric, color=fundamental_metric,
                     color_continuous_scale=[ACCENT_2, "#64748B", GOLD], title=f"Porovnanie: {fundamental_metric}")
        fig.update_layout(coloraxis_showscale=False)
        is_pct = "(%)" in fundamental_metric
        fig.update_traces(hovertemplate="<b>%{x}</b><br>%{y:.2f}" + ("%" if is_pct else "") + "<extra></extra>")
        fig.update_yaxes(tickformat=".2f", ticksuffix="%" if is_pct else "")
        st.plotly_chart(make_plotly_dark(fig, 390), use_container_width=True)
        chart_note("Porovnanie jedného ukazovateľa naprieč tickermi. Vždy zváž odvetvie a definíciu ukazovateľa, lebo bežné hodnoty sa líšia podľa typu podnikania.")

    with st.expander("Na čo si dať pozor pri fundamentálnych metrikách"):
        st.markdown("""
        - **P/E:** cena voči zisku na akciu. Pri stratových firmách môže byť nedostupné alebo zavádzajúce; nízke P/E samo osebe neznamená podhodnotenie.
        - **Forward P/E:** pracuje s odhadovaným budúcim ziskom, ktorý sa nemusí naplniť.
        - **EV/EBITDA:** porovnáva hodnotu firmy vrátane dlhu voči EBITDA. Nie je vhodné pre všetky odvetvia, napríklad banky.
        - **ROE:** účtovný zisk v pomere k vlastnému imaniu. Veľké zadlženie alebo záporné imanie môže číslo skresliť.
        - **Debt/Equity:** približný ukazovateľ zadlženia. Definícia a porovnateľnosť sa môžu medzi sektormi líšiť.
        - **Rast tržieb / zisku:** závisí od obdobia porovnania a môže obsahovať jednorazové vplyvy.
        - **Dividendový výnos:** historická alebo indikovaná hodnota sa môže meniť; vysoký výnos môže sprevádzať aj pokles ceny.
        """)

    st.markdown("#### Detail vybranej spoločnosti")
    profile_ticker = st.selectbox("Ticker spoločnosti", valid_tickers, key="profile_ticker")
    profile_info = infos.get(profile_ticker, {})
    profile_metrics = metrics.loc[metrics["Ticker"] == profile_ticker].iloc[0]
    st.markdown(f"### {safe_name(profile_info, profile_ticker)} <span class='mono' style='color:{ACCENT}'>· {profile_ticker}</span>", unsafe_allow_html=True)
    summary_en = str(profile_info.get("longBusinessSummary", "") or "")
    if summary_en:
        st.markdown(f"<div class='desc-card'>{html.escape(summary_en)}</div>", unsafe_allow_html=True)
    else:
        st.info("Opis spoločnosti nie je v dátovom zdroji dostupný.")
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        metric_card("Sektor", str(profile_info.get("sector") or "Neznámy"), str(profile_info.get("industry") or "Odvetvie neuvedené"))
    with d2:
        metric_card("Trhová kapitalizácia", pretty_large(profile_metrics["Trhová kapitalizácia"]), f"Hodnota v mene {base}")
    with d3:
        metric_card("Tržby", pretty_large(profile_metrics["Tržby"]), "Posledná dostupná celková hodnota")
    with d4:
        metric_card("Čistý zisk", pretty_large(profile_metrics["Čistý zisk"]), "Posledná dostupná hodnota")

# -----------------------------------------------------------------------------
# TAB: SWOT
# -----------------------------------------------------------------------------
with tab_swot:
    st.markdown("<div class='section-kicker'>Company-specific review</div>", unsafe_allow_html=True)
    st.subheader("SWOT analýza vybranej spoločnosti")
    st.markdown("Vyber ľubovoľný načítaný ticker. SWOT kombinuje fundamentálne a technické ukazovatele s nedávnymi správami pre tento konkrétny ticker.")
    st.markdown("<div class='warning-box'><b>Ako funguje mediálna časť SWOT:</b> aplikácia používa titulok a krátky popis z RSS feedu. Kľúčové slová len navrhnú kategóriu. Nie je to plnohodnotné prečítanie článku ani spoľahlivý AI sentiment; pred rozhodnutím otvor zdroj a over kontext.</div>", unsafe_allow_html=True)

    swot_ticker = st.selectbox("Firma / ticker pre SWOT", valid_tickers, key="swot_ticker")
    swot_row = metrics.loc[metrics["Ticker"] == swot_ticker].iloc[0]
    swot_info = infos.get(swot_ticker, {})
    st.markdown(f"### {safe_name(swot_info, swot_ticker)} <span class='mono' style='color:{ACCENT}'>· {swot_ticker}</span>", unsafe_allow_html=True)
    swot_top = st.columns(4)
    swot_top[0].metric("Sektor", str(swot_row.get("Sektor", "Neznámy")))
    swot_top[1].metric("3M výnos", fmt_pct(swot_row.get("3M (%)")))
    swot_top[2].metric("Zisková marža", fmt_pct(swot_row.get("Zisková marža (%)")))
    swot_top[3].metric("Ročná volatilita", fmt_pct(swot_row.get("Volatilita (%)")))

    swot = build_swot(swot_ticker, metrics, infos)
    swot_layout = [
        ("Silné stránky", "✦", ACCENT),
        ("Slabé stránky", "◇", GOLD),
        ("Príležitosti", "↗", ACCENT_2),
        ("Hrozby", "⚠", RED),
    ]
    swot_pairs = [(swot_layout[0], swot_layout[1]), (swot_layout[2], swot_layout[3])]
    for left_item, right_item in swot_pairs:
        left_col, right_col = st.columns(2, gap="large")
        for col, item in ((left_col, left_item), (right_col, right_item)):
            title, symbol, accent = item
            with col:
                st.markdown(f"<div class='swot-head'><div style='font-weight:800;font-size:18px;color:{accent}'>{symbol} &nbsp; {title}</div></div>", unsafe_allow_html=True)
                for point_title, point_text in swot[title]:
                    st.markdown(f"**{point_title}**")
                    st.write(point_text)
                quadrant_news = news_signal_groups_by_ticker.get(swot_ticker, {}).get(title, [])
                for news_idx, story in enumerate(quadrant_news[:3]):
                    st.markdown(f"**📰 Mediálny signál: {story['Title']}**")
                    st.write(story.get("SWOT rationale", "Automatické tematické zaradenie titulku; over celý článok."))
                    if story.get("Summary"):
                        st.caption("Krátky popis zo zdroja: " + story["Summary"][:360] + ("…" if len(story["Summary"]) > 360 else ""))
                    st.caption(f"Zdroj: {story.get('Publisher') or story.get('Feed', 'RSS')} · {story.get('Published display', 'Dátum neuvedený')} · zaradenie je heuristické")
                    st.link_button("Otvoriť pôvodný článok", story["URL"], key=f"swot_news_{swot_ticker}_{title}_{news_idx}", use_container_width=True)
                if not quadrant_news:
                    st.caption("Žiadna dostupná správa nebola automaticky zaradená do tejto kategórie.")

    ticker_all_news = news_by_ticker.get(swot_ticker, [])
    with st.expander(f"Všetky dostupné správy pre {swot_ticker} ({len(ticker_all_news)})"):
        if not ticker_all_news:
            st.info("Pre tento ticker sa nepodarilo získať správy. To neznamená, že žiadne neexistujú.")
        for story_idx, story in enumerate(ticker_all_news):
            classification = classify_news_signal(story)
            category_label = classification[0] if classification else "Bez automatického zaradenia"
            st.markdown(f"**{story['Title']}**")
            st.caption(f"{story.get('Publisher') or story.get('Feed', 'Zdroj')} · {story.get('Published display', 'Dátum neuvedený')} · SWOT signál: {category_label}")
            if story.get("Summary"):
                st.write(story["Summary"])
            st.link_button("Prečítať článok", story["URL"], key=f"swot_all_news_{swot_ticker}_{story_idx}")

    company_summary = swot_info.get("longBusinessSummary")
    if company_summary:
        with st.expander("Firemný opis zo zdroja dát"):
            st.write(company_summary)
    if np.isfinite(as_float(swot_row.get("Analytický cieľ"))):
        st.caption(f"Priemerný cieľ analytikov: {as_float(swot_row.get('Analytický cieľ')):,.2f} {base} · odhadovaný potenciál voči poslednej cene: {fmt_pct_signed(swot_row.get('Potenciál k cieľu (%)'))}. Konsenzus sa môže meniť a nie je zárukou výnosu.")
    st.caption(f"Cenové a fundamentálne údaje: Yahoo Finance cez yfinance, snapshot {fetched_at} (Europe/Prague). SWOT prahy aj klasifikácia správ sú orientačné a môžu sa mýliť.")

# -----------------------------------------------------------------------------
# TAB: glossary
# -----------------------------------------------------------------------------
with tab_glossary:
    st.markdown("<div class='section-kicker'>Learn the metrics</div>", unsafe_allow_html=True)
    st.subheader("Slovník metrík bez zbytočného žargónu")
    glossary = [
        ("Ticker", "Ticker je burzový symbol, ktorým identifikuješ obchodovaný nástroj. Napríklad AAPL označuje akcie Apple a SPY ETF sledujúci index S&P 500.", "Vždy skontroluj, či symbol označuje správnu firmu, burzu a menu. Jedna firma môže mať viac symbolov podľa burzy alebo triedy akcií.", "Ak zadáš ASML, aplikácia sa pokúsi načítať tento symbol z Yahoo Finance. Pre európsku kotáciu môže byť potrebný symbol s príponou burzy.", "Ticker sám osebe nehovorí nič o kvalite ani o tom, či je akcia lacná."),
        ("Výnos (1D / 1M / 3M / 6M / 1Y)", "Percentuálna zmena ceny medzi začiatkom a koncom zvoleného obdobia. Horizont sa počíta v obchodných dňoch, nie presných kalendárnych mesiacoch.", "Kladné číslo znamená, že cena vzrástla; záporné, že klesla. Pri porovnávaní používaj rovnaký horizont pre všetky akcie.", "Ak cena stúpne zo 100 na 110, výnos je +10,00 %. Ak potom klesne zo 110 na 100, strata z vrcholu je približne −9,09 %, nie −10 %.", "Ide o historický pohyb ceny, nie sľub budúceho výnosu. Nezahŕňa tvoje poplatky, dane ani celkový výnos z dividend."),
        ("Ročná volatilita", "Odhad veľkosti kolísania denných výnosov prepočítaný na ročné meradlo. V modeli sa denná smerodajná odchýlka násobí odmocninou z približne 252 obchodných dní.", "Vyššie číslo znamená, že cena historicky kolísala viac. Nehovorí však, či pohyby boli prevažne nahor alebo nadol.", "Ak má akcia volatilitu 40,00 % a iná 15,00 %, prvá historicky vykazovala väčšie pohyby. To automaticky neznamená horšiu investíciu.", "Volatilita vychádza z minulosti a môže sa rýchlo zmeniť. Nejde o maximálnu možnú stratu."),
        ("RSI (14)", "Relative Strength Index je oscilátor, ktorý porovnáva priemerné nedávne rastové a klesajúce pohyby za 14 období. Pohybuje sa od 0 do 100.", "Hodnota nad 70 sa často označuje ako prekúpená a pod 30 ako prepredaná. Ber to ako upozornenie na silný pohyb, nie ako príkaz obchodovať opačným smerom.", "RSI 75,00 znamená, že posledné pohyby boli silno naklonené rastu. V silnom rastovom trende môže RSI zostať nad 70 dlho.", "RSI môže dávať falošné signály a treba ho posudzovať spolu s trendom, úrovňami ceny a fundamentmi."),
        ("SMA 20 / 50 / 200", "SMA je jednoduchý kĺzavý priemer zatváracích cien za posledných 20, 50 alebo 200 obchodných dní.", "Cena nad SMA môže podporovať rastový pohľad; cena pod SMA môže signalizovať slabší trend. SMA 200 reaguje pomalšie než SMA 20.", "Ak je cena nad SMA 50 a SMA 50 je nad SMA 200, technickí analytici to často považujú za usporiadanie podporujúce rastový trend.", "Kĺzavé priemery zaostávajú za cenou a nepredpovedajú obrat."),
        ("MACD histogram", "MACD porovnáva dva exponenciálne kĺzavé priemery a ich signálnu čiaru. Histogram je rozdiel medzi čiarou MACD a signálnou čiarou.", "Histogram nad nulou znamená, že MACD je nad svojou signálnou čiarou; pod nulou opak. Zmena smeru môže naznačovať zmenu momenta.", "Keď histogram prejde z negatívnych na pozitívne hodnoty, rastové momentum sa mohlo zlepšiť.", "MACD je odvodený od minulých cien a v bočnom trhu môže vytvárať veľa falošných signálov."),
        ("ATR (14)", "Average True Range meria priemerný cenový rozsah vrátane medzery medzi predchádzajúcim zatvorením a dnešným maximom či minimom.", "ATR je vyjadrený v mene ceny a meria veľkosť pohybu, nie jeho smer. Pri porovnávaní drahých a lacných akcií zváž aj ATR ako percento ceny.", "ATR 5,00 USD pri akcii za 100,00 USD zodpovedá približne 5,00 % ceny ako orientačnej miere bežného rozsahu.", "ATR nie je predpoveď presnej budúcej ceny ani garancia, že sa cena zmestí do tohto rozsahu."),
        ("Technické skóre 0–100", "Interný súhrn pravidiel aplikácie: kladný 3-mesačný výnos (25 bodov), kladný 6-mesačný výnos (15), cena nad SMA 50 (20), SMA 50 nad SMA 200 (20) a RSI medzi 50 a 70 (20).", "Vyššie skóre znamená, že viac z týchto vopred určených podmienok bolo splnených. Ak niektorý údaj chýba, skóre sa počíta len z dostupných častí.", "Skóre 80,00/100 neznamená 80 % pravdepodobnosť zisku. Znamená, že dostupné pravidlá boli splnené vo vysokej miere.", "Nie je to rating analytikov, ocenenie firmy ani validovaný prediktívny model."),
        ("Beta voči benchmarku", "Beta porovnáva, ako sa historické výnosy akcie menili spolu s vybraným benchmarkom, napríklad SPY.", "Beta okolo 1 znamená približne podobnú citlivosť ako benchmark; nad 1 historicky väčšiu citlivosť a medzi 0 a 1 menšiu. Záporná beta znamená opačný vzťah v danom období.", "Beta 1,30 neznamená, že akcia vždy stúpne o 1,30 % pri raste indexu o 1 %. Je to štatistický vzťah, nie pevný pomer.", "Beta závisí od benchmarku a obdobia. Sama nevyjadruje celé riziko."),
        ("Trhová kapitalizácia", "Približná trhová hodnota vlastného kapitálu firmy: cena jednej akcie vynásobená počtom akcií v obehu.", "Zvyčajne sa rozlišujú veľké, stredné a malé firmy. Väčšia firma nemusí byť bezpečnejšia a menšia automaticky nie je lepšia rastová investícia.", "Kapitalizácia 100,00 mld. USD znamená, že trh oceňuje akciový kapitál firmy približne na túto sumu.", "Nezahŕňa priamo čistý dlh. Pri porovnávaní celej prevádzky môže byť užitočnejšia enterprise value."),
        ("P/E (TTM) a Forward P/E", "P/E je pomer ceny akcie k zisku na akciu. TTM vychádza zo zisku za posledných 12 mesiacov; Forward P/E používa odhad budúceho zisku.", "Nižšie P/E znamená nižšiu cenu za jednotku zisku, no môže odrážať aj slabý výhľad. Porovnávaj podobné firmy v rovnakom odvetví.", "P/E 20,00 znamená, že cena predstavuje približne 20-násobok ročného zisku na akciu.", "Pri stratovej firme môže byť P/E nezmyselné alebo nedostupné."),
        ("P/B", "Price-to-Book porovnáva trhovú kapitalizáciu s účtovnou hodnotou vlastného imania.", "Často sa používa pri bankách a finančných firmách, ale stále vyžaduje kontext.", "P/B 2,00 znamená, že trh oceňuje vlastný kapitál firmy približne na dvojnásobok jeho účtovnej hodnoty.", "Pri zápornom alebo veľmi nízkom vlastnom imaní sa ukazovateľ ťažko interpretuje."),
        ("EV/EBITDA", "EV je hodnota podniku vrátane čistého dlhu a EBITDA je približný prevádzkový zisk pred úrokmi, daňami a odpismi.", "Pomáha porovnať firmy s odlišným financovaním, najlepšie medzi firmami podobného typu.", "EV/EBITDA 10,00 znamená, že hodnota podniku je približne desaťnásobkom ročnej EBITDA.", "EBITDA nie je voľný peňažný tok a neodpočítava investície. Pri bankách býva nevhodný."),
        ("Zisková marža", "Podiel čistého zisku na tržbách. Ukazuje, koľko z jednej jednotky tržieb zostane po nákladoch a daniach.", "Vyššia marža môže naznačovať cenovú silu alebo efektívnosť. Dôležitý je vývoj v čase a porovnanie s konkurentmi.", "Marža 12,00 % znamená, že z každých 100 € tržieb firma vykáže približne 12 € čistého zisku.", "Jednorazové udalosti a účtovné položky môžu maržu dočasne skresliť."),
        ("ROE (Return on Equity)", "Zisk v pomere k vlastnému imaniu akcionárov. Pomáha posúdiť, ako efektívne firma využíva účtovný kapitál.", "Stabilne dobré ROE môže byť pozitívne, ale číslo vždy porovnaj s dlhom a maržami. Veľké zadlženie môže ROE umelo zvýšiť.", "ROE 15,00 % znamená zisk približne 15 € na každých 100 € účtovného vlastného imania.", "Pri zápornom alebo veľmi malom vlastnom imaní môže byť ROE zavádzajúce."),
        ("Debt/Equity", "Pomer dlhu k vlastnému imaniu. Definícia dlhu sa môže u poskytovateľov dát líšiť.", "Vyšší pomer znamená väčšie využitie dlhového financovania; prijateľná úroveň sa líši podľa odvetvia a stability cash flow.", "Pomer 100,00 môže znamenať dlh približne 100 % vlastného imania; vždy over definíciu poskytovateľa.", "Nie je priamo porovnateľný medzi všetkými sektormi."),
        ("Dividendový výnos", "Ročná dividenda na akciu vydelená aktuálnou cenou.", "Vyšší výnos môže byť príťažlivý pre príjem, ale porovnávaj aj schopnosť firmy dividendu financovať.", "Ak akcia stojí 100,00 € a ročná dividenda je 4,00 €, výnos je 4,00 %.", "Dividenda nie je garantovaná a cena akcie môže klesnúť viac než výplata dividendy."),
        ("Korelácia", "Štatistika od −1 do +1, ktorá ukazuje, ako sa dva súbory výnosov historicky pohybovali spolu.", "+1 znamená pohyb takmer rovnakým smerom, 0 slabý lineárny vzťah a −1 opačný pohyb.", "Ak majú dve akcie koreláciu 0,20, ich výnosy mali relatívne slabý lineárny vzťah.", "Korelácia nie je príčinnosť a v krízach sa vzťahy môžu meniť."),
        ("Sharpe ratio", "Pomer historického výnosu nad bezrizikovú sadzbu k volatilite portfólia.", "Vyššia hodnota znamená viac historického nadvýnosu na jednotku kolísania.", "Sharpe 1,00 neznamená 100 % zisk. Je to pomer rizika a nadvýnosu, nie percentuálny výnos.", "Je citlivý na obdobie a zvolenú bezrizikovú sadzbu."),
        ("CAGR / anualizovaný výnos", "CAGR je zložená ročná miera rastu medzi počiatočnou a konečnou hodnotou.", "Pomáha porovnávať rôzne dlhé obdobia, no nezobrazuje cestu medzi začiatkom a koncom ani medzitýnne prepady.", "CAGR 8,00 % znamená, že hodnota rástla zloženým tempom približne 8,00 % ročne.", "V aplikácii ide o historický odhad z denných výnosov; krátke obdobia ho môžu skresliť."),
        ("Max drawdown (maximálny prepad)", "Najväčší percentuálny pokles od predchádzajúceho maxima hodnoty po nasledujúce minimum.", "Ukazuje hĺbku historického prepadu, ktorý investor musel zvládnuť. Nie je to to isté ako volatilita.", "Ak portfólio klesne zo 100 000 € na 70 000 €, prepad od vrcholu je −30,00 %.", "Budúci prepad môže byť hlbší. Na návrat zo straty 30,00 % je potrebný rast približne 42,86 %."),
        ("VaR 95 % a CVaR 95 %", "Historický jednodňový VaR 95 % odhaduje hranicu straty, ktorú historické výnosy prekročili približne v najhorších 5 % dní. CVaR priemeruje výnosy v tejto najhoršej časti.", "VaR odpovedá na otázku, aká strata je hranicou zlého 5 % dňa. CVaR, aká bola priemerná strata v najhorších dňoch.", "Ak VaR vyjde 500,00 € pri kapitále 10 000,00 €, nejde o maximálnu stratu.", "Odhady závisia od historického obdobia a nezachytávajú spoľahlivo extrémne udalosti."),
        ("HHI a efektívny počet pozícií", "HHI je súčet druhých mocnín percentuálnych váh pozícií. Efektívny počet je 1 delené súčtom druhých mocnín váh vyjadrených ako desatinné čísla.", "Vyšší HHI znamená koncentrovanejší model. Efektívny počet hovorí, koľko rovnako veľkých pozícií by zodpovedalo danej koncentrácii.", "Pri štyroch rovnomerne vážených akciách je efektívny počet 4,00.", "Počet tickerov nadhodnocuje diverzifikáciu, ak vlastnia podobné firmy alebo reagujú na rovnaké riziká."),
        ("Rovnaká váha vs. inverzná volatilita", "Rovnaká váha rozdelí modelový kapitál rovnomerne. Inverzná volatilita dáva väčší podiel aktívam s menším kolísaním.", "Rovnaká váha sa ľahko chápe. Inverzná volatilita môže znížiť dominanciu najvolatilnejších titulov, ale nepočíta korelácie.", "Pri 5 rovnomerne vážených pozíciách dostane každá 20,00 % modelového kapitálu.", "Inverzná volatilita nie je plná risk parity a ani jedna metóda neurčuje optimálne portfólio."),
        ("Monte Carlo bootstrap", "Aplikácia opakovane náhodne vyberá pozorované denné výnosy z histórie a skladá z nich veľa možných ciest hodnoty.", "5. percentil predstavuje slabší výsledok v simulovanej množine, medián prostredný výsledok a 95. percentil silnejší výsledok.", "Ak je 5. percentil po roku 8 000,00 €, približne 5 % nasimulovaných ciest skončilo na tejto hodnote alebo nižšie.", "Nie je to pravdepodobnostná garancia ani predpoveď. Bootstrap nezachytáva režimové zmeny."),
        ("Vstup, stop-loss a pomer výnosu k riziku", "Vstupná cena je nákupná cena, stop-loss je cena, pri ktorej by si obmedzil stratu, a cieľ je cena, pri ktorej plánuješ zisk realizovať.", "Kalkulačka najprv vypočíta riziko na jednu akciu (vstup mínus stop-loss) a potom počet kusov v rámci rizikového limitu a kapitálu.", "Ak vstup = 100,00, stop-loss = 95,00 a cieľ = 110,00, riskuješ 5,00 na akciu a potenciálne získavaš 10,00; pomer je 2,00 : 1.", "Stop-loss nezaručí vykonanie presne na zadanej cene. Cenová medzera, spread, poplatky a dane menia výsledok."),
        ("Mena prepočtu", "Všetky ceny a hodnoty v aplikácii sa prepočítajú do zvolenej meny kurzom z Yahoo Finance (napr. USDEUR=X).", "Ak chceš porovnávať akcie z rôznych burz, vyber jednu základnú menu. Výnosy sa tým zmenia len o pohyb kurzu, nie o pohyb ceny firmy v pôvodnej mene.", "Ak akcia stojí 100 USD a kurz je 0,90 EUR za 1 USD, cena v mene prepočtu je 90,00 EUR.", "Kurz sa mení každý deň. Historické prepočty používajú kurz pre konkrétny deň, takže minulé hodnoty sa môžu mierne líšiť od tvojich kalkulácií."),
    ]
    for term, what_it_is, how_to_read, example, limitation in glossary:
        with st.expander(term):
            st.markdown(f"**Čo to znamená:** {what_it_is}")
            st.markdown(f"**Ako to čítať:** {how_to_read}")
            st.markdown(f"**Príklad:** {example}")
            st.markdown(f"**Na čo si dať pozor:** {limitation}")

    st.markdown("---")
    st.markdown("<div class='warning-box'><b>Dôležité upozornenie</b><br>Táto aplikácia je vzdelávací analytický nástroj. Údaje môžu byť oneskorené, neúplné alebo chybné. Výsledky nezohľadňujú automaticky poplatky, dane, spread, likviditu ani individuálnu situáciu investora. Skóre, technické indikátory, historické štatistiky a simulácie nie sú investičným odporúčaním ani zárukou budúcich výsledkov.</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown(
    f"<div style='display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:{MUTED};font-size:11px;padding:4px 2px 16px'><span class='mono'>OLIVER LESO · EQUITY RESEARCH STUDIO</span><span>Built with Python · Streamlit · Plotly · yfinance</span><span>For education & research only</span></div>",
    unsafe_allow_html=True,
)
