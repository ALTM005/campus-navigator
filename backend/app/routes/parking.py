from fastapi import APIRouter, HTTPException
import os, time, requests
from math import radians, sin, cos, atan2, sqrt
from fastapi import Query
from ..routes.resolve import BUILDING_CENTROIDS
from ..ai import get_client


router = APIRouter()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

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

@router.get("/parking/ask")
def parking_ask(q: str = Query(..., min_length=2)):
    """
    q example: 'closest student parking to Tahoe Hall right now'
    """
    #1) Get parking lots (uses cached live endpoint)
    lots_resp = parking()
    lots = lots_resp.get("LotsDataList", [])

    #2) If AI available, extract building name
    cli = get_client()
    target = None
    if cli:
        res = cli.chat.completions.create(
            model=os.getenv("OPENAI_LLM_MODEL","gpt-4o-mini"),
            messages=[
                {"role":"system","content":"Extract Sacramento State target building from a question. Return only the building name string (e.g., 'Tahoe Hall')."},
                {"role":"user","content": q}
            ],
            temperature=0
        )
        target = (res.choices[0].message.content or "").strip()

    #3) Fallback: naive match
    if not target or target not in BUILDING_CENTROIDS:
        for b in BUILDING_CENTROIDS:
            if b.lower() in q.lower():
                target = b
                break
    if not target or target not in BUILDING_CENTROIDS:
        return {"error":"Unknown building", "hint":"Try including a building name like 'Tahoe Hall'."}

    plat, plng = BUILDING_CENTROIDS[target]

    ranked = []
    for lot in lots:
        used = lot.get("SpacesUsed", 0)
        total = lot.get("TotalSpaces", 1)
        pct_full = (used/total) if total else 1
        ranked.append({
            "lot": lot.get("LotName"),
            "spaces_used": used,
            "total_spaces": total,
            "percent_full": round(pct_full*100),
            "distance_m": None 
        })
    ranked.sort(key=lambda x: x["percent_full"])
    return {"target_building": target, "recommendations": ranked[:5]}

