"""
OHLC Processor
--------------

Responsibilities:
- Convert raw 1-minute OHLC timestamps to IST
- Filter NSE market hours (09:15–15:30)
- Resample 1m data into 5m and 15m candles
"""

import pandas as pd
from backend.data_fetcher import DATA_CACHE


class OHLCProcessor:

    MARKET_START = "09:15"
    MARKET_END = "15:30"
    TIMEZONE = "Asia/Kolkata"
    
    @staticmethod
    def get_1m():
        """Return raw 1-minute OHLC DataFrame from cache."""
        df = DATA_CACHE.get("ohlc_1m")
        print(df)
        if df is None or df.empty:
            print("[OHLCProcessor] No 1m OHLC data available.")
            return None
        return df.copy()

    # ------------------------------------------------------------------
    # Timestamp handling
    # ------------------------------------------------------------------
    @staticmethod
    def convert_to_ist(df):
        """
        Convert UNIX timestamp (seconds) to IST datetime.
        """
        if "timestamp" not in df.columns:
            raise ValueError("timestamp column missing")

        df["timestamp"] = (
            pd.to_datetime(df["timestamp"], unit="s", utc=True)
              .dt.tz_convert(OHLCProcessor.TIMEZONE)
              .dt.tz_localize(None)  # make timezone-naive IST
        )

        return df

    # ------------------------------------------------------------------
    # Market hours filter
    # ------------------------------------------------------------------
    @staticmethod
    def filter_market_hours(df):
        """
        Keep only NSE market hours: 09:15–15:30
        """
        df = df.set_index("timestamp")
        df = df.between_time(
            OHLCProcessor.MARKET_START,
            OHLCProcessor.MARKET_END
        )
        return df.reset_index()

    # ------------------------------------------------------------------
    # Resampling logic
    # ------------------------------------------------------------------
    @staticmethod
    def resample(df, timeframe):
        """
        Resample OHLC data.

        timeframe examples:
        - "5T"  → 5 minutes
        - "15T" → 15 minutes
        """
        df = df.set_index("timestamp")

        ohlc = (
            df.resample(timeframe,origin="start_day",
        offset="9h15min")
              .agg({
                  "open": "first",
                  "high": "max",
                  "low": "min",
                  "close": "last",
                  "volume": "sum"
              })
              .dropna()
        )

        return ohlc.reset_index()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @staticmethod
    def get_5m():
        """Return 5-minute OHLC candles."""
        df = OHLCProcessor.get_1m()
        if df is None:
            return None

        df = OHLCProcessor.convert_to_ist(df)
        df = OHLCProcessor.filter_market_hours(df)

        return OHLCProcessor.resample(df, "5T")

    @staticmethod
    def get_15m():
        """Return 15-minute OHLC candles."""
        df = OHLCProcessor.get_1m()
        if df is None:
            return None

        df = OHLCProcessor.convert_to_ist(df)
        df = OHLCProcessor.filter_market_hours(df)

        return OHLCProcessor.resample(df, "15T")


# ----------------------------------------------------------------------
# Local test
# ----------------------------------------------------------------------
# if __name__ == "__main__":
#     df_5m = OHLCProcessor.get_5m()
#     df_15m = OHLCProcessor.get_15m()

#     print("5-minute candles:")
#     print(df_5m)

#     print("\n15-minute candles:")
#     print(df_15m)

