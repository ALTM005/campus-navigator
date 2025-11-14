# app/routes/events_smart.py
from fastapi import APIRouter, HTTPException, Query
import os
from typing import List, Dict, Any
from ..routes.events import _get_events, EVENTS_TZ
from ..ai import get_client  # your existing helper that returns an OpenAI client (or None)

router = APIRouter()

OPENAI_MODEL = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")

def _summarize_events_brief(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add a compact one-liner 'blurb' to each event via OpenAI (if configured).
    Falls back to a deterministic blurb if no API key.
    """
    cli = get_client()
    out = []
    if not cli:
        # Fallback: compact deterministic blurb
        for ev in events:
            blurb = f"{ev['title']} — {ev['start']} @ {ev.get('location') or 'TBA'}"
            out.append({**ev, "blurb": blurb})
        return out

    # Build a single prompt for efficiency (batch summarize)
    bullets = []
    for i, ev in enumerate(events, 1):
        bullets.append(f"[{i}] title: {ev['title']}\nstart: {ev['start']}\nend: {ev['end']}\nlocation: {ev.get('location') or 'TBA'}\nurl: {ev.get('url') or 'N/A'}")
    prompt = (
        "Write a single short, friendly, factual blurb for each event below (one line per item). "
        "Include title, day/time (concise), and location if present. Do NOT invent details. "
        "Output exactly N lines, numbered [1]..[N], no extra text.\n\n" + "\n\n".join(bullets)
    )

    try:
        resp = cli.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You summarize events succinctly and do not hallucinate."},
                {"role": "user", "content": prompt}
            ],
        )
        text = resp.choices[0].message.content.strip()
        # Map lines back
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        # naive alignment by index
        for i, ev in enumerate(events):
            blurb = lines[i] if i < len(lines) else f"{ev['title']} — {ev['start']} @ {ev.get('location') or 'TBA'}"
            out.append({**ev, "blurb": blurb})
        return out
    except Exception:
        # On any AI error, fallback deterministic
        for ev in events:
            blurb = f"{ev['title']} — {ev['start']} @ {ev.get('location') or 'TBA'}"
            out.append({**ev, "blurb": blurb})
        return out

@router.get("/events/smart")
def events_smart(limit: int = Query(10, ge=1, le=50)):
    """
    Same as /events but adds a compact 'blurb' per event using OpenAI if available.
    Perfect for a small homepage 'event box'.
    """
    try:
        base = _get_events()[:limit]
        enriched = _summarize_events_brief(base)
        return {
            "timezone": EVENTS_TZ,
            "count": len(enriched),
            "events": enriched
        }
    except Exception as e:
        raise HTTPException(502, f"Events smart error: {e}")
