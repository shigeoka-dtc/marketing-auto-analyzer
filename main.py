import argparse
import os
import json

from src.analysis import build_analysis_snapshot, read_mart
from src.deep_analysis import generate_deep_analysis
from src.etl import load_csv_to_duckdb
from src.recommend import generate_recommendations
from src.recommend_enhanced import enhance_recommendations_with_quantified_impact
from src.forecasting import add_forecasts_to_analysis
from src.impact_analysis import analyze_initiative_impact
from src.report import render_marketing_report, save_report
from src.site_results_service import (
    build_site_error_result,
    compact_site_results,
    get_site_results_summary,
    get_strategic_analysis_input,
    is_actionable_site_result,
)
from src.state import init_state, upsert_site_analysis_result
from src.summary_service import generate_summary
from src.url_analyzer import analyze_site
from src.url_targets import load_target_urls
from src.strategic_lp_analysis import generate_strategic_lp_analysis_report

TARGET_SITE_MAX_PAGES = int(os.getenv("TARGET_SITE_MAX_PAGES", "5"))


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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-reload", action="store_true")
    parser.add_argument("--max-site-pages", type=int, default=TARGET_SITE_MAX_PAGES)
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--enable-forecasting", action="store_true", help="Enable predictive analytics and forecasting")
    parser.add_argument("--enable-impact-analysis", action="store_true", help="Enable initiative impact analysis")
    parser.add_argument("--initiatives", type=str, default="", help="JSON string with initiatives to analyze")
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
    
    # Add forecasting if enabled
    impact_analysis_result = None
    if args.enable_forecasting:
        try:
            snapshot = add_forecasts_to_analysis(snapshot, df)
        except Exception as e:
            print(f"Warning: Forecasting failed: {e}")
    
    # Add impact analysis if enabled
    if args.enable_impact_analysis and args.initiatives:
        try:
            initiatives = json.loads(args.initiatives)
            impact_analysis_result = analyze_initiative_impact(df, initiatives)
            print(f"Initiative Impact Analysis: {len(impact_analysis_result.get('impact_results', []))} initiatives analyzed")
        except Exception as e:
            print(f"Warning: Impact analysis failed: {e}")
    
    # Enhance recommendations with quantified impact
    if args.enable_forecasting or args.enable_impact_analysis:
        try:
            recommendations = enhance_recommendations_with_quantified_impact(
                recommendations,
                df,
                channels_df=snapshot.get("channels"),
                impact_analysis=impact_analysis_result,
            )
            print(f"Enhanced {len(recommendations)} recommendations with quantified impact")
        except Exception as e:
            print(f"Warning: Recommendation enhancement failed: {e}")
    
    site_results = collect_and_store_site_results(args.max_site_pages)
    compact_urls = compact_site_results(site_results)

# Generate strategic LP analysis for the most critical site
strategic_analyses = []
if not args.skip_llm:
    try:
        actionable_results = [r for r in site_results if is_actionable_site_result(r)]
        if actionable_results:
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
                        if findings:
                            service_description = findings[0]

                    strategic_analysis = generate_strategic_lp_analysis_report(
                        url=page_url,
                        html=html,
                        body_excerpt=body_excerpt,
                        service_description=service_description,
                    )
                    strategic_analyses.append(strategic_analysis)
                    print(f"Strategic LP analysis generated for: {page_url}")
                except Exception as e:
                    print(f"Strategic LP analysis failed for {page_url}: {e}")
    except Exception as e:
        print(f"Warning: Strategic LP analysis skipped: {e}")
    
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
    
    # Save strategic LP analysis reports if generated
    if strategic_analyses:
        for idx, analysis in enumerate(strategic_analyses):
            try:
                strategic_report = _render_strategic_lp_analysis_report(analysis)
                strategic_path = save_report(f"lp_strategy_analysis_{idx+1}", strategic_report)
                print(f"戦略的LP分析レポート生成: {strategic_path}")
            except Exception as e:
                print(f"Strategic report rendering failed: {e}")
