"""
Controls UI
-----------

Start/Stop bot
Manual Buy CE / PE
Auto-trade toggle
"""

import streamlit as st
from backend.order_manager import OrderManager
from backend.signal_engine import SignalEngine
from scripts.run_bot import TradingBot
from backend.data_fetcher import DATA_CACHE


def render_controls():
    st.subheader("🎮 Controls")

    col1, col2, col3 = st.columns(3)

    # ------------------------------------------------
    # Start / Stop bot
    # ------------------------------------------------
    with col1:
        if st.button("▶ Start Bot"):
            TradingBot.start()
            st.session_state.bot_running = True
            st.session_state.status_msg = "Bot running"

    with col2:
        if st.button("⏹ Stop Bot"):
            TradingBot.stop()
            st.session_state.bot_running = False
            st.session_state.status_msg = "Bot stopped"

    # ------------------------------------------------
    # Auto trade toggle
    # ------------------------------------------------
    with col3:
        st.session_state.auto_trade = st.checkbox(
            "AUTO TRADE",
            value=st.session_state.auto_trade
        )

    st.divider()

    # ------------------------------------------------
    # Manual trade buttons
    # ------------------------------------------------
    st.subheader("⚡ Manual Trade")

    chain = DATA_CACHE.get("option_chain")
    underlying_ltp = None
    if chain:
        underlying_ltp = chain["data"].get("underlying_ltp")

    col_ce, col_pe = st.columns(2)

    with col_ce:
        if st.button("🟢 BUY CE"):
            signal = SignalEngine.generate_signal(underlying_ltp)
            signal["action"] = "BUY_CALL"
            OrderManager._place_entry(signal)
            st.session_state.last_signal = signal
            st.success("CE order sent")

    with col_pe:
        if st.button("🔴 BUY PE"):
            signal = SignalEngine.generate_signal(underlying_ltp)
            signal["action"] = "BUY_PUT"
            OrderManager._place_entry(signal)
            st.session_state.last_signal = signal
            st.success("PE order sent")
