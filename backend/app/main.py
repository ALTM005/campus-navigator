from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import offices

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