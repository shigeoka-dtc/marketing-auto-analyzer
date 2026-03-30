import argparse
import logging
import time
import traceback
from datetime import datetime

from src.state import (
    init_state,
    enqueue_url,
    fetch_next_urls,
    mark_url_done,
    requeue_stale_done_urls,
)
from src.etl import load_csv_to_duckdb
from src.analysis import read_mart, total_kpis, channel_summary, detect_anomalies
from src.recommend import generate_recommendations
from src.url_analyzer import analyze_url
from src.report import save_report
from src.llm_client import ask_llm

SLEEP_SECONDS = 600
SEED_URLS = [
    "https://service.daitecjp.com/index.php/manual-production/"
]

logger = logging.getLogger(__name__)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def run_cycle():
    logger.info("Initializing state")
    init_state()

    for url in SEED_URLS:
        enqueue_url(url, priority=10)

    # 24時間以上前にdoneになったURLを再投入
    requeue_stale_done_urls(hours=24)

    logger.info("Loading CSV into DuckDB")
    load_csv_to_duckdb()

    logger.info("Reading mart and computing KPIs")
    df = read_mart()
    kpis = total_kpis(df)
    channels = channel_summary(df)
    alerts = detect_anomalies(df)
    recs = generate_recommendations(channels)

    url_results = []
    for url in fetch_next_urls(limit=3):
        logger.info("Analyzing URL: %s", url)
        try:
            result = analyze_url(url)
            url_results.append(result)
            mark_url_done(url)
            logger.info("Completed URL: %s", url)
        except Exception:
            tb = traceback.format_exc()
            logger.exception("Failed URL analysis: %s", url)
            path = save_report(
                "worker_error_url",
                f"# URL Analysis Error\n\n"
                f"Generated: {datetime.utcnow().isoformat()}\n\n"
                f"URL: {url}\n\n"
                f"```text\n{tb}\n```"
            )
            logger.info("Saved URL error report: %s", path)

    compact_urls = [
        {
            "url": r.get("url"),
            "score": r.get("score"),
            "findings": r.get("findings", [])[:3],
            "improvements": r.get("improvements", [])[:3],
            "cta_count": r.get("cta_count"),
            "has_faq": r.get("has_faq"),
            "has_case": r.get("has_case"),
            "has_pdf": r.get("has_pdf"),
        }
        for r in url_results
    ]

    prompt = f"""
あなたはB2Bマーケティング分析アシスタントです。
必ず日本語で、簡潔に、箇条書きで答えてください。
推測は禁止です。不明な点は「不明」と書いてください。
次の3項目だけを出力してください。

1. 現状サマリー
2. 優先アクション（最大3つ）
3. 注意点

KPI:
{kpis}

Alerts:
{alerts}

Rule-based Recommendations:
{recs}

URL Summary:
{compact_urls}
"""

    logger.info("Calling LLM")
    llm_summary = ask_llm(prompt)

    report = f"""# Daily Marketing Analysis

Generated: {datetime.utcnow().isoformat()}

## KPI
{kpis}

## Alerts
{alerts}

## Rule-based Recommendations
{recs}

## URL Results
{url_results}

## LLM Summary
{llm_summary}
"""
    path = save_report("daily_analysis", report)
    logger.info("Cycle completed successfully: %s", path)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    setup_logging()

    if args.once:
        run_cycle()
        return

    while True:
        try:
            run_cycle()
        except Exception:
            tb = traceback.format_exc()
            logger.exception("Worker cycle failed")
            path = save_report(
                "worker_error",
                f"# Worker Error\n\n"
                f"Generated: {datetime.utcnow().isoformat()}\n\n"
                f"```text\n{tb}\n```"
            )
            logger.info("Saved worker error report: %s", path)

        logger.info("Sleeping %s seconds", SLEEP_SECONDS)
        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()