"""
Backend package for Options Scalper Bot.

Modules included:
- config: Credentials & constants
- data_fetcher: Fetches option chain, OHLC, LTP
- ohlc_processor: Candle resampling utilities
- option_chain_parser: ATM/Strike selection logic
- analysis_engine: Technical indicator computations
- prediction_engine: Prediction model
- signal_engine: Entry/Exit logic
- order_manager: Dhan order execution layer
- ws_manager: WebSocket listener for order updates
"""

__all__ = [
    "config",
    "data_fetcher",
    "ohlc_processor",
    "option_chain_parser",
    "analysis_engine",
    "prediction_engine",
    "signal_engine",
    "order_manager",
    "ws_manager",
]
