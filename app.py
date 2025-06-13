import streamlit as st
from nselib import capital_market, derivatives
from datetime import datetime, time
import nsepython
import concurrent.futures
import traceback
import pandas as pd

# Setup
st.set_page_config(page_title="Cash-Futures Arbitrage", layout="wide")
st.title("📈 NSE Cash-Futures Arbitrage Dashboard")

# Market hours check
def is_market_open():
    now = datetime.now()
    return time(9, 15) <= now.time() <= time(15, 30) and now.weekday() < 5

if not is_market_open():
    st.warning("⚠️ NSE market is closed (9:15 AM - 3:30 PM IST, Mon-Fri). Data may be stale.")

# Symbols
all_fno = ['NIFTY', 'NIFTYIT', 'BANKNIFTY', 'MANAPPURAM', 'MAXHEALTH', 'ICICIGI', 'OIL', 'JUBLFOOD', 'GLENMARK', 'BEL', 'ASTRAL', 'MUTHOOTFIN', 'SUPREMEIND', 'HAL', 'BDL', 'BLUESTARCO', 'ONGC', 'POLICYBZR', 'BIOCON', 'SOLARINDS', 'GODREJPROP', 'CDSL', 'TORNTPOWER', 'PRESTIGE', 'DLF', 'MCX', 'OFSS', 'CHAMBLFERT', 'TECHM', 'OBEROIRLTY', 'MFSL', 'PIIND', 'LODHA', 'APLAPOLLO', 'COFORGE', 'DELHIVERY', 'SBICARD', 'KALYANKJIL', 'PPLPHARMA', 'BHARATFORG', 'WIPRO', 'TCS', 'CIPLA', 'BOSCHLTD', 'LTIM', 'TVSMOTOR', 'NBCC', 'EICHERMOT', 'TATACOMM', 'MARUTI', 'PAGEIND', 'SRF', 'ALKEM', 'CROMPTON', 'APOLLOHOSP', 'INDIANB', 'NYKAA', 'LAURUSLABS', 'SUNPHARMA', 'KAYNES', 'DRREDDY', 'SHRIRAMFIN', 'BHEL', 'CUMMINSIND', 'UPL', 'IRCTC', 'KEI', 'GAIL', 'SIEMENS', 'MAZDOCK', 'ASIANPAINT', 'MARICO', 'BRITANNIA', 'TRENT', 'TATAMOTORS', 'BHARTIARTL', 'HCLTECH', 'SHREECEM', 'INFY', 'NESTLEIND', 'ASHOKLEY', 'BAJFINANCE', 'JIOFIN', 'HINDCOPPER', 'TORNTPHARM', 'HDFCLIFE', 'ABB', 'BALKRISIND', 'COALINDIA', 'CGPOWER', 'BANKBARODA', 'TATASTEEL', 'POLYCAB', 'HINDZINC', 'TATACONSUM', 'PERSISTENT', 'ICICIPRULI', 'MANKIND', 'PATANJALI', 'FEDERALBNK', 'M&M', 'NTPC', 'LICI', 'VEDL', 'RECLTD', 'SAIL', 'AXISBANK', 'ZYDUSLIFE', 'LT', 'KPITTECH', 'ICICIBANK', 'HINDUNILVR', 'SBILIFE', 'CESC', 'HEROMOTOCO', 'NATIONALUM', 'NAUKRI', 'AUROPHARMA', 'PHOENIXLTD', 'LICHSGFIN', 'BAJAJFINSV', 'DMART', 'MOTHERSON', 'MPHASIS', 'IDFCFIRSTB', 'VOLTAS', 'AMBUJACEM', 'INDUSTOWER', 'DIVISLAB', 'TATAPOWER', 'PETRONET', 'ETERNAL', 'DALBHARAT', 'JSWSTEEL', 'UNOMINDA', 'YESBANK', 'ACC', 'GRASIM', 'FORTIS', 'PIDILITIND', 'BSOFT', 'TATACHEM', 'ULTRACEMCO', 'TITAN', 'TATATECH', 'HAVELLS', 'RELIANCE', 'ABCAPITAL', 'KOTAKBANK', 'BAJAJ-AUTO', 'IRB', 'M&MFIN', 'IDEA', 'HUDCO', 'POWERGRID', 'LTF', 'ABFRL', 'TITAGARH', 'GMRAIRPORT', 'DABUR', 'DIXON', 'IRFC', 'POONAWALLA', 'CYIENT', 'BSE', 'SJVN', 'CONCOR', 'PAYTM', 'BANKINDIA', 'VBL', 'RVNL', 'INDHOTEL', 'SYNGENE', 'HDFCBANK', 'TATAELXSI', 'LUPIN', 'PNB', 'TIINDIA', 'AUBANK', 'INDUSINDBK', 'GODREJCP', 'COLPAL', 'HDFCAMC', 'ADANIENT', 'BANDHANBNK', 'HINDALCO', 'RBLBANK', 'IIFL', 'SONACOMS', 'NHPC', 'JSWENERGY', 'SBIN', 'JSL', 'HINDPETRO', 'AARTIIND', 'ADANIENSOL', 'MGL', 'ITC', 'IOC', 'CHOLAFIN', 'IEX', 'IGL', 'BPCL', 'PEL', 'HFCL', 'INOXWIND', 'ATGL', 'JINDALSTEL', 'CAMS', 'ADANIGREEN', 'UNITDSPR', 'PFC', 'NCC', 'EXIDEIND', 'UNIONBANK', 'NMDC', 'ADANIPORTS', 'PNBHOUSING', 'GRANULES', 'ANGELONE', 'CANBK', 'INDIGO', 'IREDA']
default_stocks = ["INFY", "TCS", "RELIANCE", "HDFCBANK", "ITC", "ICICIBANK"]
symbols = st.multiselect("Select Stocks", sorted(all_fno[3:]), default= sorted(all_fno[3:]))

