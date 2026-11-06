from typing import Dict, Any, List, Optional
from config import settings

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None


class NewsClient:
    """
    Client for fetching real-time market news, macro-economic context, 
    and scrip-specific catalysts using the Tavily Search API.
    """

    def __init__(self) -> None:
        self.api_key = settings.tavily_api_key
        self.client = None

        if self.api_key and TavilyClient:
            self.client = TavilyClient(api_key=self.api_key)

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Executes a web search query for news, macro trends, or specific scrip events.
        """
        if not self.api_key:
            return {
                "status": "warning",
                "message": "TAVILY_API_KEY is not configured in .env file.",
                "results": []
            }

        if not self.client:
            return {
                "status": "error",
                "message": "tavily-python package is not installed. Add 'tavily-python' to requirements.txt.",
                "results": []
            }

        try:
            # Execute search query using Tavily Client
            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results
            )

            results = response.get("results", [])
            formatted_articles = []

            for item in results:
                formatted_articles.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0.0)
                })

            return {
                "status": "success",
                "query": query,
                "articles": formatted_articles
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Exception during Tavily search: {str(e)}",
                "results": []
            }

    def get_macro_context(self) -> Dict[str, Any]:
        """
        Fetches broader Indian macroeconomic indicators (RBI policy, Crude oil, Inflation, USD/INR).
        """
        query = "India macroeconomic outlook RBI interest rate stance crude oil prices USD INR inflation news"
        return self.search(query=query, max_results=5)

    def get_scrip_news(self, scrip_symbol: str) -> Dict[str, Any]:
        """
        Fetches recent news, earnings announcements, and market sentiment for a target stock.
        """
        query = f"{scrip_symbol} share price news latest updates corporate announcements earnings guidance"
        return self.search(query=query, max_results=5)