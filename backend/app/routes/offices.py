from fastapi import APIRouter
from typing import List
from ..db import get_db
from ..models import Office

router = APIRouter()

@router.get("/offices", response_model=List[Office])
def list_offices(limit: int = 200):
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM offices ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
