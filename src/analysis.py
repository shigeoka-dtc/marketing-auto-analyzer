import pandas as pd

from src.db_utils import locked_duckdb_connection

BASE_METRICS = ["sessions", "users", "conversions", "revenue", "cost"]
DERIVED_METRICS = ["cvr", "cpa", "roas", "aov", "rps"]
TREND_METRICS = ["sessions", "conversions", "revenue", "cost", "cvr", "cpa", "roas"]


def _safe_div(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return float(numerator / denominator)


def _pct_change(current: float, previous: float):
    if previous is None or pd.isna(previous) or previous == 0:
        return None
    return float((current - previous) / previous)


def _as_date_str(value) -> str:
    return pd.Timestamp(value).date().isoformat()


def _metric_dict(row: pd.Series) -> dict:
    metrics = {}
    for column in BASE_METRICS + DERIVED_METRICS:
        value = row[column]
        if column in {"sessions", "users", "conversions"}:
            metrics[column] = int(value)
        else:
            metrics[column] = float(value)
    return metrics


def _unique_in_order(values):
    seen = set()
    result = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _status_rank(status: str) -> int:
    return {
        "critical": 0,
        "warning": 1,
        "opportunity": 2,
        "stable": 3,
    }.get(status, 99)


def read_mart():
    with locked_duckdb_connection(read_only=True) as conn:
        return conn.execute(
            """
            SELECT *
            FROM mart_daily_channel
            ORDER BY date, channel
            """
        ).fetchdf()


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
        "cvr": _safe_div(conversions, sessions),
        "cpa": _safe_div(cost, conversions),
        "roas": _safe_div(revenue, cost),
        "aov": _safe_div(revenue, conversions),
        "rps": _safe_div(revenue, sessions),
    }


def daily_summary(df: pd.DataFrame):
    grouped = (
        df.groupby("date", as_index=False)
        .agg(
            {
                "sessions": "sum",
                "users": "sum",
                "conversions": "sum",
                "revenue": "sum",
                "cost": "sum",
            }
        )
        .sort_values("date")
        .reset_index(drop=True)
    )

    grouped["cvr"] = grouped["conversions"] / grouped["sessions"].replace(0, 1)
    grouped["cpa"] = grouped["cost"] / grouped["conversions"].replace(0, 1)
    grouped["roas"] = grouped["revenue"] / grouped["cost"].replace(0, 1)
    grouped["aov"] = grouped["revenue"] / grouped["conversions"].replace(0, 1)
    grouped["rps"] = grouped["revenue"] / grouped["sessions"].replace(0, 1)

    return grouped


def latest_snapshot(df: pd.DataFrame):
    daily = daily_summary(df)
    if daily.empty:
        return {
            "latest_date": None,
            "previous_date": None,
            "latest": {},
            "previous": {},
            "delta_vs_previous": {},
            "delta_vs_average": {},
        }

    latest = daily.iloc[-1]
    previous = daily.iloc[-2] if len(daily) >= 2 else None
    prior_window = daily.iloc[:-1]

    latest_metrics = _metric_dict(latest)
    previous_metrics = _metric_dict(previous) if previous is not None else {}

    delta_vs_previous = {}
    for metric in TREND_METRICS:
        delta_vs_previous[metric] = _pct_change(
            latest_metrics[metric],
            previous_metrics.get(metric),
        )

    delta_vs_average = {}
    if not prior_window.empty:
        for metric in TREND_METRICS:
            delta_vs_average[metric] = _pct_change(
                latest_metrics[metric],
                float(prior_window[metric].mean()),
            )
    else:
        delta_vs_average = {metric: None for metric in TREND_METRICS}

    return {
        "latest_date": _as_date_str(latest["date"]),
        "previous_date": _as_date_str(previous["date"]) if previous is not None else None,
        "latest": latest_metrics,
        "previous": previous_metrics,
        "delta_vs_previous": delta_vs_previous,
        "delta_vs_average": delta_vs_average,
    }


