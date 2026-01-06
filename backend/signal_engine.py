"""
Signal Engine
-------------

Responsibilities:
- Convert prediction into actionable trade signals
- Decide CALL / PUT / NO TRADE
- Pick strike (ATM / OTM)
- Enforce confidence & risk filters
"""

from backend.prediction_engine import PredictionEngine
from backend.option_chain_parser import OptionChainParser


class SignalEngine:

    # ------------------------------------------------------------
    # Configuration (can later move to config.py)
    # ------------------------------------------------------------
    MIN_CONFIDENCE = 60          # Minimum confidence to trade
    STRIKE_MODE = "ATM"          # ATM / OTM / ITM
    OTM_OFFSET = 3               # 1 strike away from ATM

    # ------------------------------------------------------------
    # Core signal generator
    # ------------------------------------------------------------
    @staticmethod
    def generate_signal(underlying_ltp):
        """
        Generate trading signal based on prediction.

        Returns:
        {
            action: BUY_CALL / BUY_PUT / NO_TRADE
            strike: int
            option_type: CE / PE
            confidence: int
            reason: list
        }
        """

        prediction = PredictionEngine.predict()
        print(prediction)
        # ---------------------------
        # No trade conditions
        # ---------------------------
        if prediction["direction"] == "NO_TRADE":
            return SignalEngine._no_trade("Prediction says NO_TRADE")

        if prediction["confidence"] < SignalEngine.MIN_CONFIDENCE:
            return SignalEngine._no_trade(
                f"Low confidence ({prediction['confidence']})"
            )

        # ---------------------------
        # Parse option chain
        # ---------------------------
        parsed_chain = OptionChainParser.parse(
            underlying_ltp=underlying_ltp
        )

        if not parsed_chain:
            return SignalEngine._no_trade("Option chain unavailable")

        atm = parsed_chain["atm"]
        otm = parsed_chain["otm"]
        itm = parsed_chain["itm"]

        # ---------------------------
        # Select strike
        # ---------------------------
        if SignalEngine.STRIKE_MODE == "ATM":
            selected = atm
        elif SignalEngine.STRIKE_MODE == "OTM":
            selected = otm
        elif SignalEngine.STRIKE_MODE == "ITM":
            selected = itm
        else:
            selected = atm

        if selected is None:
            return SignalEngine._no_trade("Strike selection failed")

        # ---------------------------
        # Direction → Option type
        # ---------------------------
        if prediction["direction"] == "BULLISH":
            option_type = "CE"
            action = "BUY_CALL"
            ltp = selected["ce_ltp"]
        elif prediction["direction"] == "BEARISH":
            option_type = "PE"
            action = "BUY_PUT"
            ltp = selected["pe_ltp"]
        else:
            return SignalEngine._no_trade("Invalid prediction direction")

        # ---------------------------
        # Sanity checks
        # ---------------------------
        if ltp is None or ltp <= 0:
            return SignalEngine._no_trade("Invalid option LTP")

        # ---------------------------
        # Final signal
        # ---------------------------
        return {
            "action": action,
            "option_type": option_type,
            "strike": int(selected["strike"]),
            "confidence": prediction["confidence"],
            "reason": prediction["details"]["reasons"],
            "prediction_score": prediction["score"]
        }

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    @staticmethod
    def _no_trade(reason):
        return {
            "action": "NO_TRADE",
            "confidence": 0,
            "reason": reason
        }


# ------------------------------------------------------------
# Local test
# ------------------------------------------------------------
# if __name__ == "__main__":
#     # Example underlying price (replace with live LTP later)
#     nifty_ltp = 25942.0

#     signal = SignalEngine.generate_signal(
#         underlying_ltp=nifty_ltp
#     )

#     print("\nGenerated Signal:")
#     print(signal)

