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
from src.recommend_enhanced import enhance_recommendations_with_quantified_impact
from src.forecasting import add_forecasts_to_analysis
from src.impact_analysis import analyze_initiative_impact
from src.strategic_lp_analysis import generate_strategic_lp_analysis_report
from src.report import render_marketing_report, save_report, save_report_json, save_report_csv
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
from src import rag_utils

# Configuration constants from environment
USE_LIGHTHOUSE = os.getenv("USE_LIGHTHOUSE", "true").lower() in ("1", "true", "yes")
ENABLE_FORECASTING = os.getenv("FORECASTING_ENABLED", "true").lower() in ("1", "true", "yes")
ENABLE_IMPACT_ANALYSIS = os.getenv("IMPACT_ANALYSIS_ENABLED", "true").lower() in ("1", "true", "yes")
RAG_ENABLED = os.getenv("RAG_ENABLED", "false").lower() in ("1", "true", "yes")
MULTI_AGENT_ENABLED = os.getenv("MULTI_AGENT_ENABLED", "false").lower() in ("1", "true", "yes")
AGENT_MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "8"))
PROMPT_NAME = "deep_analysis.md"
TARGET_SITE_MAX_PAGES = int(os.getenv("TARGET_SITE_MAX_PAGES", "5"))
URL_BATCH_SIZE = int(os.getenv("URL_BATCH_SIZE", "3"))
SLEEP_SECONDS = int(os.getenv("WORKER_INTERVAL_SECONDS", "600"))
SEED_URLS = []  # Will be loaded from target URLs file

