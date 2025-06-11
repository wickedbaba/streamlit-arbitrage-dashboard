import streamlit as st
from streamlit_autorefresh import st_autorefresh
from nsepython import *
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Cash-Futures Arbitrage", layout="wide")

# Refresh every 60 seconds
st_autorefresh(interval=60 * 1000, key="datarefresh")

st.title("📈 Cash-Futures Arbitrage Dashboard (NSE India)")

# Stock list
default_stocks = ["INFY", "TCS", "RELIANCE", "HDFCBANK", "ITC", "ICICIBANK"]
stocks = st.multiselect("Select Stocks", default_stocks, default=default_stocks)

data = []

for symbol in stocks:
    try:
        # Get Spot Price (via quote)
        quote = nse_quote(symbol)
        spot_price = float(quote['priceInfo']['lastPrice'])

        # Get Futures Data
        fno_data = nse_fno(symbol)
        fut = fno_data["stocks"][0]["metadata"]
        fut_price = float(fut["lastPrice"])

        # Expiry
        expiry = pd.to_datetime(fut["expiryDate"])
        today = pd.to_datetime(datetime.now().date())
        days_left = (expiry - today).days

        # Arbitrage logic
        premium = fut_price - spot_price
        annual_coc = (premium / spot_price) * (365 / days_left) * 100

        data.append({
            "Symbol": symbol,
            "Spot Price": round(spot_price, 2),
            "Futures Price": round(fut_price, 2),
            "Premium": round(premium, 2),
            "Annualized CoC (%)": round(annual_coc, 2),
            "Expiry": expiry.strftime("%Y-%m-%d")
        })

    except Exception as e:
        st.warning(f"⚠️ {symbol}: {e}")

# Display Table
if data:
    df = pd.DataFrame(data)
    st.dataframe(df.sort_values("Annualized CoC (%)", ascending=False), use_container_width=True)
else:
    st.error("No data available. Try again later or check stock symbols.")

st.caption("Auto-refresh every 60 seconds • Live data via NSE • Made by Manav")
