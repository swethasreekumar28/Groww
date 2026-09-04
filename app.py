import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Smart Watchlist", layout="wide")
st.title("📈 Smart Market Watchlist")

# Hardcoded placeholder data for now — real data comes later
watchlist = [
    {"symbol": "RELIANCE.NS", "price": 2456.30, "change": "+1.2%"},
    {"symbol": "TCS.NS", "price": 3890.10, "change": "-0.4%"},
    {"symbol": "INFY.NS", "price": 1567.80, "change": "+2.1%"},
]

st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

for stock in watchlist:
    col1, col2, col3 = st.columns(3)
    col1.write(stock["symbol"])
    col2.write(f"₹{stock['price']}")
    col3.write(stock["change"])