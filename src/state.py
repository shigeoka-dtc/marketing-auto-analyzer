import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

STATE_DB = os.getenv("STATE_DB", "db/state.sqlite")
SQLITE_BUSY_TIMEOUT_MS = int(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "30000"))
URL_PROCESSING_STALE_MINUTES = int(os.getenv("URL_PROCESSING_STALE_MINUTES", "30"))
URL_RETRY_DELAY_MINUTES = int(os.getenv("URL_RETRY_DELAY_MINUTES", "15"))


def _now() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat()


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
    conn = sqlite3.connect(db_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _table_columns(conn, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _ensure_url_queue_columns(conn):
    columns = _table_columns(conn, "url_queue")
    additions = {
        "claimed_at": "ALTER TABLE url_queue ADD COLUMN claimed_at TEXT",
        "retry_count": "ALTER TABLE url_queue ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0",
        "next_retry_at": "ALTER TABLE url_queue ADD COLUMN next_retry_at TEXT",
        "last_error": "ALTER TABLE url_queue ADD COLUMN last_error TEXT",
    }
    for column, ddl in additions.items():
        if column not in columns:
            conn.execute(ddl)


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
            last_analyzed_at TEXT,
            claimed_at TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            next_retry_at TEXT,
            last_error TEXT
        )
        """
    )
    _ensure_url_queue_columns(conn)
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_url_queue_status_priority
        ON url_queue(status, priority, next_retry_at, last_analyzed_at)
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
        INSERT INTO url_queue(url, priority, status, retry_count)
        VALUES (?, ?, 'pending', 0)
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
                INSERT INTO url_queue(url, priority, status, retry_count)
                VALUES (?, ?, 'pending', 0)
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
        SELECT url, status, priority, last_analyzed_at, claimed_at, retry_count, next_retry_at, last_error
        FROM url_queue
        ORDER BY priority ASC, COALESCE(last_analyzed_at, '') ASC, url ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def claim_next_urls(limit: int = 5, stale_after_minutes: int = URL_PROCESSING_STALE_MINUTES) -> list[str]:
    conn = get_conn()
    now = _now()
    now_iso = now.isoformat()
    stale_before = (now - timedelta(minutes=stale_after_minutes)).isoformat()

    try:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            """
            SELECT url
            FROM url_queue
            WHERE (
                status IN ('pending', 'retry')
                AND (next_retry_at IS NULL OR next_retry_at <= ?)
            )
            OR (
                status = 'processing'
                AND claimed_at IS NOT NULL
                AND claimed_at <= ?
            )
            ORDER BY priority ASC, COALESCE(last_analyzed_at, '') ASC, url ASC
            LIMIT ?
            """,
            (now_iso, stale_before, limit),
        ).fetchall()
        urls = [row["url"] for row in rows]
        if urls:
            placeholders = ",".join("?" for _ in urls)
            conn.execute(
                f"""
                UPDATE url_queue
                SET status = 'processing',
                    claimed_at = ?,
                    last_error = NULL
                WHERE url IN ({placeholders})
                """,
                (now_iso, *urls),
            )
        conn.commit()
        return urls
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_next_urls(limit: int = 5):
    return claim_next_urls(limit=limit)


def mark_url_done(url: str):
    conn = get_conn()
    conn.execute(
        """
        UPDATE url_queue
        SET status = 'done',
            last_analyzed_at = ?,
            claimed_at = NULL,
            next_retry_at = NULL,
            last_error = NULL
        WHERE url = ?
        """,
        (_now_iso(), url),
    )
    conn.commit()
    conn.close()


def mark_url_retry(url: str, error_message: str | None = None, delay_minutes: int = URL_RETRY_DELAY_MINUTES):
    conn = get_conn()
    now = _now()
    next_retry_at = (now + timedelta(minutes=delay_minutes)).isoformat()
    conn.execute(
        """
        UPDATE url_queue
        SET status = 'retry',
            last_analyzed_at = ?,
            claimed_at = NULL,
            retry_count = retry_count + 1,
            next_retry_at = ?,
            last_error = ?
        WHERE url = ?
        """,
        (now.isoformat(), next_retry_at, error_message, url),
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

    now = _now()
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
                SET status = 'pending',
                    claimed_at = NULL,
                    next_retry_at = NULL
                WHERE url = ?
                """,
                (row["url"],),
            )

    conn.commit()
    conn.close()
