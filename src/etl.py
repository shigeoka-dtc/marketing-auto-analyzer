from pathlib import Path
import duckdb

DB_PATH = "db/marketing.duckdb"
CSV_PATH = "data/raw/marketing.csv"


def get_conn():
    Path("db").mkdir(parents=True, exist_ok=True)
    return duckdb.connect(DB_PATH)


def load_csv_to_duckdb():
    conn = get_conn()

    conn.execute("""
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
    """, [CSV_PATH])

    conn.execute("""
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
    """)

    conn.close()