from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse

from app.routes import offices, parking, events, resolve, events_smart

app = FastAPI()

# CORS (fine to keep even when same-origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    import time
    return {"ok": True, "ts": int(time.time())}

# API routers
app.include_router(offices.router,      prefix="/api", tags=["Offices"])
app.include_router(parking.router,      prefix="/api", tags=["Parking"])
app.include_router(events.router,       prefix="/api", tags=["Events"])
app.include_router(events_smart.router, prefix="/api", tags=["Events"])
app.include_router(resolve.router,      prefix="/api", tags=["Resolve"])

# ---------- Frontend paths ----------
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"
print("Serving frontend from:", FRONTEND_DIR, "| exists =", FRONTEND_DIR.exists(), "| index =", INDEX_HTML.exists())

# Serve any static assets at /static (optional but future-proof)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Explicit root -> index.html (avoids any mount quirks at "/")
@app.get("/", include_in_schema=False)
def frontend_root():
    if INDEX_HTML.exists():
        return FileResponse(str(INDEX_HTML))
    return JSONResponse({"detail": "frontend index not found"}, status_code=500)
