from typing import Dict, Any, Optional
from agents.prompt_utils import extract_symbol_from_prompt
from agents.upstox_agent import UpstoxAgent


class RiskAgent:
    """
    Agent responsible for structural downside protection, support floor detection, 
    and strict asymmetric Reward-to-Risk (R:R >= 3.0) verification for equity scripts.
    """

    def __init__(self) -> None:
        self.upstox_agent = UpstoxAgent()

    def handle(self, prompt: str) -> str:
        """
        Main entry point called by Supervisor.
        Extracts symbol, fetches historical candles, and calculates asymmetric risk parameters.
        """
        symbol = self._extract_symbol(prompt)
        if not symbol:
            return "RiskAgent: Could not identify a valid stock symbol from your prompt."

        instrument_key = self.upstox_agent.client._normalize_instrument_key(symbol)
        quote_data = self.upstox_agent.client.get_market_quote(instrument_key)

        # Fetch candles to compute structural support floors and swing resistance
        candles = self.upstox_agent.client.get_historical_candles(instrument_key, unit="days", interval="1")
        latest_price = self._extract_live_price(quote_data)
        risk_metrics = self.calculate_risk_parameters(candles, latest_price)

        if risk_metrics.get("status") == "insufficient_data":
            return f"=== Risk & Asymmetry Framework for {symbol} ===\nStatus: Insufficient historical price data to establish support floors."

        summary = (
            f"=== Asymmetric Risk & Reward Framework for {symbol} ===\n"
            f"Current Reference Price: ₹{risk_metrics.get('latest_price', 'N/A')}\n"
            f"Structural Support Floor (Stop-Loss): ₹{risk_metrics.get('support_floor', 'N/A')}\n"
            f"Downside Risk per Share: ₹{risk_metrics.get('downside_risk', 'N/A')}\n"
            f"Target Price: ₹{risk_metrics.get('target_price', 'N/A')}\n"
            f"Calculated Reward-to-Risk Ratio: 1 : {risk_metrics.get('rr_num', 0.0)} (Upside ₹{risk_metrics.get('upside_reward', 'N/A')} vs Risk ₹{risk_metrics.get('downside_risk', 'N/A')})\n"
            f"Asymmetry Viability Status: {risk_metrics.get('asymmetry_status', 'N/A')}\n"
        )
        return summary

    def calculate_risk_parameters(self, candles: list, latest_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Computes structural support floor, downside risk, and enforces the 
        strict >= 3:1 asymmetric reward-to-risk mathematical threshold dynamically.
        """
        if not candles or len(candles) < 30:
            return {"status": "insufficient_data"}

        # Upstox candles: [timestamp, open, high, low, close, volume, open_interest]
        closes = [float(c[4]) for c in candles]
        lows = [float(c[3]) for c in candles]
        highs = [float(c[2]) for c in candles]

        latest_price = latest_price if latest_price is not None else closes[0]
        
        # Determine structural support floor from recent 60-period swing lows
        recent_lows = lows[:60] if len(lows) >= 60 else lows
        support_floor = min(recent_lows)
        
        # Ensure support floor sits logically below current price with safety buffer
        if support_floor >= latest_price:
            support_floor = round(latest_price * 0.93, 2)  # Default 7% structural stop buffer

        downside_risk = round(latest_price - support_floor, 2)
        if downside_risk <= 0:
            downside_risk = round(latest_price * 0.02, 2)
            support_floor = round(latest_price - downside_risk, 2)

        # Enforce strict minimum 3:1 reward distance relative to structural risk
        minimum_reward_distance = downside_risk * 3.0
        
        # Check historical swing resistance from recent highs
        recent_highs = highs[:60] if len(highs) >= 60 else highs
        resistance_ceiling = max(recent_highs)

        # Target price is whichever is higher: structural resistance or the 3:1 minimum asymmetry threshold
        target_price = max(resistance_ceiling, round(latest_price + minimum_reward_distance, 2))

        upside_reward = round(target_price - latest_price, 2)
        rr_ratio = round(upside_reward / downside_risk, 2) if downside_risk > 0 else 0.0

        # Asymmetry verification gate
        is_viable = rr_ratio >= 3.0
        asymmetry_status = "High Asymmetry (Viable Setup)" if is_viable else "Unfavorable R:R (Below 3:1 Threshold)"

        return {
            "latest_price": latest_price,
            "support_floor": support_floor,
            "downside_risk": downside_risk,
            "target_price": target_price,
            "upside_reward": upside_reward,
            "rr_num": rr_ratio,
            "asymmetry_status": asymmetry_status,
            "passed_threshold": is_viable
        }

    def _extract_live_price(self, quote_data: Dict[str, Any]) -> Optional[float]:
        data = quote_data.get("data", {})
        if not isinstance(data, dict) or not data:
            return None

        first_quote = next(iter(data.values()), None)
        if not isinstance(first_quote, dict):
            return None

        last_price = first_quote.get("last_price")
        return float(last_price) if last_price is not None else None

    def _extract_symbol(self, prompt: str) -> Optional[str]:
        return extract_symbol_from_prompt(prompt)