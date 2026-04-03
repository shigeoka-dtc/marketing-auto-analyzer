import argparse
import json
import logging
import os
from pathlib import Path

from src.orchestration import (
    DataService,
    AnalysisService,
    EnhancementService,
    ReportService,
)
from src.report import save_json_summary
from src.site_results_service import (
    compact_site_results,
    get_strategic_analysis_input,
)
from src.state import init_state

TARGET_SITE_MAX_PAGES = int(os.getenv("TARGET_SITE_MAX_PAGES", "5"))


def configure_logger():
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(__name__)


def _render_strategic_lp_analysis_report(analysis: dict) -> str:
    """
    Strategic LP analysis を Markdown レポートに変換
    """
    url = analysis.get("url", "不明")
    sections = analysis.get("sections", {})
    executive_summary = analysis.get("executive_summary", "")
    
    lines = [
        "# 戦略的LP分析レポート",
        "",
        f"**対象ページ**: {url}",
        f"**レポートタイプ**: {analysis.get('report_type', '不明')}",
        "",
        "---",
        "",
    ]
    
    # Executive Summary
    if executive_summary:
        lines.extend([
            "## エグゼクティブサマリー",
            "",
            executive_summary,
            "",
            "---",
            "",
        ])
    
    # 現状分析：LP構造と課題
    current_analysis = sections.get("現状分析_LP構造と課題", {})
    if current_analysis:
        lines.extend([
            "## 現状分析：LP構造と課題",
            "",
        ])
        
        lp_elements = current_analysis.get("lp_elements", {})
        if lp_elements:
            lines.extend([
                "### LP要素分析",
                "",
                f"- **H1**: {lp_elements.get('h1', '未検出')}",
                f"- **H2数**: {lp_elements.get('h2_count', 0)}",
                f"- **CTA数**: {lp_elements.get('cta_count', 0)}",
                f"- **テキスト総量**: {lp_elements.get('text_length', 0)}文字",
                f"- **段落数**: {lp_elements.get('paragraph_count', 0)}",
                f"- **セクション数**: {lp_elements.get('section_count', 0)}",
                f"- **画像数**: {lp_elements.get('images_count', 0)}",
                "",
            ])
        
        analysis_detail = current_analysis.get("analysis", {})
        if analysis_detail:
            lines.extend([
                "### 詳細分析",
                "",
                f"**総合スコア**: {analysis_detail.get('overall_score', 'N/A')}/10",
                "",
                f"**H1評価**: {analysis_detail.get('h1_assessment', 'N/A')}",
                f"- スコア: {analysis_detail.get('h1_score', 'N/A')}/10",
                "",
                f"**CTA評価**: {analysis_detail.get('cta_assessment', 'N/A')}",
                f"- スコア: {analysis_detail.get('cta_score', 'N/A')}/10",
                "",
                f"**テキスト構成評価**: {analysis_detail.get('text_assessment', 'N/A')}",
                f"- スコア: {analysis_detail.get('text_score', 'N/A')}/10",
                "",
                f"**ファーストビュー評価**: {analysis_detail.get('first_view_assessment', 'N/A')}",
                f"- スコア: {analysis_detail.get('first_view_score', 'N/A')}/10",
                "",
                f"**信頼形成評価**: {analysis_detail.get('trust_elements', 'N/A')}",
                f"- スコア: {analysis_detail.get('trust_score', 'N/A')}/10",
                "",
            ])
            
            key_issues = analysis_detail.get("key_issues", [])
            if key_issues:
                lines.extend([
                    "### 主な課題",
                    "",
                ])
                for idx, issue in enumerate(key_issues, 1):
                    lines.append(f"{idx}. {issue}")
                lines.append("")
        
        lines.extend(["---", ""])
    
    # 競合・ベストプラクティス調査
    industry_analysis = sections.get("競合・ベストプラクティス調査", {})
    if industry_analysis:
        lines.extend([
            "## 競合・ベストプラクティス調査",
            "",
            f"**業界コンテキスト**: {industry_analysis.get('industry_context', 'N/A')}",
            "",
        ])
        
        success_patterns = industry_analysis.get("success_patterns", [])
        if success_patterns:
            lines.extend([
                "### 成功パターン",
                "",
            ])
            for pattern in success_patterns[:5]:
                lines.extend([
                    f"#### {pattern.get('company', 'N/A')}",
                    f"{pattern.get('strategy', 'N/A')}",
                    "",
                ])
        
        common_factors = industry_analysis.get("common_success_factors", [])
        if common_factors:
            lines.extend([
                "### 共通成功要素",
                "",
            ])
            for factor in common_factors:
                lines.append(f"- {factor}")
            lines.append("")
        
        differences = industry_analysis.get("differentiation_opportunities", [])
        if differences:
            lines.extend([
                "### 差別化機会",
                "",
            ])
            for diff in differences:
                lines.append(f"- {diff}")
            lines.append("")
        
        lines.extend(["---", ""])
    
    # 改善案
    improvement = sections.get("改善案", {})
    if improvement:
        lines.extend([
            "## 改善案（複数パターン）",
            "",
            improvement.get("summary", ""),
            "",
        ])
        
        patterns = improvement.get("patterns", [])
        for idx, pattern in enumerate(patterns[:5], 1):
            lines.extend([
                f"### 改善パターン {idx}: {pattern.get('title', '未定義')}",
                "",
                f"**説明**: {pattern.get('description', 'N/A')}",
                "",
                f"- **カテゴリ**: {pattern.get('category', 'N/A')}",
                f"- **優先度**: {pattern.get('priority', 'N/A')}",
                f"- **実装難度**: {pattern.get('effort', 'N/A')}",
                "",
            ])
            
            expected = pattern.get("expected_impact", {})
            if expected:
                lines.extend([
                    "**期待効果**:",
                    "",
                ])
                for key, value in expected.items():
                    lines.append(f"- {key}: {value}")
                lines.append("")
            
            implementation = pattern.get("implementation_details", [])
            if implementation:
                lines.extend([
                    "**実装ステップ**:",
                    "",
                ])
                for step_idx, step in enumerate(implementation[:5], 1):
                    lines.append(f"{step_idx}. {step}")
                lines.append("")
            
            lines.append("")
        
        lines.extend(["---", ""])
    
    # A/Bテスト設計
    ab_tests = sections.get("A/Bテスト設計", {})
    if ab_tests:
        lines.extend([
            "## A/Bテスト設計と実行プラン",
            "",
        ])
        
        test_plan = ab_tests.get("test_plan", {})
        if test_plan:
            phase_1 = test_plan.get("phase_1_quick_wins", [])
            if phase_1:
                lines.extend([
                    "### Phase 1: クイックウィン（短期テスト）",
                    "",
                ])
                for test in phase_1[:5]:
                    lines.extend([
                        f"**{test.get('title', 'N/A')}**",
                        f"- ID: {test.get('test_id', 'N/A')}",
                        f"- 期間: {test.get('duration_days', 'N/A')}日",
                        f"- 優先度: {test.get('priority', 'N/A')}",
                        "",
                    ])
            
            measurement = ab_tests.get("measurement_framework", {})
            if measurement:
                lines.extend([
                    "### 測定フレームワーク",
                    "",
                    "**主要指標**:",
                    "",
                ])
                for metric in measurement.get("primary_metrics", []):
                    lines.append(f"- {metric}")
                lines.extend([
                    "",
                    "**補助指標**:",
                    "",
                ])
                for metric in measurement.get("secondary_metrics", []):
                    lines.append(f"- {metric}")
                lines.extend([
                    "",
                    f"**統計閾値**: {measurement.get('statistical_threshold', 'N/A')}",
                    "",
                ])
        
        lines.extend(["---", ""])
    
    # 期待される効果
    expected_effects = sections.get("期待される効果", {})
    if expected_effects:
        lines.extend([
            "## 期待される効果（定量予測）",
            "",
        ])
        
        baseline = expected_effects.get("baseline_metrics", {})
        if baseline:
            lines.extend([
                "### 基準メトリクス",
                "",
            ])
            for metric, value in baseline.items():
                lines.append(f"- {metric}: {value}")
            lines.append("")
        
        impacts = expected_effects.get("predicted_impacts", [])
        if impacts:
            lines.extend([
                "### 改善インパクト予測",
                "",
            ])
            for impact in impacts[:3]:
                lines.extend([
                    f"#### {impact.get('pattern_title', 'N/A')}",
                    "",
                ])
                predicted = impact.get("predicted_impact", {})
                if isinstance(predicted, dict):
                    for key, value in predicted.items():
                        if key not in ["status", "error"]:
                            lines.append(f"- {key}: {value}")
                lines.append("")
        
        cumulative = expected_effects.get("cumulative_impact", {})
        if cumulative and isinstance(cumulative, dict):
            lines.extend([
                "### 累積インパクト",
                "",
            ])
            if cumulative.get("status") != "error":
                for key, value in cumulative.items():
                    if key not in ["status", "error"]:
                        lines.append(f"- {key}: {value}")
            lines.append("")
    
    lines.extend([
        "---",
        "",
        "**レポート生成時刻**: 自動生成",
        "**注記**: このレポートはAIによる自動分析結果です。実装前に専門家による検証を推奨します。",
    ])
    
    return "\n".join(lines)


