import argparse
import logging
import os
import time
import traceback
from datetime import UTC, datetime

from src.analysis import build_analysis_snapshot, read_mart
from src.deep_analysis import generate_deep_analysis
from src.etl import load_csv_to_duckdb
from src.recommend import generate_recommendations
from src.report import render_marketing_report, save_report
from src.site_results_service import (
    build_site_error_result,
    compact_site_results,
    merge_site_results,
)
from src.state import (
    claim_next_urls,
    init_state,
    list_site_analysis_results,
    mark_url_done,
    mark_urls_pending,
    mark_url_retry,
    requeue_stale_done_urls,
    sync_url_queue,
    upsert_site_analysis_result,
)
from src.summary_service import generate_summary
from src.url_analyzer import analyze_site
from src.url_targets import load_target_urls, target_urls_file_exists

from src import lighthouse_analyzer
from src import llm_helper
import os

USE_LIGHTHOUSE = os.getenv("USE_LIGHTHOUSE", "true").lower() in ("1","true","yes")
PROMPT_NAME = "deep_analysis.md"

# ... inside the for url loop, after result obtained ...
site_summary = result  # result is upserted site summary
if USE_LIGHTHOUSE:
    try:
        lh_json = lighthouse_analyzer.run_lighthouse(url, output_dir="reports/lighthouse")
        lh_summary = lighthouse_analyzer.summarize_lighthouse(lh_json)
    except Exception as e:
        lh_summary = {"error": str(e)}

# Build evidence: combine Lh summary + top page snippets + screenshot path if any
evidence = []
if isinstance(lh_summary, dict):
    evidence.append(f"Lighthouse summary: {lh_summary.get('vitals',{})}")
# add top N page titles/snippets
for p in site_summary.get("pages", [])[:3]:
    evidence.append(f"Page: {p.get('url','')} title: {p.get('title','')}, score:{p.get('score')}")
# Playwright screenshot path if created (if crawl stores screenshot path in result)
screenshot_path = site_summary.get("screenshot_path")
if screenshot_path:
    evidence.append(f"Screenshot: {screenshot_path}")

llm_res = llm_helper.generate_analysis(PROMPT_NAME, evidence, model=os.getenv("OLLAMA_MODEL","phi3:mini"))
# store or attach llm_res["result"] into reports via upsert_site_analysis_result or save_report


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


def load_seed_urls() -> list[str]:
    if target_urls_file_exists():
        return load_target_urls()
    return SEED_URLS


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
    stored_results = list_site_analysis_results(seed_urls)
    missing_result_urls = [
        url for url in seed_urls
        if url not in {result.get("url") for result in stored_results}
    ]
    mark_urls_pending(missing_result_urls)

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
    for url in claim_next_urls(limit=URL_BATCH_SIZE):
        logger.info("Analyzing site: %s", url)
        try:
            result = upsert_site_analysis_result(
                analyze_site(url, max_pages=max_site_pages),
                analysis_status="success",
            )
            url_results.append(result)
            mark_url_done(url)
            logger.info(
                "Completed site: %s (%s pages)",
                url,
                result.get("page_count", 0),
            )
        except Exception as exc:
            mark_url_retry(url, error_message=str(exc))
            url_results.append(
                upsert_site_analysis_result(
                    build_site_error_result(url, str(exc)),
                    analysis_status="error",
                )
            )
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

    all_site_results = merge_site_results(
        seed_urls,
        url_results,
        list_site_analysis_results(seed_urls),
    )
    compact_urls = compact_site_results(all_site_results)

    logger.info("Generating summary")
    summary = generate_summary(
        snapshot,
        recommendations,
        compact_urls,
        all_site_results,
        skip_llm=skip_llm,
    )
    deep_analysis = generate_deep_analysis(
        snapshot,
        recommendations,
        all_site_results,
        skip_llm=skip_llm,
    )

    report = render_marketing_report(
        snapshot=snapshot,
        recommendations=recommendations,
        url_results=all_site_results,
        llm_summary=summary,
        deep_analysis=deep_analysis,
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



# 既存の成功パス直後（upsert_site_analysis_result / mark_url_done の直後）
try:
    # Lighthouse
    lh_summary = None
    if USE_LIGHTHOUSE:
        try:
            lh_json = lighthouse_analyzer.run_lighthouse(url, output_dir=f"reports/lighthouse/{safe_domain}")
            lh_summary = lighthouse_analyzer.summarize_lighthouse(lh_json)
        except Exception as e:
            logger.exception("Lighthouse failed for %s: %s", url, e)
            lh_summary = {"error": str(e)}

    # build evidence (always ensure at least one evidence item if possible)
    evidence = []
    if lh_summary and "vitals" in lh_summary:
        evidence.append(f"Lighthouse vitals: {lh_summary.get('vitals')}")
    # take top 3 pages
    for p in result.get("pages", [])[:3]:
        snippet = p.get("body_excerpt") or (p.get("title") or "")  # add body_excerpt field in url_analyzer if needed
        evidence.append(f"Page: {p.get('url')} title: {p.get('title')} snippet: {snippet} score:{p.get('score')}")
        if p.get("screenshot_path"):
            evidence.append(f"Screenshot: {p.get('screenshot_path')}")
    # call LLM (llm_helper will skip if OLLAMA_ENABLED=false)
    try:
        llm_res = llm_helper.generate_analysis(PROMPT_NAME, evidence, model=os.getenv("OLLAMA_MODEL","phi3:mini"))
        # attach llm_res to result or save report
        upsert_site_analysis_result({**result, "llm_analysis": llm_res}, analysis_status="success")
    except Exception as e:
        logger.exception("LLM generation failed: %s", e)