"""
Option Chain Parser Module
--------------------------

This module parses the raw option chain data returned by Dhan
and provides structured outputs:

- ATM strike
- CE / PE extraction
- Distance-based strike selection (OTM/ITM)
- Clean DataFrame version for analytics
"""
from backend.config import OI_STRIKE_RANGE  
from backend.data_fetcher import DATA_CACHE, CACHE_LOCK
import pandas as pd
PREV_OPTION_DF = None
DAY_START_OPTION_DF = None
PREV_EXPIRY = None
SESSION_DATE = None

class OptionChainParser:

    @staticmethod
    def get_raw_chain():
        """Return raw option chain JSON from DATA_CACHE."""
        with CACHE_LOCK:
            return DATA_CACHE.get("option_chain")

    @staticmethod
    def _first_present(item, keys):
        for key in keys:
            if key in item and item.get(key) is not None:
                return item.get(key)
        return None

    @staticmethod
    def to_dataframe(raw_chain=None):
        """
        Convert option chain into a DataFrame with columns:
        strike, ce_bid, ce_ask, ce_ltp, ce_oi, pe_bid, pe_ask, pe_ltp, pe_oi
        """
        if raw_chain is None:
            raw_chain = OptionChainParser.get_raw_chain()

        if not raw_chain:
            print("[OptionChainParser] No valid option chain found.")
            return None

        # Some callers store the whole response, others only response["data"].
        chain_data = raw_chain.get("data", raw_chain)
        if not chain_data:
            print("[OptionChainParser] No valid option chain found.")
            return None

        ce_list = []
        pe_list = []

        # Dhan GH SDK stores CE/PE under data['CE'] & data['PE']
        ce_raw = chain_data.get("CE", [])
        pe_raw = chain_data.get("PE", [])

        # Convert CE to dict keyed by strike
        for item in ce_raw:
            ce_list.append({
                "strike": item.get("strike_price"),
                "ce_ltp": item.get("ltp"),
                "ce_bid": item.get("bidPrice"),
                "ce_ask": item.get("askPrice"),
                "ce_oi": item.get("openInterest"),
                "ce_security_id": OptionChainParser._first_present(
                    item,
                    ["securityId", "security_id", "securityID"]
                ),
                "ce_oi_prev_day_change_api": OptionChainParser._first_present(
                    item,
                    ["oiChange", "changeInOI", "changeinOpenInterest", "openInterestChange"]
                ),
                "ce_prev_oi": OptionChainParser._first_present(
                    item,
                    ["previousOpenInterest", "prevOpenInterest", "prevOI", "previous_oi"]
                ),
                "ce_ltp_prev_day_change_api": OptionChainParser._first_present(
                    item,
                    ["change", "netChange", "ltpChange", "changeValue"]
                ),
                "ce_prev_close": OptionChainParser._first_present(
                    item,
                    ["previousClose", "prevClose", "closePrice", "previous_close"]
                ),
            })

        # Convert PE to dict keyed by strike
        for item in pe_raw:
            pe_list.append({
                "strike": item.get("strike_price"),
                "pe_ltp": item.get("ltp"),
                "pe_bid": item.get("bidPrice"),
                "pe_ask": item.get("askPrice"),
                "pe_oi": item.get("openInterest"),
                "pe_security_id": OptionChainParser._first_present(
                    item,
                    ["securityId", "security_id", "securityID"]
                ),
                "pe_oi_prev_day_change_api": OptionChainParser._first_present(
                    item,
                    ["oiChange", "changeInOI", "changeinOpenInterest", "openInterestChange"]
                ),
                "pe_prev_oi": OptionChainParser._first_present(
                    item,
                    ["previousOpenInterest", "prevOpenInterest", "prevOI", "previous_oi"]
                ),
                "pe_ltp_prev_day_change_api": OptionChainParser._first_present(
                    item,
                    ["change", "netChange", "ltpChange", "changeValue"]
                ),
                "pe_prev_close": OptionChainParser._first_present(
                    item,
                    ["previousClose", "prevClose", "closePrice", "previous_close"]
                ),
            })

        df_ce = pd.DataFrame(ce_list)
        df_pe = pd.DataFrame(pe_list)

        # Merge CE & PE into one table
        df = pd.merge(df_ce, df_pe, on="strike", how="outer").sort_values("strike")
        numeric_cols = [c for c in df.columns if c not in ("strike", "ce_security_id", "pe_security_id")]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

        return df.reset_index(drop=True)
    
    @staticmethod
    def get_atm_window(df, atm_strike, window=3):
        df = df.sort_values("strike").reset_index(drop=True)

        if atm_strike not in df["strike"].values:
            return None

        atm_idx = df.index[df["strike"] == atm_strike][0]

        start = max(atm_idx - window, 0)
        end = atm_idx + window + 1

        return df.iloc[start:end]

    @staticmethod
    def get_atm_strike(ltp, strikes):
        """Return the ATM strike closest to underlying LTP."""
        return min(strikes, key=lambda x: abs(x - ltp))

    @staticmethod
    def get_atm(df, underlying_ltp):
        """Return ATM CE/PE row."""
        df_strikes = df["strike"].tolist()
        atm_strike = OptionChainParser.get_atm_strike(underlying_ltp, df_strikes)

        atm_row = df[df["strike"] == atm_strike]
        return atm_row.iloc[0] if not atm_row.empty else None

    @staticmethod
    def get_strike_offset(df, atm_row, offset):
        """
        +offset = OTM, -offset = ITM relative to ATM.
        For example:
            offset = 1 → 1 step OTM
            offset = -1 → 1 step ITM
        """
        if atm_row is None:
            return None

        idx = df[df["strike"] == atm_row["strike"]].index[0]
        target_idx = idx + offset

        if 0 <= target_idx < len(df):
            return df.iloc[target_idx]

        return None

    @staticmethod
    def parse(underlying_ltp=None):
        """
        Convenience helper:
        - Convert chain to DataFrame
        - Find ATM
        - Find 1-step OTM and ITM
        """
        global PREV_OPTION_DF, DAY_START_OPTION_DF, PREV_EXPIRY, SESSION_DATE

        raw = OptionChainParser.get_raw_chain()
        if not raw:
            print("[OptionChainParser] No option chain cached.")
            return None

        df = OptionChainParser.to_dataframe(raw)

        if df is None:
            return None

        # If LTP not passed, try from data_fetcher stored chain
        if underlying_ltp is None:
            chain_data = raw.get("data", raw)
            try:
                underlying_ltp = chain_data.get("underlying_ltp")
            except AttributeError:
                underlying_ltp = None

        if underlying_ltp is None:
            print("[OptionChainParser] underlying_ltp unavailable.")
            return df

        atm = OptionChainParser.get_atm(df, underlying_ltp)
        if atm is None:
            print("[OptionChainParser] Unable to locate ATM strike.")
            return None
        otm = OptionChainParser.get_strike_offset(df, atm, +1)
        itm = OptionChainParser.get_strike_offset(df, atm, -1)
        df = df.sort_values("strike").reset_index(drop=True)
        chain_data = raw.get("data", raw)
        current_expiry = chain_data.get("expiry")
        current_session_date = pd.Timestamp.now(tz="Asia/Kolkata").date()

        # Reset on expiry/day change
        if PREV_EXPIRY != current_expiry or SESSION_DATE != current_session_date:
            PREV_OPTION_DF = None
            DAY_START_OPTION_DF = None
            PREV_EXPIRY = current_expiry
            SESSION_DATE = current_session_date

        # First snapshot of the day for day-level intraday deltas.
        if DAY_START_OPTION_DF is None:
            DAY_START_OPTION_DF = df.copy()

        # -------------------------------
        # SNAPSHOT-INTRADAY CHANGE
        # -------------------------------
        df_indexed = df.set_index("strike")
        if PREV_OPTION_DF is not None:
            prev = PREV_OPTION_DF.set_index("strike")
            df["ce_oi_intraday_change"] = (
                (df_indexed["ce_oi"] - prev["ce_oi"]).fillna(0).values
            )
            df["pe_oi_intraday_change"] = (
                (df_indexed["pe_oi"] - prev["pe_oi"]).fillna(0).values
            )
            df["ce_ltp_intraday_change"] = (
                (df_indexed["ce_ltp"] - prev["ce_ltp"]).fillna(0).values
            )
            df["pe_ltp_intraday_change"] = (
                (df_indexed["pe_ltp"] - prev["pe_ltp"]).fillna(0).values
            )
        else:
            df["ce_oi_intraday_change"] = 0
            df["pe_oi_intraday_change"] = 0
            df["ce_ltp_intraday_change"] = 0
            df["pe_ltp_intraday_change"] = 0

        # -------------------------------
        # DAILY INTRADAY CHANGE
        # -------------------------------
        day_start = DAY_START_OPTION_DF.set_index("strike")
        df["ce_oi_daily_intraday_change"] = (
            (df_indexed["ce_oi"] - day_start["ce_oi"]).fillna(0).values
        )
        df["pe_oi_daily_intraday_change"] = (
            (df_indexed["pe_oi"] - day_start["pe_oi"]).fillna(0).values
        )
        df["ce_ltp_daily_intraday_change"] = (
            (df_indexed["ce_ltp"] - day_start["ce_ltp"]).fillna(0).values
        )
        df["pe_ltp_daily_intraday_change"] = (
            (df_indexed["pe_ltp"] - day_start["pe_ltp"]).fillna(0).values
        )

        # -------------------------------
        # OVERALL CHANGE FROM PREVIOUS DAY
        # -------------------------------
        df["ce_oi_prev_day_change"] = df["ce_oi_prev_day_change_api"].where(
            df["ce_oi_prev_day_change_api"].notna(),
            (df["ce_oi"] - df["ce_prev_oi"]).where(df["ce_prev_oi"].notna(), df["ce_oi_daily_intraday_change"])
        )
        df["pe_oi_prev_day_change"] = df["pe_oi_prev_day_change_api"].where(
            df["pe_oi_prev_day_change_api"].notna(),
            (df["pe_oi"] - df["pe_prev_oi"]).where(df["pe_prev_oi"].notna(), df["pe_oi_daily_intraday_change"])
        )
        df["ce_ltp_prev_day_change"] = df["ce_ltp_prev_day_change_api"].where(
            df["ce_ltp_prev_day_change_api"].notna(),
            (df["ce_ltp"] - df["ce_prev_close"]).where(df["ce_prev_close"].notna(), df["ce_ltp_daily_intraday_change"])
        )
        df["pe_ltp_prev_day_change"] = df["pe_ltp_prev_day_change_api"].where(
            df["pe_ltp_prev_day_change_api"].notna(),
            (df["pe_ltp"] - df["pe_prev_close"]).where(df["pe_prev_close"].notna(), df["pe_ltp_daily_intraday_change"])
        )

        atm_window = OptionChainParser.get_atm_window(
            df,
            atm["strike"],
            window=OI_STRIKE_RANGE
        )

        # Save snapshot
        PREV_OPTION_DF = df.copy()           
        return {
            "df": df,
            "atm": atm,
            "otm": otm,
            "itm": itm,
            "atm_strike": atm["strike"],
            "window_df": atm_window,
        }
