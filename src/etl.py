from pathlib import Path

from src.db_utils import locked_duckdb_connection

DB_PATH = "db/marketing.duckdb"
CSV_PATH = "data/raw/marketing.csv"
DATASET_NAME = "marketing_csv"


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'main' AND table_name = ?
        """,
        [table_name],
    ).fetchone()
    return row is not None


def _csv_signature() -> dict:
    csv_path = Path(CSV_PATH)
    stat = csv_path.stat()
    return {
        "csv_path": str(csv_path.resolve()),
        "csv_mtime_ns": int(stat.st_mtime_ns),
        "csv_size": int(stat.st_size),
    }


def _read_etl_meta(conn):
    if not _table_exists(conn, "etl_meta"):
        return None

    row = conn.execute(
        """
        SELECT csv_path, csv_mtime_ns, csv_size, loaded_at
        FROM etl_meta
        WHERE dataset_name = ?
        """,
        [DATASET_NAME],
    ).fetchone()

    if row is None:
        return None

    return {
        "csv_path": row[0],
        "csv_mtime_ns": int(row[1]),
        "csv_size": int(row[2]),
        "loaded_at": row[3],
    }


def _should_reload(conn, signature: dict) -> bool:
    required_tables = ["raw_marketing", "mart_daily_channel"]
    if not all(_table_exists(conn, table_name) for table_name in required_tables):
        return True

    meta = _read_etl_meta(conn)
    if meta is None:
        return True

    return any(
        meta.get(key) != signature.get(key)
        for key in ["csv_path", "csv_mtime_ns", "csv_size"]
    )


def _write_etl_meta(conn, signature: dict):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS etl_meta (
            dataset_name TEXT PRIMARY KEY,
            csv_path TEXT NOT NULL,
            csv_mtime_ns BIGINT NOT NULL,
            csv_size BIGINT NOT NULL,
            loaded_at TIMESTAMP NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO etl_meta(dataset_name, csv_path, csv_mtime_ns, csv_size, loaded_at)
        VALUES (?, ?, ?, ?, now())
        ON CONFLICT(dataset_name) DO UPDATE SET
            csv_path = excluded.csv_path,
            csv_mtime_ns = excluded.csv_mtime_ns,
            csv_size = excluded.csv_size,
            loaded_at = excluded.loaded_at
        """,
        [
            DATASET_NAME,
            signature["csv_path"],
            signature["csv_mtime_ns"],
            signature["csv_size"],
        ],
    )


def get_conn():
    Path("db").mkdir(parents=True, exist_ok=True)
    return locked_duckdb_connection()


def load_csv_to_duckdb(force: bool = False):
    signature = _csv_signature()

    with get_conn() as conn:
        if not force and not _should_reload(conn, signature):
            return {"status": "skipped", **signature}

        conn.execute(
            """
            CREATE OR REPLACE TABLE raw_marketing AS
            SELECT
                CAST(date AS DATE) AS date,
                channel,
                campaign,
                CAST(sessions AS BIGINT) AS sessions,
                CAST(users AS BIGINT) AS users,
                CAST(conversions AS BIGINT) AS conversions,
                CAST(revenue AS DOUBLE) AS revenue,
                CAST(cost AS DOUBLE) AS cost
            FROM read_csv_auto(?)
            """,
            [CSV_PATH],
        )

        conn.execute(
            """
            CREATE OR REPLACE TABLE mart_daily_channel AS
            SELECT
                date,
                channel,
                SUM(sessions) AS sessions,
                SUM(users) AS users,
                SUM(conversions) AS conversions,
                SUM(revenue) AS revenue,
                SUM(cost) AS cost,
                CASE WHEN SUM(sessions) = 0 THEN 0
                     ELSE SUM(conversions) * 1.0 / SUM(sessions) END AS cvr,
                CASE WHEN SUM(conversions) = 0 THEN 0
                     ELSE SUM(cost) * 1.0 / SUM(conversions) END AS cpa,
                CASE WHEN SUM(cost) = 0 THEN 0
                     ELSE SUM(revenue) * 1.0 / SUM(cost) END AS roas,
                CASE WHEN SUM(conversions) = 0 THEN 0
                     ELSE SUM(revenue) * 1.0 / SUM(conversions) END AS aov,
                CASE WHEN SUM(sessions) = 0 THEN 0
                     ELSE SUM(revenue) * 1.0 / SUM(sessions) END AS rps
            FROM raw_marketing
            GROUP BY 1,2
            ORDER BY 1,2
            """
        )

        _write_etl_meta(conn, signature)
        return {"status": "loaded", **signature}
