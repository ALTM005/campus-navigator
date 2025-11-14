# app/routes/parking.py
from fastapi import APIRouter, HTTPException, Query
import os, time, requests
from math import radians, sin, cos, atan2, sqrt
from typing import Dict, Any, List, Optional

from ..routes.resolve import BUILDING_CENTROIDS
from ..ai import get_client

router = APIRouter()

# ---------------------------
# Config
# ---------------------------
PARKING_URL = os.getenv("PARKING_URL", "https://csusfeeds.webhost.csus.edu/api/parking/all")
PARKING_TTL = int(os.getenv("PARKING_TTL", "60"))
OPENAI_MODEL = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")

# Score weights: higher favors that signal more
WEIGHT_AVAIL = float(os.getenv("PARK_W_AVAIL", "0.65"))   # availability weight
WEIGHT_DIST  = float(os.getenv("PARK_W_DIST",  "0.35"))   # distance weight

_cache = {"data": None, "ts": 0}

# ---------------------------
# Lot centroids + metadata (edit/expand these as needed)
# If your feed already has lat/lng: keep this as fallback/override.
# flags: ev, ada, structure; type: visitor | student | faculty | mixed
# ---------------------------
LOT_CENTROIDS: Dict[str, Dict[str, Any]] = {
    "Parking Structure V (PS5)": {
        "lat": 38.5599, "lng": -121.4289, "type": "mixed",
        "flags": {"ev": True, "ada": True, "structure": True}
    },
    "Parking Structure III (PS3)": {
        "lat": 38.5617, "lng": -121.4276, "type": "mixed",
        "flags": {"ev": True, "ada": True, "structure": True}
    },
    "Parking Structure I (PS1)": {
        "lat": 38.5565, "lng": -121.4248, "type": "mixed",
        "flags": {"ev": False, "ada": True, "structure": True}
    },
    "Lot 1":  { "lat": 38.5633, "lng": -121.4297, "type": "student", "flags": {"ev": False, "ada": True, "structure": False} },
    "Lot 7":  { "lat": 38.5571, "lng": -121.4209, "type": "visitor", "flags": {"ev": False, "ada": True, "structure": False} },
    "Lot 8":  { "lat": 38.5587, "lng": -121.4217, "type": "mixed",   "flags": {"ev": True,  "ada": True, "structure": False} },
    "Lot 10": { "lat": 38.5612, "lng": -121.4229, "type": "student", "flags": {"ev": False, "ada": True, "structure": False} },
    "Hornet Stadium Lot": { "lat": 38.5568, "lng": -121.4195, "type": "visitor", "flags": {"ev": False, "ada": True, "structure": False} },
}

# ---------------------------
# Helpers
# ---------------------------
def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def walk_minutes(meters: float, mps: float = 1.4) -> int:
    return max(1, int(round(meters / mps / 60)))

def normalize(s: str) -> str:
    return " ".join((s or "").lower().strip().split())

def get_parking_feed() -> Dict[str, Any]:
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

def extract_building_from_query(q: str) -> Optional[str]:
    """LLM-first extraction; fallback to substring match."""
    cli = get_client()
    if cli:
        try:
            res = cli.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role":"system","content":(
                        "Extract the Sacramento State building name from the user's question. "
                        "Return ONLY the building name string (e.g., 'Tahoe Hall'). "
                        "If none is present, return 'NONE'."
                    )},
                    {"role":"user","content": q}
                ],
                temperature=0
            )
            target = (res.choices[0].message.content or "").strip()
            if target and target.upper() != "NONE":
                return target
        except Exception:
            pass
    # fallback: naive match
    ql = normalize(q)
    for b in BUILDING_CENTROIDS:
        if normalize(b) in ql or ql in normalize(b):
            return b
    return None

def parse_filters_from_query(q: str) -> Dict[str, Any]:
    """Very light NLP for filters in the user's sentence."""
    ql = normalize(q)
    # user type
    user_type = "visitor"
    if "student" in ql: user_type = "student"
    if "faculty" in ql or "staff" in ql: user_type = "faculty"
    if "visitor" in ql or "guest" in ql: user_type = "visitor"

    need_ev = any(tok in ql for tok in ["ev", "charger", "charging", "electric"])
    need_ada = any(tok in ql for tok in ["ada", "accessible", "handicap"])

    return {"user_type": user_type, "ev": need_ev, "ada": need_ada}

def lot_meta(lot_name: str) -> Dict[str, Any]:
    """Merge feed metadata with our local centroid map."""
    meta = LOT_CENTROIDS.get(lot_name, {}).copy()
    return meta

def permit_ok(lot_type: str, user_type: str) -> bool:
    if not lot_type:
        return True
    lot_type = lot_type.lower()
    user_type = user_type.lower()
    if lot_type == "mixed":
        return True
    if user_type == "visitor":
        return lot_type in ("visitor", "mixed")
    if user_type == "student":
        return lot_type in ("student", "mixed")
    if user_type == "faculty":
        return lot_type in ("faculty", "mixed")
    return True

