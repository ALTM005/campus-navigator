# app/routes/events.py
from fastapi import APIRouter, HTTPException, Query
import os, time, requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from dateutil import tz
from ics import Calendar

router = APIRouter()

# ---------- Config ----------
EVENTS_JSON_URL = os.getenv("EVENTS_JSON_URL", "")  # (optional) JSON feed; shape: [{"title","start","end","location","url"}]
EVENTS_ICS_URLS = [u.strip() for u in os.getenv("EVENTS_ICS_URLS", "").split(",") if u.strip()]  # one or more ICS feeds
EVENTS_TTL = int(os.getenv("EVENTS_TTL", "300"))  # seconds
EVENTS_TZ = os.getenv("EVENTS_TIMEZONE", "America/Los_Angeles")
MAX_LOOKAHEAD_DAYS = int(os.getenv("EVENTS_LOOKAHEAD_DAYS", "60"))

_cache = {"data": None, "ts": 0}

# ---------- Helpers ----------
def _now_local() -> datetime:
    return datetime.now(tz.gettz(EVENTS_TZ))

def _to_iso(dt: datetime) -> str:
    # Always return ISO with offset for frontend convenience
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def _fetch_json_events() -> List[Dict[str, Any]]:
    if not EVENTS_JSON_URL:
        return []
    try:
        r = requests.get(EVENTS_JSON_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        out = []
        for ev in data:
            # Expecting keys but be tolerant
            out.append({
                "title": ev.get("title") or ev.get("name") or "Untitled event",
                "start": ev.get("start"),
                "end": ev.get("end"),
                "location": ev.get("location") or ev.get("place"),
                "url": ev.get("url") or ev.get("link"),
                "source": "json",
            })
        return out
    except Exception:
        return []

def _fetch_ics_events() -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if not EVENTS_ICS_URLS:
        return events
    for url in EVENTS_ICS_URLS:
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            cal = Calendar(r.text)
            for e in cal.events:
                start = e.begin.datetime
                end = (e.end or e.begin).datetime
                # Coerce tz
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                events.append({
                    "title": e.name or "Untitled event",
                    "start": _to_iso(start),
                    "end": _to_iso(end),
                    "location": (e.location or "").strip() or None,
                    "url": e.url or None,
                    "source": url,
                })
        except Exception:
            # Skip bad feeds silently
            continue
    return events

def _load_events_uncached() -> List[Dict[str, Any]]:
    # Prefer JSON if provided; append ICS results
    all_ev = _fetch_json_events()
    all_ev.extend(_fetch_ics_events())

    # Filter to upcoming window and sort
    now = _now_local()
    horizon = now + timedelta(days=MAX_LOOKAHEAD_DAYS)

    def _parse(dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            # Let fromisoformat try first
            return datetime.fromisoformat(dt_str.replace("Z","+00:00"))
        except Exception:
            from dateutil.parser import isoparse
            try:
                return isoparse(dt_str)
            except Exception:
                return None

    upcoming = []
    seen = set()
    for ev in all_ev:
        s = _parse(ev["start"])
        e = _parse(ev.get("end"))
        if not s:
            continue
        # Normalize tz to display tz (for consistent sorting)
        s_local = s.astimezone(tz.gettz(EVENTS_TZ))
        if s_local < now or s_local > horizon:
            continue
        key = (ev["title"], s.isoformat(), ev.get("url"))
        if key in seen:
            continue
        seen.add(key)
        upcoming.append({
            "title": ev["title"],
            "start": _to_iso(s_local),
            "end": _to_iso((e or s).astimezone(tz.gettz(EVENTS_TZ))),
            "location": ev.get("location"),
            "url": ev.get("url"),
            "source": ev.get("source"),
        })

    upcoming.sort(key=lambda x: x["start"])
    return upcoming

def _get_events() -> List[Dict[str, Any]]:
    now = time.time()
    if _cache["data"] and (now - _cache["ts"] < EVENTS_TTL):
        return _cache["data"]
    data = _load_events_uncached()
    _cache.update({"data": data, "ts": now})
    return data

# ---------- Routes ----------
@router.get("/events")
def list_events(limit: int = Query(10, ge=1, le=50)):
    """
    Return the next `limit` upcoming events (normalized).
    Use this endpoint for your 'event box' on page load.
    """
    try:
        items = _get_events()[:limit]
        return {
            "timezone": EVENTS_TZ,
            "count": len(items),
            "events": items
        }
    except Exception as e:
        raise HTTPException(502, f"Events error: {e}")
