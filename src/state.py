from pathlib import Path
import sqlite3
from datetime import datetime

STATE_DB = "db/state.sqlite"

def get_conn():
    Path("db").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(STATE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_state():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kv_state (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS job_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS url_queue (
            url TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            priority INTEGER NOT NULL DEFAULT 100,
            last_analyzed_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def set_state(key: str, value: str):
    conn = get_conn()
    conn.execute("""
        INSERT INTO kv_state(key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value,
            updated_at=excluded.updated_at
    """, (key, value, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_state(key: str, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM kv_state WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def enqueue_url(url: str, priority: int = 100):
    conn = get_conn()
    conn.execute("""
        INSERT INTO url_queue(url, priority, status)
        VALUES (?, ?, 'pending')
        ON CONFLICT(url) DO NOTHING
    """, (url, priority))
    conn.commit()
    conn.close()

def fetch_next_urls(limit: int = 5):
    conn = get_conn()
    rows = conn.execute("""
        SELECT url
        FROM url_queue
        WHERE status IN ('pending', 'retry')
        ORDER BY priority ASC, COALESCE(last_analyzed_at, '') ASC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [r["url"] for r in rows]

def mark_url_done(url: str):
    conn = get_conn()
    conn.execute("""
        UPDATE url_queue
        SET status = 'done',
            last_analyzed_at = ?
        WHERE url = ?
    """, (datetime.utcnow().isoformat(), url))
    conn.commit()
    conn.close()