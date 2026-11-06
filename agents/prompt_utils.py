from typing import Optional


COMMON_PROMPT_WORDS = {
    "ANALYZE",
    "ANALYSIS",
    "WHAT",
    "IS",
    "THE",
    "PRICE",
    "OF",
    "FOR",
    "BUY",
    "SELL",
    "HOLD",
    "SHOULD",
    "I",
    "STOCK",
    "SCRIPT",
    "FUNDAMENTALS",
    "FUNDAMENTAL",
    "EXPECTATION",
    "EXPECTATIONS",
    "RISK",
    "MACRO",
    "NEWS",
    "TECHNICAL",
    "TECHNICALS",
    "DATA",
    "REPORT",
}


def extract_symbol_from_prompt(prompt: str) -> Optional[str]:
    cleaned = prompt.replace("?", "").replace(",", " ").strip()
    words = cleaned.split()
    filtered_words = [word for word in words if word.upper() not in COMMON_PROMPT_WORDS]

    if not filtered_words:
        return None

    return " ".join(filtered_words)