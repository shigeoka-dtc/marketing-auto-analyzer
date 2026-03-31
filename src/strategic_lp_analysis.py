"""
LP戦略詳細分析レポートジェネレータ
ユーザー提供レベルの深掘り分析を自動生成
"""

import json
import logging
from typing import Optional

from src.lp_deep_analysis import analyze_lp_deep
from src.competitor_analysis import (
    generate_improvement_patterns,
    generate_ab_test_plan,
    predict_improvement_impact,
)
from src.llm_client import ask_llm

logger = logging.getLogger(__name__)


def generate_strategic_lp_analysis_report(
    url: str,
    html: str,
    body_excerpt: str = "",
    service_description: str = "",
) -> dict:
    """
    LP戦略的な深掘り分析レポートを生成
    ユーザー提供の分析（LP構造分析 → 競合調査 → 改善案 → ABテスト設計）に相当するレベルの分析を返す
    """
    
    logger.info(f"Generating strategic LP analysis for {url}")
    
    report = {
        "url": url,
        "report_type": "strategic_lp_analysis",
        "sections": {
            "現状分析_LP構造と課題": None,
            "競合・ベストプラクティス調査": None,
            "改善案": None,
            "A/Bテスト設計": None,
            "期待される効果": None,
        }
    }
    
    # =========================================================================
    # 1. LP深掘り分析（LP構造と課題）
    # =========================================================================
    logger.info(f"Step 1: LP deep analysis for {url}")
    lp_analysis = analyze_lp_deep(url, html, body_excerpt)
    
    if lp_analysis.get("status") == "error":
        logger.error(f"LP analysis failed: {lp_analysis.get('error')}")
        return {
            "url": url,
            "status": "error",
            "error": lp_analysis.get("error")
        }
    
    report["sections"]["現状分析_LP構造と課題"] = {
        "lp_elements": lp_analysis.get("lp_elements"),
        "analysis": lp_analysis.get("analysis"),
    }
    
    # =========================================================================
    # 2. 競合・ベストプラクティス調査
    # =========================================================================
    logger.info(f"Step 2: Competitor and best practice analysis for {url}")
    industry_analysis = _generate_industry_analysis(service_description or "")
    report["sections"]["競合・ベストプラクティス調査"] = industry_analysis
    
    # =========================================================================
    # 3. 改善案生成（複数パターン + 優先度）
    # =========================================================================
    logger.info(f"Step 3: Generating improvement patterns for {url}")
    improvement_patterns = generate_improvement_patterns(
        target_url=url,
        lp_analysis=lp_analysis.get("analysis", {}),
        industry_context=industry_analysis.get("industry_context", ""),
        num_patterns=3
    )
    
    report["sections"]["改善案"] = {
        "patterns": improvement_patterns,
        "summary": _summarize_improvement_patterns(improvement_patterns),
    }
    
    # =========================================================================
    # 4. A/Bテスト設計
    # =========================================================================
    logger.info(f"Step 4: Designing A/B tests for {url}")
    ab_test_plan = generate_ab_test_plan(
        lp_analysis=lp_analysis.get("analysis", {}),
        improvement_patterns=improvement_patterns
    )
    
    report["sections"]["A/Bテスト設計"] = ab_test_plan
    
    # =========================================================================
    # 5. 期待される効果（定量予測）
    # =========================================================================
    logger.info(f"Step 5: Predicting improvement impact for {url}")
    baseline_metrics = _extract_baseline_metrics(lp_analysis.get("analysis", {}))
    predicted_impacts = []
    
    for pattern in improvement_patterns[:3]:  # 上位3パターンのインパクト予測
        impact = predict_improvement_impact(
            baseline_metrics=baseline_metrics,
            improvement_pattern=pattern,
        )
        predicted_impacts.append({
            "pattern_id": pattern.get("id"),
            "pattern_title": pattern.get("title"),
            "predicted_impact": impact,
        })
    
    report["sections"]["期待される効果"] = {
        "baseline_metrics": baseline_metrics,
        "predicted_impacts": predicted_impacts,
        "cumulative_impact": _calculate_cumulative_impact(predicted_impacts),
    }
    
    # =========================================================================
    # 最終要約
    # =========================================================================
    report["executive_summary"] = _generate_executive_summary(report)
    report["status"] = "success"
    
    return report


