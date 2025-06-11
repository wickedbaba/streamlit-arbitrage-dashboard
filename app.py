import streamlit as st
from streamlit_autorefresh import st_autorefresh
from nselib import capital_market, derivatives
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Cash-Futures Arbitrage", layout="wide")
st_autorefresh(interval=60 * 1000, key="autorefresh")

st.title("📈 NSE Cash-Futures Arbitrage Dashboard")

# 🏦 List of stocks
default_stocks = ["INFY", "TCS", "RELIANCE", "HDFCBANK", "ITC", "ICICIBANK"]
stocks = st.multiselect("Select Stocks", default_stocks, default=default_stocks)

results = []

for symbol in stocks:
    try:
        # 📊 Spot Price from capital_market
        spot_df = capital_market.price_volume_data(symbol=symbol, period="1D")
        spot_price = float(spot_df["LastPrice"].iloc[-1])

        # 📉 Futures Price (latest expiry) from derivatives
        future_df = derivatives.future_price_volume_data(
            symbol=symbol, instrument="FUTSTK", period="1D"
        )

        # Use the first row as nearest expiry
        fut_price = float(future_df["Close"].iloc[0])
        expiry_str = future_df["Expiry"].iloc[0]  # Format: '27-Jun-2025'
        expiry_date = pd.to_datetime(expiry_str, format="%d-%b-%Y")
        today = pd.to_datetime(datetime.now().date())
        days_left = max((expiry_date - today).days, 1)

        # 🧮 Arbitrage Calculations
        premium = fut_price - spot_price
        annual_coc = (premium / spot_price) * (365 / days_left) * 100

        results.append({
            "Symbol": symbol,
            "Spot Price": round(spot_price, 2),
            "Futures Price": round(fut_price, 2),
            "Premium": round(premium, 2),
            "Annualized CoC (%)": round(annual_coc, 2),
            "Expiry": expiry_date.strftime("%Y-%m-%d")
        })

    except Exception as e:
        st.warning(f"❌ {symbol}: {e}")

# 📊 Display results
if results:
    df = pd.DataFrame(results)
    df = df.sort_values("Annualized CoC (%)", ascending=False)
    st.dataframe(df, use_container_width=True)
else:
    st.error("⚠️ No data fetched.")

st.caption("Auto-refreshes every 60 seconds • Spot & Futures via nselib • Built by Manav")
