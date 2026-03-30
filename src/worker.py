import argparse
import logging
import os
import time
import traceback
from datetime import UTC, datetime

from src.analysis import build_analysis_snapshot, read_mart
from src.etl import load_csv_to_duckdb
from src.llm_client import ask_llm
from src.recommend import generate_recommendations
from src.report import render_marketing_report, save_report
from src.state import (
    fetch_next_urls,
    init_state,
    mark_url_done,
    mark_url_retry,
    requeue_stale_done_urls,
    sync_url_queue,
)
from src.url_analyzer import analyze_site
from src.url_targets import load_target_urls, target_urls_file_exists

SLEEP_SECONDS = int(os.getenv("WORKER_INTERVAL_SECONDS", "600"))
TARGET_SITE_MAX_PAGES = int(os.getenv("TARGET_SITE_MAX_PAGES", "5"))
URL_BATCH_SIZE = int(os.getenv("URL_BATCH_SIZE", "3"))
SEED_URLS = [
    "https://service.daitecjp.com/index.php/manual-production/",
]

logger = logging.getLogger(__name__)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


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


def load_seed_urls() -> list[str]:
    if target_urls_file_exists():
        return load_target_urls()
    return SEED_URLS


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

    if url_results and len(action_lines) < 4:
        weakest_site = min(url_results, key=lambda item: item.get("score", 0))
        site_improvement = (weakest_site.get("site_improvements") or [None])[0]
        if site_improvement:
            action_lines.append(f"- P2 site: {site_improvement}")

    caution_lines = ["3. 注意点"]
    if alerts:
        for alert in alerts[:3]:
            caution_lines.append(f"- {alert['message']}")
    else:
        caution_lines.append("- 大きな異常は検出されていません。")

    if url_results:
        weakest_site = min(url_results, key=lambda item: item.get("score", 0))
        caution_lines.append(
            f"- サイト診断: {weakest_site.get('url')} の平均score={weakest_site.get('score')} "
            f"({weakest_site.get('page_count', 0)}ページ)"
        )
        weakest_page = (weakest_site.get("weak_pages") or [None])[0]
        if weakest_page:
            caution_lines.append(
                f"- 弱いページ: {weakest_page.get('url')} score={weakest_page.get('score')}"
            )

    if llm_note:
        caution_lines.append(f"- LLM補足: {llm_note}")

    return "\n".join(summary_lines + [""] + action_lines + [""] + caution_lines)


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


def run_cycle(
    skip_llm: bool = False,
    force_reload: bool = False,
    max_site_pages: int = TARGET_SITE_MAX_PAGES,
):
    logger.info("Initializing state")
    init_state()

    seed_urls = load_seed_urls()
    logger.info("Syncing target URLs: %s", len(seed_urls))
    sync_url_queue(seed_urls, base_priority=10)
    requeue_stale_done_urls(hours=24)

    logger.info("Loading CSV into DuckDB")
    load_result = load_csv_to_duckdb(force=force_reload)
    logger.info("CSV load status: %s", load_result["status"])

    logger.info("Reading mart and computing analysis snapshot")
    df = read_mart()
    snapshot = build_analysis_snapshot(df)
    recommendations = generate_recommendations(
        snapshot["channels"],
        snapshot["diagnostics"],
        snapshot["alerts"],
    )

    url_results = []
    for url in fetch_next_urls(limit=URL_BATCH_SIZE):
        logger.info("Analyzing site: %s", url)
        try:
            result = analyze_site(url, max_pages=max_site_pages)
            url_results.append(result)
            mark_url_done(url)
            logger.info(
                "Completed site: %s (%s pages)",
                url,
                result.get("page_count", 0),
            )
        except Exception:
            mark_url_retry(url)
            tb = traceback.format_exc()
            logger.exception("Failed site analysis: %s", url)
            path = save_report(
                "worker_error_url",
                f"# URL Analysis Error\n\n"
                f"Generated: {datetime.now(UTC).isoformat()}\n\n"
                f"URL: {url}\n\n"
                f"```text\n{tb}\n```",
            )
            logger.info("Saved URL error report: %s", path)

    compact_urls = [
        {
            "url": result.get("url"),
            "score": result.get("score"),
            "page_count": result.get("page_count"),
            "site_findings": result.get("site_findings", [])[:3],
            "site_improvements": result.get("site_improvements", [])[:3],
            "weak_pages": [
                {
                    "url": page.get("url"),
                    "score": page.get("score"),
                }
                for page in result.get("weak_pages", [])[:2]
            ],
        }
        for result in url_results
    ]

    logger.info("Generating summary")
    summary = generate_summary(
        snapshot,
        recommendations,
        compact_urls,
        url_results,
        skip_llm=skip_llm,
    )

    report = render_marketing_report(
        snapshot=snapshot,
        recommendations=recommendations,
        url_results=url_results,
        llm_summary=summary,
    )
    path = save_report("daily_analysis", report)
    logger.info("Cycle completed successfully: %s", path)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--force-reload", action="store_true")
    parser.add_argument("--max-site-pages", type=int, default=TARGET_SITE_MAX_PAGES)
    args = parser.parse_args()

    setup_logging()

    if args.once:
        run_cycle(
            skip_llm=args.skip_llm,
            force_reload=args.force_reload,
            max_site_pages=args.max_site_pages,
        )
        return

    while True:
        try:
            run_cycle(
                skip_llm=args.skip_llm,
                force_reload=args.force_reload,
                max_site_pages=args.max_site_pages,
            )
        except Exception:
            tb = traceback.format_exc()
            logger.exception("Worker cycle failed")
            path = save_report(
                "worker_error",
                f"# Worker Error\n\n"
                f"Generated: {datetime.now(UTC).isoformat()}\n\n"
                f"```text\n{tb}\n```",
            )
            logger.info("Saved worker error report: %s", path)

        logger.info("Sleeping %s seconds", SLEEP_SECONDS)
        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
