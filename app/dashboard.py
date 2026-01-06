"""
Dashboard View
--------------

Displays:
- Prediction output
- Underlying price
- Bot status
"""

import streamlit as st
from backend.prediction_engine import PredictionEngine
from backend.data_fetcher import DATA_CACHE


def render_dashboard():
    st.subheader("📊 Dashboard")

    # ------------------------------------------------
    # Underlying price
    # ------------------------------------------------
    chain = DATA_CACHE.get("option_chain")
    underlying_ltp = None
    if chain:
        underlying_ltp = chain["data"].get("underlying_ltp")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Underlying LTP",
            value=underlying_ltp if underlying_ltp else "—"
        )

    with col2:
        st.metric(
            "Bot Status",
            value="RUNNING" if st.session_state.bot_running else "STOPPED"
        )

    st.divider()

    # ------------------------------------------------
    # Prediction
    # ------------------------------------------------
    prediction = PredictionEngine.predict()
    st.session_state.last_prediction = prediction

    st.subheader("🧠 Prediction Engine")
    st.json(prediction)

    # ------------------------------------------------
    # Last signal
    # ------------------------------------------------
    if st.session_state.last_signal:
        st.subheader("📌 Last Trade Signal")
        st.json(st.session_state.last_signal)
