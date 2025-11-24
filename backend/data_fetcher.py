import threading
import time
import pandas as pd
from datetime import datetime, timedelta
import dhanhq

from backend.config import dhan, UNDER_INTERVAL, DEFAULT_FETCH_INTERVAL, UNDER_SECURITY_ID, UNDER_EXCHANGE_SEGMENT,OHLC_DAYS,UNDER_INSTRUMENT_TYPE


DATA_CACHE = {
    "option_chain": None,
    "option_chain_timestamp": None,

    "ohlc_1m": None,
    "ohlc_timestamp": None,

    "last_updated": None
}


class DataFetcher :
    def __init__(self, interval_seconds=DEFAULT_FETCH_INTERVAL):
        self.interval = interval_seconds
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

        print(f"[DataFetcher] Started (interval={self.interval} sec)")

    # Stop polling
    def stop(self):
        self.running = False
        print("[DataFetcher] Stopped")

    # Update interval (frontend control)
    def update_interval(self, new_interval):
        self.interval = new_interval
        print(f"[DataFetcher] Fetch interval changed to {new_interval} sec")

    # Main polling loop
    def _run_loop(self):
        while self.running:
            try:
                self.fetch_option_chain()
                self.fetch_ohlc_1m()
                DATA_CACHE["last_updated"] = datetime.now()
            except Exception as e:
                print(f"[DataFetcher] Error: {e}")

            time.sleep(self.interval)

    #=====================================================
    # Expiry List to get current expiry date via SDK
    #=====================================================
    def expiry_lists(self):
        expiries = dhan.expiry_list(
            under_security_id=UNDER_SECURITY_ID,                       # Nifty
            under_exchange_segment=UNDER_EXCHANGE_SEGMENT
        )
        if not expiries:
            print("[DataFetcher] No expiry data found")
            return

        nearest_expiry = expiries["data"]["data"][0]
        return nearest_expiry
        
    # =====================================================
    # Option Chain via SDK
    # =====================================================
    def fetch_option_chain(self):
        """
        Fetch full option chain using Dhan SDK.
        Auto-detects nearest expiry.
        """
        try:
            chain = dhan.option_chain(
                under_security_id=UNDER_SECURITY_ID,               
                under_exchange_segment=UNDER_EXCHANGE_SEGMENT,      
                expiry = self.expiry_lists()
            )         
            DATA_CACHE["option_chain"] = chain["data"]
            DATA_CACHE["option_chain_timestamp"] = datetime.now()         

        except Exception as e:
            print(f"[DataFetcher] Option Chain Fetch ERROR: {e}")


    # =====================================================
    # OHLC using SDK (1 minute candles)
    # =====================================================
    def fetch_ohlc(self):
        try:
            # Last 2 days of 1-minute data
            start_date = (datetime.now() - timedelta(OHLC_DAYS)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")

            candles = dhan.intraday_minute_data(
                security_id=UNDER_SECURITY_ID, 
                exchange_segment=UNDER_EXCHANGE_SEGMENT,
                instrument_type=UNDER_INSTRUMENT_TYPE,
                from_date=start_date,
                to_date=end_date,
                interval=UNDER_INTERVAL
            )
            if not candles:
                print("[DataFetcher] No OHLC data returned")
                return

            df = pd.DataFrame(candles["data"], columns=[
                "timestamp", "open", "high", "low", "close", "volume"
            ])
            df["timestamp"] = (pd.to_datetime(df["timestamp"], unit="s", utc=True)
                                .dt.tz_convert("Asia/Kolkata")
                                .dt.tz_localize(None))
            DATA_CACHE["ohlc"] = df
            DATA_CACHE["ohlc_timestamp"] = datetime.now()

        except Exception as e:
            print(f"[DataFetcher] OHLC Fetch ERROR: {e}")


# Create singleton DataFetcher instance
data_fetcher = DataFetcher()

if __name__ == "__main__":
    

    df = DataFetcher()
    df.fetch_ohlc()
    print(DATA_CACHE["ohlc"])