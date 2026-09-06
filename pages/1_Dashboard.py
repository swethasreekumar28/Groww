import streamlit as st
import yfinance as yf
from supabase import create_client, Client
from streamlit_cookies_controller import CookieController
 
# ============================================================
# PAGE CONFIG
# ============================================================
 
st.set_page_config(
    page_title="Dashboard - GrowwStock",
    page_icon="📊",
    layout="wide",
)
 
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@400;500;600&display=swap');
 
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
 
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
 
h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif;
    color: #141b3a;
}
 
div.stButton > button {
    border-radius: 9px;
    border: none;
    background: #2b3a8c;
    color: white !important;
    font-weight: 600;
}
 
div.stButton > button:hover {
    background: #7c83fd;
    color: white !important;
}
 
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e0e4fb;
    border-radius: 14px;
    padding: 14px 18px;
    box-shadow: 0 2px 10px rgba(43, 58, 140, 0.06);
}
 
div[data-testid="stMetricLabel"] {
    color: #2b3a8c !important;
}
 
div[data-testid="stMetricValue"] {
    color: #141b3a !important;
}
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
    """
    Read-only auth check for this page - Dashboard does not handle
    sign-in/sign-up itself. If there's no valid session, the user is
    directed back to the main Watchlist page to log in there.
    """
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
# SCORING (mirrors app.py's logic so the numbers match exactly)
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
    return ticker.history(period="1mo")
 
 
def get_watchlist(user_id):
    response = (
        supabase.table("watchlist")
        .select("symbol")
        .eq("user_id", user_id)
        .order("added_at")
        .execute()
    )
    data = response.data or []
    return [row["symbol"] for row in data]
 
 
def get_last_snapshot(user_id, symbol):
    response = (
        supabase.table("snapshots")
        .select("last_price,last_viewed_at")
        .eq("user_id", user_id)
        .eq("symbol", symbol)
        .execute()
    )
    if response.data:
        row = response.data[0]
        return (row["last_price"], row["last_viewed_at"])
    return None
 
 
# ============================================================
# AUTH GATE
# ============================================================
 
current_user_id = get_current_user_id()
 
if not current_user_id:
    st.title("📊 Dashboard")
    st.info(
        "Please sign in from the **Watchlist** page first, then come "
        "back here to view your dashboard."
    )
    st.stop()
 
 
# ============================================================
# HEADER
# ============================================================
 
st.title("📊 Portfolio Dashboard")
st.caption("A cross-stock view of what's happening across your whole watchlist.")
 
 
# ============================================================
# GATHER DATA FOR EVERY TRACKED STOCK
# ============================================================
 
symbols = get_watchlist(current_user_id)
 
if not symbols:
    st.info("Your watchlist is empty. Add stocks from the Watchlist page first.")
    st.stop()
 
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
 
        last_snapshot = get_last_snapshot(current_user_id, symbol)
 
        if last_snapshot is not None:
            last_price, _ = last_snapshot
            if last_price and float(last_price) != 0:
                diff_pct = ((latest_price - float(last_price)) / float(last_price)) * 100
            else:
                diff_pct = 0.0
        else:
            diff_pct = 0.0
 
        score = calculate_meaningful_change_score(change_pct, diff_pct, volatility)
        level = get_change_level(score)
 
        rows.append({
            "symbol": symbol,
            "price": latest_price,
            "change_pct": change_pct,
            "volatility": volatility,
            "score": score,
            "level": level,
        })
 
    except Exception:
        continue
 
if not rows:
    st.warning("Couldn't load data for your watchlist right now. Try again shortly.")
    st.stop()
 
 
# ============================================================
# TOP SUMMARY METRICS (always shown, clear regardless of count)
# ============================================================
 
st.subheader("At a glance")
 
top_row = sorted(rows, key=lambda r: r["score"], reverse=True)[0]
 
k1, k2, k3, k4 = st.columns(4)
k1.metric("Stocks tracked", len(rows))
k2.metric(
    "Needs most attention",
    top_row["symbol"],
    f"{top_row['score']:.1f} / 100",
)
k3.metric(
    "Gainers today",
    sum(1 for r in rows if r["change_pct"] > 0),
)
k4.metric(
    "Losers today",
    sum(1 for r in rows if r["change_pct"] < 0),
)
 
 
# ============================================================
# COMPARISON CHARTS - only meaningful with 2+ stocks
# ============================================================
 
if len(rows) < 2:
    st.info(
        "Add at least one more stock to your watchlist to unlock "
        "side-by-side comparison charts here."
    )
else:
    st.subheader("Attention score by stock")
    st.caption("Higher bars need more attention right now.")
    score_data = {row["symbol"]: row["score"] for row in rows}
    st.bar_chart(score_data)
 
    st.subheader("Today's % change by stock")
    change_data = {row["symbol"]: row["change_pct"] for row in rows}
    st.bar_chart(change_data)
 
    st.subheader("Normal volatility by stock")
    st.caption("Which of your stocks are naturally calmer vs. more volatile.")
    volatility_data = {row["symbol"]: row["volatility"] for row in rows}
    st.bar_chart(volatility_data)
 
 
# ============================================================
# SUMMARY TABLE
# ============================================================
 
st.subheader("Full breakdown")
 
table_rows = [
    {
        "Symbol": r["symbol"],
        "Price": f"₹{r['price']:,.2f}",
        "Today's Change": f"{r['change_pct']:+.2f}%",
        "Volatility": f"{r['volatility']:.2f}%",
        "Score": r["score"],
        "Level": r["level"],
    }
    for r in sorted(rows, key=lambda r: r["score"], reverse=True)
]
 
st.table(table_rows)
 
