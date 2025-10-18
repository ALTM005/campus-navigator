from fastapi import APIRouter, HTTPException
import os, requests

router = APIRouter()

TRUMBA_FEATURED = os.getenv(
    "TRUMBA_FEATURED_JSON",
    "https://calendarfeed.webhost.csus.edu/featuredevents.json"
)

@router.get("/events/raw")
def events_raw():
    try:
        r = requests.get(TRUMBA_FEATURED, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Events feed error: {e}")
