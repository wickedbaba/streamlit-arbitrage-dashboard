import streamlit as st
from streamlit_autorefresh import st_autorefresh
from nselib import derivatives
import pandas as pd
from datetime import datetime
import requests
import time

st.set_page_config(page_title="Cash-Futures Arbitrage", layout="wide")
st_autorefresh(interval=60 * 1000, key="autorefresh")

st.title("📈 NSE Cash-Futures Arbitrage Monitor")

# ⏳ Spot price function with cookie preload
def get_spot_price(symbol):
    url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol.upper()}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": f"https://www.nseindia.com/get-quotes/equity?symbol={symbol.upper()}"
    }

    session = requests.Session()
    session.headers.update(headers)

    try:
        # Load cookies (NSE requires this)
        session.get("https://www.nseindia.com", timeout=5)
        time.sleep(1)  # let cookies register
        response = session.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data["priceInfo"]["lastPrice"])

    except Exception as e:
        raise Exception(f"NSE spot API error for {symbol}: {e}")

# 🏦 Stock list
default_stocks = ["INFY", "TCS", "RELIANCE", "HDFCBANK", "ITC", "ICICIBANK"]
stocks = st.multiselect("Select Stocks", default_stocks, default=default_stocks)

data = []

# 📊 Loop through each stock
for symbol in stocks:
    try:
        # Spot price
        spot_price = get_spot_price(symbol)

        # Futures price
        fut_chain = derivatives.equity_derivatives(symbol)
        fut_data = next((item for item in fut_chain["data"] if item["instrumentType"] == "FUTSTK"), None)

        if not fut_data:
            st.warning(f"❌ No futures data found for {symbol}")
            continue

        fut_price = float(fut_data["lastPrice"])
        expiry_date = pd.to_datetime(fut_data["expiryDate"], format="%d-%b-%Y")
        today = pd.to_datetime(datetime.now().date())
        days_left = max((expiry_date - today).days, 1)

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

# 📈 Show DataFrame
if data:
    df = pd.DataFrame(data)
    st.dataframe(df.sort_values("Annualized CoC (%)", ascending=False), use_container_width=True)
else:
    st.error("⚠️ No data could be fetched. Please try again or check symbols.")

st.caption("⏱ Auto-refreshes every 60s • Spot via NSE • Futures via nselib • Built by Manav")
