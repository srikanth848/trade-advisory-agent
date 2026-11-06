import os
import urllib.parse
from datetime import datetime, timedelta
import requests
from typing import Dict, Any, List, Optional
from config import settings


class UpstoxClient:
    """
    Production-Grade Upstox v2 API Client optimized strictly for Equity scripts.
    """

    def __init__(self) -> None:
        self.access_token = settings.upstox_access_token
        self.base_url = "https://api.upstox.com/v2"
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}" if self.access_token else ""
        }

    def _normalize_instrument_key(self, query: str) -> str:
        query = query.strip()
        if "|" in query:
            return query

        if not self.access_token:
            return f"NSE_EQ|{query.upper().split()[0]}"

        search_url = "https://api.upstox.com/v2/instruments/search"
        params = {
            "query": query,
            "exchanges": "NSE",
            "segments": "EQ"
        }

        try:
            res = requests.get(search_url, headers=self.headers, params=params, timeout=8)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data and isinstance(data, list):
                    q_upper = query.upper()
                    for item in data:
                        ikey = item.get("instrument_key", "")
                        sym = str(item.get("trading_symbol", item.get("symbol", ""))).upper()
                        name = str(item.get("name", "")).upper()
                        if q_upper == sym or q_upper in name:
                            return ikey
                    if data[0].get("instrument_key"):
                        return data[0].get("instrument_key")
        except Exception as e:
            print(f"[Debug] Search exception for '{query}': {e}")

        return f"NSE_EQ|{query.upper().split()[0]}"

    def get_market_quote(self, instrument_key: str) -> Dict[str, Any]:
        if not self.access_token:
            return {"status": "error", "message": "UPSTOX_ACCESS_TOKEN is missing."}

        raw_key = self._normalize_instrument_key(instrument_key)
        url = f"{self.base_url}/market-quote/quotes"
        params = {"instrument_key": raw_key}

        try:
            res = requests.get(url, headers=self.headers, params=params, timeout=10)
            if res.status_code == 200:
                return {"status": "success", "data": res.json().get("data", {})}
            return {"status": "error", "code": res.status_code, "message": res.text}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_historical_candles(
        self, 
        instrument_key: str, 
        unit: str = "days", 
        interval: str = "1", 
        to_date: Optional[str] = None, 
        from_date: Optional[str] = None
    ) -> List[List[Any]]:
        if not self.access_token:
            return []

        raw_key = self._normalize_instrument_key(instrument_key)
        encoded_key = urllib.parse.quote(raw_key, safe="")

        upstox_interval = "day" if unit in ["days", "day"] else f"{interval}minute"

        if not to_date or not from_date:
            to_dt = datetime.now()
            from_dt = to_dt - timedelta(days=180)
            to_date = to_dt.strftime("%Y-%m-%d")
            from_date = from_dt.strftime("%Y-%m-%d")

        url = f"{self.base_url}/historical-candle/{encoded_key}/{upstox_interval}/{to_date}/{from_date}"

        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                return res.json().get("data", {}).get("candles", [])
        except Exception as e:
            print(f"Exception while requesting historical candles: {e}")

        return []