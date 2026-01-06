"""
State Manager for Streamlit App
-------------------------------

Keeps all UI / bot state in one place.
"""

import streamlit as st


def init_state():
    defaults = {
        "bot_running": False,
        "auto_trade": True,
        "last_signal": None,
        "last_prediction": None,
        "status_msg": "Idle",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