def channel_summary(df: pd.DataFrame):
    grouped = (
        df.groupby("channel", as_index=False)
        .agg(
            {
                "sessions": "sum",
                "users": "sum",
                "conversions": "sum",
                "revenue": "sum",
                "cost": "sum",
            }
        )
        .sort_values("revenue", ascending=False)
        .reset_index(drop=True)
    )

    grouped["cvr"] = grouped["conversions"] / grouped["sessions"].replace(0, 1)
    grouped["cpa"] = grouped["cost"] / grouped["conversions"].replace(0, 1)
    grouped["roas"] = grouped["revenue"] / grouped["cost"].replace(0, 1)
    grouped["aov"] = grouped["revenue"] / grouped["conversions"].replace(0, 1)
    grouped["rps"] = grouped["revenue"] / grouped["sessions"].replace(0, 1)
    grouped["profit"] = grouped["revenue"] - grouped["cost"]
    total_revenue = float(grouped["revenue"].sum()) or 1.0
    grouped["revenue_share"] = grouped["revenue"] / total_revenue

    return grouped


def channel_diagnostics(df: pd.DataFrame):
    rows = []

    for channel, channel_df in df.groupby("channel"):
        channel_df = channel_df.sort_values("date").reset_index(drop=True).copy()
        latest = channel_df.iloc[-1]
        previous = channel_df.iloc[-2] if len(channel_df) >= 2 else None
        prior_window = channel_df.iloc[:-1]

        latest_metrics = _metric_dict(latest)
        previous_metrics = _metric_dict(previous) if previous is not None else {}

        deltas = {
            f"{metric}_delta_pct": _pct_change(
                latest_metrics[metric],
                previous_metrics.get(metric),
            )
            for metric in TREND_METRICS
        }

        average_deltas = {}
        if not prior_window.empty:
            for metric in ["revenue", "cost", "conversions", "cvr", "roas"]:
                average_deltas[f"{metric}_vs_avg_pct"] = _pct_change(
                    latest_metrics[metric],
                    float(prior_window[metric].mean()),
                )
        else:
            average_deltas = {
                "revenue_vs_avg_pct": None,
                "cost_vs_avg_pct": None,
                "conversions_vs_avg_pct": None,
                "cvr_vs_avg_pct": None,
                "roas_vs_avg_pct": None,
            }

        issue_score = 0
        opportunity_score = 0
        reasons = []

        revenue_delta = deltas["revenue_delta_pct"]
        cost_delta = deltas["cost_delta_pct"]
        conversions_delta = deltas["conversions_delta_pct"]
        cvr_delta = deltas["cvr_delta_pct"]
        cpa_delta = deltas["cpa_delta_pct"]
        roas_delta = deltas["roas_delta_pct"]

        if latest_metrics["cost"] > 0 and latest_metrics["revenue"] == 0:
            issue_score += 5
            reasons.append("費用発生に対して売上ゼロ")

        if revenue_delta is not None and revenue_delta <= -0.15:
            issue_score += 2
            reasons.append("売上が前日比15%以上減少")

        if conversions_delta is not None and conversions_delta <= -0.15:
            issue_score += 2
            reasons.append("CVが前日比15%以上減少")

        if cvr_delta is not None and cvr_delta <= -0.10:
            issue_score += 1
            reasons.append("CVRが前日比10%以上低下")

        if roas_delta is not None and roas_delta <= -0.15:
            issue_score += 2
            reasons.append("ROASが前日比15%以上悪化")

        if cpa_delta is not None and cpa_delta >= 0.15:
            issue_score += 1
            reasons.append("CPAが前日比15%以上悪化")

        if (
            cost_delta is not None
            and cost_delta >= 0.15
            and (revenue_delta is None or revenue_delta <= 0.05)
        ):
            issue_score += 2
            reasons.append("費用増に対して売上が伸びていない")

        if revenue_delta is not None and revenue_delta >= 0.15:
            opportunity_score += 1

        if latest_metrics["roas"] >= 3.0 and latest_metrics["cvr"] >= 0.03:
            opportunity_score += 2
            reasons.append("ROASとCVRが良好")

        if conversions_delta is not None and conversions_delta >= 0.15:
            opportunity_score += 1

        if issue_score >= 5:
            status = "critical"
        elif issue_score >= 2:
            status = "warning"
        elif opportunity_score >= 2:
            status = "opportunity"
        else:
            status = "stable"

        if latest_metrics["cost"] > 0 and latest_metrics["revenue"] == 0:
            recommended_action = "配信停止候補を洗い出し、入札・配信面・訴求を絞り込む"
        elif cvr_delta is not None and cvr_delta <= -0.10:
            recommended_action = "LPの訴求、フォーム、CTA導線を優先点検する"
        elif cost_delta is not None and cost_delta >= 0.15 and (roas_delta is None or roas_delta <= 0):
            recommended_action = "入札、配信面、クリエイティブの無駄打ちを削減する"
        elif status == "opportunity":
            recommended_action = "勝ち訴求を維持したまま小さく予算増額テストを行う"
        else:
            recommended_action = "大きな異常はないため継続監視する"

        rows.append(
            {
                "channel": channel,
                "latest_date": _as_date_str(latest["date"]),
                "status": status,
                "priority_score": issue_score * 10 + opportunity_score,
                "reason": " / ".join(_unique_in_order(reasons)) or "大きな異常なし",
                "recommended_action": recommended_action,
                **latest_metrics,
                **deltas,
                **average_deltas,
            }
        )

    diagnostics = pd.DataFrame(rows)
    if diagnostics.empty:
        return diagnostics

    return diagnostics.sort_values(
        by=["status", "priority_score", "revenue"],
        ascending=[True, False, False],
        key=lambda column: column.map(_status_rank) if column.name == "status" else column,
    ).reset_index(drop=True)


