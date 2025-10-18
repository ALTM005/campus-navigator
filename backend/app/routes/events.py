from fastapi import APIRouter, HTTPException
import os, requests
from ..models import EventsResponse

router = APIRouter()

TRUMBA_FEATURED = os.getenv(
    "TRUMBA_FEATURED_JSON",
    "https://calendarfeed.webhost.csus.edu/featuredevents.json"
)

@router.get("/events", response_model=EventsResponse)
def events(limit: int = 20):
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
                "url": ev.get("url") or ev.get("Url") or ev.get("permalink"),
            })
        return {"events": items[:limit]}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Events feed error: {e}")