// src/App.tsx
import { useEffect, useRef, useState } from "react";
import "./index.css";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import { MapView, MapHandle } from "./components/MapView";
import Events from "./components/Events";
import Resources from "./components/Resources";
import { getJSON } from "./services/api";

type ResolveResp = {
  lat?: number; lng?: number; building?: string; room?: string; source?: string; detail?: string;
};

const SAC_CENTER = { lat: 38.561, lng: -121.424 };

export default function App() {
  const mapRef = useRef<MapHandle>(null);
  const [health, setHealth] = useState("checking…");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("Welcome! Search for a place to drop a pin.");

  // health pill
  useEffect(() => {
    getJSON<{ ok: boolean }>("/api/health")
      .then((j) => setHealth(j.ok ? "backend: ok" : "backend: error"))
      .catch(() => setHealth("backend: unreachable"));
  }, []);

  async function doSearch() {
    const term = q.trim();
    if (!term) { setStatus("Type something to search."); return; }
    setStatus("Searching…");

    try {
      const data = await getJSON<ResolveResp>(`/api/resolve?q=${encodeURIComponent(term)}`);
      if (typeof data.lat === "number" && typeof data.lng === "number") {
        const label = data.room ? `${data.building} ${data.room}` : (data.building ?? "Location");
        mapRef.current?.dropMarker(data.lat, data.lng, label);
        setStatus(`Pinned: ${label}${data.source ? ` (${data.source})` : ""}`);
      } else {
        setStatus(data.detail || "Found, but no coordinates returned.");
      }
    } catch (e: any) {
      setStatus(e?.message || "Search failed.");
      console.error(e);
    }
  }

  return (
    <>
      <Header health={health} />
      <div className="page">
        <main>
          <div className="toolbar" role="search">
            <input
              className="input"
              placeholder="Search a place or office (e.g., Veterans Success Center, Tahoe Hall Room 2302)"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && doSearch()}
            />
            <button className="btn" onClick={doSearch}>Search</button>
          </div>

          <div id="status" aria-live="polite">{status}</div>

          <MapView ref={mapRef} center={SAC_CENTER} />

          <div className="grid">
            <div className="card">
              <h2>Upcoming Events</h2>
              <div className="muted"><Events /></div>
            </div>

            <div className="card">
              <h2>Campus Resources</h2>
              <Resources />
            </div>
          </div>
        </main>

        <Sidebar />
      </div>
    </>
  );
}
