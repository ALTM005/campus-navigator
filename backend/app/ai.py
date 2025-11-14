import os, json
import numpy as np
from typing import List, Dict, Any, Optional
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

_client: Optional[OpenAI] = None

def get_client() -> Optional[OpenAI]:
    """Return a singleton OpenAI client if OPENAI_API_KEY is set; else None."""
    global _client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        _client = None
        return None
    if _client is None:
        _client = OpenAI(api_key=api_key)
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

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_office_from_html(snippets):
    text = "\n".join(snippets)
    buildings = ", ".join([
        "Lassen Hall", "Eureka Hall", "Desmond Hall", "Riverside Hall", "Tahoe Hall",
        "Mendocino Hall", "Sequoia Hall", "AIRC", "University Union", "Library",
        "River Front Ctr.", "Amador Hall", "Mariposa Hall", "Kadema Hall", "Solano Hall",
        "Brighton Hall", "The WELL", "Student Health and Counseling Services",
        "Tschannen Science Complex", "Hornet Bookstore", "Capistrano Hall",
        "Sacramento Hall", "Folsom Hall", "Placer Hall", "Tschannen Engineering Building",
        "Douglass Hall", "Dining Commons", "Benicia Hall", "Calaveras Hall",
        "Del Norte Hall", "Humboldt Hall", "Jenkins Hall", "Klamath Hall", "Modoc Hall",
        "Napa Hall", "Shasta Hall", "Sierra Hall", "Sutter Hall", "Yosemite Hall"
    ])

    prompt = f"""
    You are an assistant that extracts building and room info for Sacramento State offices.

    You are given 10–25 text snippets from a csus.edu page.

    **Task:** Return the most likely current office location as strict JSON.

    Rules:
    - building: one of [{buildings}] (choose EXACTLY from this list)
    - room: a 3–4 digit number with optional letter (e.g. 2302 or 2302A), or null if not present
    - confidence: float 0.0–1.0 (higher if phrase is explicit like "in Lassen Hall 2302")
    - If the page says "moved to X", choose X (not the old location).
    - If no valid building found, return null for building.

    Respond ONLY in this JSON format:
    {{
      "building": "...",
      "room": "...",
      "confidence": 0.0
    }}

    Snippets:
    {text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract building and room information from snippets."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        # Parse JSON safely
        import json
        return json.loads(raw)
    except Exception:
        return None


def summarize_events(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cli = get_client()
    if not cli:
        return items

    capped = items[:10]
    text = "\n".join([
        f"- {ev.get('title','(no title)')} | {ev.get('start','?')} | {ev.get('location','?')} | {ev.get('url','')}"
        for ev in capped
    ])
    prompt = [
        {"role":"system","content":"Classify and summarize events. Return JSON list with fields: title, summary, category."},
        {"role":"user","content": f"Events:\n{text}\n\nCategories: academic, social, sports, arts, admin.\nReturn JSON array only."}
    ]
    res = cli.chat.completions.create(model=LLM_MODEL, messages=prompt, temperature=0.2)
    try:
        enriched = json.loads(res.choices[0].message.content)
        by_title = {e["title"]: e for e in enriched if "title" in e}
        out = []
        for ev in items:
            e = by_title.get(ev.get("title"))
            if e:
                ev = {**ev, "summary": e.get("summary"), "category": e.get("category")}
            out.append(ev)
        return out
    except Exception:
        return items

def llm_expand_queries(user_text: str) -> List[str]:
    """
    Return 5–8 search queries targeted at csus.edu for finding location info
    (building/room) about the user's term.
    """
    # Replace with your real LLM call; keep it deterministic/brief.
    prompt = f"""
You expand a user intent into csus.edu-focused search queries.
User said: "{user_text}"

Rules:
- Only csus.edu related queries.
- Prefer location intent words like: location, address, room, building, "Lassen Hall".
- Include some quoted exact phrases and some generic variants.
- 5 to 8 queries, one per line.
    """.strip()

    # PSEUDO: call your LLM and parse lines -> return list[str]
    # return call_llm(prompt).splitlines()

    # TEMP baseline (until you wire your LLM):
    t = user_text.strip().strip('"')
    return [
        f'"{t}" site:csus.edu',
        f'{t} site:csus.edu location',
        f'{t} site:csus.edu address',
        f'{t} site:csus.edu "Lassen Hall"',
        f'{t} site:csus.edu "Room"',
        f'{t} site:csus.edu Sac State',
        f'{t} site:csus.edu student affairs',
        f'{t} site:csus.edu centers programs',
    ]