def _generate_industry_analysis(service_description: str) -> dict:
    """業界分析・ベストプラクティス調査を生成"""
    
    prompt = f"""
あなたはマーケティング業界のスペシャリストです。以下のサービス業界について、ベストプラクティスと競合動向を分析してください。

【対象サービス】
{service_description or "BtoB SaaS / サービス提供企業"}

【分析項目】
1. 業界のLP成功パターン（3～4例）
2. 共通する成功要素
3. 一般的な課題
4. 競合との差別化ポイント

【出力形式】
JSON形式で以下を返してください：
{{
    "industry_context": "業界の簡潔な説明",
    "success_patterns": [
        {{
            "company": "企業例（仮名可）",
            "strategy": "戦略の説明",
            "key_elements": ["要素1", "要素2"]
        }}
    ],
    "common_success_factors": [
        "成功要素1",
        "成功要素2",
        ...
    ],
    "typical_challenges": [
        "課題1",
        "課題2"
    ],
    "differentiation_opportunities": [
        "差別化機会1",
        "差別化機会2"
    ]
}}
"""
    
    try:
        response = ask_llm(prompt)
        return json.loads(response)
    except Exception as e:
        logger.error(f"Failed to generate industry analysis: {e}")
        return {
            "industry_context": "業界分析（パース失敗）",
            "success_patterns": [],
            "common_success_factors": [],
            "typical_challenges": [],
            "differentiation_opportunities": [],
        }


def _summarize_improvement_patterns(patterns: list[dict]) -> str:
    """改善案を要約"""
    if not patterns:
        return "改善案の生成に失敗しました"
    
    high_priority = [p for p in patterns if p.get("priority") == "high"]
    
    summary = f"優先度の高い改善案は{len(high_priority)}件。"
    if high_priority:
        summary += f"最優先は「{high_priority[0].get('title')}」です。"
    
    return summary


def _extract_baseline_metrics(analysis: dict) -> dict:
    """分析結果から基本メトリクスを抽出"""
    return {
        "h1_clarity_score": analysis.get("h1_score", 5),
        "cta_effectiveness_score": analysis.get("cta_score", 5),
        "text_structure_score": analysis.get("text_score", 5),
        "first_view_score": analysis.get("first_view_score", 5),
        "trust_score": analysis.get("trust_score", 5),
        "overall_score": analysis.get("overall_score", 25),
    }


def _calculate_cumulative_impact(predicted_impacts: list[dict]) -> dict:
    """複数改善案の累積インパクトを計算"""
    
    if not predicted_impacts:
        return {
            "total_improvement_potential": "分析不可",
            "recommendation": "改善案の実装順序に従って段階的に実施してください"
        }
    
    prompt = f"""
以下の複数改善案による累積的なインパクトを予測してください。

【個別改善のインパクト】
{json.dumps([p.get('predicted_impact', {}) for p in predicted_impacts[:3]], ensure_ascii=False, indent=2)}

【要件】
- 各改善は独立していると仮定
- 累積効果を計算（相互作用を考慮）
- 実現可能性を踏まえた調整

【出力形式】
JSON形式で以下を返してください：
{{
    "cumulative_bounce_rate_reduction": "想定削減率",
    "cumulative_ctr_improvement": "想定向上率",
    "revenue_impact": "売上インパクトの想定",
    "implementation_timeline": "実装期間",
    "priority_sequence": ["最優先", "次点", "その後"],
    "key_success_factors": ["成功要因1", "成功要因2"]
}}
"""
    
    try:
        response = ask_llm(prompt)
        return json.loads(response)
    except Exception as e:
        logger.error(f"Failed to calculate cumulative impact: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def _generate_executive_summary(report: dict) -> str:
    """レポート全体のエグゼクティブサマリーを生成"""
    
    lp_analysis = report.get("sections", {}).get("現状分析_LP構造と課題", {})
    improvement_patterns = report.get("sections", {}).get("改善案", {})
    
    overall_score = lp_analysis.get("analysis", {}).get("overall_score", "不明")
    pattern_count = len(improvement_patterns.get("patterns", []))
    
    return f"""
【戦略的LP分析サマリー】

現状LP総合スコア: {overall_score}/10

主な課題: {', '.join(lp_analysis.get('analysis', {}).get('key_issues', [])[:3])}

提案される改善パターン: {pattern_count}件

期待される改善:
- 直帰率の削減
- CTA到達率の向上
- コンバージョン率の改善

次のステップ: 優先度の高い改善から段階的に実装し、各々についてA/Bテストを実施してください
"""
