from fastapi import APIRouter, HTTPException
import os, time, requests

router = APIRouter()

PARKING_URL = os.getenv("PARKING_URL", "https://csusfeeds.webhost.csus.edu/api/parking/all")
PARKING_TTL = int(os.getenv("PARKING_TTL", "60"))
_cache = {"data": None, "ts": 0}

@router.get("/parking")
def parking():
    now = time.time()
    if _cache["data"] and (now - _cache["ts"] < PARKING_TTL):
        return {"cached": True, **_cache["data"]}
    try:
        r = requests.get(PARKING_URL, timeout=8)
        r.raise_for_status()
        data = r.json()
        _cache.update({"data": data, "ts": now})
        return {"cached": False, **data}
    except Exception as e:
        if _cache["data"]:
            return {"cached": True, **_cache["data"], "warning": str(e)}
        raise HTTPException(status_code=502, detail=f"Parking feed error: {e}")
