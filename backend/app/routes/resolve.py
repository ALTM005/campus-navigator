from fastapi import APIRouter, HTTPException, Query
import re, time, requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from ..db import get_db
from ..ai import extract_office_from_html

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
    r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
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

def ai_guess_office_from_url(url: str):
    """LLM-assisted fallback when regex/centroids miss."""
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    candidates = [t.get_text(" ", strip=True) for t in soup.select("h1, h2, h3, p, li")][:20]
    guess = extract_office_from_html(candidates)
    if not guess:
        return None

    building = guess.get("building")
    if building not in BUILDING_CENTROIDS:
        return None

    lat, lng = BUILDING_CENTROIDS[building]
    title = (soup.title.string or url).strip() if soup.title else url
    return {
        "type": "office",
        "name": title,
        "building": building,
        "room": guess.get("room"),
        "lat": lat,
        "lng": lng,
        "url": url,
        "confidence": float(guess.get("confidence", 0.6)),
        "source": "web+ai",
    }


@router.get("/resolve")
def resolve(q: str = Query(..., min_length=2)):
    #1) local DB first
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM offices WHERE name LIKE ? OR building LIKE ? ORDER BY confidence DESC, updated_at DESC LIMIT 1",
            (f"%{q}%", f"%{q}%")
        ).fetchone()
        if row:
            r = dict(row); r.update({"type":"office","source":"local"})
            return r

    #2) web assist, scrape first, then AI fallback
    for link in ddg_csus_links(q):
        hits = crawl_page(link)
        if hits:
            best = hits[0]
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO offices (name,building,room,lat,lng,url,confidence,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                    (best["name"], best["building"], best["room"], best["lat"], best["lng"], best["url"], best["confidence"], int(time.time()))
                )
                conn.commit()
            return best

        #AI fallback
        ai_best = ai_guess_office_from_url(link)
        if ai_best:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO offices (name,building,room,lat,lng,url,confidence,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                    (ai_best["name"], ai_best["building"], ai_best["room"], ai_best["lat"], ai_best["lng"], ai_best["url"], ai_best["confidence"], int(time.time()))
                )
                conn.commit()
            return ai_best

    raise HTTPException(status_code=404, detail="Could not resolve query to an office with a known building/room.")
