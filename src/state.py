import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

STATE_DB = os.getenv("STATE_DB", "db/state.sqlite")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _resolve_state_db_path() -> Path:
    requested = Path(STATE_DB)
    requested.parent.mkdir(parents=True, exist_ok=True)

    if requested.exists():
        if os.access(requested, os.W_OK):
            return requested
    elif os.access(requested.parent, os.W_OK):
        return requested

    fallback = Path("db/state.local.sqlite")
    fallback.parent.mkdir(parents=True, exist_ok=True)
    return fallback


def get_conn():
    db_path = _resolve_state_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_state():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS kv_state (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS url_queue (
            url TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            priority INTEGER NOT NULL DEFAULT 100,
            last_analyzed_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_url_queue_status_priority
        ON url_queue(status, priority, last_analyzed_at)
        """
    )
    conn.commit()
    conn.close()


def set_state(key: str, value: str):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO kv_state(key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """,
        (key, value, _now_iso()),
    )
    conn.commit()
    conn.close()


def get_state(key: str, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM kv_state WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def enqueue_url(url: str, priority: int = 100):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO url_queue(url, priority, status)
        VALUES (?, ?, 'pending')
        ON CONFLICT(url) DO UPDATE SET
            priority = excluded.priority
        """,
        (url, priority),
    )
    conn.commit()
    conn.close()


def sync_url_queue(urls: list[str], base_priority: int = 10):
    conn = get_conn()
    normalized_urls = [url for url in urls if url]

    if normalized_urls:
        placeholders = ",".join("?" for _ in normalized_urls)
        conn.execute(
            f"DELETE FROM url_queue WHERE url NOT IN ({placeholders})",
            normalized_urls,
        )
        for offset, url in enumerate(normalized_urls):
            conn.execute(
                """
                INSERT INTO url_queue(url, priority, status)
                VALUES (?, ?, 'pending')
                ON CONFLICT(url) DO UPDATE SET
                    priority = excluded.priority
                """,
                (url, base_priority + offset),
            )
    else:
        conn.execute("DELETE FROM url_queue")

    conn.commit()
    conn.close()


def list_url_queue(limit: int = 100) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT url, status, priority, last_analyzed_at
        FROM url_queue
        ORDER BY priority ASC, COALESCE(last_analyzed_at, '') ASC, url ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def fetch_next_urls(limit: int = 5):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT url
        FROM url_queue
        WHERE status IN ('pending', 'retry')
        ORDER BY priority ASC, COALESCE(last_analyzed_at, '') ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [row["url"] for row in rows]


def mark_url_done(url: str):
    conn = get_conn()
    conn.execute(
        """
        UPDATE url_queue
        SET status = 'done',
            last_analyzed_at = ?
        WHERE url = ?
        """,
        (_now_iso(), url),
    )
    conn.commit()
    conn.close()


def mark_url_retry(url: str):
    conn = get_conn()
    conn.execute(
        """
        UPDATE url_queue
        SET status = 'retry',
            last_analyzed_at = ?
        WHERE url = ?
        """,
        (_now_iso(), url),
        )
    conn.commit()
    conn.close()


def requeue_stale_done_urls(hours: int = 24):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT url, last_analyzed_at
        FROM url_queue
        WHERE status = 'done'
        """
    ).fetchall()

    now = datetime.now(UTC)
    for row in rows:
        ts = row["last_analyzed_at"]
        if not ts:
            continue

        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
        except Exception:
            continue

        if now - dt >= timedelta(hours=hours):
            conn.execute(
                """
                UPDATE url_queue
                SET status = 'pending'
                WHERE url = ?
                """,
                (row["url"],),
            )

    conn.commit()
    conn.close()
