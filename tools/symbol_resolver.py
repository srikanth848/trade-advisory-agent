from openai import OpenAI
import requests
from pydantic import BaseModel, Field
from config import settings

# 1. Structured Schema for Intent Extraction
class SymbolExtraction(BaseModel):
    is_stock_query: bool = Field(description="True if the user prompt is asking about stocks/market instruments.")
    extracted_query: str = Field(description="Extracted target symbol or company name (e.g., 'RELIANCE', 'TCS', 'Tata Motors'). Empty string if non-stock query.")
    is_followup_without_mention: bool = Field(description="True if the user asks a follow-up question like 'should I buy it?' without naming a stock.")


class AutomatedSymbolResolver:
    """
    Automated Symbol Resolver using Amplify Intent Extraction and Upstox Live API.
    """
    def __init__(self) -> None:
        if settings.amplify_api_key:
            client_kwargs = {"api_key": settings.amplify_api_key}
            if settings.amplify_base_url:
                client_kwargs["base_url"] = settings.amplify_base_url
            self.client = OpenAI(**client_kwargs)
        else:
            self.client = None

    def _candidate_models(self) -> list[str]:
        models = [settings.amplify_model]
        if settings.amplify_fallback_model:
            models.append(settings.amplify_fallback_model)
        return models

    def resolve(self, user_input: str, active_session_symbol: str = None) -> str:
        """
        Extracts stock symbol from natural language user query using Amplify Structured Output,
        queries Upstox Live Instrument Search API, and resolves to standard ticker symbol.
        """
        if not self.client:
            return user_input.split()[-1].upper() if user_input.split() else None

        # Step A: Intent & Entity Extraction via Amplify Structured Output
        prompt = f"""
        Analyze the following user input for an Indian Stock Market trading assistant.
        User input: "{user_input}"
        
        Extract the core company/ticker name if present (e.g., 'INFY' or 'INFOSYS' for Infosys, 'RELIANCE' for Reliance). Strip out filler words like 'buy', 'sell', 'good time', 'fresh buy in', 'analyze'.
        """

        response_text = None
        
        for model_name in self._candidate_models():
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You extract stock-symbol intent for an Indian equities assistant. "
                                "Return JSON only with keys: is_stock_query, extracted_query, "
                                "is_followup_without_mention."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                if response.choices and response.choices[0].message.content:
                    response_text = response.choices[0].message.content
                    break
            except Exception:
                continue

        if not response_text:
            return user_input.split()[-1].upper()

        extracted: SymbolExtraction = SymbolExtraction.model_validate_json(response_text)

        search_term = None
        if extracted.extracted_query:
            search_term = extracted.extracted_query.strip()
        elif extracted.is_followup_without_mention and active_session_symbol:
            return active_session_symbol

        if not search_term:
            return None

        # Step B: Search Upstox Live Instrument API
        resolved_ticker = self.search_upstox_instrument(search_term)
        return resolved_ticker or search_term.upper()

    def search_upstox_instrument(self, query: str) -> str:
        """
        Query Upstox v2/instruments/search API
        """
        url = "https://api.upstox.com/v2/instruments/search"
        params = {
            "query": query,
            "exchanges": "NSE",
            "segments": "EQ"
        }
        headers = {"Accept": "application/json"}
        if settings.upstox_access_token:
            headers["Authorization"] = f"Bearer {settings.upstox_access_token}"
        
        try:
            res = requests.get(url, params=params, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data:
                    # Return the trading symbol of the top matching instrument
                    return data[0].get("trading_symbol")
            print(f"[Debug] Upstox Search returned {res.status_code} for query '{query}'")
        except Exception as e:
            print(f"[Debug] Upstox Search Error: {e}")
        
        return None