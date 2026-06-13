"""Shared Gemini client + JSON parsing — used by parse / scoring / impact nodes.

Gemini 2.0 Flash via langchain-google-genai. Key from GEMINI_API_KEY (.env).
"""
import json
import os
import re
from functools import lru_cache
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI

_MODEL = "gemini-2.0-flash"


@lru_cache(maxsize=4)
def get_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    """Cached Gemini client. temp 0.2 default for scoring determinism."""
    return ChatGoogleGenerativeAI(
        model=_MODEL,
        temperature=temperature,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` fences Gemini sometimes wraps around JSON."""
    return _FENCE_RE.sub("", text.strip()).strip()


def parse_json(text: str) -> Optional[object]:
    """Strip fences and json.loads. Returns None on failure (caller retries/falls back)."""
    try:
        return json.loads(strip_json_fences(text))
    except (json.JSONDecodeError, ValueError):
        return None
