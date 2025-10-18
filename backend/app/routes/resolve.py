from fastapi import APIRouter
import re
from bs4 import BeautifulSoup

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

DUCK_URL = "https://duckduckgo.com/html/?q={query}"

def ddg_csus_links(query: str, max_links: int = 5):
    q = quote_plus(f"site:csus.edu {query} Location")
    r = requests.get(DUCK_URL.format(query=q), timeout=10, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    for a in soup.select("a.result__a"):
        href = a.get("href")
        if href and "csus.edu" in href:
            links.append(href)
        if len(links) >= max_links:
            break
    return links

@router.get("/resolve/ping")
def ping():
    return {"ok": True}
