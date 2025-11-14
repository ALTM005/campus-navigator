# app/routes/resolve.py
from fastapi import APIRouter, HTTPException, Query
import re, time, requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from ..db import get_db
from ..ai import extract_office_from_html,llm_expand_queries
from ..ai_locate import ai_locate_office
import math

PARKING_NAME_RE = re.compile(r"\b(parking|garage|lot|structure)\b", re.I)

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def _extract_building_from_query(q: str) -> str | None:
    m = BUILDING_NAME_RE.search(q)
    if m: 
        return m.group(1).strip()
    # light fallback: try simple contains
    low = q.lower()
    for name in BUILDING_CENTROIDS.keys():
        if name.lower() in low:
            return name
    return None

def _nearest_parking_to(building: str):
    if building not in BUILDING_CENTROIDS:
        return None
    blat, blng = BUILDING_CENTROIDS[building]
    # include common variants
    parking_rx = re.compile(r"\b(parking|structure|garage|lot)\b", re.I)
    candidates = [
        (name, ll) for name, ll in BUILDING_CENTROIDS.items()
        if parking_rx.search(name)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda it: _haversine(blat, blng, it[1][0], it[1][1]))




router = APIRouter()

# -----------------------------
# Constants FIRST (used below)
# -----------------------------
TIMEOUT = 10                # network calls for page fetch / AI
SEARCH_TIMEOUT = 6          # network calls for search HTML
DDG_MAX_LINKS = 12
DUCK_URL = "https://duckduckgo.com/html/?q={query}"

# Words we care about for boosting relevance in titles/snippets
RELEVANCE_TOKENS = [
    "location", "office", "where", "room", "suite",
    "address", "building", "lassen", "hall", "mendocino",
    "eureka", "sequoia", "tahoe", "airc", "university union",
    "center", "program", "student affairs", "services"
]

BUILDING_CENTROIDS = {
   "Academic Resource Center": (38.558909, -121.423056),
    "Academy 65": (38.555175, -121.426975),
    "Alpine Hall": (38.561685, -121.424275),
    "Amador Hall": (38.55907, -121.424656),
    "Art Studio Lab": (38.557868, -121.419071),
    "Benicia Hall": (38.557946, -121.422569),
    "Brighton Hall": (38.561298, -121.424114),
    "CJ Gas": (38.554801, -121.428088),
    "Calaveras Hall": (38.562185, -121.424473),
    "California State University Sacramento": (38.562684, -121.42412),
    "Capistrano Hall": (38.559919, -121.425779),
    "Central Plant": (38.561316, -121.426133),
    "Challenge Center": (38.562385, -121.427585),
    "Children's Center": (38.558511, -121.420258),
    "Del Norte Hall": (38.563354, -121.423433),
    "Douglass Hall": (38.562556, -121.424621),
    "Enterprise": (38.555721, -121.4261),
    "Ernest E. Tschannen Science Complex": (38.560631, -121.421177),
    "Eureka Hall": (38.561219, -121.42523),
    "Facilities Managment": (38.563509, -121.429697),
    "Giovanni's Old World New York Pizzeria": (38.554977, -121.430522),
    "Hornet Athletic Center": (38.563505, -121.42819),
    "Hornet Bookstore": (38.559947, -121.420709),
    "Humboldt Hall": (38.561546, -121.423206),
    "Kadema Hall": (38.562119, -121.425631),
    "Lassen Hall": (38.562729, -121.425968),
    "Mariposa Hall": (38.561706, -121.425398),
    "Mendocino Hall": (38.562777, -121.423557),
    "Modoc Hall": (38.553196, -121.419324),
    "Napa Hall": (38.553802, -121.419077),
    "Parking Structure 5": (38.564213, -121.428346),
    "Parking Structure I": (38.559634, -121.426951),
    "Parking Structure II": (38.559232, -121.420141),
    "Parking Structure III": (38.55723, -121.42143),
    "Placer Hall": (38.562075, -121.423488),
    "Public Safety (Police)": (38.557486, -121.419701),
    "Receiving": (38.562696, -121.430073),
    "Reprographics and Mailroom": (38.562928, -121.429515),
    "River Front Center": (38.563502, -121.423956),
    "Riverside Hall": (38.561013, -121.422439),
    "Riverview Hall": (38.565538, -121.423928),
    "Sac State Library": (38.559609, -121.423664),
    "Sacramento Hall": (38.563459, -121.426282),
    "Sacramento State Alumni Center": (38.554748, -121.421022),
    "Saigon Bay Express": (38.560159, -121.424731),
    "Santa Clara Hall": (38.560743, -121.422814),
    "Sequoia Hall": (38.562044, -121.422665),
    "Shasta Hall": (38.564482, -121.424021),
    "Solano Hall": (38.561797, -121.426342),
    "Tahoe Hall": (38.55838, -121.424016),
    "The Well": (38.556819, -121.423636),
    "University Union": (38.559641, -121.422328),
    "Welcome Center": (38.564625, -121.427523),
    "Yosemite Hall": (38.562446, -121.427233),
}

