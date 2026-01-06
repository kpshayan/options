import time
from backend.data_fetcher import data_fetcher, DATA_CACHE
from backend.order_manager import OrderManager
from backend.signal_engine import SignalEngine


class TradingBot:

    running = False

    @staticmethod
    def start():
        if TradingBot.running:
            return

        TradingBot.running = True
        data_fetcher.start()
        print("[Bot] Started")

    @staticmethod
    def stop():
        TradingBot.running = False
        data_fetcher.stop()
        print("[Bot] Stopped")

    @staticmethod
    def tick(auto_trade=True):
        """
        Called every few seconds from Streamlit.
        """
        if not TradingBot.running:
            return

        # Get latest underlying price
        chain = DATA_CACHE.get("option_chain")
        if not chain:
            return

        underlying_ltp = chain["data"].get("underlying_ltp")
        if not underlying_ltp:
            return

        if auto_trade:
            OrderManager.process_signal(underlying_ltp)