def configure_logger():
    logger = logging.getLogger("marketing_auto_analyzer")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    if not logger.handlers:
        logger.addHandler(handler)
    return logger


def filter_site_results_by_score(site_results: list[dict], min_score: int | None):
    if min_score is None:
        return site_results
    return [r for r in site_results if (r.get("score") is not None and r.get("score") >= min_score)]


def generate_strategic_lp_analyses(site_results: list[dict], skip_llm: bool):
    from src.site_results_service import get_strategic_analysis_input, is_actionable_site_result
    from src.strategic_lp_analysis import generate_strategic_lp_analysis_report

    strategic_analyses = []
    if skip_llm:
        return strategic_analyses

    actionable_results = [r for r in site_results if is_actionable_site_result(r)]
    if not actionable_results:
        return strategic_analyses

    weakest_site = min(actionable_results, key=lambda x: x.get("score", 0))
    strategic_inputs = get_strategic_analysis_input(weakest_site)

    for page in strategic_inputs[:1]:
        page_url = page.get("url", weakest_site.get("url"))
        try:
            html = page.get("html", "")
            body_excerpt = page.get("excerpt", "")
            service_description = page.get("service_description", "")
            if not service_description:
                findings = page.get("findings", [])
                service_description = findings[0] if findings else ""

            strategic_analysis = generate_strategic_lp_analysis_report(
                url=page_url,
                html=html,
                body_excerpt=body_excerpt,
                service_description=service_description,
            )
            strategic_analyses.append(strategic_analysis)
        except Exception as e:
            logging.getLogger("marketing_auto_analyzer").warning(
                f"Strategic LP analysis failed for {page_url}: {e}"
            )

    return strategic_analyses