# Data Retrieval
def process_symbol(symbol):
    try:
        fut_data = derivatives.future_price_volume_data(
            symbol=symbol, instrument="FUTSTK",
            from_date="06-06-2025", to_date="13-06-2025", period="1D"
        )
        spot_data = capital_market.price_volume_data(
            symbol=symbol, from_date="06-06-2025", to_date="13-06-2025", period="1D"
        )

        fut_price = float(fut_data["LAST_TRADED_PRICE"][0])
        raw_price = spot_data["LastPrice"][1]
        spot_price = float(raw_price.replace(",", "")) if isinstance(raw_price, str) else float(raw_price)

        expiry_str = fut_data["EXPIRY_DT"][0]
        expiry_date = datetime.strptime(expiry_str, "%d-%b-%Y")
        premium = fut_price - spot_price

        days_to_expiry = (expiry_date - datetime.now()).days
        annual_coc = ((premium / spot_price) * (365 / days_to_expiry) * 100) if days_to_expiry > 0 else 0.0

        return {
            "Symbol": symbol,
            "Spot Price": spot_price,
            "Futures Price": fut_price,
            "Premium": premium,
            "Annualized CoC (%)": annual_coc,
            "Expiry": expiry_date.strftime("%Y-%m-%d")
        }

    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")
        traceback.print_exc()
        return None

# Run concurrent fetch + update session state
def update_data():
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=70) as executor:
        futures = [executor.submit(process_symbol, symbol) for symbol in symbols]
        for f in concurrent.futures.as_completed(futures):
            result = f.result()
            if result:
                results.append(result)
    st.session_state.results = results
    st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")

# Refresh trigger
if "last_updated" not in st.session_state:
    update_data()
elif st.button("🔄 Refresh Now") or (is_market_open() and datetime.now().second % 60 == 0):
    update_data()

# Display results
if "results" in st.session_state and st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    df = df.sort_values("Annualized CoC (%)", ascending=False)

    def highlight_coc(row):
        return ['background-color: #3e403e' if row['Annualized CoC (%)'] > 8 else ''] * len(row)

    st.dataframe(df.style.apply(highlight_coc, axis=1), use_container_width=True)
    st.caption(f"Last updated at ⏰ {st.session_state.last_updated}")
else:
    st.info("⏳ Awaiting data...")

st.caption("Auto-updates every 60s during market hours • Parallel fetch via ThreadPool • Powered by NSElib • Built by Anuj")
