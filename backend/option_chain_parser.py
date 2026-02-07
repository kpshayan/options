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
from backend.data_fetcher import DATA_CACHE
import pandas as pd
PREV_OPTION_DF = None
PREV_EXPIRY = None

class OptionChainParser:

    @staticmethod
    def get_raw_chain():
        """Return raw option chain JSON from DATA_CACHE."""
        return DATA_CACHE.get("option_chain")

    @staticmethod
    def to_dataframe(raw_chain=None):
        """
        Convert option chain into a DataFrame with columns:
        strike, ce_bid, ce_ask, ce_ltp, ce_oi, pe_bid, pe_ask, pe_ltp, pe_oi
        """
        if raw_chain is None:
            raw_chain = OptionChainParser.get_raw_chain()

        if not raw_chain or "data" not in raw_chain:
            print("[OptionChainParser] No valid option chain found.")
            return None

        ce_list = []
        pe_list = []

        # Dhan GH SDK stores CE/PE under data['CE'] & data['PE']
        ce_raw = raw_chain["data"].get("CE", [])
        pe_raw = raw_chain["data"].get("PE", [])

        # Convert CE to dict keyed by strike
        for item in ce_raw:
            ce_list.append({
                "strike": item.get("strike_price"),
                "ce_ltp": item.get("ltp"),
                "ce_bid": item.get("bidPrice"),
                "ce_ask": item.get("askPrice"),
                "ce_oi": item.get("openInterest"),
                "ce_coi": item.get("")
            })

        # Convert PE to dict keyed by strike
        for item in pe_raw:
            pe_list.append({
                "strike": item.get("strike_price"),
                "pe_ltp": item.get("ltp"),
                "pe_bid": item.get("bidPrice"),
                "pe_ask": item.get("askPrice"),
                "pe_oi": item.get("openInterest"),
            })

        df_ce = pd.DataFrame(ce_list)
        df_pe = pd.DataFrame(pe_list)

        # Merge CE & PE into one table
        df = pd.merge(df_ce, df_pe, on="strike", how="outer").sort_values("strike")

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
        raw = OptionChainParser.get_raw_chain()
        if not raw:
            print("[OptionChainParser] No option chain cached.")
            return None

        df = OptionChainParser.to_dataframe(raw)

        if df is None:
            return None

        # If LTP not passed, try from data_fetcher stored chain
        if underlying_ltp is None:
            try:
                underlying_ltp = raw["data"].get("underlying_ltp")
            except:
                pass

        if underlying_ltp is None:
            print("[OptionChainParser] underlying_ltp unavailable.")
            return df

        atm = OptionChainParser.get_atm(df, underlying_ltp)
        otm = OptionChainParser.get_strike_offset(df, atm, +1)
        itm = OptionChainParser.get_strike_offset(df, atm, -1)
        atm_window = OptionChainParser.get_atm_window(
            df,
            atm["strike"],
            window=OI_STRIKE_RANGE      
            )
        df = df.sort_values("strike").reset_index(drop=True)
        current_expiry = raw["data"].get("expiry")

        # Reset on expiry change
        if PREV_EXPIRY != current_expiry:
            PREV_OPTION_DF = None
            PREV_EXPIRY = current_expiry

        # -------------------------------
        # INTRADAY OI CHANGE (snapshot)
        # -------------------------------
        if PREV_OPTION_DF is not None:
            prev = PREV_OPTION_DF.set_index("strike")

            df["ce_oi_intraday_change"] = df["strike"].map(
                lambda s: df.loc[df["strike"] == s, "ce_oi"].values[0]
                - prev["ce_oi"].get(s, 0)
                )

            df["pe_oi_intraday_change"] = df["strike"].map(
                lambda s: df.loc[df["strike"] == s, "pe_oi"].values[0]
                - prev["pe_oi"].get(s, 0)
            )
        else:
            df["ce_oi_intraday_change"] = 0
            df["pe_oi_intraday_change"] = 0

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