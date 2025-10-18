from fastapi import APIRouter

router = APIRouter()

@router.get("/events/ping")
def ping():
    return {"ok": True}