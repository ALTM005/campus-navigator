# app/ai_locate.py
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI

# Optional Tavily (recommended for csus.edu-only search)
TAVILY_AVAILABLE = False
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except Exception:
    pass

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")

client = OpenAI(api_key=OPENAI_API_KEY)
tavily: Optional["TavilyClient"] = None
if TAVILY_AVAILABLE and os.getenv("TAVILY_API_KEY"):
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def _search_csus(query: str, limit: int = 6) -> List[Dict[str, str]]:
    """
    Domain-restricted web search (csus.edu) for titles/snippets.
    Requires Tavily; if unavailable, returns [] and we let the LLM say not found.
    """
    if not tavily:
        return []
    res = tavily.search(
        query=f"{query} site:csus.edu location room building",
        include_domains=["csus.edu"],
        max_results=limit,
        search_depth="basic",
        include_answer=False,
        include_raw_content=False
    )
    out: List[Dict[str, str]] = []
    for r in (res.get("results") or []):
        out.append({
            "title": r.get("title") or "",
            "url": r.get("url") or "",
            "snippet": r.get("content") or r.get("snippet") or "",
        })
    return out

def ai_locate_office(user_query: str, building_whitelist: List[str]) -> Optional[Dict[str, Any]]:
    """
    No scraping. Search (csus.edu) -> ask OpenAI to extract building/room.
    Returns dict {building, room, source_url, confidence} or None.
    """
    results = _search_csus(user_query, limit=6)
    bullets = []
    for i, r in enumerate(results[:8], 1):
        bullets.append(f"[{i}] {r['title']}\nURL: {r['url']}\nSNIPPET: {r['snippet']}\n")
    evidence = "\n\n".join(bullets) if bullets else "NO_RESULTS"

    allowed = ", ".join(building_whitelist)

    # Ask for strict JSON back
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise campus location resolver for Sacramento State (csus.edu). "
                    "Extract the CURRENT office location (building + optional room) ONLY if the building "
                    "is one of the allowed names. Be cautious of outdated pages and 'we moved' notices."
                ),
            },
            {
                "role": "user",
                "content": f"""
User query: {user_query}

Allowed buildings (choose EXACTLY from these; else reply not_found):
{allowed}

Evidence (csus.edu search results - titles, URLs, snippets):
{evidence}

Return STRICT JSON:
{{
  "status": "found" | "not_found",
  "building": string or null,     // only when status == "found"
  "room": string or null,         // e.g., "2302" or "2302A"
  "source_url": string or null,   // best page
  "confidence": number or null    // 0.0..1.0
}}

Rules:
- Prefer explicit phrasing like "in Lassen Hall 2302" or "Location: Lassen Hall 2302".
- If a page says "moved to X", choose X (not the old place).
- If building appears without room, set room to null.
- If you cannot map to an allowed building, return "status":"not_found".
""".strip(),
            },
        ],
    )

    # Parse JSON
    data = None
    try:
        data = resp.choices[0].message.parsed
    except Exception:
        import json
        try:
            data = json.loads(resp.choices[0].message.content)
        except Exception:
            return None

    if not data or data.get("status") != "found":
        return None

    building = (data.get("building") or "").strip()
    if building not in building_whitelist:
        return None

    room = data.get("room")
    if isinstance(room, str) and not room.strip():
        room = None

    return {
        "building": building,
        "room": room,
        "source_url": data.get("source_url"),
        "confidence": float(data.get("confidence") or 0.6),
    }
