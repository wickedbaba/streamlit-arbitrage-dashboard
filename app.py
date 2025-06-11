import streamlit as st
from streamlit_autorefresh import st_autorefresh
from nsepython import *
import pandas as pd

st.set_page_config(page_title="Arbitrage Dashboard", layout="wide")

# Auto-refresh every 60 seconds
st_autorefresh(interval=60 * 1000, key="datarefresh")

st.title("📈 Cash-Futures Arbitrage Dashboard")

# Input stocks
default_stocks = ["INFY", "TCS", "RELIANCE", "HDFCBANK", "ITC", "ICICIBANK"]
stocks = st.multiselect("Select Stocks", default_stocks, default=default_stocks)

data = []

for symbol in stocks:
    try:
        # Get Spot Price
        spot_raw = nse_eq(symbol)['data'][0]['lastPrice']
        spot = float(spot_raw.replace(",", ""))

        # Get Futures Data
        fut_data = nse_fno(symbol)
        future_info = fut_data["stocks"][0]["metadata"]
        fut_price = float(future_info["lastPrice"])

        # Calculate Premium
        premium = fut_price - spot

        # Days till expiry
        expiry = pd.to_datetime(future_info["expiryDate"])
        today = pd.to_datetime("today")
        days_left = (expiry - today).days

        # Annualized Cost of Carry
        annual_coc = (premium / spot) * (365 / days_left) * 100

        data.append({
            "Symbol": symbol,
            "Spot Price": spot,
            "Futures Price": fut_price,
            "Premium": round(premium, 2),
            "Annualized CoC (%)": round(annual_coc, 2),
            "Expiry": expiry.strftime('%Y-%m-%d')
        })

    except Exception as e:
        st.warning(f"Error fetching data for {symbol}: {e}")

# Show data table
if data:
    df = pd.DataFrame(data)
    st.dataframe(df.sort_values("Annualized CoC (%)", ascending=False), use_container_width=True)
else:
    st.write("No data to display.")

st.caption("Auto-refreshes every 60 seconds. Data from NSE.")