def flags_ok(flags: Dict[str, Any], need_ev: bool, need_ada: bool) -> bool:
    flags = flags or {}
    if need_ev and not flags.get("ev", False): return False
    if need_ada and not flags.get("ada", False): return False
    return True

def score_lot(percent_free: float, distance_m: float) -> float:
    """
    Combine availability & distance into a single score.
    percent_free: 0..1 (higher better)
    distance_m: meters (lower better) -> normalized via soft curve
    """
    # Normalize distance ~ 0..1 where 0m -> 1.0, 600m -> ~0.5, 1200m -> ~0.25
    d_norm = 1.0 / (1.0 + (distance_m / 600.0))
    return WEIGHT_AVAIL * percent_free + WEIGHT_DIST * d_norm

# ---------------------------
# Endpoints
# ---------------------------
@router.get("/parking")
def parking():
    """Pass-through for the raw feed (cached)."""
    return get_parking_feed()

@router.get("/parking/ask")
def parking_ask(
    q: str = Query(..., min_length=2, description="e.g., 'closest student parking to Tahoe Hall with EV'"),
    user_type: Optional[str] = Query(None, description="visitor | student | faculty (overrides NLP)"),
    ev: Optional[bool] = Query(None, description="Require EV charging (overrides NLP)"),
    ada: Optional[bool] = Query(None, description="Require ADA (overrides NLP)"),
    limit: int = Query(5, ge=1, le=10)
):
    """
    NL parking search:
      - Extract destination building (LLM + fallback)
      - Parse filters (visitor/student/faculty, EV, ADA)
      - Rank lots by availability & walking distance
    """
    # 1) Feed
    lots_resp = parking()
    lots = lots_resp.get("LotsDataList", [])
    if not lots:
        raise HTTPException(502, "Parking feed returned no lots.")

    # 2) Destination building
    building = extract_building_from_query(q)
    if not building or building not in BUILDING_CENTROIDS:
        raise HTTPException(404, detail="Unknown building; include a building name like 'Tahoe Hall'.")

    dest_lat, dest_lng = BUILDING_CENTROIDS[building]

    # 3) Filters
    parsed = parse_filters_from_query(q)
    utype = user_type or parsed["user_type"]
    need_ev = parsed["ev"] if ev is None else ev
    need_ada = parsed["ada"] if ada is None else ada

    # 4) Rank lots
    ranked: List[Dict[str, Any]] = []
    for lot in lots:
        name = lot.get("LotName") or lot.get("Name") or ""
        if not name:
            continue

        meta = lot_meta(name)
        lot_type = meta.get("type")
        lot_flags = meta.get("flags", {})

        if not permit_ok(lot_type, utype):
            continue
        if not flags_ok(lot_flags, need_ev, need_ada):
            continue

        # availability
        used = lot.get("SpacesUsed", 0) or 0
        total = lot.get("TotalSpaces", 0) or 0
        if total <= 0:
            percent_free = 0.0
        else:
            percent_free = max(0.0, min(1.0, (total - used) / total))

        # distance (use local centroids; if none, skip distance scoring)
        if "lat" in meta and "lng" in meta:
            d_m = haversine(dest_lat, dest_lng, meta["lat"], meta["lng"])
            walk_min = walk_minutes(d_m)
        else:
            d_m = float("inf")
            walk_min = None

        score = score_lot(percent_free, 0 if d_m == float("inf") else d_m)

        ranked.append({
            "lot": name,
            "type": lot_type or "unknown",
            "percent_full": int(round((1 - percent_free) * 100)),
            "percent_free": int(round(percent_free * 100)),
            "spaces_used": used,
            "total_spaces": total,
            "distance_m": None if d_m == float("inf") else int(round(d_m)),
            "walk_min": walk_min,
            "flags": lot_flags,
            "score": round(score, 3),
            "coordinates": {"lat": meta.get("lat"), "lng": meta.get("lng")}
        })

    if not ranked:
        raise HTTPException(404, detail="No eligible parking lots match your filters.")

    ranked.sort(key=lambda x: (-x["score"], x["distance_m"] if x["distance_m"] is not None else 1e9))

    return {
        "query": q,
        "destination": {"building": building, "lat": dest_lat, "lng": dest_lng},
        "filters": {"user_type": utype, "ev": need_ev, "ada": need_ada},
        "suggestions": ranked[:limit],
        "meta": {
            "cached_feed": lots_resp.get("cached", False),
            "timestamp": int(time.time()),
            "weights": {"availability": WEIGHT_AVAIL, "distance": WEIGHT_DIST},
            "lots_considered": len(ranked)
        }
    }
