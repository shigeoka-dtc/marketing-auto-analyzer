import duckdb
import pandas as pd

DB_PATH = "db/marketing.duckdb"


def read_mart():
    conn = duckdb.connect(DB_PATH)
    df = conn.execute("""
        SELECT *
        FROM mart_daily_channel
        ORDER BY date, channel
    """).fetchdf()
    conn.close()
    return df


def total_kpis(df: pd.DataFrame):
    sessions = df["sessions"].sum()
    users = df["users"].sum()
    conversions = df["conversions"].sum()
    revenue = df["revenue"].sum()
    cost = df["cost"].sum()

    return {
        "sessions": int(sessions),
        "users": int(users),
        "conversions": int(conversions),
        "revenue": float(revenue),
        "cost": float(cost),
        "cvr": float(conversions / sessions) if sessions else 0.0,
        "cpa": float(cost / conversions) if conversions else 0.0,
        "roas": float(revenue / cost) if cost else 0.0,
        "aov": float(revenue / conversions) if conversions else 0.0,
        "rps": float(revenue / sessions) if sessions else 0.0,
    }


def channel_summary(df: pd.DataFrame):
    grouped = (
        df.groupby("channel", as_index=False)
        .agg({
            "sessions": "sum",
            "users": "sum",
            "conversions": "sum",
            "revenue": "sum",
            "cost": "sum"
        })
    )

    grouped["cvr"] = grouped["conversions"] / grouped["sessions"].replace(0, 1)
    grouped["cpa"] = grouped["cost"] / grouped["conversions"].replace(0, 1)
    grouped["roas"] = grouped["revenue"] / grouped["cost"].replace(0, 1)
    grouped["aov"] = grouped["revenue"] / grouped["conversions"].replace(0, 1)
    grouped["rps"] = grouped["revenue"] / grouped["sessions"].replace(0, 1)

    return grouped.sort_values("revenue", ascending=False)


def detect_anomalies(df: pd.DataFrame):
    alerts = []

    for channel, g in df.groupby("channel"):
        g = g.sort_values("date").copy()
        if len(g) < 5:
            continue

        g["revenue_ma3"] = g["revenue"].rolling(3).mean()
        g["cost_ma3"] = g["cost"].rolling(3).mean()
        g["conv_ma3"] = g["conversions"].rolling(3).mean()

        latest = g.iloc[-1]

        if pd.notna(latest["revenue_ma3"]) and latest["revenue"] < latest["revenue_ma3"] * 0.7:
            alerts.append(f"{channel}: 直近売上が3日平均より30%以上低下")
        if pd.notna(latest["cost_ma3"]) and latest["cost"] > latest["cost_ma3"] * 1.3:
            alerts.append(f"{channel}: 直近広告費が3日平均より30%以上増加")
        if pd.notna(latest["conv_ma3"]) and latest["conversions"] < latest["conv_ma3"] * 0.7:
            alerts.append(f"{channel}: 直近CV数が3日平均より30%以上低下")

    return alerts