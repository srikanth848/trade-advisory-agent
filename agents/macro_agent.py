from typing import Dict, Any, Optional
from agents.prompt_utils import extract_symbol_from_prompt
from tools.news_client import NewsClient


class MacroAgent:
    """
    Agent responsible for fetching macro-economic conditions (RBI, inflation, 
    crude, currency) and stock-specific news/catalysts via Tavily Search.
    """

    def __init__(self) -> None:
        self.client = NewsClient()

    def handle(self, prompt: str) -> str:
        """
        Main entry point called by Supervisor.
        Extracts symbol (if any) and pulls news/macro intelligence.
        """
        symbol = self._extract_symbol(prompt)
        
        # Fetch broader macro context
        macro_data = self.client.get_macro_context()
        
        # If a specific scrip is mentioned, fetch scrip-specific news
        scrip_news = {}
        if symbol:
            scrip_news = self.client.get_scrip_news(symbol)

        summary_lines = ["=== Macroeconomic & News Intelligence Report ==="]
        
        # Append macro context articles
        if macro_data.get("status") == "success":
            summary_lines.append("\n[Macroeconomic Outlook & Market Sentiment]")
            for article in macro_data.get("articles", [])[:3]:
                summary_lines.append(f"  - {article.get('title')}")
        else:
            summary_lines.append(f"\nMacro Context Status: {macro_data.get('message', 'Unavailable')}")

        # Append scrip news if symbol was detected
        if symbol:
            summary_lines.append(f"\n[News Catalysts & Headlines for {symbol}]")
            if scrip_news.get("status") == "success":
                articles = scrip_news.get("articles", [])
                if articles:
                    summary_lines.append(self._format_news_headlines(articles))
                else:
                    summary_lines.append("  - No recent major news articles found.")
            else:
                summary_lines.append(f"  - Status: {scrip_news.get('message', 'Unavailable')}")

        return "\n".join(summary_lines)

    def _extract_symbol(self, prompt: str) -> Optional[str]:
        return extract_symbol_from_prompt(prompt)

    def _is_valid_headline(self, title: str) -> bool:
        """Filters out generic boilerplate news links and archive titles."""
        junk_keywords = [
            "press release", 
            "share price today", 
            "results earnings call", 
            "live chart", 
            "bse/nse updates", 
            "bids offers",
            "stock quote",
            "news and updates"
        ]
        t_lower = title.lower()
        return not any(junk in t_lower for junk in junk_keywords)

    def _format_news_headlines(self, raw_news_list: list) -> str:
        """Applies the headline filter to display only substantive catalysts."""
        filtered_news = []
        for item in raw_news_list:
            title = item.get("title", "")
            if self._is_valid_headline(title):
                filtered_news.append(f"  - {title}")
                
        if not filtered_news:
            return "  - No major recent news catalysts identified."
            
        return "\n".join(filtered_news[:5])  # Top 5 clean headlines