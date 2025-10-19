from fastapi import APIRouter
import os, time, requests
from ..ai import summarize_events

router = APIRouter()

TRUMBA_FEATURED = os.getenv("TRUMBA_FEATURED_JSON", "https://calendarfeed.webhost.csus.edu/featuredevents.json")
EVENTS_TTL = int(os.getenv("EVENTS_TTL", "300"))
_cache = {"data": None, "ts": 0}

def _fetch_events():
    r = requests.get(TRUMBA_FEATURED, timeout=10)
    r.raise_for_status()
    raw = r.json()
    iterable = raw if isinstance(raw, list) else raw.get("events", [])
    items = []
    for ev in iterable:
        def g(*keys):
            for k in keys:
                if isinstance(ev, dict) and k in ev:
                    return ev[k]
            return None
        items.append({
            "id": g("id","eventid","EventId"),
            "title": g("title","Title"),
            "start": g("startDateTime","start","StartDateTime"),
            "end": g("endDateTime","end","EndDateTime"),
            "location": g("location","Location"),
            "description": g("description","Description"),
            "url": g("url","Url","permalink"),
        })
    return items

@router.get("/events_smart")
def events_smart(limit: int = 20):
    now = time.time()
    if _cache["data"] and (now - _cache["ts"] < EVENTS_TTL):
        items = _cache["data"]
    else:
        items = _fetch_events()
        _cache.update({"data": items, "ts": now})
    items = items[:limit]
    enriched = summarize_events(items)  #no-op if AI disabled
    return {"events": enriched}
