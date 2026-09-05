import streamlit as st
import yfinance as yf
import textwrap
from datetime import datetime
from supabase import create_client, Client
from streamlit_cookies_controller import CookieController

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Smart Market Watchlist",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# SUPABASE SETUP
# ============================================================

SUPABASE_URL = "https://byxfjgopvafrkilaulco.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ5eGZqZ29wdmFmcmtpbGF1bGNvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg1OTkzNjQsImV4cCI6MjEwNDE3NTM2NH0.66o3N0H3MKilfGaNZesSpD3d89hUzL8oj9k0gaGa12Q"


@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = get_supabase_client()


# CookieController creates widget-like state and must not be wrapped in a
# cached function; Streamlit treats that as a cache miss during startup.
cookie_controller = CookieController()


def persist_auth_session(user_id, access_token, refresh_token):
    st.session_state["sb_user_id"] = user_id
    st.session_state["sb_access_token"] = access_token
    st.session_state["sb_refresh_token"] = refresh_token
    cookie_controller.set("sb_access_token", access_token)
    cookie_controller.set("sb_refresh_token", refresh_token)
    cookie_controller.set("sb_user_id", user_id)


def clear_auth_session():
    for key in ["sb_user_id", "sb_access_token", "sb_refresh_token"]:
        st.session_state.pop(key, None)
    cookie_controller.set("sb_access_token", "")
    cookie_controller.set("sb_refresh_token", "")
    cookie_controller.set("sb_user_id", "")
    try:
        supabase.auth.sign_out()
    except Exception:
        pass


def ensure_authenticated():
    """
    Restore an existing email/password authentication session
    from Streamlit session state or browser cookies.

    Returns:
        user_id if authenticated
        None if the user needs to sign in
    """

    # 1. Already authenticated during this Streamlit run
    if (
        "sb_access_token" in st.session_state
        and "sb_refresh_token" in st.session_state
    ):
        try:
            supabase.auth.set_session(
                st.session_state["sb_access_token"],
                st.session_state["sb_refresh_token"],
            )

            user = supabase.auth.get_user()

            if user and user.user:
                st.session_state["sb_user_id"] = user.user.id
                return user.user.id

        except Exception:
            pass

    # 2. Try restoring session from browser cookies
    access_token = cookie_controller.get("sb_access_token")
    refresh_token = cookie_controller.get("sb_refresh_token")

    if access_token and refresh_token:
        try:
            supabase.auth.set_session(
                access_token,
                refresh_token,
            )

            user = supabase.auth.get_user()

            if user and user.user:
                st.session_state["sb_access_token"] = access_token
                st.session_state["sb_refresh_token"] = refresh_token
                st.session_state["sb_user_id"] = user.user.id

                return user.user.id

        except Exception:
            # Invalid/expired cookies.
            # Do NOT create an anonymous user.
            pass

    # 3. No valid login
    return None


def login_with_email(email, password):
    try:
        auth_response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        if auth_response.user and auth_response.session:
            persist_auth_session(
                auth_response.user.id,
                auth_response.session.access_token,
                auth_response.session.refresh_token,
            )
            return True, None
        return False, "Sign-in failed. Please check your email and password."
    except Exception as exc:
        return False, str(exc)


def signup_with_email(email, password):
    try:
        auth_response = supabase.auth.sign_up(
            {"email": email, "password": password}
        )
        if auth_response.user and auth_response.session:
            persist_auth_session(
                auth_response.user.id,
                auth_response.session.access_token,
                auth_response.session.refresh_token,
            )
            return True, None
        if auth_response.user:
            return False, "Account created. Check your email to confirm and then sign in."
        return False, "Could not create account. Please try again."
    except Exception as exc:
        return False, str(exc)


