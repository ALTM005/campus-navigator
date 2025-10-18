from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import offices, parking, events, resolve

app = FastAPI()

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

app.include_router(offices.router, prefix="/api", tags=["Offices"])
app.include_router(parking.router, prefix="/api", tags=["Parking"])
app.include_router(events.router, prefix="/api", tags=["Events"])
app.include_router(resolve.router,  prefix="/api", tags=["Resolve"])