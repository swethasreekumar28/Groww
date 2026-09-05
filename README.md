# Smart Market Watchlist

Built for Code by Groww (2026) — *"Build a Smart Market Watchlist"*

A market watchlist that doesn't just show prices — it tells you what actually changed since you last checked, and what deserves your attention right now.

## What it does

**Track stocks** — add/remove any NSE-listed stock (case-insensitive, handles missing `.NS` suffixes automatically), with a real, persistent, per-user watchlist backed by a hosted database — not local storage.

**See what's meaningfully changed since you last checked** — every visit is snapshotted. On your next visit, the app compares the current price against your own last snapshot (not just today's open) and shows a real diff.

**Know what deserves attention now** — a composite *Meaningful Change Score* (0–100) combines:
- today's raw price movement
- movement since your last visit
- movement relative to the stock's normal volatility (a 2% move in a usually-flat stock matters more than a 2% move in a volatile one)

Stocks are sorted by this score, highest first, and a **Digest banner** at the top summarizes which stocks need attention in one glance — so you never have to scan every card manually.

## Key design decisions

**Volatility-adjusted scoring, not raw % change.** A flat percentage threshold treats every stock the same; comparing movement against a stock's own historical volatility gives a more honest signal of what's actually unusual for that stock.

**Snapshot-based comparison, not a fixed daily job.** "Since you last checked" is visit-triggered — it compares against whenever you last opened the app, not a fixed clock time. This matches how people actually check a watchlist (irregularly), rather than assuming daily use.

**Visit-history tracking.** Beyond the single latest snapshot, every visit's score is logged, powering a *"significant movement in X of your last 5 visits"* pattern — so a one-off spike reads differently from a stock that's been consistently active.

**Real per-user isolation via Supabase + Row-Level Security.** Each user authenticates with email (sign-up, email verification, sign-in), and Postgres Row-Level Security enforces that every query only touches that user's own rows — enforced at the database layer, not just in application code.

**Session persistence via browser cookies.** Login state survives full page refreshes and closing/reopening the browser, not just in-memory state that would reset on every reload.

## Tech stack

| Layer | Choice |
|-------|--------|
| **Frontend + backend** | Streamlit (Python) — single codebase, no separate frontend framework |
| **Database** | Supabase (hosted Postgres) |
| **Auth** | Supabase Auth (email/password + verification) |
| **Session persistence** | Browser cookies via `streamlit-cookies-controller` |
| **Market data** | yfinance (Yahoo Finance) |
| **Caching** | `st.cache_data` (60s TTL) to reduce redundant API calls at scale |

## Setup instructions

### Clone the repo:
```bash
git clone https://github.com/swethasreekumar28/smart-market-watchlist
cd smart-market-watchlist
```

### Install dependencies:
```bash
pip install -r requirements.txt
```

### Run the app:
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`. Sign up with an email and password (email verification required), then start adding stocks (e.g. `TCS`, `RELIANCE`, `INFY` — the `.NS` suffix is added automatically if omitted).

### Live demo:
[https://4dxy8beld8pg9unboqllgs.streamlit.app](https://4dxy8beld8pg9unboqllgs.streamlit.app)

> **Note:** the demo runs on Streamlit Community Cloud's free tier, which sleeps after a period of inactivity. If you see a "Zzz" screen, click "Yes, get this app back up" — it resumes in under a minute.

## Edge cases handled

- ✓ Invalid or misspelled stock symbols are validated against live data before being added, with a clear error message
- ✓ Duplicate stock entries are rejected per-user
- ✓ Failed/unavailable data fetches show a visible warning instead of silently disappearing or crashing
- ✓ Empty watchlist shows a clear call-to-action instead of a blank page
- ✓ Light theme is enforced app-wide to avoid visibility issues under a visitor's system dark-mode setting

## Known trade-offs (given the 72-hour timeline)

**Fuzzy company-name matching** (e.g. typing "Infosys" instead of the ticker `INFY`) is not implemented — the app validates against real ticker symbols, not a name-to-ticker dictionary, to avoid an incomplete/misleading mapping. A clear error message guides the user to the correct ticker instead.

**No live news or sector-trend data** — scoring is based purely on price, volume-adjusted volatility, and visit history, not external news sentiment. This was a deliberate scope decision to keep the "meaningful change" signal grounded in verifiable market data rather than unreliable summarization.

**Free-tier hosting** means the live demo may need a manual "wake up" after inactivity (see above).

## What's next (if extended beyond this hackathon)

- A *"Market Discovery"* view surfacing unusually active stocks outside the user's own watchlist, reusing the existing volatility-scoring engine
- Sector-level trend aggregation
- Push/email alerts when a stock crosses a `HIGH` attention threshold

---

**Built by** [Swetha Sree Kumar](https://github.com/swethasreekumar28)