def render_auth_screen():
    st.markdown(
        """
        <div style="text-align:center; margin-top:60px;">
            <h1 style="color:#101828;">Smart Market</h1>
            <p style="color:#475467;">
                Track. Analyze. Decide Smarter.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Default mode
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "signin"

    # --------------------------------------------------------
    # SIGN IN
    # --------------------------------------------------------

    if st.session_state.auth_mode == "signin":

        st.subheader("Sign In")

        with st.form("signin_form"):

            email = st.text_input(
                "Email",
                placeholder="you@example.com",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
            )

            submitted = st.form_submit_button(
                "Sign In",
                use_container_width=True,
            )

        if submitted:

            if not email or not password:
                st.error("Please enter both email and password.")

            else:
                try:
                    response = supabase.auth.sign_in_with_password(
                        {
                            "email": email,
                            "password": password,
                        }
                    )

                    if response.user is not None:

                        persist_auth_session(
                            response.user.id,
                            response.session.access_token,
                            response.session.refresh_token,
                        )

                        st.success("Signed in successfully.")
                        st.rerun()

                except Exception as e:
                    st.error(f"Sign in failed: {e}")

        # IMPORTANT:
        # This button is OUTSIDE the form.
        if st.button(
            "Create an account",
            key="go_to_signup",
            use_container_width=True,
        ):
            st.session_state.auth_mode = "signup"
            st.rerun()

    # --------------------------------------------------------
    # SIGN UP
    # --------------------------------------------------------

    else:

        st.subheader("Create Account")

        with st.form("signup_form"):

            email = st.text_input(
                "Email",
                placeholder="you@example.com",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Create a password",
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Re-enter your password",
            )

            submitted = st.form_submit_button(
                "Create Account",
                use_container_width=True,
            )

        if submitted:

            if not email or not password or not confirm_password:
                st.error("Please fill in all fields.")

            elif password != confirm_password:
                st.error("Passwords do not match.")

            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")

            else:

                try:
                    response = supabase.auth.sign_up(
                        {
                            "email": email,
                            "password": password,
                        }
                    )

                    if response.user is not None:

                        # If email confirmation is disabled,
                        # Supabase gives us a session immediately.
                        if response.session:

                            persist_auth_session(
                                response.user.id,
                                response.session.access_token,
                                response.session.refresh_token,
                            )

                            st.success(
                                "Account created successfully."
                            )

                            st.rerun()

                        else:
                            st.success(
                                "Account created. "
                                "Please check your email to confirm "
                                "your account, then sign in."
                            )

                except Exception as e:
                    st.error(f"Account creation failed: {e}")

        # IMPORTANT:
        # Also OUTSIDE the form.
        if st.button(
            "Already have an account? Sign In",
            key="go_to_signin",
            use_container_width=True,
        ):
            st.session_state.auth_mode = "signin"
            st.rerun()


# ============================================================
# CUSTOM CSS
# ============================================================


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>
.stApp {
    background: #f6f8fb;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

section[data-testid="stSidebar"] {
    background: #0b1b33;
}

section[data-testid="stSidebar"] * {
    color: white;
}

.sidebar-logo {
    font-size: 25px;
    font-weight: 700;
    margin-bottom: 4px;
}

.sidebar-subtitle {
    color: #c7d2e3 !important;
    font-size: 13px;
    margin-bottom: 25px;
}

.sidebar-item {
    padding: 11px 14px;
    border-radius: 9px;
    margin: 4px 0;
    font-size: 14px;
}

.sidebar-active {
    background: #1c3150;
    border-left: 3px solid #22c55e;
}

.sidebar-market {
    margin-top: 35px;
    padding: 14px;
    border: 1px solid #33445d;
    border-radius: 10px;
}

.market-title {
    color: #d0d9e8 !important;
    font-size: 12px;
    margin-bottom: 12px;
}

.market-name {
    font-size: 12px;
    font-weight: 600;
}

.market-value {
    font-size: 14px;
    margin-top: 3px;
}

.market-change {
    color: #22c55e !important;
    font-size: 11px;
    margin-top: 2px;
}

.page-title {
    font-size: 34px;
    font-weight: 750;
    color: #101828;
    margin-bottom: 2px;
}

.page-subtitle {
    color: #475467;
    font-size: 14px;
    margin-bottom: 22px;
}

.summary-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 18px;
    min-height: 112px;
    box-shadow: 0 2px 8px rgba(16, 24, 40, 0.04);
}

.summary-label {
    color: #475467;
    font-size: 12px;
}

.summary-value {
    color: #101828;
    font-size: 28px;
    font-weight: 700;
    margin-top: 7px;
}

.summary-description {
    color: #98A2B3;
    font-size: 11px;
    margin-top: 4px;
}

.digest-box {
    background: linear-gradient(135deg, #0b1b33, #1c3150);
    border-radius: 16px;
    padding: 20px 24px;
    margin: 22px 0;
    color: white;
}

.digest-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: #9ad8ff !important;
    margin-bottom: 8px;
}

.digest-text {
    font-size: 16px;
    line-height: 1.5;
    color: #ffffff !important;
}

.digest-tag {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
    margin: 0 3px;
}

.digest-tag-high {
    background: #fee2e2;
    color: #b91c1c;
}

.digest-tag-medium {
    background: #fef3c7;
    color: #b45309;
}

.stock-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 22px;
    margin-top: 18px;
    box-shadow: 0 3px 12px rgba(16, 24, 40, 0.05);
}

.stock-symbol {
    color: #101828;
    font-size: 19px;
    font-weight: 700;
}

.stock-company {
    color: #475467;
    font-size: 12px;
    margin-top: 3px;
}

.stock-price {
    color: #101828;
    font-size: 25px;
    font-weight: 700;
}

.positive {
    color: #16a34a !important;
    font-weight: 650;
}

.negative {
    color: #dc2626 !important;
    font-weight: 650;
}

.neutral {
    color: #475467 !important;
    font-weight: 650;
}

.metric-label {
    color: #475467;
    font-size: 11px;
    margin-bottom: 7px;
}

.metric-value {
    color: #101828;
    font-size: 16px;
    font-weight: 650;
}

.metric-small {
    color: #98A2B3;
    font-size: 11px;
    margin-top: 5px;
}

.metric-panel {
    min-height: 105px;
    padding: 8px 12px;
    border-right: 1px solid #eaecf0;
}

.score-container {
    text-align: center;
}

.score-circle {
    width: 92px;
    height: 92px;
    border-radius: 50%;
    margin: 4px auto 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background:
        radial-gradient(circle, white 57%, transparent 58%),
        conic-gradient(
            #f59e0b 0deg,
            #f59e0b var(--score-angle),
            #e5e7eb var(--score-angle),
            #e5e7eb 360deg
        );
}

.score-number {
    color: #101828;
    font-size: 20px;
    font-weight: 700;
}

.score-max {
    color: #475467;
    font-size: 10px;
}

.badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 7px;
    font-size: 10px;
    font-weight: 700;
}

.badge-low {
    background: #dcfce7;
    color: #15803d;
}

.badge-medium {
    background: #fef3c7;
    color: #b45309;
}

.badge-high {
    background: #fee2e2;
    color: #b91c1c;
}

.trend-card {
    border: 1px solid #e5e7eb;
    border-radius: 11px;
    padding: 14px;
    background: #ffffff;
}

.trend-title {
    color: #101828;
    font-size: 12px;
    font-weight: 650;
    margin-bottom: 12px;
}

.trend-label {
    color: #475467;
    font-size: 10px;
}

.trend-value-up {
    color: #16a34a;
    font-weight: 700;
    font-size: 15px;
    margin-top: 3px;
}

.trend-value-down {
    color: #dc2626;
    font-weight: 700;
    font-size: 15px;
    margin-top: 3px;
}

.trend-value-neutral {
    color: #475467;
    font-weight: 700;
    font-size: 15px;
    margin-top: 3px;
}

.trend-confirmed-up,
.trend-confirmed-down,
.trend-confirmed-neutral {
    padding: 8px;
    border-radius: 8px;
    text-align: center;
    font-size: 10px;
    font-weight: 700;
    margin-top: 12px;
}

.trend-confirmed-up {
    background: #dcfce7;
    color: #15803d;
}

.trend-confirmed-down {
    background: #fee2e2;
    color: #b91c1c;
}

.trend-confirmed-neutral {
    background: #f2f4f7;
    color: #475467;
}

.history-panel {
    padding: 8px 12px;
}

.history-value {
    color: #101828;
    font-size: 16px;
    font-weight: 700;
}

div.stButton > button {
    border-radius: 9px;
    border: 1px solid #d0d5dd;
    background: white;
}

div.stButton > button:hover {
    border-color: #22c55e;
    color: #15803d;
}

div[data-testid="stExpander"] {
    border-radius: 11px;
}

.info-box {
    background: #eff6ff;
    border: 1px solid #dbeafe;
    border-radius: 12px;
    padding: 14px;
    margin-top: 22px;
    color: #1e40af;
    font-size: 11px;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SCORE
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


def get_signal(level, today_change, visit_change):
    if today_change > 0 and visit_change >= 0:
        if level == "HIGH":
            return "STRONG POSITIVE MOVEMENT"
        if level == "MEDIUM":
            return "MODERATE POSITIVE MOVEMENT"
        return "SMALL POSITIVE MOVEMENT"

    if today_change < 0 and visit_change <= 0:
        if level == "HIGH":
            return "STRONG NEGATIVE MOVEMENT"
        if level == "MEDIUM":
            return "MODERATE NEGATIVE MOVEMENT"
        return "SMALL NEGATIVE MOVEMENT"

    if (
        (today_change > 0 and visit_change < 0)
        or (today_change < 0 and visit_change > 0)
    ):
        return "MIXED MOVEMENT"

    return "STABLE"


# ============================================================
# TREND
# ============================================================

def calculate_trend(info, latest_price):
    if len(info) < 5:
        return "UNKNOWN", "UNKNOWN", "INSUFFICIENT DATA", None, None

    ma5 = float(info["Close"].tail(5).mean())

    if latest_price > ma5:
        short_trend = "UP"
    elif latest_price < ma5:
        short_trend = "DOWN"
    else:
        short_trend = "STABLE"

    if len(info) >= 20:
        ma20 = float(info["Close"].tail(20).mean())

        if latest_price > ma20:
            medium_trend = "UP"
        elif latest_price < ma20:
            medium_trend = "DOWN"
        else:
            medium_trend = "STABLE"

        if short_trend == "UP" and medium_trend == "UP":
            trend_signal = "CONFIRMED UPWARD TREND"
        elif short_trend == "DOWN" and medium_trend == "DOWN":
            trend_signal = "CONFIRMED DOWNWARD TREND"
        elif short_trend == "UP" and medium_trend == "DOWN":
            trend_signal = "SHORT-TERM RECOVERY"
        elif short_trend == "DOWN" and medium_trend == "UP":
            trend_signal = "SHORT-TERM PULLBACK"
        else:
            trend_signal = "STABLE / MIXED TREND"
    else:
        ma20 = None
        medium_trend = "UNKNOWN"
        trend_signal = "SHORT-TERM TREND ONLY"

    return short_trend, medium_trend, trend_signal, ma5, ma20


# ============================================================
# DATABASE (Supabase)
# ============================================================

def add_symbol(symbol):
    try:
        supabase.table("watchlist").upsert(
            {"symbol": symbol, "user_id": current_user_id},
            on_conflict="user_id,symbol",
        ).execute()
    except Exception:
        st.warning(f"{symbol} is already on your watchlist.")


def remove_symbol(symbol):
    supabase.table("watchlist").delete().eq("symbol", symbol).eq("user_id", current_user_id).execute()
    supabase.table("snapshots").delete().eq("symbol", symbol).eq("user_id", current_user_id).execute()


def get_watchlist():
    response = (
        supabase.table("watchlist")
        .select("symbol")
        .eq("user_id", current_user_id)
        .order("added_at")
        .execute()
    )
    data = response.data or []
    return [row["symbol"] for row in data]


def get_last_snapshot(symbol):
    response = (
        supabase.table("snapshots")
        .select("last_price,last_viewed_at")
        .eq("user_id", current_user_id)
        .eq("symbol", symbol)
        .execute()
    )
    if response.data:
        row = response.data[0]
        return (row["last_price"], row["last_viewed_at"])
    return None


def save_snapshot(symbol, price):
    supabase.table("snapshots").upsert(
        {
            "symbol": symbol,
            "user_id": current_user_id,
            "last_price": price,
            "last_viewed_at": datetime.now().isoformat(),
        },
        on_conflict="symbol,user_id",
    ).execute()


def log_visit(symbol, score, level):
    """Records this visit's score/level for the symbol, building a
    real history of movement over time (not just the latest snapshot)."""
    supabase.table("visit_history").insert({
        "symbol": symbol,
        "user_id": current_user_id,
        "score": score,
        "level": level,
    }).execute()


def should_log_visit(symbol, score, level):
    """Only log once per symbol per score/level in a single app session.

    This avoids duplicate entries when Streamlit reruns on button clicks,
    expand/collapse toggles, or state refreshes.
    """
    visit_state = st.session_state.setdefault("visit_log_state", {})
    key = symbol
    current = (float(score), str(level))
    last = visit_state.get(key)

    if last != current:
        visit_state[key] = current
        return True

    return False


def get_recent_significant_count(symbol, limit=5):
    """Looks at the last `limit` logged visits for this symbol and
    counts how many were HIGH or MEDIUM - powers the
    'moved significantly in X of your last Y visits' stat."""
    response = (
        supabase.table("visit_history")
        .select("level")
        .eq("user_id", current_user_id)
        .eq("symbol", symbol)
        .order("visited_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = response.data or []
    total = len(rows)
    significant = sum(1 for r in rows if r["level"] in ("HIGH", "MEDIUM"))
    return significant, total


# ============================================================
# VALIDATE STOCK
# ============================================================

def validate_symbol(raw_input):
    cleaned = raw_input.strip().upper()

    if not cleaned:
        return None, "Please enter a symbol."

    candidates = [cleaned]

    if "." not in cleaned:
        candidates.append(f"{cleaned}.NS")

    for candidate in candidates:
        try:
            ticker = yf.Ticker(candidate)
            data = ticker.history(period="5d")

            if not data.empty:
                return candidate, None

        except Exception:
            continue

    return None, f"Couldn't find a stock matching '{raw_input}'."


# ============================================================
# HELPERS
# ============================================================

def movement_class(value):
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def trend_class(value):
    if value == "UP":
        return "trend-value-up"
    if value == "DOWN":
        return "trend-value-down"
    return "trend-value-neutral"


def trend_arrow(value):
    if value == "UP":
        return "↑"
    if value == "DOWN":
        return "↓"
    return "→"


def trend_box_class(signal):
    if "UPWARD" in signal or "RECOVERY" in signal:
        return "trend-confirmed-up"
    if "DOWNWARD" in signal or "PULLBACK" in signal:
        return "trend-confirmed-down"
    return "trend-confirmed-neutral"


# ============================================================
# INITIALIZE
# ============================================================

current_user_id = ensure_authenticated()

if not current_user_id:
    render_auth_screen()
    st.stop()

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        '<div class="sidebar-logo">📈 Smart</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-subtitle">Market Watchlist</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-item sidebar-active">⌂ &nbsp; Watchlist</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-item">▣ &nbsp; Dashboard</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-item">＋ &nbsp; Add Stock</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-item">◩ &nbsp; Insights</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-item">◷ &nbsp; History</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-item">⚙ &nbsp; Settings</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-item">ⓘ &nbsp; About</div>',
        unsafe_allow_html=True,
    )

    st.markdown(textwrap.dedent("""
        <div class="sidebar-market">
            <div class="market-title">🌐 Market Overview</div>
            <hr style="border-color:#33445d">
            <div class="market-name">NIFTY 50</div>
            <div class="market-value">24,914.15</div>
            <div class="market-change">+0.63%</div>
            <br>
            <div class="market-name">SENSEX</div>
            <div class="market-value">81,628.77</div>
            <div class="market-change">+0.61%</div>
            <br>
            <div class="market-name">NIFTY BANK</div>
            <div class="market-value">51,354.20</div>
            <div class="market-change">+0.41%</div>
        </div>
    """), unsafe_allow_html=True)

    st.markdown(
        f"<br><small>Session ID: {current_user_id[:8]}...</small>",
        unsafe_allow_html=True,
    )

    if st.button("Log Out", key="logout_btn"):
        clear_auth_session()
        st.session_state["auth_mode"] = "signin"
        st.rerun()

    st.markdown(
        "<br><small>Market data by Yahoo Finance</small>",
        unsafe_allow_html=True,
    )


# ============================================================
# MAIN HEADER
# ============================================================

st.markdown(
    '<div class="page-title">My Watchlist</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="page-subtitle">Track. Analyze. Decide Smarter.</div>',
    unsafe_allow_html=True,
)


# ============================================================
# ADD STOCK
# ============================================================

with st.expander("＋ Add Stock"):
    with st.form(key="add_stock_form", clear_on_submit=True):
        new_symbol = st.text_input(
            "Enter stock symbol",
            placeholder="Example: RELIANCE, TCS, INFY",
        )

        submitted = st.form_submit_button("Add Stock")

        if submitted:
            valid_symbol, error = validate_symbol(new_symbol)

            if error:
                st.error(error)
            else:
                add_symbol(valid_symbol)
                st.success(f"{valid_symbol} added.")
                st.rerun()


# ============================================================
# GET STOCKS
# ============================================================

symbols = get_watchlist()


# ============================================================
# FETCH STOCK DATA
# ============================================================

@st.cache_data(ttl=60)
def fetch_stock_history(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.history(period="1mo")


stock_data = []
failed_symbols = []

for symbol in symbols:
    try:
        info = fetch_stock_history(symbol)

        if len(info) < 2:
            failed_symbols.append(symbol)
            continue

        latest_price = float(info["Close"].iloc[-1])
        prev_close = float(info["Close"].iloc[-2])

        if prev_close == 0:
            failed_symbols.append(symbol)
            continue

        change_pct = ((latest_price - prev_close) / prev_close) * 100

        daily_returns = info["Close"].pct_change().dropna() * 100
        volatility = float(daily_returns.std()) if not daily_returns.empty else 0.0

        (
            short_trend,
            medium_trend,
            trend_signal,
            ma5,
            ma20,
        ) = calculate_trend(info, latest_price)

        last_snapshot = get_last_snapshot(symbol)

        if last_snapshot is not None:
            last_price, last_viewed_at = last_snapshot

            if last_price and float(last_price) != 0:
                diff = latest_price - float(last_price)
                diff_pct = (diff / float(last_price)) * 100
            else:
                diff = 0.0
                diff_pct = 0.0

            score = calculate_meaningful_change_score(
                change_pct,
                diff_pct,
                volatility,
            )

            level = get_change_level(score)

            signal = get_signal(
                level,
                change_pct,
                diff_pct,
            )
        else:
            diff = 0.0
            diff_pct = 0.0
            score = 0.0
            level = "LOW"
            signal = "FIRST VISIT"

        save_snapshot(symbol, latest_price)

        # Avoid creating a new visit record on every Streamlit rerun. Only log when
        # this symbol's score/level has changed within the active session.
        if should_log_visit(symbol, score, level):
            log_visit(symbol, score, level)

        sig_count, visit_count = get_recent_significant_count(symbol, limit=5)

        stock_data.append({
            "symbol": symbol,
            "price": latest_price,
            "change": change_pct,
            "diff": diff,
            "diff_pct": diff_pct,
            "score": score,
            "level": level,
            "signal": signal,
            "volatility": volatility,
            "short_trend": short_trend,
            "medium_trend": medium_trend,
            "trend_signal": trend_signal,
            "ma5": ma5,
            "ma20": ma20,
            "sparkline": info["Close"].tail(30),
            "sig_count": sig_count,
            "visit_count": visit_count,
        })

    except Exception:
        failed_symbols.append(symbol)
        continue

if failed_symbols:
    st.warning(
        f"Couldn't fetch live data for: {', '.join(failed_symbols)}. "
        f"This may be due to an invalid symbol or a temporary issue "
        f"with the data source."
    )


# ============================================================
# SUMMARY
# ============================================================

total_stocks = len(symbols)
gainers = sum(1 for item in stock_data if item["change"] > 0)
losers = sum(1 for item in stock_data if item["change"] < 0)
high_movement = sum(1 for item in stock_data if item["score"] >= 60)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(textwrap.dedent(f"""
        <div class="summary-card">
            <div class="summary-label">Total Stocks</div>
            <div class="summary-value">{total_stocks}</div>
            <div class="summary-description">In your watchlist</div>
        </div>
    """), unsafe_allow_html=True)

with c2:
    st.markdown(textwrap.dedent(f"""
        <div class="summary-card">
            <div class="summary-label">High Movement</div>
            <div class="summary-value">{high_movement}</div>
            <div class="summary-description">Score ≥ 60</div>
        </div>
    """), unsafe_allow_html=True)

with c3:
    st.markdown(textwrap.dedent(f"""
        <div class="summary-card">
            <div class="summary-label">Gainers</div>
            <div class="summary-value">{gainers}</div>
            <div class="summary-description">Up today</div>
        </div>
    """), unsafe_allow_html=True)

with c4:
    st.markdown(textwrap.dedent(f"""
        <div class="summary-card">
            <div class="summary-label">Losers</div>
            <div class="summary-value">{losers}</div>
            <div class="summary-description">Down today</div>
        </div>
    """), unsafe_allow_html=True)


# ============================================================
# DIGEST SUMMARY
# ============================================================
# Answers "what deserves your attention now" as a single glanceable
# line, before the user has to scan every individual card.

if stock_data:
    high_syms = [d["symbol"] for d in stock_data if d["level"] == "HIGH"]
    medium_syms = [d["symbol"] for d in stock_data if d["level"] == "MEDIUM"]

    if not high_syms and not medium_syms:
        digest_text = "Nothing significant since you last checked. All quiet."
    else:
        parts = []
        if high_syms:
            tags = " ".join(
                f'<span class="digest-tag digest-tag-high">{s}</span>'
                for s in high_syms
            )
            parts.append(f"Major movement in {tags}")
        if medium_syms:
            tags = " ".join(
                f'<span class="digest-tag digest-tag-medium">{s}</span>'
                for s in medium_syms
            )
            parts.append(f"Notable movement in {tags}")
        digest_text = " &nbsp;·&nbsp; ".join(parts)

    st.markdown(textwrap.dedent(f"""
        <div class="digest-box">
            <div class="digest-title">📋 YOUR DIGEST</div>
            <div class="digest-text">{digest_text}</div>
        </div>
    """), unsafe_allow_html=True)


# ============================================================
# EMPTY WATCHLIST
# ============================================================

if not symbols:
    st.info("Your watchlist is empty. Add a stock above to get started.")


# ============================================================
# STOCK CARDS
# ============================================================

for data in stock_data:

    symbol = data["symbol"]
    price = data["price"]
    change = data["change"]
    diff = data["diff"]
    diff_pct = data["diff_pct"]
    score = data["score"]
    level = data["level"]
    signal = data["signal"]
    volatility = data["volatility"]
    short_trend = data["short_trend"]
    medium_trend = data["medium_trend"]
    trend_signal = data["trend_signal"]
    ma5 = data["ma5"]
    ma20 = data["ma20"]
    sparkline = data["sparkline"]
    sig_count = data["sig_count"]
    visit_count = data["visit_count"]

    change_cls = movement_class(change)
    diff_cls = movement_class(diff_pct)
    short_cls = trend_class(short_trend)
    medium_cls = trend_class(medium_trend)

    if level == "HIGH":
        badge_cls = "badge-high"
    elif level == "MEDIUM":
        badge_cls = "badge-medium"
    else:
        badge_cls = "badge-low"

    angle = score / 100 * 360
    box_cls = trend_box_class(trend_signal)

    top1, top2, top3, top4 = st.columns([3, 2, 2, 0.6])

    with top1:
        st.markdown(textwrap.dedent(f"""
            <div class="stock-symbol">{symbol}</div>
            <div class="stock-company">Market-listed security</div>
        """), unsafe_allow_html=True)

    with top2:
        st.markdown(textwrap.dedent(f"""
            <div class="stock-price">₹{price:,.2f}</div>
            <div class="{change_cls}">
                {change:+.2f}% &nbsp;
                {"↑" if change > 0 else "↓" if change < 0 else "→"}
            </div>
            <div class="metric-small">Today's change</div>
        """), unsafe_allow_html=True)

    with top3:
        st.markdown(
            '<div class="metric-label">Signal</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="{change_cls}">{signal}</div>',
            unsafe_allow_html=True,
        )

    with top4:
        if st.button("🗑", key=f"remove_{symbol}", help=f"Remove {symbol}"):
            remove_symbol(symbol)
            st.rerun()

    # --- Sparkline: last 30 days at a glance ---
    st.line_chart(sparkline, height=90, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    m1, m2, m3, m4, m5 = st.columns([1.3, 1.3, 1.2, 1.9, 1.6])

    with m1:
        st.markdown(textwrap.dedent(f"""
            <div class="metric-panel">
                <div class="metric-label">SINCE LAST VISIT</div>
                <div class="{diff_cls}">
                    {diff:+.2f} ({diff_pct:+.2f}%)
                </div>
                <div class="metric-small">Previous snapshot</div>
            </div>
        """), unsafe_allow_html=True)

    with m2:
        st.markdown(textwrap.dedent(f"""
            <div class="metric-panel score-container">
                <div class="metric-label">MEANINGFUL SCORE</div>
                <div
                    class="score-circle"
                    style="--score-angle:{angle}deg;"
                >
                    <div>
                        <div class="score-number">{score:.2f}</div>
                        <div class="score-max">/100</div>
                    </div>
                </div>
            </div>
        """), unsafe_allow_html=True)

    with m3:
        st.markdown(textwrap.dedent(f"""
            <div class="metric-panel">
                <div class="metric-label">CHANGE LEVEL</div>
                <span class="badge {badge_cls}">{level}</span>
                <div class="metric-small">
                    Score indicates movement importance.
                </div>
            </div>
        """), unsafe_allow_html=True)

    with m4:
        st.markdown(textwrap.dedent(f"""
            <div class="trend-card">
                <div class="trend-title">Trend</div>
                <div style="display:flex; gap:35px;">
                    <div>
                        <div class="trend-label">5-DAY</div>
                        <div class="{short_cls}">
                            {short_trend} {trend_arrow(short_trend)}
                        </div>
                    </div>
                    <div>
                        <div class="trend-label">20-DAY</div>
                        <div class="{medium_cls}">
                            {medium_trend} {trend_arrow(medium_trend)}
                        </div>
                    </div>
                </div>
                <div class="{box_cls}">
                    {trend_signal}
                </div>
            </div>
        """), unsafe_allow_html=True)

    with m5:
        st.markdown(textwrap.dedent(f"""
            <div class="history-panel">
                <div class="metric-label">RECENT PATTERN</div>
                <div class="history-value">
                    {sig_count} of last {visit_count} visits
                </div>
                <div class="metric-small">
                    Showed significant movement
                </div>
            </div>
        """), unsafe_allow_html=True)

    with st.expander(f"ⓘ Why this score? — {symbol}"):

        e1, e2, e3 = st.columns(3)

        with e1:
            st.markdown("### Movements")

            if change > 0:
                st.write(f"↑ Today's price increased by {change:.2f}%.")
            elif change < 0:
                st.write(f"↓ Today's price decreased by {abs(change):.2f}%.")
            else:
                st.write("→ Today's price did not change.")

            if diff_pct > 0:
                st.write(
                    f"↑ Since your last visit, price increased by "
                    f"{diff_pct:.2f}%."
                )
            elif diff_pct < 0:
                st.write(
                    f"↓ Since your last visit, price decreased by "
                    f"{abs(diff_pct):.2f}%."
                )
            else:
                st.write("→ Little or no movement since your last visit.")

        with e2:
            st.markdown("### Volatility")

            st.write(
                f"Normal daily volatility: **{volatility:.2f}%**"
            )

            if volatility > 0:
                volatility_ratio = abs(change) / volatility
                st.write(
                    f"Today's movement is **{volatility_ratio:.2f}×** "
                    f"normal volatility."
                )

        with e3:
            st.markdown("### Trend Details")

            if ma5 is not None:
                st.write(f"5-day average: **₹{ma5:,.2f}**")

            if ma20 is not None:
                st.write(f"20-day average: **₹{ma20:,.2f}**")

            st.write(f"Trend: **{trend_signal}**")

    st.markdown(
        """
        <div style="
            margin-top:10px;
            color:#98A2B3;
            font-size:11px;
        ">
            Score = today's movement + movement since last visit
            + movement relative to normal volatility.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("""
    <div class="info-box">
        <b>ⓘ About the Meaningful Score</b><br>
        The score measures how notable the observed price movement is.
        Positive and negative values retain their direction, while the
        score measures the magnitude of the movement. Trend information
        provides additional context. This system describes observed
        market data and is not a direct buy/sell recommendation.
    </div>
""", unsafe_allow_html=True)

st.caption(
    f"Last updated: {datetime.now().strftime('%d %b %Y, %I:%M:%S %p')}"
)
