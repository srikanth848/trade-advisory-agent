# Trade Advisory Agent

CLI-based multi-agent trading assistant for Indian equities. The app combines Upstox market data, Screener fundamentals, Tavily news, risk framing, and an Amplify-hosted LLM synthesis layer.

## Components

- `app.py`: Interactive CLI entry point.
- `supervisor.py`: Symbol resolution, intent routing, parallel agent execution, and final advisory synthesis.
- `config.py`: Environment-backed settings.
- `agents/`: Technical, fundamental, macro, expectation, risk, and Upstox-facing agents.
- `tools/`: API clients and data helpers for Upstox, Screener, Tavily, and symbol resolution.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and fill in the required credentials.
4. Run the CLI with `python app.py`.

## Environment Variables

- `UPSTOX_API_KEY`: Upstox app key.
- `UPSTOX_ACCESS_TOKEN`: Upstox bearer token used for quotes, candles, and authenticated instrument search.
- `AMPLIFY_API_KEY`: Amplify API key for the OpenAI-compatible LLM endpoint.
- `AMPLIFY_BASE_URL`: Optional custom Amplify base URL.
- `AMPLIFY_MODEL`: Primary model name. Defaults to `gpt-5.4`.
- `AMPLIFY_FALLBACK_MODEL`: Optional secondary model if the primary model fails.
- `TAVILY_API_KEY`: Tavily key for macro and stock-specific news search.

## Current Behavior

- Technical analysis uses Upstox quotes and historical candles.
- Risk analysis uses live quote `last_price` as the current reference price.
- Fundamental analysis shows both Screener standalone and consolidated views when available.
- Expectation analysis compares technical trend against parsed valuation and return metrics.
- Final synthesis is generated through the Amplify OpenAI-compatible streaming API.

## Validation

Run a quick project compile check with `python -m compileall .`.
