import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load key-value pairs from .env file into os.environ
load_dotenv()


@dataclass(frozen=True)
class Settings:
    upstox_api_key: str = os.getenv("UPSTOX_API_KEY", "")
    upstox_access_token: str = os.getenv("UPSTOX_ACCESS_TOKEN", "")
    amplify_api_key: str = os.getenv("AMPLIFY_API_KEY", "")
    amplify_base_url: str = os.getenv("AMPLIFY_BASE_URL", "")
    amplify_model: str = os.getenv("AMPLIFY_MODEL", "gpt-5.4")
    amplify_fallback_model: str = os.getenv("AMPLIFY_FALLBACK_MODEL", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")

settings = Settings()