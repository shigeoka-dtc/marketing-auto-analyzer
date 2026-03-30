import argparse
import os

from src.analysis import build_analysis_snapshot, read_mart
from src.deep_analysis import generate_deep_analysis
from src.etl import load_csv_to_duckdb
from src.recommend import generate_recommendations
from src.report import render_marketing_report, save_report
from src.site_results_service import build_site_error_result, compact_site_results
from src.state import init_state, upsert_site_analysis_result
from src.summary_service import generate_summary
from src.url_analyzer import analyze_site
from src.url_targets import load_target_urls

TARGET_SITE_MAX_PAGES = int(os.getenv("TARGET_SITE_MAX_PAGES", "5"))


def collect_site_results(max_site_pages: int) -> list[dict]:
    results = []
    for url in load_target_urls():
        try:
            results.append(
                upsert_site_analysis_result(
                    analyze_site(url, max_pages=max_site_pages),
                    analysis_status="success",
                )
            )
        except Exception as exc:
            results.append(
                upsert_site_analysis_result(
                    build_site_error_result(url, str(exc)),
                    analysis_status="error",
                )
            )
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-reload", action="store_true")
    parser.add_argument("--max-site-pages", type=int, default=TARGET_SITE_MAX_PAGES)
    parser.add_argument("--skip-llm", action="store_true")
    args = parser.parse_args()

    init_state()
    load_result = load_csv_to_duckdb(force=args.force_reload)
    df = read_mart()
    snapshot = build_analysis_snapshot(df)
    recommendations = generate_recommendations(
        snapshot["channels"],
        snapshot["diagnostics"],
        snapshot["alerts"],
    )
    site_results = collect_site_results(args.max_site_pages)
    compact_urls = compact_site_results(site_results)
    summary = generate_summary(
        snapshot,
        recommendations,
        compact_urls,
        site_results,
        skip_llm=args.skip_llm,
    )
    deep_analysis = generate_deep_analysis(
        snapshot,
        recommendations,
        site_results,
        skip_llm=args.skip_llm,
    )

    report = render_marketing_report(
        snapshot=snapshot,
        recommendations=recommendations,
        url_results=site_results,
        llm_summary=summary,
        deep_analysis=deep_analysis,
    )
    path = save_report("manual_analysis", report)
    print(f"CSV同期: {load_result['status']}")
    print(f"対象サイト数: {len(site_results)}")
    print(f"分析レポートを生成しました: {path}")
