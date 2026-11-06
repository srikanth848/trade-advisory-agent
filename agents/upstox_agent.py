from typing import Dict, Any, List, Optional
from agents.prompt_utils import extract_symbol_from_prompt
from tools.upstox_client import UpstoxClient


class UpstoxAgent:
    """
    Agent responsible for fetching live quotes, historical candles, 
    and calculating technical indicators (RSI, SMAs) for equity scripts.
    """

    def __init__(self) -> None:
        self.client = UpstoxClient()

    def handle(self, prompt: str) -> str:
        """
        Main entry point called by Supervisor.
        Extracts symbol and executes technical and quote data retrieval.
        """
        symbol = self._extract_symbol(prompt)
        if not symbol:
            return "UpstoxAgent: Could not identify a valid stock symbol from your prompt."

        # Ensure we resolve to a proper instrument key using the client's internal normalizer
        instrument_key = self.client._normalize_system_key(symbol) if hasattr(self.client, '_normalize_system_key') else self.client._normalize_instrument_key(symbol)

        quote_data = self.client.get_market_quote(instrument_key)
        candles = self.client.get_historical_candles(instrument_key, unit="day", interval="1")

        tech_analysis = self.analyze_technicals(candles)
        
        summary = (
            f"=== Technical & Market Data Analysis for {symbol} ===\n"
            f"Live Quote Status: {quote_data.get('status', 'unknown')}\n"
            f"Historical Candles Pulled: {len(candles)}\n"
            f"Technical Trend (20 SMA vs 50 SMA): {tech_analysis.get('sma_trend', 'N/A')}\n"
            f"RSI (14): {tech_analysis.get('rsi_14', 'N/A')}\n"
        )
        return summary

    def _extract_symbol(self, prompt: str) -> Optional[str]:
        return extract_symbol_from_prompt(prompt)

    def analyze_technicals(self, candles: List[List[Any]]) -> Dict[str, Any]:
        """
        Computes 20-day SMA, 50-day SMA, and 14-period RSI from candle data.
        Upstox candles format: [timestamp, open, high, low, close, volume, open_interest]
        """
        if not candles or len(candles) < 14:
            return {"status": "insufficient_data"}

        # Extract closing prices
        closes = [float(c[4]) for c in candles]
        
        # 1. Simple Moving Averages
        sma_20 = sum(closes[:20]) / min(len(closes), 20) if len(closes) >= 20 else None
        sma_50 = sum(closes[:50]) / min(len(closes), 50) if len(closes) >= 50 else None

        sma_trend = "BULLISH" if (sma_20 and sma_50 and sma_20 > sma_50) else "BEARISH"

        # 2. Relative Strength Index (RSI 14)
        rsi_14 = self._calculate_rsi(closes[:30], period=14)

        return {
            "latest_close": closes[0] if closes else None,
            "sma_20": round(sma_20, 2) if sma_20 else None,
            "sma_50": round(sma_50, 2) if sma_50 else None,
            "sma_trend": sma_trend,
            "rsi_14": round(rsi_14, 2) if rsi_14 else None,
        }

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        if len(prices) < period + 1:
            return None

        gains = []
        losses = []
        for i in range(len(prices) - 1):
            change = prices[i] - prices[i + 1]  # Latest close is at index 0
            if change >= 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(change))

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi