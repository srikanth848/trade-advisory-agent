import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from openai import OpenAI
from config import settings

from agents.upstox_agent import UpstoxAgent
from agents.fundamental_agent import FundamentalAgent
from agents.macro_agent import MacroAgent
from agents.expectation_agent import ExpectationAgent
from agents.risk_agent import RiskAgent
from tools.symbol_resolver import AutomatedSymbolResolver


class Supervisor:
    """
    Supervisor Orchestrator optimized for low latency & live response streaming.
    """

    def __init__(self) -> None:
        self.upstox_agent = UpstoxAgent()
        self.fundamental_agent = FundamentalAgent()
        self.macro_agent = MacroAgent()
        self.expectation_agent = ExpectationAgent()
        self.risk_agent = RiskAgent()

        self.resolver = AutomatedSymbolResolver()
        self.active_symbol: Optional[str] = None

        # Configure Amplify Client
        if settings.amplify_api_key:
            client_kwargs = {"api_key": settings.amplify_api_key}
            if settings.amplify_base_url:
                client_kwargs["base_url"] = settings.amplify_base_url
            self.amplify_client = OpenAI(
                **client_kwargs,
            )
        else:
            self.amplify_client = None

    def handle(self, prompt: str) -> str:
        return self.process(prompt)

    def _candidate_models(self) -> list[str]:
        models = [settings.amplify_model]
        if settings.amplify_fallback_model:
            models.append(settings.amplify_fallback_model)
        return models

    @staticmethod
    def _stream_chunk_text(chunk) -> str:
        if not getattr(chunk, "choices", None):
            return ""
        delta = chunk.choices[0].delta
        content = getattr(delta, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                text = getattr(item, "text", None)
                if text:
                    parts.append(text)
            return "".join(parts)
        return ""

    def process(self, prompt: str) -> str:
        symbol = self.resolver.resolve(prompt, self.active_symbol)

        if not symbol:
            return "Supervisor: Could not determine which stock symbol you are asking about."

        self.active_symbol = symbol
        p_lower = prompt.lower()

        # Direct sub-agent routing
        if "fundamental" in p_lower or "p/e" in p_lower or "sales" in p_lower:
            return self.fundamental_agent.handle(f"Analyze {self.active_symbol} fundamentals")

        if "macro" in p_lower or "news" in p_lower or "rbi" in p_lower:
            return self.macro_agent.handle(f"Analyze {self.active_symbol} macro and news")

        if "expectation" in p_lower or "priced in" in p_lower:
            return self.expectation_agent.handle(f"Analyze {self.active_symbol} expectation")

        if "risk" in p_lower or "stop loss" in p_lower or "target" in p_lower:
            return self.risk_agent.handle(f"Analyze {self.active_symbol} risk")

        if "technical" in p_lower or "rsi" in p_lower or "option" in p_lower:
            return self.upstox_agent.handle(f"Analyze {self.active_symbol} technicals")

        # Full Synthesis Mode
        return self._full_synthesis(prompt, self.active_symbol)

    def _full_synthesis(self, user_prompt: str, symbol: str) -> str:
        print(f"\n  [+] Collecting multi-agent signals for {symbol} in parallel...")
        
        # Parallel Execution
        with ThreadPoolExecutor(max_workers=5) as executor:
            fut_tech = executor.submit(self.upstox_agent.handle, f"Analyze {symbol} technicals")
            fut_fund = executor.submit(self.fundamental_agent.handle, f"Analyze {symbol} fundamentals")
            fut_macro = executor.submit(self.macro_agent.handle, f"Analyze {symbol} macro and news")
            fut_exp = executor.submit(self.expectation_agent.handle, f"Analyze {symbol} expectation")
            fut_risk = executor.submit(self.risk_agent.handle, f"Analyze {symbol} risk")

            # Slice large strings to avoid context bloat
            tech_out = fut_tech.result()[:2000]
            fund_out = fut_fund.result()[:2000]
            macro_out = fut_macro.result()[:1500]
            exp_out = fut_exp.result()[:1000]
            risk_out = fut_risk.result()[:1000]

        raw_data_payload = (
            f"--- TECHNICAL DATA ---\n{tech_out}\n\n"
            f"--- FUNDAMENTAL DATA ---\n{fund_out}\n\n"
            f"--- MACRO DATA ---\n{macro_out}\n\n"
            f"--- EXPECTATION DATA ---\n{exp_out}\n\n"
            f"--- RISK & LEVELS DATA ---\n{risk_out}\n"
        )

        if not self.amplify_client:
            return raw_data_payload

        print("  [+] Synthesizing final advisory via Amplify LLM...\n")

        system_instruction = (
            "You are an expert SEBI-registered Quantitative Trade Analyst. "
            "Synthesize the provided multi-factor agent data into a concise, direct, "
            "Markdown advisory recommendation addressing the user's query."
        )

        full_prompt = (
            f"User Query: '{user_prompt}'\n"
            f"Active Symbol: {symbol}\n\n"
            f"Multi-Agent Raw Data:\n{raw_data_payload}\n"
        )

        for model_name in self._candidate_models():
            try:
                response_stream = self.amplify_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": full_prompt}
                    ],
                    stream=True
                )

                full_text = ""
                for chunk in response_stream:
                    chunk_text = self._stream_chunk_text(chunk)
                    if chunk_text:
                        print(chunk_text, end="", flush=True)
                        full_text += chunk_text

                if full_text:
                    print("\n")
                    return ""  # Output streamed successfully
                raise RuntimeError(f"No text returned from model {model_name}")
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print(f"\n  [!] Daily quota limit reached on {model_name}. Rotating to fallback model...")
                    time.sleep(1)
                    continue
                print(f"\n  [!] Stream warning on {model_name}: {e}. Retrying fallback...")
                continue

        return f"\nFalling back to raw data payload:\n\n{raw_data_payload}"