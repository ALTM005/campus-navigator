from fastapi import APIRouter, Query
import re, time, requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from ..db import get_db

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

def crawl_page(url: str):
    r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    title = (soup.title.string or url).strip() if soup.title else url

    found = []
    for node in soup.find_all(string=re.compile(r"Location:\s*", re.I)):
        text = node if isinstance(node, str) else node.get_text(" ")
        m = LOCATION_RE.search(text)
        if not m:
            continue
        building, room = m.group(1).strip(), m.group(2).strip()
        if building not in BUILDING_CENTROIDS:
            continue
        lat, lng = BUILDING_CENTROIDS[building]
        found.append({
            "type": "office",
            "name": title,
            "building": building,
            "room": room,
            "lat": lat, "lng": lng,
            "url": url,
            "confidence": 0.7,
            "source": "web",
        })
    return found

@router.get("/resolve")
def resolve(q: str = Query(..., min_length=2)):
    #1) try local DB first
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM offices WHERE name LIKE ? OR building LIKE ? ORDER BY confidence DESC, updated_at DESC LIMIT 1",
            (f"%{q}%", f"%{q}%")
        ).fetchone()
        if row:
            r = dict(row); r.update({"type":"office","source":"local"})
            return r
    return {"detail": "no local match", "query": q}