def detect_anomalies(
    df: pd.DataFrame,
    latest=None,
    diagnostics: pd.DataFrame | None = None,
):
    latest = latest or latest_snapshot(df)
    diagnostics = diagnostics if diagnostics is not None else channel_diagnostics(df)

    alerts = []

    overall_delta = latest["delta_vs_previous"]
    if latest["previous_date"]:
        if overall_delta.get("revenue") is not None and overall_delta["revenue"] <= -0.15:
            alerts.append(
                {
                    "severity": "high",
                    "scope": "overall",
                    "message": "全体売上が前日比15%以上低下",
                }
            )

        if (
            overall_delta.get("cost") is not None
            and overall_delta["cost"] >= 0.15
            and overall_delta.get("roas") is not None
            and overall_delta["roas"] <= -0.10
        ):
            alerts.append(
                {
                    "severity": "medium",
                    "scope": "overall",
                    "message": "全体費用が増加し、ROASが悪化",
                }
            )

        if overall_delta.get("conversions") is not None and overall_delta["conversions"] <= -0.15:
            alerts.append(
                {
                    "severity": "medium",
                    "scope": "overall",
                    "message": "全体CVが前日比15%以上低下",
                }
            )

    if diagnostics is not None and not diagnostics.empty:
        for _, row in diagnostics.iterrows():
            if row["status"] not in {"critical", "warning"}:
                continue

            severity = "high" if row["status"] == "critical" else "medium"
            alerts.append(
                {
                    "severity": severity,
                    "scope": row["channel"],
                    "message": f'{row["channel"]}: {row["reason"]}',
                }
            )

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(alerts, key=lambda x: (severity_rank.get(x["severity"], 99), x["scope"]))


def _rolling_trends(df: pd.DataFrame, window_short: int = 7, window_long: int = 28):
    daily = daily_summary(df)
    if daily.empty:
        return {}

    data = daily.set_index("date")["revenue"]
    short_ma = data.rolling(window=window_short, min_periods=1).mean()
    long_ma = data.rolling(window=window_long, min_periods=1).mean()

    momentum = (short_ma - long_ma) / long_ma.replace(0, float("nan"))
    volatility = data.pct_change().rolling(window=window_short, min_periods=1).std().fillna(0)

    latest_date = daily.iloc[-1]["date"]

    return {
        "latest_date": _as_date_str(latest_date),
        "revenue_short_ma": float(short_ma.iloc[-1]),
        "revenue_long_ma": float(long_ma.iloc[-1]),
        "revenue_momentum": float(momentum.iloc[-1]) if not pd.isna(momentum.iloc[-1]) else None,
        "revenue_volatility": float(volatility.iloc[-1]),
    }


def _channel_correlations(df: pd.DataFrame):
    if df.empty:
        return {"strong_correlations": [], "correlation_matrix": {}}

    pivot = df.pivot_table(
        index="date",
        columns="channel",
        values="revenue",
        aggfunc="sum",
        fill_value=0
    )

    corr_matrix = pivot.corr()
    strong_correlations = []

    for i in range(len(corr_matrix.columns)):
        for j in range(i + 1, len(corr_matrix.columns)):
            channel_a = corr_matrix.columns[i]
            channel_b = corr_matrix.columns[j]
            correlation = corr_matrix.iloc[i, j]

            if abs(correlation) >= 0.7:
                strong_correlations.append({
                    "channel_a": channel_a,
                    "channel_b": channel_b,
                    "correlation": float(correlation),
                    "strength": "strong_positive" if correlation > 0 else "strong_negative"
                })

    return {
        "strong_correlations": strong_correlations,
        "correlation_matrix": corr_matrix.to_dict()
    }


