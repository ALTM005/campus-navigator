#!/usr/bin/env python3
import os, sys, time, json, math, requests
from typing import Dict, Tuple

# Campus rough bbox (lon/lat): west, south, east, north
BBOX = (-121.4320, 38.5530, -121.4180, 38.5650)
CAMPUS_CENTER = (38.5599, -121.4247)  # lat, lon for distance ranking

# Optional normalization/aliases for your frontend/backend names
ALIASES = {
    "AIRC": "Academic Information Resource Center",
    "River Front Ctr.": "River Front Center",
    "Student Health and Counseling Services": "Student Health & Counseling",
    "Library": "University Library",
    # add more as needed
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl   = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))  # meters

def normalize_name(name: str) -> str:
    name = name.strip()
    name = ALIASES.get(name, name)
    # Tidy punctuation variants
    name = name.replace("Ctr.", "Center")
    return name

def fetch_overpass():
    w, s, e, n = BBOX
    # Query all nodes/ways/relations with building + name, return centers
    query = f"""
    [out:json][timeout:60];
    (
      node["building"]["name"]({s},{w},{n},{e});
      way["building"]["name"]({s},{w},{n},{e});
      relation["building"]["name"]({s},{w},{n},{e});
    );
    out center tags;
    """
    r = requests.post(OVERPASS_URL, data=query, timeout=90)
    r.raise_for_status()
    return r.json()

def pick_centroid(elem) -> Tuple[float, float]:
    # nodes: lat/lon; ways/relations: center provided by 'out center'
    if "lat" in elem and "lon" in elem:
        return elem["lat"], elem["lon"]
    if "center" in elem:
        c = elem["center"]
        return c["lat"], c["lon"]
    # Fallback: no geometry center
    return None

def main():
    data = fetch_overpass()
    elems = data.get("elements", [])
    results: Dict[str, Tuple[float, float]] = {}
    distances: Dict[str, float] = {}

    for e in elems:
        tags = e.get("tags", {})
        raw_name = tags.get("name")
        if not raw_name:
            continue
        name = normalize_name(raw_name)
        centroid = pick_centroid(e)
        if not centroid:
            continue
        lat, lon = centroid
        # if multiple features share name, keep the one closest to campus center
        d = haversine(CAMPUS_CENTER[0], CAMPUS_CENTER[1], lat, lon)
        if name not in results or d < distances[name]:
            results[name] = (round(lat, 6), round(lon, 6))
            distances[name] = d

    # Optionally filter to “likely campus” by distance (< 2km)
    filtered = {
        k: v for k, v in results.items()
        if haversine(CAMPUS_CENTER[0], CAMPUS_CENTER[1], v[0], v[1]) < 2000
    }

    # Pretty-print Python dict
    lines = ["BUILDING_CENTROIDS = {"]
    for k in sorted(filtered.keys()):
        lat, lon = filtered[k]
        lines.append(f'    "{k}": ({lat}, {lon}),')
    lines.append("}")
    py_text = "\n".join(lines)

    os.makedirs("scripts_out", exist_ok=True)
    with open("scripts_out/centroids_overpass.py", "w") as f:
        f.write(py_text + "\n")
    with open("scripts_out/centroids_overpass.json", "w") as f:
        json.dump({k: {"lat": v[0], "lng": v[1]} for k, v in filtered.items()}, f, indent=2)

    print(f"Found {len(filtered)} named buildings.")
    print("Wrote scripts_out/centroids_overpass.py and scripts_out/centroids_overpass.json")

if __name__ == "__main__":
    main()
