import streamlit as st
from streamlit_autorefresh import st_autorefresh
from nselib import derivatives
import pandas as pd
from datetime import datetime
import requests

st.set_page_config(page_title="Cash-Futures Arbitrage", layout="wide")
st_autorefresh(interval=60 * 1000, key="autorefresh")

st.title("📈 NSE Cash-Futures Arbitrage Monitor")

# Spot price fetcher from NSE
def get_spot_price(symbol):
    url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"
    }
    session = requests.Session()
    session.headers.update(headers)
    # Required to get cookies
    session.get("https://www.nseindia.com", timeout=5)
    response = session.get(url, timeout=5)
    data = response.json()
    return float(data["priceInfo"]["lastPrice"])

# Input
default_stocks = ["INFY", "TCS", "RELIANCE", "HDFCBANK", "ITC", "ICICIBANK"]
stocks = st.multiselect("Select Stocks", default_stocks, default=default_stocks)

data = []

for symbol in stocks:
    try:
        # Get spot price via direct NSE API
        spot_price = get_spot_price(symbol)

        # Get futures data using nselib
        fno_chain = derivatives.equity_derivatives(symbol)
        fut_data = next((item for item in fno_chain["data"] if item["instrumentType"] == "FUTSTK"), None)

        if not fut_data:
            st.warning(f"No futures data for {symbol}")
            continue

        fut_price = float(fut_data["lastPrice"])
        expiry_date = pd.to_datetime(fut_data["expiryDate"], format="%d-%b-%Y")
        today = pd.to_datetime(datetime.now().date())
        days_left = (expiry_date - today).days

        premium = fut_price - spot_price
        annual_coc = (premium / spot_price) * (365 / days_left) * 100

        data.append({
            "Symbol": symbol,
            "Spot Price": round(spot_price, 2),
            "Futures Price": round(fut_price, 2),
            "Premium": round(premium, 2),
            "Annualized CoC (%)": round(annual_coc, 2),
            "Expiry": expiry_date.strftime("%Y-%m-%d")
        })

    except Exception as e:
        st.warning(f"❌ {symbol}: {e}")

if data:
    df = pd.DataFrame(data)
    st.dataframe(df.sort_values("Annualized CoC (%)", ascending=False), use_container_width=True)
else:
    st.error("⚠️ No data could be fetched.")

st.caption("Auto-refreshes every 60s • Live arbitrage monitor")
