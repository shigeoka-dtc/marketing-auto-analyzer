from src.llm_client import ask_llm
from src.site_results_service import is_actionable_site_result


def _alert_lines(alerts: list) -> str:
    if not alerts:
        return "- 目立つアラートなし"
    return "\n".join(
        f"- [{alert['severity'].upper()}] {alert['message']}"
        for alert in alerts
    )


def _recommendation_lines(recommendations: list) -> str:
    if not recommendations:
        return "- 提案なし"
    return "\n".join(
        f"- {rec['priority']} | {rec['channel']} | {rec['issue']} | {rec['action']}"
        for rec in recommendations[:5]
    )


def _diagnostic_records(snapshot: dict):
    diagnostics = snapshot["diagnostics"]
    if diagnostics is None or diagnostics.empty:
        return []
    columns = [
        "channel",
        "status",
        "revenue",
        "cost",
        "conversions",
        "roas",
        "cvr",
        "revenue_delta_pct",
        "cvr_delta_pct",
        "roas_delta_pct",
        "reason",
        "recommended_action",
    ]
    return diagnostics[columns].to_dict(orient="records")


def _diagnostic_focus_lines(snapshot: dict) -> list[str]:
    diagnostics = snapshot["diagnostics"]
    if diagnostics is None or diagnostics.empty:
        return ["- チャネル別の大きな変動は見つかっていません。"]

    lines = []
    issues = diagnostics[diagnostics["status"].isin(["critical", "warning"])].head(2)
    opportunities = diagnostics[diagnostics["status"] == "opportunity"].head(1)

    for _, row in issues.iterrows():
        lines.append(
            f"- 要改善 {row['channel']}: {row['reason']} / 対応: {row['recommended_action']}"
        )

    for _, row in opportunities.iterrows():
        lines.append(
            f"- 伸長候補 {row['channel']}: {row['reason']} / 対応: {row['recommended_action']}"
        )

    return lines or ["- チャネル別の大きな変動は見つかっていません。"]


def _site_focus_lines(url_results: list) -> list[str]:
    actionable_results = [result for result in url_results if is_actionable_site_result(result)]
    if not actionable_results:
        return ["- 対象サイトの診断結果はまだありません。"]

    weakest_site = min(actionable_results, key=lambda item: item.get("score", 0))
    lines = [
        f"- 最も弱いサイト: {weakest_site.get('url')} / 平均score={weakest_site.get('score')} / "
        f"分析ページ数={weakest_site.get('page_count', 0)}"
    ]

    for page in weakest_site.get("weak_pages", [])[:2]:
        lines.append(
            f"- 弱いページ: {page.get('url')} / score={page.get('score')} / "
            f"改善: {', '.join(page.get('improvements', [])[:2]) or '改善提案なし'}"
        )

    for improvement in weakest_site.get("site_improvements", [])[:2]:
        lines.append(f"- サイト横断改善: {improvement}")

    return lines


def build_rule_based_summary(
    snapshot: dict,
    recommendations: list,
    url_results: list,
    llm_note: str | None = None,
) -> str:
    latest = snapshot["latest"]
    latest_totals = latest.get("latest", {})
    latest_delta = latest.get("delta_vs_previous", {})
    alerts = snapshot["alerts"]

    summary_lines = [
        "1. 現状サマリー",
        f"- 最新日: {latest.get('latest_date') or '不明'}",
        f"- 売上: {latest_totals.get('revenue', 0):.0f}",
        f"- CV: {latest_totals.get('conversions', 0)}",
        f"- ROAS: {latest_totals.get('roas', 0):.2f}",
    ]
    if latest.get("previous_date"):
        revenue_delta = latest_delta.get("revenue")
        roas_delta = latest_delta.get("roas")
        summary_lines.append(
            f"- 前日比: 売上 {revenue_delta * 100:+.1f}% / ROAS {roas_delta * 100:+.1f}%"
            if revenue_delta is not None and roas_delta is not None
            else "- 前日比: 不明"
        )

    action_lines = ["2. 優先アクション（最大3つ）"]
    if recommendations:
        for rec in recommendations[:3]:
            action_lines.append(f"- {rec['priority']} {rec['channel']}: {rec['action']}")
    else:
        action_lines.append("- 優先度の高い改善提案はありません。")

    actionable_results = [result for result in url_results if is_actionable_site_result(result)]
    if actionable_results and len(action_lines) < 4:
        weakest_site = min(actionable_results, key=lambda item: item.get("score", 0))
        site_improvement = (weakest_site.get("site_improvements") or [None])[0]
        if site_improvement:
            action_lines.append(f"- P2 site: {site_improvement}")

    diagnostic_lines = ["3. チャネル深掘り"]
    diagnostic_lines.extend(_diagnostic_focus_lines(snapshot))

    site_lines = ["4. サイト改善優先度"]
    site_lines.extend(_site_focus_lines(url_results))

    caution_lines = ["5. 注意点"]
    if alerts:
        for alert in alerts[:3]:
            caution_lines.append(f"- {alert['message']}")
    else:
        caution_lines.append("- 大きな異常は検出されていません。")

    if llm_note:
        caution_lines.append(f"- LLM補足: {llm_note}")

    return "\n".join(
        summary_lines
        + [""]
        + action_lines
        + [""]
        + diagnostic_lines
        + [""]
        + site_lines
        + [""]
        + caution_lines
    )


def build_llm_prompt(snapshot: dict, recommendations: list, compact_urls: list) -> str:
    return f"""
あなたはB2Bマーケティング分析アシスタントです。
必ず日本語で、簡潔に、箇条書きで答えてください。
推測は禁止です。不明な点は「不明」と書いてください。
次の3項目だけを出力してください。

1. 現状サマリー
2. 優先アクション（最大3つ）
3. 注意点

Latest Snapshot:
{snapshot["latest"]}

Period KPI:
{snapshot["kpis"]}

Alerts:
{_alert_lines(snapshot["alerts"])}

Priority Actions:
{_recommendation_lines(recommendations)}

Channel Diagnostics:
{_diagnostic_records(snapshot)}

Site Summary:
{compact_urls}
"""


def generate_summary(
    snapshot: dict,
    recommendations: list,
    compact_urls: list,
    url_results: list,
    skip_llm: bool = False,
) -> str:
    if skip_llm:
        return build_rule_based_summary(
            snapshot,
            recommendations,
            url_results,
            llm_note="skip_llm オプションによりルールベース要約を使用",
        )

    llm_summary = ask_llm(build_llm_prompt(snapshot, recommendations, compact_urls))
    if llm_summary.startswith("[LLM"):
        return build_rule_based_summary(
            snapshot,
            recommendations,
            url_results,
            llm_note=llm_summary,
        )
    return llm_summary
