#!/usr/bin/env python3
import json, os, time, sys, textwrap
from urllib.parse import urlencode
import requests

# -----------------------------
# Configure your campus bounds
# -----------------------------
# Sacramento State campus rough bbox:
# west, south, east, north  (lon/lat order for Nominatim viewbox)
VIEWBOX = (-121.4320, 38.5530, -121.4180, 38.5650)

BUILDINGS = [
    # Core set — add/remove freely
    "Lassen Hall",
    "Eureka Hall",
    "Desmond Hall",
    "Riverside Hall",
    "Tahoe Hall",
    "Mendocino Hall",
    "Sequoia Hall",
    "AIRC",
    "University Union",
    "Library",

    # Added buildings
    "River Front Center",
    "Amador Hall",
    "Mariposa Hall",
    "Kadema Hall",
    "Solano Hall",
    "Brighton Hall",
    "The WELL",
    "Student Health and Counseling Services",
    "Tschannen Science Complex",
    "Hornet Bookstore",
    "Capistrano Hall",
    "Sacramento Hall",
    "Folsom Hall",               # off-campus
    "Placer Hall",
    "Tschannen Engineering Building",
    "Douglass Hall",
    "Dining Commons",

    # Residence
    "Benicia Hall",
    "Calaveras Hall",
    "Del Norte Hall",
    "Humboldt Hall",
    "Jenkins Hall",
    "Klamath Hall",
    "Modoc Hall",
    "Napa Hall",
    "Shasta Hall",
    "Sierra Hall",
    "Sutter Hall",
    "Yosemite Hall",
]

# Optional Google Places fallback
GOOGLE_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()

def query_nominatim(name: str):
    """Query OpenStreetMap Nominatim within campus viewbox."""
    base = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{name}, California State University, Sacramento",
        "format": "json",
        "limit": 1,
        "viewbox": f"{VIEWBOX[0]},{VIEWBOX[3]},{VIEWBOX[2]},{VIEWBOX[1]}",  # lonW,latN,lonE,latS
        "bounded": 1,
        "addressdetails": 0,
        "extratags": 0,
    }
    headers = {"User-Agent": "campus-navigator/1.0 (academic use)"}
    r = requests.get(base, params=params, headers=headers, timeout=12)
    r.raise_for_status()
    arr = r.json()
    if not arr:
        return None
    hit = arr[0]
    try:
        lat = float(hit["lat"]); lon = float(hit["lon"])
        return (lat, lon, "nominatim")
    except Exception:
        return None

def query_google_places(name: str):
    if not GOOGLE_KEY:
        return None
    base = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": f"{name}, California State University, Sacramento",
        "location": "38.5599,-121.4247",   # campus center-ish
        "radius": 2000,
        "key": GOOGLE_KEY,
    }
    r = requests.get(base, params=params, timeout=12)
    r.raise_for_status()
    data = r.json()
    if data.get("results"):
        g = data["results"][0]["geometry"]["location"]
        return (g["lat"], g["lng"], "google")
    return None

def normalize_label(name: str):
    # Minimal normalization to match common aliases
    n = name.strip()
    n = n.replace("Ctr.", "Center")
    n = n.replace("River Front Ctr", "River Front Center")
    return n

def main():
    out = {}
    failures = []
    for name in BUILDINGS:
        qname = normalize_label(name)
        res = query_nominatim(qname)
        # Respect Nominatim usage policy: 1 req/sec
        time.sleep(1.1)
        if not res:
            res = query_google_places(qname)
        if not res:
            failures.append(qname)
            continue
        lat, lon, src = res
        out[qname] = (round(lat, 6), round(lon, 6), src)

    # Pretty-print Python dict (without the source tag for runtime, but keep JSON too)
    python_lines = ["BUILDING_CENTROIDS = {"]
    for k, (lat, lon, src) in out.items():
        python_lines.append(f'    "{k}": ({lat}, {lon}),  # {src}')
    python_lines.append("}")
    py_text = "\n".join(python_lines)

    json_text = json.dumps(
        {k: {"lat": v[0], "lng": v[1], "source": v[2]} for k, v in out.items()},
        indent=2,
    )

    os.makedirs("scripts_out", exist_ok=True)
    with open("scripts_out/centroids.py", "w") as f:
        f.write(py_text + "\n")
    with open("scripts_out/centroids.json", "w") as f:
        f.write(json_text + "\n")

    print("\nGenerated:")
    print(" - scripts_out/centroids.py  (paste into your backend)")
    print(" - scripts_out/centroids.json (for debugging)")
    if failures:
        print("\nCould not resolve these (check spelling or add aliases):")
        for n in failures:
            print(" -", n)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
