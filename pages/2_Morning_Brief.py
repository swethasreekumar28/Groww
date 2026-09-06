import streamlit as st
import yfinance as yf
from datetime import datetime
from supabase import create_client, Client
from streamlit_cookies_controller import CookieController
 
# ============================================================
# PAGE CONFIG
# ============================================================
 
st.set_page_config(
    page_title="Morning Brief - GrowwStock",
    page_icon="🌅",
    layout="wide",
)
 
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
 
.stApp {
    background:
        radial-gradient(circle at 8% 8%, rgba(124, 131, 253, 0.10), transparent 42%),
        radial-gradient(circle at 92% 15%, rgba(43, 58, 140, 0.08), transparent 42%),
        #f5f6ff;
}
 
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #141b3a 0%, #1e2a63 100%);
}
 
section[data-testid="stSidebar"] * {
    color: white !important;
}
 
.brief-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 32px;
    font-weight: 700;
    color: #141b3a;
}
.brief-sub { color: #2b3a8c; font-size: 14px; margin-bottom: 20px; }
.brief-section {
    background: white;
    border: 1px solid #e0e4fb;
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 16px;
}
.brief-heading {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 15px;
    font-weight: 700;
    color: #141b3a;
    margin-bottom: 10px;
}
.brief-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid #f0f1fb;
    font-size: 14px;
}
.brief-row:last-child { border-bottom: none; }
</style>
""", unsafe_allow_html=True)
 
# ============================================================
# SUPABASE SETUP (same credentials as the main app)
# ============================================================
 
SUPABASE_URL = "https://byxfjgopvafrkilaulco.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ5eGZqZ29wdmFmcmtpbGF1bGNvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg1OTkzNjQsImV4cCI6MjEwNDE3NTM2NH0.66o3N0H3MKilfGaNZesSpD3d89hUzL8oj9k0gaGa12Q"
 
 
@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)
 
 
supabase = get_supabase_client()
cookie_controller = CookieController()
 
 
def get_current_user_id():
    access_token = cookie_controller.get("sb_access_token")
    refresh_token = cookie_controller.get("sb_refresh_token")
    if access_token and refresh_token:
        try:
            supabase.auth.set_session(access_token, refresh_token)
            user = supabase.auth.get_user()
            if user and user.user:
                return user.user.id
        except Exception:
            pass
    return None
 
 
# ============================================================
# SHARED LOGIC (mirrors app.py so numbers match exactly)
# ============================================================
 
def calculate_meaningful_change_score(today_change, visit_change, volatility):
    today_score = min(abs(today_change) / 5 * 30, 30)
    visit_score = min(abs(visit_change) / 10 * 30, 30)
    if volatility > 0:
        volatility_ratio = abs(today_change) / volatility
        volatility_score = min(volatility_ratio / 3 * 40, 40)
    else:
        volatility_score = 0
    return round(min(today_score + visit_score + volatility_score, 100), 2)
 
 
def get_change_level(score):
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"
 
 
@st.cache_data(ttl=60)
def fetch_stock_history(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.history(period="1mo", timeout=10)
 
 
def get_watchlist(user_id):
    response = (
        supabase.table("watchlist")
        .select("symbol")
        .eq("user_id", user_id)
        .order("added_at")
        .execute()
    )
    return [row["symbol"] for row in (response.data or [])]
 
 
def get_last_snapshot(user_id, symbol):
    response = (
        supabase.table("snapshots")
        .select("last_price")
        .eq("user_id", user_id)
        .eq("symbol", symbol)
        .execute()
    )
    if response.data:
        return response.data[0]["last_price"]
    return None
 
 
MARKET_PULSE_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS",
    "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS",
    "LT.NS", "MARUTI.NS", "TITAN.NS", "TATAMOTORS.NS",
]
 
 
def get_top_discoveries(tracked_symbols, top_n=3):
    candidates = [s for s in MARKET_PULSE_UNIVERSE if s not in tracked_symbols]
    discoveries = []
    for symbol in candidates:
        try:
            info = fetch_stock_history(symbol)
            if len(info) < 2:
                continue
            latest = float(info["Close"].iloc[-1])
            prev = float(info["Close"].iloc[-2])
            if prev == 0:
                continue
            change_pct = ((latest - prev) / prev) * 100
            daily_returns = info["Close"].pct_change().dropna() * 100
            volatility = float(daily_returns.std()) if not daily_returns.empty else 0.0
            score = calculate_meaningful_change_score(change_pct, 0, volatility)
            discoveries.append({
                "symbol": symbol, "change": change_pct, "score": score,
                "level": get_change_level(score),
            })
        except Exception:
            continue
    discoveries.sort(key=lambda d: d["score"], reverse=True)
    return discoveries[:top_n]
 
 
# ============================================================
# AUTH GATE
# ============================================================
 
current_user_id = get_current_user_id()
 
if not current_user_id:
    st.markdown('<div class="brief-title">🌅 Morning Brief</div>', unsafe_allow_html=True)
    st.info("Please sign in from the **Watchlist** page first, then come back here.")
    st.stop()
 
 
# ============================================================
# GREETING
# ============================================================
 
hour = datetime.now().hour
greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
 
st.markdown(f'<div class="brief-title">🌅 {greeting}</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="brief-sub">Here\'s what matters in your market today.</div>',
    unsafe_allow_html=True,
)
 
 
# ============================================================
# GATHER WATCHLIST DATA (reuses the same scoring as the main app)
# ============================================================
 
symbols = get_watchlist(current_user_id)
rows = []
 
for symbol in symbols:
    try:
        info = fetch_stock_history(symbol)
        if len(info) < 2:
            continue
        latest_price = float(info["Close"].iloc[-1])
        prev_close = float(info["Close"].iloc[-2])
        if prev_close == 0:
            continue
        change_pct = ((latest_price - prev_close) / prev_close) * 100
        daily_returns = info["Close"].pct_change().dropna() * 100
        volatility = float(daily_returns.std()) if not daily_returns.empty else 0.0
 
        last_price = get_last_snapshot(current_user_id, symbol)
        if last_price and float(last_price) != 0:
            diff_pct = ((latest_price - float(last_price)) / float(last_price)) * 100
        else:
            diff_pct = 0.0
 
        score = calculate_meaningful_change_score(change_pct, diff_pct, volatility)
        level = get_change_level(score)
 
        rows.append({
            "symbol": symbol, "price": latest_price,
            "change": change_pct, "score": score, "level": level,
        })
    except Exception:
        continue
 
rows.sort(key=lambda r: r["score"], reverse=True)
 
 
# ============================================================
# YOUR WATCHLIST SECTION
# ============================================================
 
if not rows:
    watchlist_body = (
        '<div style="color:#8890c9; font-size:13px;">'
        "Your watchlist is empty. Add stocks from the Watchlist page."
        "</div>"
    )
else:
    high_count = sum(1 for r in rows if r["level"] == "HIGH")
    medium_count = sum(1 for r in rows if r["level"] == "MEDIUM")
    if high_count or medium_count:
        summary_line = (
            f"{high_count} stock(s) need serious attention, "
            f"{medium_count} showing notable movement."
        )
    else:
        summary_line = "All quiet - nothing significant since your last visit."
 
    row_html = ""
    for r in rows:
        arrow = "↑" if r["change"] > 0 else "↓" if r["change"] < 0 else "→"
        row_html += (
            f'<div class="brief-row">'
            f'<span><b>{r["symbol"]}</b></span>'
            f'<span>₹{r["price"]:,.2f} &nbsp; {arrow} {r["change"]:+.2f}%'
            f' &nbsp; <i>{r["level"]}</i></span>'
            f'</div>'
        )
 
    watchlist_body = (
        f'<div style="color:#8890c9; font-size:13px; margin-bottom:8px;">'
        f'{summary_line}</div>{row_html}'
    )
 
st.markdown(
    f'<div class="brief-section">'
    f'<div class="brief-heading">📋 Your Watchlist</div>'
    f'{watchlist_body}'
    f'</div>',
    unsafe_allow_html=True,
)
 
 
# ============================================================
# MARKET SECTION
# ============================================================
# Note: these index values are currently static reference data, not
# a live fetch - kept consistent with the sidebar on the main page.
 
st.markdown(
    '<div class="brief-section">'
    '<div class="brief-heading">🌐 Market</div>'
    '<div class="brief-row"><span>NIFTY 50</span><span>24,914.15 &nbsp; ↑ +0.63%</span></div>'
    '<div class="brief-row"><span>SENSEX</span><span>81,628.77 &nbsp; ↑ +0.61%</span></div>'
    '<div class="brief-row"><span>NIFTY BANK</span><span>51,354.20 &nbsp; ↑ +0.41%</span></div>'
    '</div>',
    unsafe_allow_html=True,
)
 
 
# ============================================================
# BEYOND YOUR WATCHLIST
# ============================================================
 
discoveries = get_top_discoveries(symbols, top_n=3)
 
if not discoveries:
    discover_body = (
        '<div style="color:#8890c9; font-size:13px;">'
        "No unusual movement detected outside your watchlist right now."
        "</div>"
    )
else:
    discover_body = ""
    for d in discoveries:
        arrow = "↑" if d["change"] > 0 else "↓" if d["change"] < 0 else "→"
        discover_body += (
            f'<div class="brief-row">'
            f'<span><b>{d["symbol"]}</b></span>'
            f'<span>{arrow} {d["change"]:+.2f}% &nbsp; <i>{d["level"]}</i></span>'
            f'</div>'
        )
 
st.markdown(
    f'<div class="brief-section">'
    f'<div class="brief-heading">🔍 Beyond Your Watchlist</div>'
    f'{discover_body}'
    f'</div>',
    unsafe_allow_html=True,
)
 
st.caption(
    "This brief is assembled entirely from data already collected by "
    "your watchlist and discovery engine - no external news source."
)
 
