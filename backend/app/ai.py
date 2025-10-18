import os, json
import numpy as np
from typing import List, Dict, Any, Optional
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

_client: Optional[OpenAI] = None

def get_client() -> Optional[OpenAI]:
    global _client
    if OPENAI_API_KEY and _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client

def embed_texts(texts: List[str]) -> List[List[float]]:
    cli = get_client()
    if not cli:
        return []
    resp = cli.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0: return 0.0
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    if na == 0 or nb == 0: return 0.0
    return float(np.dot(a, b) / (na * nb))

def extract_office_from_html(html_snippets: List[str]) -> Optional[Dict[str, Any]]:
    """
    Ask the LLM to pull {building, room} even if text is messy.
    Returns dict or None.
    """
    cli = get_client()
    if not cli:
        return None
    prompt = {
        "role": "system",
        "content": "You extract structured campus location data from noisy text. Return JSON ONLY."
    }
    user = {
        "role": "user",
        "content": (
            "From the text below, find the Sac State office location. "
            "Return strictly this JSON: {\"building\": string, \"room\": string|null, \"confidence\": number}.\n\n"
            f"TEXT:\n---\n{'\n---\n'.join(html_snippets)}\n---"
        )
    }
    res = cli.chat.completions.create(model=LLM_MODEL, messages=[prompt, user], temperature=0.1)
    raw = res.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "building" in data:
            return data
    except Exception:
        pass
    return None


