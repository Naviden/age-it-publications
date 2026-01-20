"""
Translate keywords to English *only if they are Italian* using OpenRouter.

Input CSV columns:
- title
- keywords   (comma-separated string)

Output:
- keywords_en (English keywords; unchanged if already English)

Requirements:
pip install pandas langdetect requests
Set env var:
export OPENROUTER_API_KEY="YOUR_KEY"
"""

from __future__ import annotations

import os
import json
import time
from typing import Optional

import pandas as pd
import requests
from langdetect import detect, LangDetectException


OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
if not OPENROUTER_API_KEY:
    raise RuntimeError("Missing OPENROUTER_API_KEY environment variable.")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Choose any model you have access to on OpenRouter.
# This is a sensible default for light translation tasks.
MODEL = "openai/gpt-4o-mini"

# Optional but recommended by OpenRouter for analytics/rate-limit attribution
APP_URL = os.environ.get("OPENROUTER_APP_URL", "https://localhost")
APP_NAME = os.environ.get("OPENROUTER_APP_NAME", "keywords-translator")


def looks_italian(text: str) -> bool:
    """Return True if the string is detected as Italian; False otherwise."""
    t = (text or "").strip()
    if not t:
        return False
    try:
        return detect(t) == "it"
    except LangDetectException:
        # If detection fails on very short/noisy strings, assume not Italian.
        return False


def openrouter_translate_keywords_it_to_en(
    keywords: str,
    model: str = MODEL,
    timeout_s: int = 60,
    max_retries: int = 3,
    sleep_between_retries_s: float = 1.5,
) -> str:
    """
    Translate a comma-separated keyword string from Italian to English.
    Preserves comma-separated format, returns ONLY the translated keywords string.
    """
    prompt = (
        "Translate the following comma-separated keywords from Italian to English.\n"
        "Rules:\n"
        "- Keep them comma-separated.\n"
        "- Do not add or remove keywords.\n"
        "- Keep proper nouns as-is.\n"
        "- Return ONLY the translated keywords string, nothing else.\n\n"
        f"Keywords: {keywords}"
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": APP_URL,  # optional but recommended by OpenRouter
        "X-Title": APP_NAME,      # optional but recommended by OpenRouter
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise translation assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
    }

    last_err: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(payload), timeout=timeout_s)
            r.raise_for_status()
            data = r.json()
            out = data["choices"][0]["message"]["content"].strip()

            # Minimal cleanup: remove wrapping quotes if model adds them.
            if len(out) >= 2 and ((out[0] == '"' and out[-1] == '"') or (out[0] == "'" and out[-1] == "'")):
                out = out[1:-1].strip()

            return out

        except Exception as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(sleep_between_retries_s)
            else:
                raise RuntimeError(f"OpenRouter call failed after {max_retries} attempts: {e}") from e

    # Unreachable, but keeps type checkers happy.
    raise RuntimeError(f"OpenRouter call failed: {last_err}")


def translate_keywords_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds keywords_en:
    - If keywords detected as Italian -> translated via OpenRouter
    - Else -> copied as-is
    """
    def _process(k: str) -> str:
        k = (k or "").strip()
        if not k:
            return k
        if looks_italian(k):
            return openrouter_translate_keywords_it_to_en(k)
        return k

    df = df.copy()
    df["keywords_en"] = df["keywords"].apply(_process)
    return df


if __name__ == "__main__":
    # Example usage
    in_path = "/Users/navid/Documents/1_Projects/0_Age-It/Our Tasks/Mario_report/src/keywords.csv"       # your input
    out_path = "keywords_EN.csv"   # output

    df_in = pd.read_csv(in_path)
    if not {"title", "keywords"}.issubset(df_in.columns):
        raise ValueError("Input CSV must contain columns: title, keywords")

    df_out = translate_keywords_column(df_in)
    df_out.to_csv(out_path, index=False)
    print(f"Saved: {out_path}")