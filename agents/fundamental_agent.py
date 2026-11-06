from typing import Dict, Any, Optional
from agents.prompt_utils import extract_symbol_from_prompt
from tools.screener_client import ScreenerClient


class FundamentalAgent:
    """
    Agent responsible for fundamental analysis and sector-aware metrics evaluation.
    """

    def __init__(self) -> None:
        self.client = ScreenerClient()

    def handle(self, prompt: str) -> str:
        symbol = self._extract_symbol(prompt)
        if not symbol:
            return "FundamentalAgent: Could not identify a valid stock symbol from your prompt."

        standalone_data = self.client.get_company_financials(symbol, consolidated=False)
        consolidated_data = self.client.get_company_financials(symbol, consolidated=True)

        if standalone_data.get("status") != "success" and consolidated_data.get("status") != "success":
            return (
                f"FundamentalAgent Error for {symbol}: "
                f"standalone={standalone_data.get('message', 'Unknown error')}; "
                f"consolidated={consolidated_data.get('message', 'Unknown error')}"
            )

        primary_data = consolidated_data if consolidated_data.get("status") == "success" else standalone_data

        sections = [
            self._build_summary_section(standalone_data, symbol, "Standalone")
            if standalone_data.get("status") == "success"
            else f"--- Standalone Fundamentals ---\nUnavailable: {standalone_data.get('message', 'Unknown error')}\n",
            self._build_summary_section(consolidated_data, symbol, "Consolidated")
            if consolidated_data.get("status") == "success"
            else f"--- Consolidated Fundamentals ---\nUnavailable: {consolidated_data.get('message', 'Unknown error')}\n",
        ]

        header = (
            f"=== Fundamental Analysis for {primary_data.get('symbol', symbol)} ===\n"
            "Source Views: Screener Standalone and Consolidated\n\n"
        )

        return header + "\n".join(sections)

    def _build_summary_section(self, data: Dict[str, Any], symbol: str, label: str) -> str:
        ratios = data.get("ratios", {})
        history = data.get("financial_history", [])
        is_bank = data.get("is_bank", False)

        latest_quarter = history[0] if history else {}

        mcap = ratios.get('market_cap', 'N/A')
        pe = ratios.get('pe', 'N/A')
        roe = ratios.get('roe', 'N/A')
        roce = ratios.get('roce', 'N/A')

        if is_bank:
            return (
                f"--- {label} Fundamentals (Banking & Financials) ---\n"
                f"Market Cap: ₹{mcap} Cr\n"
                f"P/E Ratio: {pe}\n"
                f"ROE: {roe}%\n\n"
                f"Asset Quality & Latest Performance ({latest_quarter.get('quarter', 'Latest')}):\n"
                f"  - Gross NPA: {latest_quarter.get('gross_npa', 'N/A')}%\n"
                f"  - Net NPA: {latest_quarter.get('net_npa', 'N/A')}%\n"
                f"  - Interest Earned / Revenue: ₹{latest_quarter.get('sales', 'N/A')} Cr\n"
                f"  - Net Profit: ₹{latest_quarter.get('net_profit', 'N/A')} Cr\n"
                f"  - EPS: ₹{latest_quarter.get('eps_rs', 'N/A')}\n"
                f"Total Quarters Scraped: {len(history)}\n"
            )

        return (
            f"--- {label} Fundamentals ---\n"
            f"Market Cap: ₹{mcap} Cr\n"
            f"P/E Ratio: {pe}\n"
            f"ROCE: {roce}% | ROE: {roe}%\n\n"
            f"Latest Quarter Performance ({latest_quarter.get('quarter', 'Latest')}):\n"
            f"  - Sales / Revenue: ₹{latest_quarter.get('sales', 'N/A')} Cr\n"
            f"  - Operating Profit: ₹{latest_quarter.get('operating_profit', 'N/A')} Cr "
            f"(OPM: {latest_quarter.get('opm_pct', 'N/A')}%)\n"
            f"  - Net Profit: ₹{latest_quarter.get('net_profit', 'N/A')} Cr\n"
            f"  - EPS: ₹{latest_quarter.get('eps_rs', 'N/A')}\n"
            f"Total Quarters Scraped: {len(history)}\n"
        )

    def _extract_symbol(self, prompt: str) -> Optional[str]:
        return extract_symbol_from_prompt(prompt)