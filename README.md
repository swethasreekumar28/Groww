GrowwStock
A market watchlist that doesn't just show prices ,it tells you what actually changed since you last checked, and what deserves your attention right now.

What it does
Track stocks — add/remove any NSE-listed stock (case-insensitive, handles missing .NS suffixes automatically), with a real, persistent, per-user watchlist backed by a hosted database not local storage.

See what's meaningfully changed since you last checked ; every visit is snapshotted. On your next visit, the app compares the current price against your own last snapshot (not just today's open) and shows a real diff.

Know what deserves attention now ; a composite Meaningful Change Score (0–100) combines:

today's raw price movement
movement since your last visit
movement relative to the stock's normal volatility (a 2% move in a usually-flat stock matters more than a 2% move in a volatile one)
Stocks are sorted by this score, highest first, and a Digest banner at the top summarizes which stocks need attention in one glance — so you never have to scan every card manually.

Completed product scope
Watchlist management — add and remove stocks with persistent, per-user storage
Latest market information — live price, daily percentage change, trend, volatility, and recent movement pattern
Meaningful change definition — an explicit 0–100 score combining today's move, movement since the last visit, and volatility adjustment
Dashboard — cross-stock score, daily-change, and volatility comparisons, plus a score-ranked breakdown table
Morning Brief — a single narrative view assembled from data the app already collects: watchlist summary, market indices, and top discoveries
Market Pulse (Discovery) — surfaces unusual movement beyond the user's watchlist, each with an explicit "why it's showing" explanation, an honest related-news link, and a deliberate add action (nothing is auto-added)
Navigation and visual polish — working multipage navigation, deterministic avatars, urgency accent bars, hover cards, responsive summaries, and a consistent indigo/periwinkle visual system
Key design decisions
Volatility-adjusted scoring, not raw % change. A flat percentage threshold treats every stock the same; comparing movement against a stock's own historical volatility gives a more honest signal of what's actually unusual for that stock.

Snapshot-based comparison, not a fixed daily job. "Since you last checked" is visit-triggered .It compares against whenever you last opened the app, not a fixed clock time. This matches how people actually check a watchlist (irregularly), rather than assuming daily use.

Visit-history tracking. Beyond the single latest snapshot, every visit's score is logged, powering a "significant movement in X of your last 5 visits" pattern so a one-off spike reads differently from a stock that's been consistently active.

Real per-user isolation via Supabase + Row-Level Security. Each user authenticates with email (sign-up, email verification, sign-in), and Postgres Row-Level Security enforces that every query only touches that user's own rows — enforced at the database layer, not just in application code. Verified directly: RLS is confirmed enabled on all three tables (watchlist, snapshots, visit_history), each with a policy scoping access to auth.uid() = user_id.

Session persistence via browser cookies. Login state survives full page refreshes and closing/reopening the browser, not just in-memory state that would reset on every reload.

Shared market-data caching. A 60-second cache reuses the same Yahoo Finance response across users for the same symbol. This keeps the app efficient as the watchlist and user count grow, while Supabase Row-Level Security keeps private user data isolated. An index on visit_history (user_id, symbol, visited_at) keeps the "recent pattern" lookup fast as history accumulates.

Distinct, honest failure handling. A market-data fetch failure (network/timeout/invalid ticker) and a database persistence failure (a Supabase hiccup while saving a snapshot) are handled and reported separately — a DB hiccup never hides a stock's live price, and a data-fetch failure never gets blamed on the database. The user is always told which part failed and reassured that their saved watchlist itself is never at risk.

Tech stack
Layer	Choice
Frontend + backend	Streamlit (Python) — single codebase, no separate frontend framework
Database	Supabase (hosted Postgres)
Auth	Supabase Auth (email/password + verification)
Session persistence	Browser cookies via streamlit-cookies-controller
Market data	yfinance (Yahoo Finance), fetched with explicit timeouts
Caching	st.cache_data (60s TTL) to reduce redundant API calls at scale
Setup instructions
Clone the repo:
bash
git clone https://github.com/swethasreekumar28/smart-market-watchlist
cd smart-market-watchlist
Install dependencies:
bash
pip install -r requirements.txt
Run the app:
bash
streamlit run app.py
The app will open at http://localhost:8501. Sign up with an email and password (email verification required), then start adding stocks (e.g. TCS, RELIANCE, INFY — the .NS suffix is added automatically if omitted). Use the sidebar navigation to reach the Dashboard and Morning Brief pages.

Live demo:
https://4dxy8beld8pg9unboqllgs.streamlit.app

Note: the demo runs on Streamlit Community Cloud's free tier, which sleeps after a period of inactivity. If you see a "Zzz" screen, click "Yes, get this app back up" ,it resumes in under a minute.

Edge cases handled
✓ Invalid or misspelled stock symbols are validated against live data before being added, with a clear error message
✓ Duplicate stock entries are rejected per-user (enforced at the database level via a primary key on symbol, user_id)
✓ Market-data fetch failures (network, timeout, invalid ticker) are shown with a clear, specific warning distinct from database errors
✓ Database persistence failures are shown separately, and never hide the stock's live price data
✓ Explicit network timeouts on all external data calls, so a slow connection can't hang the whole page
✓ Empty watchlist shows a clear call-to-action instead of a blank page
✓ Light theme is enforced app-wide to avoid visibility issues under a visitor's system dark-mode setting
Known trade-offs (given the 72-hour timeline)
Fuzzy company-name matching (e.g. typing "Infosys" instead of the ticker INFY) is not implemented The app validates against real ticker symbols, not a name-to-ticker dictionary, to avoid an incomplete/misleading mapping. A clear error message guides the user to the correct ticker instead.

No live news or sector-trend data — scoring is based purely on price, volume-adjusted volatility, and visit history, not external news sentiment. This was a deliberate scope decision to keep the "meaningful change" signal grounded in verifiable market data rather than unreliable summarization. Discovery cards link out to a real news search instead of attempting summarization.

Free-tier hosting means the live demo may need a manual "wake up" after inactivity (see above).

Cross-device session persistence relies on the same browser's cookies for the same account — logging in with the same email on a different device correctly restores the same watchlist (verified via real email auth), so this is a genuine cross-device capability, not a limitation.

What's next (if extended beyond this hackathon)
Sector-level trend aggregation
Push/email alerts when a stock crosses a HIGH attention threshold
Larger and configurable discovery universes
Live-fetched index values (currently static reference data in the sidebar/Morning Brief)
Built by Swetha Sreekumar


