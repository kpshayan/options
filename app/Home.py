import streamlit as st
import time
from dotenv import load_dotenv


from app.state import init_state
from app.controls import render_controls
from app.dashboard import render_dashboard
from scripts.run_bot import TradingBot

load_dotenv()

st.set_page_config(page_title="Options Scalper Bot", layout="wide")

# ------------------------------------------------
# Init state
# ------------------------------------------------
init_state()

st.title("📈 Options Scalper Bot")

# ------------------------------------------------
# Dashboard + Controls
# ------------------------------------------------
render_dashboard()
st.divider()
render_controls()

# ------------------------------------------------
# Bot loop
# ------------------------------------------------
if st.session_state.bot_running:
    TradingBot.tick(auto_trade=st.session_state.auto_trade)
    time.sleep(2)
    st.rerun()
