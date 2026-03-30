from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def save_report(title: str, body: str):
    Path("reports").mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = Path("reports") / f"{ts}_{title}.md"
    path.write_text(body, encoding="utf-8")
    return str(path)


def _fmt_int(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{int(value):,}"


def _fmt_currency(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"¥{float(value):,.0f}"


def _fmt_ratio(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.2f}"


def _fmt_pct(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def _fmt_delta(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    sign = "+" if value > 0 else ""
    return f"{sign}{float(value) * 100:.1f}%"


def _markdown_table(headers, rows):
    if not rows:
        return "_なし_"

    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = []
    for row in rows:
        cleaned = []
        for value in row:
            text = str(value).replace("\n", "<br>").replace("|", "/")
            cleaned.append(text)
        body.append("| " + " | ".join(cleaned) + " |")

    return "\n".join([header_line, separator, *body])


def render_marketing_report(
    *,
    snapshot: dict,
    recommendations: list,
    url_results: list,
    llm_summary: str,
):
    latest = snapshot["latest"]
    kpis = snapshot["kpis"]
    alerts = snapshot["alerts"]
    diagnostics = snapshot["diagnostics"]

    latest_totals = latest.get("latest", {})
    latest_delta = latest.get("delta_vs_previous", {})

    latest_lines = [
        f"- 最新日: {latest.get('latest_date') or '-'}",
        f"- 比較基準日: {latest.get('previous_date') or 'なし'}",
    ]

    if latest_totals:
        latest_lines.extend(
            [
                f"- 売上: {_fmt_currency(latest_totals.get('revenue'))} ({_fmt_delta(latest_delta.get('revenue'))})",
                f"- CV: {_fmt_int(latest_totals.get('conversions'))} ({_fmt_delta(latest_delta.get('conversions'))})",
                f"- 広告費: {_fmt_currency(latest_totals.get('cost'))} ({_fmt_delta(latest_delta.get('cost'))})",
                f"- ROAS: {_fmt_ratio(latest_totals.get('roas'))} ({_fmt_delta(latest_delta.get('roas'))})",
                f"- CVR: {_fmt_pct(latest_totals.get('cvr'))} ({_fmt_delta(latest_delta.get('cvr'))})",
            ]
        )

    kpi_lines = [
        f"- Sessions: {_fmt_int(kpis.get('sessions'))}",
        f"- Users: {_fmt_int(kpis.get('users'))}",
        f"- Conversions: {_fmt_int(kpis.get('conversions'))}",
        f"- Revenue: {_fmt_currency(kpis.get('revenue'))}",
        f"- Cost: {_fmt_currency(kpis.get('cost'))}",
        f"- ROAS: {_fmt_ratio(kpis.get('roas'))}",
        f"- CPA: {_fmt_currency(kpis.get('cpa'))}",
        f"- CVR: {_fmt_pct(kpis.get('cvr'))}",
    ]

    alert_lines = [
        f"- [{alert['severity'].upper()}] {alert['message']}"
        for alert in alerts
    ] or ["- 大きな異常は検出されませんでした。"]

    recommendation_rows = [
        [
            rec["priority"],
            rec["channel"],
            rec["issue"],
            rec["action"],
            rec["reason"],
        ]
        for rec in recommendations
    ]

    diagnostic_rows = []
    if diagnostics is not None and not diagnostics.empty:
        for _, row in diagnostics.iterrows():
            diagnostic_rows.append(
                [
                    row["channel"],
                    row["status"],
                    _fmt_currency(row["revenue"]),
                    _fmt_currency(row["cost"]),
                    _fmt_ratio(row["roas"]),
                    _fmt_delta(row["revenue_delta_pct"]),
                    _fmt_delta(row["cvr_delta_pct"]),
                    row["reason"],
                ]
            )

    site_rows = []
    weak_page_rows = []
    for result in url_results:
        site_rows.append(
            [
                result.get("url"),
                result.get("page_count", 0),
                result.get("score", "-"),
                ", ".join(result.get("site_findings", [])[:4]) or "-",
                ", ".join(result.get("site_improvements", [])[:4]) or "-",
            ]
        )

        for page in result.get("weak_pages", []):
            weak_page_rows.append(
                [
                    result.get("url"),
                    page.get("url"),
                    page.get("score"),
                    page.get("cta_count", 0),
                    ", ".join(page.get("findings", [])[:3]) or "-",
                    ", ".join(page.get("improvements", [])[:3]) or "-",
                ]
            )

    error_lines = []
    for result in url_results:
        for error in result.get("errors", []):
            error_lines.append(f"- {error.get('url')}: {error.get('error')}")
    if not error_lines:
        error_lines = ["- サイト巡回エラーなし"]

    return f"""# Daily Marketing Analysis

Generated: {datetime.now(UTC).isoformat()}

## Latest Snapshot
{chr(10).join(latest_lines)}

## Period KPI
{chr(10).join(kpi_lines)}

## Alerts
{chr(10).join(alert_lines)}

## Priority Actions
{_markdown_table(
    ["Priority", "Channel", "Issue", "Action", "Reason"],
    recommendation_rows,
)}

## Channel Diagnostics
{_markdown_table(
    ["Channel", "Status", "Revenue", "Cost", "ROAS", "Revenue Δ", "CVR Δ", "Reason"],
    diagnostic_rows,
)}

## Site Results
{_markdown_table(
    ["Site", "Pages", "Avg Score", "Findings", "Improvements"],
    site_rows,
)}

## Weak Pages
{_markdown_table(
    ["Site", "Page", "Score", "CTA", "Findings", "Improvements"],
    weak_page_rows,
)}

## Site Crawl Errors
{chr(10).join(error_lines)}

## LLM Summary
{llm_summary or "LLM summary unavailable"}
"""
