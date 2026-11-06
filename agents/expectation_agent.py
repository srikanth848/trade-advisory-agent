import re
from typing import Dict, Any, Optional
from agents.prompt_utils import extract_symbol_from_prompt
from agents.upstox_agent import UpstoxAgent
from agents.fundamental_agent import FundamentalAgent


class ExpectationAgent:
    """
    Agent responsible for evaluating Expectation Mismatches & Priced-in Dynamics.
    It synthesizes fundamental quarter growth against recent technical price momentum.
    """

    def __init__(self) -> None:
        self.upstox_agent = UpstoxAgent()
        self.fundamental_agent = FundamentalAgent()

    def handle(self, prompt: str) -> str:
        """
        Main entry point called by Supervisor.
        Performs comparative expectations scoring between business performance and price action.
        """
        symbol = self._extract_symbol(prompt)
        if not symbol:
            return "ExpectationAgent: Could not identify a valid stock symbol from your prompt."

        # Pull technical and fundamental snapshots
        tech_summary = self.upstox_agent.handle(prompt)
        fund_summary = self.fundamental_agent.handle(prompt)

        expectation_score = self.evaluate_expectation(tech_summary, fund_summary)

        summary = (
            f"=== Expectation & Priced-in Analysis for {symbol} ===\n"
            f"Expectation Bias: {expectation_score.get('bias', 'NEUTRAL')}\n"
            f"Assessment: {expectation_score.get('reasoning', 'No clear divergence.')}\n"
        )
        return summary

    def evaluate_expectation(self, tech_summary: str, fund_summary: str) -> Dict[str, str]:
        """
        Heuristic evaluation comparing technical trend with parsed valuation and return metrics.
        """
        is_bullish_tech = "BULLISH" in tech_summary
        is_bearish_tech = "BEARISH" in tech_summary
        metrics = self._extract_fundamental_metrics(fund_summary)

        pe = metrics.get("pe")
        roce = metrics.get("roce")
        roe = metrics.get("roe")

        strong_returns = any(metric is not None and metric >= 15.0 for metric in (roce, roe))
        weak_returns = all(metric is not None and metric < 10.0 for metric in (roce, roe)) if roce is not None and roe is not None else False
        expensive_valuation = pe is not None and pe >= 35.0
        reasonable_valuation = pe is not None and pe <= 25.0

        if is_bearish_tech and (strong_returns or reasonable_valuation):
            return {
                "bias": "ACCUMULATION OPPORTUNITY / NEGATIVE DIVERGENCE",
                "reasoning": "Technical price action is short-term weak even though fundamentals are comparatively supportive. Market may be over-discounting temporary risks."
            }
        if is_bullish_tech and expensive_valuation and weak_returns:
            return {
                "bias": "MOMENTUM WITHOUT FUNDAMENTAL SUPPORT",
                "reasoning": "Price action is firm, but valuation is stretched relative to soft return ratios. Upside may already be fully priced in."
            }
        if is_bullish_tech:
            return {
                "bias": "POSITIVE MOMENTUM WITH FUNDAMENTAL SUPPORT" if strong_returns else "POSITIVE MOMENTUM PRICED IN",
                "reasoning": "Price action reflects strong bullish momentum with reasonable fundamental backing." if strong_returns else "Price action reflects strong bullish momentum. Ensure entry isn't overextended relative to current valuation and profitability."
            }
        if expensive_valuation and weak_returns:
            return {
                "bias": "CAUTION / EXPECTATIONS STILL HIGH",
                "reasoning": "The stock is not in a strong uptrend, yet valuation remains rich while return ratios are weak. Expectations may still be ahead of business strength."
            }
        
        return {
            "bias": "NEUTRAL / BALANCED",
            "reasoning": "Price trend, valuation, and return ratios do not show an extreme expectation mismatch."
        }

    def _extract_fundamental_metrics(self, fund_summary: str) -> Dict[str, Optional[float]]:
        preferred_section = fund_summary
        consolidated_marker = "--- Consolidated Fundamentals"
        standalone_marker = "--- Standalone Fundamentals"

        if consolidated_marker in fund_summary:
            preferred_section = fund_summary.split(consolidated_marker, 1)[1]
        elif standalone_marker in fund_summary:
            preferred_section = fund_summary.split(standalone_marker, 1)[1]

        return {
            "pe": self._extract_metric(preferred_section, r"P/E Ratio:\s*([0-9]+(?:\.[0-9]+)?)"),
            "roce": self._extract_metric(preferred_section, r"ROCE:\s*([0-9]+(?:\.[0-9]+)?)%"),
            "roe": self._extract_metric(preferred_section, r"ROE:\s*([0-9]+(?:\.[0-9]+)?)%"),
        }

    def _extract_metric(self, text: str, pattern: str) -> Optional[float]:
        match = re.search(pattern, text)
        if not match:
            return None
        try:
            return float(match.group(1))
        except (TypeError, ValueError):
            return None

    def _extract_symbol(self, prompt: str) -> Optional[str]:
        return extract_symbol_from_prompt(prompt)