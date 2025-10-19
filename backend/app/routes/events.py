from fastapi import APIRouter, HTTPException
import os, time, requests
from ..models import EventsResponse
from ..ai import summarize_events

router = APIRouter()

TRUMBA_FEATURED = os.getenv(
    "TRUMBA_FEATURED_JSON",
    "https://calendarfeed.webhost.csus.edu/featuredevents.json"
)
EVENTS_TTL = int(os.getenv("EVENTS_TTL", "300"))
_cache = {"data": None, "ts": 0}

@router.get("/events", response_model=EventsResponse)
def events(limit: int = 20, summarize: bool = False):
    now = time.time()
    if _cache["data"] and (now - _cache["ts"] < EVENTS_TTL):
        data = _cache["data"]
    else:
        try:
            r = requests.get(TRUMBA_FEATURED, timeout=10)
            r.raise_for_status()
            raw = r.json()
            items = []
            for ev in raw.get("events", raw if isinstance(raw, list) else []):
                items.append({
                    "id": ev.get("id") or ev.get("eventid") or ev.get("EventId"),
                    "title": ev.get("title") or ev.get("Title"),
                    "start": ev.get("startDateTime") or ev.get("start") or ev.get("StartDateTime"),
                    "end": ev.get("endDateTime") or ev.get("end") or ev.get("EndDateTime"),
                    "location": ev.get("location") or ev.get("Location"),
                    "description": ev.get("description") or ev.get("Description"),
                    "url": (ev.get("url") or ev.get("Url") or ev.get("permalink") or None),
                })
            data = {"events": items}
            _cache.update({"data": data, "ts": now})
        except Exception as e:
            #fall back to stale cache if available
            if _cache["data"]:
                data = _cache["data"]
            else:
                raise HTTPException(status_code=502, detail=f"Events feed error: {e}")
    payload = data["events"][:limit]
    if summarize:
        payload = summarize_events(payload)
    return {"events": payload}