def _predictive_insights(df: pd.DataFrame):
    daily = daily_summary(df)
    if len(daily) < 7:
        return {"trend_direction": "insufficient_data", "confidence": 0.0, "forecast": {}}

    from sklearn.linear_model import LinearRegression
    import numpy as np

    data = daily.copy()
    data["day_index"] = range(len(data))

    X = data[["day_index"]].values
    y = data["revenue"].values

    model = LinearRegression()
    model.fit(X, y)

    slope = model.coef_[0]
    intercept = model.intercept_

    trend_direction = "increasing" if slope > 0 else "decreasing"
    confidence = max(0.0, min(1.0, abs(slope) / (abs(slope) + data["revenue"].std())))

    next_day_index = len(data)
    forecast_revenue = float(model.predict([[next_day_index]])[0])

    return {
        "trend_direction": trend_direction,
        "confidence": float(confidence),
        "forecast": {
            "next_day_revenue": forecast_revenue,
            "slope": float(slope),
            "intercept": float(intercept)
        }
    }


def _anomaly_detection(df: pd.DataFrame):
    daily = daily_summary(df)
    if len(daily) < 7:
        return {"anomalies": [], "z_score_threshold": 2.0}

    import numpy as np

    data = daily["revenue"].values
    mean = np.mean(data)
    std = np.std(data)

    if std == 0:
        return {"anomalies": [], "z_score_threshold": 2.0}

    z_scores = [(value - mean) / std for value in data]
    anomalies = []

    for i, (date, z_score) in enumerate(zip(daily["date"], z_scores)):
        if abs(z_score) > 2.0:
            anomalies.append({
                "date": _as_date_str(date),
                "revenue": float(data[i]),
                "z_score": float(z_score),
                "type": "high" if z_score > 0 else "low",
                "severity": "extreme" if abs(z_score) > 3.0 else "moderate"
            })

    return {
        "anomalies": anomalies,
        "z_score_threshold": 2.0,
        "mean_revenue": float(mean),
        "std_revenue": float(std)
    }


def _segmentation_analysis(df: pd.DataFrame):
    if df.empty:
        return {"segments": [], "insights": []}

    channel_summary_df = channel_summary(df)
    total_revenue = float(channel_summary_df["revenue"].sum())

    segments = []
    insights = []

    for _, row in channel_summary_df.iterrows():
        revenue_share = float(row["revenue"]) / total_revenue if total_revenue > 0 else 0
        roas = float(row["roas"])

        segment_type = "high_performer" if roas > 3.0 and revenue_share > 0.3 else \
                      "consistent" if roas > 1.5 else \
                      "under_performer"

        segments.append({
            "channel": row["channel"],
            "segment_type": segment_type,
            "revenue_share": revenue_share,
            "roas": roas,
            "cvr": float(row["cvr"]),
            "cpa": float(row["cpa"])
        })

    high_performers = [s for s in segments if s["segment_type"] == "high_performer"]
    under_performers = [s for s in segments if s["segment_type"] == "under_performer"]

    if high_performers:
        insights.append(f"高パフォーマンスチャネル: {', '.join([s['channel'] for s in high_performers])} - 予算増強検討")

    if under_performers:
        insights.append(f"改善対象チャネル: {', '.join([s['channel'] for s in under_performers])} - 最適化優先")

    return {
        "segments": segments,
        "insights": insights
    }


def build_analysis_snapshot(df: pd.DataFrame):
    latest = latest_snapshot(df)
    channels = channel_summary(df)
    diagnostics = channel_diagnostics(df)
    alerts = detect_anomalies(df, latest=latest, diagnostics=diagnostics)
    advanced = _rolling_trends(df)
    correlations = _channel_correlations(df)
    predictions = _predictive_insights(df)
    anomalies = _anomaly_detection(df)
    segmentation = _segmentation_analysis(df)

    return {
        "kpis": total_kpis(df),
        "daily": daily_summary(df),
        "latest": latest,
        "channels": channels,
        "diagnostics": diagnostics,
        "alerts": alerts,
        "advanced": {
            **advanced,
            "channel_correlations": correlations,
            "predictions": predictions,
            "anomalies": anomalies,
            "segmentation": segmentation,
        },
    }