# ----------------------------------
# Regex SECOND (can use constants)
# ----------------------------------
LOCATION_RE = re.compile(r"Location:\s*([A-Za-z &\-.]+)\s+(\d{3,4}[A-Z]?)", re.I)
ROOM_RE = re.compile(r"\b(\d{3,4}[A-Z]?)\b")
ALT_LOC_RE = re.compile(
    r"(?:Location|Where|Office|Offices|Address)\s*[:\-–]\s*([A-Za-z &\-.]+)\s*(?:,|\s+)?(Room\s*)?(\d{3,4}[A-Z]?)*",
    re.I
)
BUILDING_NAME_RE = re.compile(
    r"\b(" + "|".join(map(re.escape, BUILDING_CENTROIDS.keys())) + r")\b"
    r"(?:\s*(?:,|\-|—)?\s*(?:Room\s*)?(\d{3,4}[A-Z]?))?",
    re.I
)
ANYWHERE_BLDG_ROOM_RE = re.compile(
    r"\b(" + "|".join(map(re.escape, BUILDING_CENTROIDS.keys())) + r")\b"
    r".{0,80}?(?:Room\s*)?(\d{3,4}[A-Z]?)\b",
    re.I | re.S
)

# -----------------------------
# Search helpers (ChatGPT-like)
# -----------------------------
def _normalize_query(q: str) -> str:
    q = q.strip().lower()
    for prefix in [
        "where is", "where's", "what is the location of", "location of",
        "find", "show me", "how do i get to", "take me to", "where can i find"
    ]:
        if q.startswith(prefix):
            q = q[len(prefix):].strip(" :,-?")
            break
    return q

def _expand_queries(q: str) -> list[str]:
    qn = _normalize_query(q)
    variants = [
        f'"{qn}" site:csus.edu',
        f'{qn} site:csus.edu location',
        f'{qn} site:csus.edu "Lassen Hall"',
        f'{qn} site:csus.edu "Room"',
        f'{qn} site:csus.edu Sac State',
        f'{qn} site:csus.edu offices',
        f'{qn} site:csus.edu student affairs',
        f'{qn} site:csus.edu',
    ]
    seen, out = set(), []
    for v in variants:
        if v not in seen:
            seen.add(v); out.append(v)
    return out

