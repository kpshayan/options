"""
Analysis Engine
---------------

Responsibilities:
- Compute technical indicators on OHLC data
- Provide trend & momentum context
- Serve features for prediction_engine & signal_engine
"""

import pandas as pd
import numpy as np

from backend.ohlc_processor import OHLCProcessor


class AnalysisEngine:

    # ============================================================
    # EMA
    # ============================================================
    @staticmethod
    def add_ema(df, periods=(9, 20, 50)):
        """
        Add EMA columns to dataframe.
        """
        for p in periods:
            df[f"ema_{p}"] = df["close"].ewm(span=p, adjust=False).mean()
        return df

    # ============================================================
    # RSI
    # ============================================================
    @staticmethod
    def add_rsi(df, period=14):
        """
        RSI using Wilder's smoothing (matches Zerodha / TradingView)
        """
        delta = df["close"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(
            alpha=1/period,
            min_periods=period,
            adjust=False
        ).mean()

        avg_loss = loss.ewm(
            alpha=1/period,
            min_periods=period,
            adjust=False
        ).mean()

        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))

        return df

    # ============================================================
    # VWAP
    # ============================================================
    @staticmethod
    def add_vwap(df):
        """
        Add VWAP (per day).
        """
        df = df.copy()
        df["date"] = df["timestamp"].dt.date

        df["tp"] = (df["high"] + df["low"] + df["close"]) / 3
        df["tpv"] = df["tp"] * df["volume"]

        df["cum_tpv"] = df.groupby("date")["tpv"].cumsum()
        df["cum_vol"] = df.groupby("date")["volume"].cumsum()

        df["vwap"] = df["cum_tpv"] / df["cum_vol"]

        df.drop(columns=["tp", "tpv", "cum_tpv", "cum_vol", "date"], inplace=True)

        return df

    # ============================================================
    # Volume Spike
    # ============================================================
    @staticmethod
    def add_volume_spike(df, lookback=20):
        avg_vol = df["volume"].rolling(lookback).mean()
        df["volume_ratio"] = df["volume"] / avg_vol

        df["volume_spike"] = df["volume_ratio"] >= 1.8
        return df

    # ============================================================
    # Trend Bias
    # ============================================================
    @staticmethod
    def add_trend_bias(df):
        """
        Determine bullish / bearish / neutral trend.
        """
        conditions = [
            (df["ema_9"] > df["ema_20"]) & (df["ema_20"] > df["ema_50"]),
            (df["ema_9"] < df["ema_20"]) & (df["ema_20"] < df["ema_50"]),
        ]

        choices = ["BULLISH", "BEARISH"]

        df["trend_bias"] = np.select(conditions, choices, default="NEUTRAL")
        return df

    # ============================================================
    # Composite indicator pipeline
    # ============================================================
    @staticmethod
    def enrich(df):
        """
        Apply all indicators in correct order.
        """
        df = df.copy()

        df = AnalysisEngine.add_ema(df)
        df = df.iloc[:-1].copy()
        df = AnalysisEngine.add_rsi(df)
        df = AnalysisEngine.add_vwap(df)
        df = AnalysisEngine.add_volume_spike(df)
        df = AnalysisEngine.add_trend_bias(df)

        return df

    # ============================================================
    # Public helpers by timeframe
    # ============================================================
    @staticmethod
    def analyze_5m():
        df = OHLCProcessor.get_5m()
        if df is None:
            return None
        return AnalysisEngine.enrich(df)

    @staticmethod
    def analyze_15m():
        df = OHLCProcessor.get_15m()
        if df is None:
            return None
        return AnalysisEngine.enrich(df)


# ------------------------------------------------------------------
# Local test
# ------------------------------------------------------------------
if __name__ == "__main__":
    df_5m = AnalysisEngine.analyze_5m()
    df_15m = AnalysisEngine.analyze_15m()

    print("5m analysis sample:")
    print(df_5m.tail(3))

    print("\n15m analysis sample:")
    print(df_15m.tail(3))

