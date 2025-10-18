import sqlite3, os

DB_PATH = os.getenv("DB_PATH", "data/map.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS offices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  building TEXT NOT NULL,
  room TEXT,
  lat REAL NOT NULL,
  lng REAL NOT NULL,
  url TEXT,
  confidence REAL DEFAULT 1.0,
  updated_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_offices_name ON offices(name);
CREATE INDEX IF NOT EXISTS idx_offices_building ON offices(building);
"""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

with get_db() as conn:
    conn.executescript(SCHEMA_SQL)
    conn.commit()
