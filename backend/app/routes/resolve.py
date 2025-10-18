from fastapi import APIRouter
import re

router = APIRouter()

LOCATION_RE = re.compile(r"Location:\s*([A-Za-z &\-]+)\s+(\d{3,4}[A-Z]?)", re.I)

BUILDING_CENTROIDS = {
    "Lassen Hall": (38.55933, -121.42464),
    "Eureka Hall": (38.55864, -121.42447),
    "Desmond Hall": (38.56307, -121.42341),
    "Riverside Hall": (38.55895, -121.42222),
    "Tahoe Hall": (38.55773, -121.42452),
    "Mendocino Hall": (38.55976, -121.42562),
    "Sequoia Hall": (38.55893, -121.42664),
    "AIRC": (38.55973, -121.42793),
    "University Union": (38.55838, -121.42563),
    "Library": (38.55888, -121.42709),
}

@router.get("/resolve/ping")
def ping():
    return {"ok": True}