logger = logging.getLogger(__name__)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    global logger
    logger = logging.getLogger(__name__)


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
    
    # Add forecasting if enabled
    if ENABLE_FORECASTING:
        try:
            snapshot = add_forecasts_to_analysis(snapshot, df)
            logger.info("Forecasting analysis added to snapshot")
        except Exception as e:
            logger.warning("Forecasting failed: %s", e)
    
    # Add impact analysis if enabled
    impact_analysis_result = None
    if ENABLE_IMPACT_ANALYSIS:
        try:
            # For worker, we analyze all channels as potential initiatives
            initiatives = [
                {"name": f"{channel} channel", "date": datetime.now(UTC).isoformat(), "metric": "roas"}
                for channel in snapshot.get("channels", {}).keys()
            ]
            if initiatives:
                impact_analysis_result = analyze_initiative_impact(df, initiatives)
                logger.info("Impact analysis completed for %d initiatives", len(initiatives))
        except Exception as e:
            logger.warning("Impact analysis failed: %s", e)
    
    # Enhance recommendations with quantified impact
    if ENABLE_FORECASTING or ENABLE_IMPACT_ANALYSIS:
        try:
            recommendations = enhance_recommendations_with_quantified_impact(
                recommendations,
                df,
                channels_df=snapshot.get("channels"),
                impact_analysis=impact_analysis_result,
            )
            logger.info("Enhanced recommendations with quantified impact")
        except Exception as e:
            logger.warning("Recommendation enhancement failed: %s", e)

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

            # Lighthouse and LLM analysis
            try:
                lh_summary = None
                if USE_LIGHTHOUSE:
                    try:
                        from urllib.parse import urlsplit
                        safe_domain = urlsplit(url).netloc.replace(":", "_")
                        lh_json = lighthouse_analyzer.run_lighthouse(
                            url, output_dir=f"reports/lighthouse/{safe_domain}"
                        )
                        lh_summary = lighthouse_analyzer.summarize_lighthouse(lh_json)
                    except Exception as e:
                        logger.exception("Lighthouse failed for %s: %s", url, e)
                        lh_summary = {"error": str(e)}

                # Build evidence
                evidence = []
                vision_analyses = []
                
                if isinstance(lh_summary, dict) and lh_summary.get("vitals"):
                    evidence.append(f"Lighthouse vitals: {lh_summary.get('vitals')}")
                
                # Add up to 3 page snippets from site result
                for p in result.get("pages", [])[:3]:
                    title = p.get("title") or ""
                    snippet = p.get("body_excerpt") or title
                    evidence.append(
                        f"Page: {p.get('url')} title: {title} snippet: {snippet} "
                        f"score:{p.get('score')}"
                    )
                    
                    # ===== Vision AI 分析 =====
                    if p.get("screenshot_path") and not skip_llm:
                        try:
                            vision_result = llm_helper.analyze_vision_lp(p.get("screenshot_path"), p)
                            if not vision_result.get("skipped"):
                                vision_analyses.append({
                                    "url": p.get("url"),
                                    "vision_analysis": vision_result.get("vision_analysis")
                                })
                                logger.info("Vision LP analysis completed for %s", p.get("url"))
                        except Exception as e:
                            logger.warning("Vision analysis failed for %s: %s", p.get("url"), e)
                    
                    if p.get("screenshot_path"):
                        evidence.append(f"Screenshot: {p.get('screenshot_path')}")

                # Only call LLM if we have at least one evidence line
                if evidence and not skip_llm:
                    try:
                        llm_res = llm_helper.generate_analysis(
                            PROMPT_NAME,
                            evidence,
                            model=os.getenv("OLLAMA_MODEL", "phi3:mini"),
                        )
                        # Attach LLM result and Vision analyses to site record
                        upsert_site_analysis_result(
                            {
                                **result,
                                "llm_analysis": llm_res,
                                "vision_analyses": vision_analyses
                            },
                            analysis_status="success",
                        )
                    except Exception as e:
                        logger.exception("LLM generation failed for %s: %s", url, e)
                else:
                    logger.info("Skipping LLM generation for %s", url)
                
                # ===== Strategic LP Analysis (最も弱いページを深掘り) =====
                strategic_lp_analyses = []
                if not skip_llm and result.get("weak_pages"):
                    try:
                        for weak_page in result.get("weak_pages", [])[:2]:  # Top 2 weakest pages
                            weak_url = weak_page.get("url")
                            page_html = weak_page.get("html", "")
                            page_excerpt = weak_page.get("body_excerpt", "")
                            
                            if page_html or page_excerpt:
                                logger.info("Strategic LP analysis for weak page: %s", weak_url)
                                lp_report = generate_strategic_lp_analysis_report(
                                    weak_url,
                                    page_html,
                                    page_excerpt,
                                    service_description=""
                                )
                                strategic_lp_analyses.append(lp_report)
                                logger.info("Strategic LP analysis completed for %s", weak_url)
                    except Exception as e:
                        logger.warning("Strategic LP analysis failed: %s", e)
                
                if strategic_lp_analyses:
                    upsert_site_analysis_result(
                        {
                            **result,
                            "strategic_lp_analyses": strategic_lp_analyses
                        },
                        analysis_status="success",
                    )
            except Exception:
                logger.exception("Post-analysis processing failed for %s", url)

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
    
    # ===== RAG に分析結果を保存 =====
    if RAG_ENABLED:
        try:
            collection = rag_utils.get_rag_collection()
            if collection:
                # レポートを保存
                rag_utils.add_report_to_rag(collection, path, report)
                
                # 各サイト分析結果を保存
                for result in all_site_results:
                    rag_utils.add_site_analysis_to_rag(collection, result.get("url", ""), result)
                
                # レコメンデーションを保存
                rag_utils.add_recommendations_to_rag(collection, recommendations)
                
                logger.info("RAG documents updated")
        except Exception as e:
            logger.warning(f"RAG update failed: {e}")
    
    # ===== Multi-Agent 分析実行 =====
    if MULTI_AGENT_ENABLED:
        try:
            from src.agents import PlannerAgent, AnalystAgent, CopywriterAgent, ValidatorAgent
            
            logger.info("Starting Multi-Agent analysis...")
            
            # Analyst: データ深掘り分析
            analyst = AnalystAgent()
            analyst_context = {
                "channels": snapshot.get("channels", {}),
                "diagnostics": snapshot.get("diagnostics", {}),
                "alerts": snapshot.get("alerts", [])
            }
            analyst_result = analyst.analyze_anomalies(
                analyst_context,
                snapshot.get("alerts", [])
            )
            logger.info("Analyst completed")
            
            # Planner: 戦略立案
            planner = PlannerAgent()
            planner_context = {
                "snapshot": snapshot,
                "recommendations": recommendations,
                "analyst_findings": analyst_result.get("analysis", "")
            }
            planner_result = planner.plan_strategy(planner_context, AGENT_MAX_ITERATIONS)
            logger.info("Planner completed")
            
            # Copywriter: 施策テキスト生成
            copywriter = CopywriterAgent()
            copywriter_context = {
                "recommendations": recommendations,
                "site_results": compact_urls
            }
            # 最初のサイト/ページのコピー案を生成（簡略化）
            if all_site_results and all_site_results[0].get("pages"):
                first_page = all_site_results[0]["pages"][0]
                copy_variations = copywriter.generate_copy_variations(first_page, num_variations=3)
                logger.info("Copywriter completed")
            
            # Validator: 戦略検証と ROI 最適化
            validator = ValidatorAgent()
            validator_context = {
                "strategy": planner_result.get("strategy", ""),
                "constraints": {
                    "budget": 100000,  # 例：月間予算
                    "team_size": 5,
                    "timeline_weeks": 12
                }
            }
            validator_result = validator.validate_strategy(
                planner_result.get("strategy", ""),
                validator_context.get("constraints", {})
            )
            logger.info("Validator completed")
            
            # Multi-Agent レポートを追加生成
            multi_agent_report = render_marketing_report(
                snapshot=snapshot,
                recommendations=recommendations,
                url_results=all_site_results,
                llm_summary=summary,
                deep_analysis=deep_analysis,
                multi_agent_analysis={
                    "analyst": analyst_result,
                    "planner": planner_result,
                    "validator": validator_result
                }
            )
            multi_agent_path = save_report("multi_agent_analysis", multi_agent_report)
            logger.info("Multi-Agent report saved: %s", multi_agent_path)
            
        except Exception as e:
            logger.warning(f"Multi-Agent analysis failed: {e}")
    
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