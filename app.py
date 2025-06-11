import streamlit as st
from streamlit_autorefresh import st_autorefresh
from nselib import capital_market, derivatives
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Cash-Futures Arbitrage", layout="wide")
st_autorefresh(interval=60 * 1000, key="autorefresh")

st.title("📈 NSE Cash-Futures Arbitrage Monitor")

# Select stocks
default_stocks = ["INFY", "TCS", "RELIANCE", "HDFCBANK", "ITC", "ICICIBANK"]
stocks = st.multiselect("Select Stocks", default_stocks, default=default_stocks)

data = []

for symbol in stocks:
    try:
        # Get spot price
        spot_data = capital_market.equity_stock_quote(symbol)
        spot_price = float(spot_data["priceInfo"]["lastPrice"])

        # Get futures chain
        fut_chain = derivatives.equity_derivatives(symbol)
        fut_row = next((item for item in fut_chain["data"] if item["instrumentType"] == "FUTSTK"), None)

        if not fut_row:
            st.warning(f"No futures data for {symbol}")
            continue

        fut_price = float(fut_row["lastPrice"])
        expiry_str = fut_row["expiryDate"]
        expiry_date = pd.to_datetime(expiry_str, format="%d-%b-%Y")
        today = pd.to_datetime(datetime.now().date())
        days_left = (expiry_date - today).days

        # Arbitrage calculations
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
        st.warning(f"{symbol}: {e}")

# Display table
if data:
    df = pd.DataFrame(data)
    st.dataframe(df.sort_values("Annualized CoC (%)", ascending=False), use_container_width=True)
else:
    st.error("No data to display.")

st.caption("Auto-refreshes every 60 seconds • Powered by nselib")