def _ddg_fetch(query: str) -> list[dict]:
    """Return list of {'title','url','snippet'} from DDG HTML for a single query."""
    q = quote_plus(query)
    try:
        r = requests.get(
            DUCK_URL.format(query=q),
            timeout=SEARCH_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        r.raise_for_status()
    except Exception:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    # DuckDuckGo HTML layout (works on /html endpoint)
    for res in soup.select(".result"):
        a = res.select_one("a.result__a")
        if not a:
            continue
        href = a.get("href")
        if not href or "csus.edu" not in href:
            continue
        title = a.get_text(" ", strip=True)
        snip_el = res.select_one(".result__snippet")
        snippet = snip_el.get_text(" ", strip=True) if snip_el else ""
        items.append({"title": title or "", "url": href, "snippet": snippet or ""})
    return items

def _score_item(it: dict, user_q: str) -> float:
    title = (it.get("title") or "").lower()
    snippet = (it.get("snippet") or "").lower()
    q = _normalize_query(user_q)

    score = 0.0
    # exact phrase boosts
    if q and q in title:   score += 3.0
    if q and q in snippet: score += 1.5
    # token boosts
    for tok in q.split():
        if tok and tok in title:   score += 0.6
        if tok and tok in snippet: score += 0.3
    # location-ish words
    for tok in RELEVANCE_TOKENS:
        if tok in title:   score += 0.4
        if tok in snippet: score += 0.2
    # small boost for official student-affairs center pages
    url = it.get("url","")
    if "/student-affairs/" in url or "/centers-programs/" in url:
        score += 0.8
    # tiny boost if "location" or "room" is in URL
    if "location" in url or "room" in url:
        score += 0.3
    return score

def ddg_csus_links(query: str, max_links: int = DDG_MAX_LINKS) -> list[str]:
    """Natural-language search over csus.edu (no URLs from users)."""
    variants = _expand_queries(query)
    pool: list[dict] = []
    seen_urls = set()

    for v in variants:
        for it in _ddg_fetch(v):
            url = it["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            it["_score"] = _score_item(it, query)
            pool.append(it)

    # rank by score desc, then by shortness of title (official pages are often concise)
    pool.sort(key=lambda x: (-x["_score"], len(x.get("title",""))))

    return [it["url"] for it in pool[:max_links]]

def _normalize_query(q: str) -> str:
    q = q.strip().lower()
    for p in ["where is", "where's", "location of", "find", "show me", "how do i get to"]:
        if q.startswith(p):
            q = q[len(p):].strip(" :,-?")
            break
    return q

def _expand_queries(q: str) -> list[str]:
    # Ask LLM; fall back to a deterministic set if needed
    try:
        qs = llm_expand_queries(q)
        # de-dupe & trim
        seen, out = set(), []
        for v in qs:
            if v and v not in seen:
                seen.add(v); out.append(v)
        return out[:12]
    except Exception:
        # fallback to your previous static variants
        qn = _normalize_query(q)
        return [
            f'"{qn}" site:csus.edu',
            f'{qn} site:csus.edu location',
            f'{qn} site:csus.edu address',
            f'{qn} site:csus.edu "Lassen Hall"',
            f'{qn} site:csus.edu "Room"',
            f'{qn} site:csus.edu Sac State',
            f'{qn} site:csus.edu student affairs',
            f'{qn} site:csus.edu',
        ]

# -----------------------------
# Core extraction
# -----------------------------
def crawl_page(url: str):
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except Exception:
        return []  # Return empty list on request failure

    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    found = []

    def push(building, room, source, conf_r, conf_nr):
        building_clean = (building or "").strip()
        if building_clean in BUILDING_CENTROIDS:
            lat, lng = BUILDING_CENTROIDS[building_clean]
            found.append({
                "type": "office", "name": title, "building": building_clean,
                "room": (room or None), "lat": lat, "lng": lng,
                "url": url, "confidence": conf_r if room else conf_nr,
                "source": source
            })

    # 1) strict label
    for node in soup.find_all(string=re.compile(r"Location:\s*", re.I)):
        text = node if isinstance(node, str) else node.get_text(" ")
        m = LOCATION_RE.search(text)
        if m:
            push(m.group(1).strip(), (m.group(2) or "").strip() or None, "web-strict", 0.70, 0.62)
            break

    # 2) alt labels
    if not found:
        for node in soup.find_all(string=ALT_LOC_RE):
            text = node if isinstance(node, str) else node.get_text(" ")
            m = ALT_LOC_RE.search(text)
            if not m: continue
            push((m.group(1) or "").strip(), (m.group(3) or "").strip() or None, "web-alt", 0.67, 0.62)
            break

    # 3) window around building mention (±240)
    full = soup.get_text(" ", strip=True)
    if not found:
        low = full.lower()
        for bldg in BUILDING_CENTROIDS.keys():
            pos = low.find(bldg.lower())
            if pos != -1:
                s = max(0, pos - 240); e = min(len(full), pos + len(bldg) + 240)
                window = full[s:e]
                rm = ROOM_RE.search(window)
                room = rm.group(1) if rm else None
                push(bldg, room, "web-heuristic", 0.64, 0.56)
                break

    # 4) free-form anywhere "<Building> [Room] 2302"
    if not found:
        m = ANYWHERE_BLDG_ROOM_RE.search(full)
        if m:
            push(m.group(1).strip(), (m.group(2) or "").strip() or None, "web-freeform", 0.68, 0.60)

    # 5) last resort (building mention alone)
    if not found:
        m = BUILDING_NAME_RE.search(full)
        if m:
            push(m.group(1).strip(), (m.group(2) or "").strip() or None, "web-building-re", 0.60, 0.55)

    return found

def ai_guess_office_from_url(url: str):
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except Exception:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    snippets = [t.get_text(" ", strip=True) for t in soup.select("h1, h2, h3, p, li")][:25]
    guess = extract_office_from_html(snippets)
    if not guess: return None
    building = (guess.get("building") or "").strip()
    if building not in BUILDING_CENTROIDS: return None
    lat, lng = BUILDING_CENTROIDS[building]
    return {
        "type": "office", "name": title, "building": building,
        "room": guess.get("room"), "lat": lat, "lng": lng, "url": url,
        "confidence": float(guess.get("confidence", 0.6)), "source": "web+ai",
    }

# -----------------------------
# DB helper
# -----------------------------
def _persist_and_return(best: dict):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO offices (name,building,room,lat,lng,url,confidence,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (best["name"], best["building"], best.get("room"), best["lat"], best["lng"],
             best.get("url"), best["confidence"], int(time.time()))
        )
        conn.commit()
    return best

# -----------------------------
# Public route
# -----------------------------
@router.get("/resolve")
def resolve(q: str = Query(..., min_length=2), debug: int = 0):

    qn = q.strip()

    # ---- Parking intent FIRST ----
    if PARKING_NAME_RE.search(qn):
        target = _extract_building_from_query(qn)
        if target:
            nearest = _nearest_parking_to(target)
            if nearest:
                pname, (plat, plng) = nearest
                result = {
                    "type": "parking",
                    "name": f"Closest parking to {target}",
                    "building": pname,     # <- label will show the parking structure
                    "room": None,
                    "lat": plat,
                    "lng": plng,
                    "url": None,
                    "confidence": 0.66,
                    "source": "proximity",
                    "target": target,
                }
                # Do NOT let DB override this. Either return directly,
                # or persist to a different table / with a 'type' column.
                if debug:
                    result["__debug"] = {"target": target, "picked": pname}
                return result
    # 1) DB first (case-insensitive)
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM offices WHERE LOWER(name) LIKE LOWER(?) OR LOWER(building) LIKE LOWER(?) "
            "ORDER BY confidence DESC, updated_at DESC LIMIT 1",
            (f"%{q}%", f"%{q}%")
        ).fetchone()
        if row:
            r = dict(row); r.update({"type":"office","source":"local"})
            return r

    # 2) AI locate (OpenAI + Tavily). No scraping.
    ai_best = ai_locate_office(q, list(BUILDING_CENTROIDS.keys()))
    if ai_best:
        building = ai_best["building"]
        lat, lng = BUILDING_CENTROIDS[building]
        best = {
            "type": "office",
            "name": q,
            "building": building,
            "room": ai_best.get("room"),
            "lat": lat,
            "lng": lng,
            "url": ai_best.get("source_url"),
            "confidence": ai_best.get("confidence", 0.6),
            "source": "ai-search",
        }
        # persist
        with get_db() as conn:
            conn.execute(
                "INSERT INTO offices (name,building,room,lat,lng,url,confidence,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (best["name"], best["building"], best.get("room"), best["lat"], best["lng"],
                 best.get("url"), best["confidence"], int(time.time()))
            )
            conn.commit()
        if debug:
            best["__debug"] = {"used": "ai_locate_office"}
        return best

    # 3) Nothing found
    raise HTTPException(status_code=404, detail="No such office found or insufficient evidence.")