def save_json_summary(filename: str, data: dict):
    from src.report import save_report_json
    try:
        return save_report_json(filename, data, latest=True)
    except Exception as exc:
        logging.getLogger("marketing_auto_analyzer").warning(f"Could not save JSON summary: {exc}")
        return ""


def collect_and_store_site_results(max_site_pages: int) -> list[dict]:
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

def run_analysis(
    force_reload: bool = False,
    max_site_pages: int = TARGET_SITE_MAX_PAGES,
    skip_llm: bool = False,
    skip_site_analysis: bool = False,
    enable_forecasting: bool = False,
    enable_impact_analysis: bool = False,
    initiatives: list[dict] | None = None,
    dry_run: bool = False,
    min_site_score: int | None = None,
    save_json: bool = False,
):
    logger = configure_logger()

    init_state()
    load_result = load_csv_to_duckdb(force=force_reload)
    df = read_mart()
    snapshot = build_analysis_snapshot(df)
    recommendations = generate_recommendations(
        snapshot["channels"],
        snapshot["diagnostics"],
        snapshot["alerts"],
    )

    impact_analysis_result = None
    if enable_forecasting:
        try:
            snapshot = add_forecasts_to_analysis(snapshot, df)
            logger.info("Forecasting completed successfully")
        except Exception as e:
            logger.warning(f"Forecasting failed: {e}")

    if enable_impact_analysis and initiatives:
        try:
            impact_analysis_result = analyze_initiative_impact(df, initiatives)
            count = len(impact_analysis_result.get("impact_results", []))
            logger.info(f"Initiative Impact Analysis: {count} initiatives analyzed")
        except Exception as e:
            logger.warning(f"Impact analysis failed: {e}")

    if enable_forecasting or enable_impact_analysis:
        try:
            recommendations = enhance_recommendations_with_quantified_impact(
                recommendations,
                df,
                channels_df=snapshot.get("channels"),
                impact_analysis=impact_analysis_result,
            )
            logger.info(f"Enhanced {len(recommendations)} recommendations with quantified impact")
        except Exception as e:
            logger.warning(f"Recommendation enhancement failed: {e}")

    site_results = []
    compact_urls: list[dict] = []
    strategic_analyses: list[str] = []

    if not dry_run and not skip_site_analysis:
        site_results = collect_and_store_site_results(max_site_pages)
        if min_site_score is not None:
            site_results = filter_site_results_by_score(site_results, min_score=min_site_score)
        compact_urls = compact_site_results(site_results)
        strategic_analyses = generate_strategic_lp_analyses(site_results, skip_llm)
    else:
        logger.info("Site analysis skipped: dry_run=%s skip_site_analysis=%s", dry_run, skip_site_analysis)

    summary = None
    deep_analysis = None
    report_path = None

    if not skip_llm:
        summary = generate_summary(
            snapshot,
            recommendations,
            compact_urls,
            site_results,
            skip_llm=skip_llm,
        )
        deep_analysis = generate_deep_analysis(
            snapshot,
            recommendations,
            site_results,
            skip_llm=skip_llm,
        )

    if not dry_run:
        report = render_marketing_report(
            snapshot=snapshot,
            recommendations=recommendations,
            url_results=site_results,
            llm_summary=summary or "LLM処理をスキップしました",
            deep_analysis=deep_analysis,
        )
        report_path = save_report("manual_analysis", report)
        logger.info("Report saved: %s", report_path)
    else:
        logger.info("Dry run: report generation skipped")

    if save_json:
        json_path = save_json_summary(
            "manual_analysis",
            {
                "snapshot": snapshot,
                "recommendations": recommendations,
                "site_results": site_results,
                "strategic_analyses": strategic_analyses,
                "summary": summary,
                "deep_analysis": deep_analysis,
                "load_result": load_result,
            },
        )
        logger.info("JSON summary saved: %s", json_path)

    return {
        "load_result": load_result,
        "snapshot": snapshot,
        "recommendations": recommendations,
        "site_results": site_results,
        "compact_urls": compact_urls,
        "summary": summary,
        "deep_analysis": deep_analysis,
        "report_path": report_path,
        "strategic_analyses": strategic_analyses,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-reload", action="store_true")
    parser.add_argument("--max-site-pages", type=int, default=TARGET_SITE_MAX_PAGES)
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--skip-site-analysis", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline without saving reports or invoking crawling/LLM outputs")
    parser.add_argument("--enable-forecasting", action="store_true", help="Enable predictive analytics and forecasting")
    parser.add_argument("--enable-impact-analysis", action="store_true", help="Enable initiative impact analysis")
    parser.add_argument("--initiatives", type=str, default="", help="JSON string with initiatives to analyze")
    parser.add_argument("--min-site-score", type=int, default=None, help="最低評価サイトスコアを指定して対象を絞る（0-100）")
    parser.add_argument("--save-json", action="store_true", help="Save a JSON summary alongside markdown output")
    args = parser.parse_args()

    initiatives_json = None
    if args.enable_impact_analysis and args.initiatives:
        try:
            initiatives_json = json.loads(args.initiatives)
        except json.JSONDecodeError as e:
            raise SystemExit(f"Invalid --initiatives JSON: {e}")

    result = run_analysis(
        force_reload=args.force_reload,
        max_site_pages=args.max_site_pages,
        skip_llm=args.skip_llm,
        skip_site_analysis=args.skip_site_analysis,
        enable_forecasting=args.enable_forecasting,
        enable_impact_analysis=args.enable_impact_analysis,
        initiatives=initiatives_json,
        dry_run=args.dry_run,
        min_site_score=args.min_site_score,
        save_json=args.save_json,
    )

    print(f"CSV同期: {result['load_result'].get('status')}")
    print(f"対象サイト数: {len(result['site_results'])}")
    if result["report_path"]:
        print(f"分析レポートを生成しました: {result['report_path']}")
    if result["strategic_analyses"]:
        for idx, analysis_markdown in enumerate(result["strategic_analyses"]):
            try:
                strategic_report = _render_strategic_lp_analysis_report(analysis_markdown)
                strategic_path = save_report(f"lp_strategy_analysis_{idx+1}", strategic_report)
                print(f"戦略的LP分析レポート生成: {strategic_path}")
            except Exception as e:
                print(f"Strategic report rendering failed: {e}")

