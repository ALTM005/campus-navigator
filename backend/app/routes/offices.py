from fastapi import APIRouter
from typing import List
import time
from ..db import get_db
from ..models import Office, OfficeIn
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/offices", response_model=List[Office])
def list_offices(limit: int = 200):
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM offices ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]

@router.post("/offices", response_model=Office)
def create_office(payload: OfficeIn):
    now = int(time.time())
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO offices (name,building,room,lat,lng,url,confidence,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (
                payload.name, payload.building, payload.room,
                payload.lat, payload.lng,
                str(payload.url) if payload.url else None,
                payload.confidence, now
            )
        )
        oid = cur.lastrowid
        row = conn.execute("SELECT * FROM offices WHERE id=?", (oid,)).fetchone()
        return dict(row)

@router.delete("/offices/{office_id}")
def delete_office(office_id: int):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM offices WHERE id=?", (office_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Not found")
        return {"deleted": office_id}