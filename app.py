import streamlit as st
from streamlit_autorefresh import st_autorefresh
from nselib import capital_market, derivatives
import pandas as pd
from datetime import datetime, time
import yfinance as yf
import logging
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache configuration
st.set_page_config(page_title="Cash-Futures Arbitrage", layout="wide")
st_autorefresh(interval=60 * 1000, key="autorefresh")

st.title("📈 NSE Cash-Futures Arbitrage Dashboard")

# Check market hours (9:15 AM to 3:30 PM IST)
def is_market_open():
    current_time = datetime.now().time()
    market_open = time(9, 15)
    market_close = time(15, 30)
    return market_open <= current_time <= market_close and datetime.now().weekday() < 5

if not is_market_open():
    st.warning("⚠️ NSE market is closed (9:15 AM - 3:30 PM IST, Mon-Fri). Data may be stale or unavailable.")

# Fetch valid NSE symbols for validation
@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_valid_symbols():
    try:
        equity_df = capital_market.equity_list()
        return set(equity_df['SYMBOL'].str.upper())
    except Exception as e:
        logger.error(f"Failed to fetch equity list: {e}")
        return set()

valid_symbols = get_valid_symbols()

# 🏦 List of stocks
default_stocks = ["INFY", "TCS", "RELIANCE", "HDFCBANK", "ITC", "ICICIBANK"]
stocks = st.multiselect("Select Stocks", default_stocks, default=default_stocks)

# Validate selected stocks
invalid_stocks = [s for s in stocks if s.upper() not in valid_symbols]
if invalid_stocks:
    st.warning(f"⚠️ Invalid symbols: {', '.join(invalid_stocks)}. Please select valid NSE symbols.")

results = []

# Function to fetch spot price with retry and fallback
@st.cache_data(ttl=60)
def fetch_spot_price(symbol, retries=3):
    for attempt in range(retries):
        try:
            spot_df = capital_market.price_volume_data(symbol=symbol, period="1D")
            if spot_df.empty:
                raise ValueError("Empty DataFrame returned")
            # Clean the price string by removing commas before converting to float
            price_str = spot_df["LastPrice"].iloc[-1]
            if isinstance(price_str, str):
                price_str = price_str.replace(',', '')
            return float(price_str)
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {symbol}: {e}")
            if attempt == retries - 1:
                # Fallback to yfinance
                try:
                    stock = yf.Ticker(f"{symbol}.NS")
                    hist = stock.history(period="1d")
                    if hist.empty:
                        raise ValueError("No data available from yfinance")
                    spot_price = hist["Close"].iloc[-1]
                    st.warning(f"⚠️ {symbol}: Using yfinance fallback for spot price")
                    return float(spot_price)
                except Exception as e2:
                    logger.error(f"Fallback failed for {symbol}: {e2}")
                    raise Exception(f"Failed to fetch spot price: {e2}")
            continue

# Function to fetch futures price
@st.cache_data(ttl=60)
def fetch_futures_price(symbol, retries=3):
    for attempt in range(retries):
        try:
            future_df = derivatives.future_price_volume_data(symbol=symbol, instrument="FUTSTK", period="1D")
            if future_df.empty:
                raise ValueError("Empty DataFrame returned")
            
            # Use the correct uppercase column names
            price_columns = ['LAST_TRADED_PRICE', 'CLOSING_PRICE', 'SETTLE_PRICE', 'OPENING_PRICE']
            price_col = None
            for col in price_columns:
                if col in future_df.columns:
                    price_col = col
                    break
            if price_col is None:
                raise ValueError("No valid price column found in futures data")
            
            expiry_col = 'EXPIRY_DT' if 'EXPIRY_DT' in future_df.columns else 'Expiry'
            if expiry_col not in future_df.columns:
                raise ValueError("No expiry date column found")
            
            return future_df, price_col, expiry_col
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {symbol}: {e}")
            if attempt == retries - 1:
                raise Exception(f"Failed to fetch futures price: {e}")
            continue

# Fetch data with spinner
with st.spinner("Fetching data..."):
    for symbol in stocks:
        if symbol.upper() not in valid_symbols:
            continue
        try:
            # 📊 Spot Price
            spot_price = fetch_spot_price(symbol)

            # 📉 Futures Price (latest expiry)
            future_df, price_col, expiry_col = fetch_futures_price(symbol)
            fut_price = float(future_df[price_col].iloc[0])
            expiry_str = future_df[expiry_col].iloc[0]  # Format: '27-Jun-2025' or similar
            try:
                expiry_date = pd.to_datetime(expiry_str, format="%d-%b-%Y")
            except ValueError as e:
                logger.error(f"Failed to parse expiry date for {symbol}: {e}")
                st.warning(f"❌ {symbol}: Invalid expiry date format")
                continue
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
            logger.error(f"Error processing {symbol}: {e}")
            st.warning(f"❌ {symbol}: {e}")

# 📊 Display results
if results:
    df = pd.DataFrame(results)
    df = df.sort_values("Annualized CoC (%)", ascending=False)
    # Highlight high CoC
    def highlight_coc(row):
        color = 'background-color: #3e403e' if row['Annualized CoC (%)'] > 8 else ''
        return [color] * len(row)
    st.dataframe(df.style.apply(highlight_coc, axis=1), use_container_width=True)
else:
    st.error("⚠️ No data fetched.")

st.caption("Auto-refreshes every 60 seconds • Spot & Futures via nselib/yfinance • Built by Manav")
