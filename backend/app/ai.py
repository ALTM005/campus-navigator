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
