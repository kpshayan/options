from backend.data_fetcher import data_fetcher, DATA_CACHE
from backend.ohlc_processor import OHLCProcessor
from backend.analysis_engine import AnalysisEngine
from backend.prediction_engine import PredictionEngine
from backend.signal_engine import SignalEngine

# Step 1: Fetch data
data_fetcher.fetch_ohlc()
print("1m data loaded:", DATA_CACHE["ohlc_1m"].shape)

# Step 2: OHLC processing
df_5m = OHLCProcessor.get_5m()
print("5m candles:", df_5m.tail(3))

# Step 3: Analysis
df_analysis = AnalysisEngine.analyze_5m()
print("analysis*******")
print(df_analysis[["timestamp", "close", "trend_bias"]].tail())

# Step 4: Prediction
prediction = PredictionEngine.predict()
print("Prediction:", prediction)
# data_fetcher.fetch_option_chain()
# nifty_ltp = DATA_CACHE["option_chain"]
# print("*********Singnal output******\n")
# nifty_ltp = 26181.0

# signal = SignalEngine.generate_signal(
#         underlying_ltp=nifty_ltp
#     )
# print(signal)