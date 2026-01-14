"""
Prediction Engine
-----------------

Responsibilities:
- Combine multi-timeframe analysis (1m / 5m / 15m)
- Produce directional bias with confidence
- Feed signal_engine for order decisions
"""

import numpy as np
from backend.analysis_engine import AnalysisEngine


class PredictionEngine:

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    @staticmethod
    def _latest(df):
        """Return last completed candle."""
        if df is None or df.empty:
            return None
        return df.iloc[-1]

    # ------------------------------------------------------------
    # Core prediction logic
    # ------------------------------------------------------------
    @staticmethod
    def predict():
        """
        Multi-timeframe prediction.

        Returns:
        {
            direction: BULLISH / BEARISH / NO_TRADE
            confidence: 0-100
            details: dict
        }
        """

        df_5m = AnalysisEngine.analyze_5m()
        df_15m = AnalysisEngine.analyze_15m()

        if df_5m is None or df_15m is None:
            return PredictionEngine._no_trade("Insufficient OHLC data")

        c5 = PredictionEngine._latest(df_5m)
        c15 = PredictionEngine._latest(df_15m)

        score = 0
        reasons = []

        # --------------------------------------------------------
        # 1. Higher timeframe trend (15m) – highest weight
        # --------------------------------------------------------
        if c15["trend_bias"] == "BULLISH":
            score += 30
            reasons.append("15m trend bullish")
        elif c15["trend_bias"] == "BEARISH":
            score -= 30
            reasons.append("15m trend bearish")

        # --------------------------------------------------------
        # 2. Medium timeframe confirmation (5m)
        # --------------------------------------------------------
        if c5["trend_bias"] == c15["trend_bias"]:
            score += 20
            reasons.append("5m aligns with 15m")
        else:
            score -= 10
            reasons.append("5m conflicts with 15m")

        # --------------------------------------------------------
        # 3. Momentum (EMA stack on 5m)
        # --------------------------------------------------------
        if c5["ema_9"] > c5["ema_20"] > c5["ema_50"]:
            score += 15
            reasons.append("EMA bullish stack (5m)")
        elif c5["ema_9"] < c5["ema_20"] < c5["ema_50"]:
            score -= 15
            reasons.append("EMA bearish stack (5m)")

        # --------------------------------------------------------
        # 4. RSI condition (avoid extreme entries)
        # --------------------------------------------------------
        if c5["rsi"] > 70:
            score -= 10
            reasons.append("RSI overbought (5m)")
        elif c5["rsi"] < 30:
            score += 10
            reasons.append("RSI oversold (5m)")

        # --------------------------------------------------------
        # 5. Volume confirmation
        # --------------------------------------------------------
        if c5["volume_ratio"] >= 2.5:
            score += 15
        elif c5["volume_ratio"] >= 1.8:
            score += 10

        # --------------------------------------------------------
        # Final decision
        # --------------------------------------------------------
        confidence = min(abs(score), 100)

        if score >= 40:
            direction = "BULLISH"
        elif score <= -40:
            direction = "BEARISH"
        else:
            direction = "NO_TRADE"

        return {
            "direction": direction,
            "confidence": confidence,
            "score": score,
            "details": {
                "15m_trend": c15["trend_bias"],
                "5m_trend": c5["trend_bias"],
                "rsi_15m": round(float(c15["rsi"]),2),
                "reasons": reasons
            }
        }

    # ------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------
    @staticmethod
    def _no_trade(reason):
        return {
            "direction": "NO_TRADE",
            "confidence": 0,
            "score": 0,
            "details": {"reason": reason}
        }


# ------------------------------------------------------------
# Local test
# ------------------------------------------------------------
if __name__ == "__main__":
    result = PredictionEngine.predict()
    print("\nPrediction Output:")
    print(result)
