from fastapi import APIRouter
from typing import List
import time
from ..db import get_db
from ..models import Office, OfficeIn
from fastapi import APIRouter, HTTPException
from fastapi import APIRouter, HTTPException, Query
from ..ai import embed_texts
import numpy as np, struct

router = APIRouter()

def _pack(vec):
    return struct.pack(f"{len(vec)}f", *vec)

def _unpack(blob):
    n = len(blob)//4
    return np.array(struct.unpack(f"{n}f", blob), dtype=np.float32)

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

@router.get("/search", response_model=List[Office])
def search(q: str = Query(..., min_length=1), limit: int = 20):
    q_like = f"%{q}%"
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT *,
              (CASE WHEN name LIKE ? THEN 2 ELSE 0 END) +
              (CASE WHEN building LIKE ? THEN 1 ELSE 0 END) AS score
            FROM offices
            WHERE name LIKE ? OR building LIKE ?
            ORDER BY score DESC, updated_at DESC
            LIMIT ?
            """,
            (q_like, q_like, q_like, q_like, limit)
        ).fetchall()
        return [dict(r) for r in rows]

@router.post("/offices/reindex")
def reindex_embeddings():
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, building FROM offices").fetchall()
        texts = [f"{r['name']} — {r['building']}" for r in rows]
        embs = embed_texts(texts)
        if not embs:
            return {"ok": False, "reason": "AI disabled (no OPENAI_API_KEY)"}
        for (r, v) in zip(rows, embs):
            conn.execute(
                "REPLACE INTO office_embeddings (office_id, vector) VALUES (?, ?)",
                (r["id"], _pack(v))
            )
        conn.commit()
    return {"ok": True, "count": len(rows)}

@router.get("/semantic_search")
def semantic_search(q: str, limit: int = 10):
    qv = embed_texts([q])
    if not qv:
        #fallback if AI disabled
        return search(q=q, limit=limit)
    qv = np.array(qv[0], dtype=np.float32)
    with get_db() as conn:
        rows = conn.execute("""
            SELECT o.*, e.vector as vec
            FROM offices o
            JOIN office_embeddings e ON e.office_id = o.id
        """).fetchall()
    scored = []
    for r in rows:
        v = _unpack(r["vec"])
        denom = (np.linalg.norm(qv) * np.linalg.norm(v)) or 1.0
        s = float(np.dot(qv, v) / denom)
        scored.append((s, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for s, r in scored[:limit]:
        d = dict(r)
        d["semantic_score"] = s
        d.pop("vec", None)
        out.append(d)
    return out
