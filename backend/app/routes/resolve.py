from fastapi import APIRouter

router = APIRouter()

@router.get("/resolve/ping")
def ping():
    return {"ok": True}