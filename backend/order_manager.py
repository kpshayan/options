"""
Order Manager
-------------

Responsibilities:
- Place orders using DhanHQ SDK
- Manage SL & Target
- Prevent duplicate trades
- Log trades to local storage
"""

import os
from datetime import datetime
import pandas as pd

from backend.config import dhan
from backend.signal_engine import SignalEngine
from backend.data_fetcher import DATA_CACHE


# ============================================================
# Configuration (can move to config.py later)
# ============================================================
TRADE_QTY = 50                   # lot size
PRODUCT_TYPE = "INTRADAY"
ORDER_TYPE = "MARKET"

STOPLOSS_PCT = 25                # % SL on option premium
TARGET_PCT = 40                  # % target on option premium

TRADE_LOG_PATH = "storage/trades.xlsx"


class OrderManager:

    active_trade = None   # holds current open trade (single trade model)

    # ------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------
    @staticmethod
    def process_signal(underlying_ltp):
        """
        Main entry called from bot loop.
        """
        if OrderManager.active_trade:
            print("[OrderManager] Trade already active, skipping new entry.")
            return

        signal = SignalEngine.generate_signal(underlying_ltp)

        if signal["action"] == "NO_TRADE":
            print("[OrderManager] NO_TRADE:", signal["reason"])
            return

        OrderManager._place_entry(signal)

    # ------------------------------------------------------------
    # Place entry order
    # ------------------------------------------------------------
    @staticmethod
    def _place_entry(signal):
        """
        Places entry order based on signal.
        """
        option_type = signal["option_type"]
        strike = signal["strike"]

        option_symbol = f"NIFTY {strike} {option_type}"

        try:
            print(f"[OrderManager] Placing order: {option_symbol}")

            # response = dhan.place_order(
            #     security_id=signal["strike"],          # NOTE: replace with option security_id
            #     exchange_segment="NFO_OPT",
            #     transaction_type="BUY",
            #     quantity=TRADE_QTY,
            #     order_type=ORDER_TYPE,
            #     product_type=PRODUCT_TYPE
            # )
            response = print("[PAPER TRADE] Order would be placed:", signal)

            if response.get("status") != "success":
                print("[OrderManager] Order failed:", response)
                return

            entry_price = response["data"].get("average_price")

            OrderManager.active_trade = {
                "symbol": option_symbol,
                "strike": strike,
                "option_type": option_type,
                "entry_price": entry_price,
                "qty": TRADE_QTY,
                "entry_time": datetime.now(),
                "sl": entry_price * (1 - STOPLOSS_PCT / 100),
                "target": entry_price * (1 + TARGET_PCT / 100)
            }

            OrderManager._log_trade("ENTRY", OrderManager.active_trade)

            print("[OrderManager] Entry placed:", OrderManager.active_trade)

        except Exception as e:
            print("[OrderManager] Entry ERROR:", e)

    # ------------------------------------------------------------
    # Monitor active trade
    # ------------------------------------------------------------
    @staticmethod
    def monitor_trade(current_option_ltp):
        """
        Check SL / Target for active trade.
        """
        if not OrderManager.active_trade:
            return

        trade = OrderManager.active_trade

        if current_option_ltp <= trade["sl"]:
            print("[OrderManager] Stoploss hit")
            OrderManager._exit_trade(current_option_ltp, "SL")

        elif current_option_ltp >= trade["target"]:
            print("[OrderManager] Target hit")
            OrderManager._exit_trade(current_option_ltp, "TARGET")

    # ------------------------------------------------------------
    # Exit trade
    # ------------------------------------------------------------
    @staticmethod
    def _exit_trade(exit_price, reason):
        trade = OrderManager.active_trade

        try:
            dhan.place_order(
                security_id=trade["strike"],           # NOTE: replace with option security_id
                exchange_segment="NFO_OPT",
                transaction_type="SELL",
                quantity=trade["qty"],
                order_type=ORDER_TYPE,
                product_type=PRODUCT_TYPE
            )

            trade["exit_price"] = exit_price
            trade["exit_time"] = datetime.now()
            trade["exit_reason"] = reason
            trade["pnl"] = (exit_price - trade["entry_price"]) * trade["qty"]

            OrderManager._log_trade("EXIT", trade)

            print("[OrderManager] Trade exited:", trade)

        except Exception as e:
            print("[OrderManager] Exit ERROR:", e)

        finally:
            OrderManager.active_trade = None

    # ------------------------------------------------------------
    # Trade logger
    # ------------------------------------------------------------
    @staticmethod
    def _log_trade(event_type, trade):
        """
        Append trade details to Excel.
        """
        os.makedirs(os.path.dirname(TRADE_LOG_PATH), exist_ok=True)

        row = {
            "event": event_type,
            "timestamp": datetime.now(),
            "symbol": trade["symbol"],
            "strike": trade["strike"],
            "option_type": trade["option_type"],
            "qty": trade["qty"],
            "entry_price": trade.get("entry_price"),
            "exit_price": trade.get("exit_price"),
            "sl": trade.get("sl"),
            "target": trade.get("target"),
            "pnl": trade.get("pnl"),
            "reason": trade.get("exit_reason")
        }

        df = pd.DataFrame([row])

        if os.path.exists(TRADE_LOG_PATH):
            existing = pd.read_excel(TRADE_LOG_PATH)
            df = pd.concat([existing, df], ignore_index=True)

        df.to_excel(TRADE_LOG_PATH, index=False)


# ------------------------------------------------------------
# Local test (DRY RUN – no real orders)
# ------------------------------------------------------------
if __name__ == "__main__":
    print("OrderManager loaded. Integrate via bot loop.")
