"""
競合・ベストプラクティス分析エンジン
関連サイトを自動調査し、業界の成功例を抽出・分析
"""

import json
import logging
from typing import Optional

from src.llm_client import ask_llm

logger = logging.getLogger(__name__)


def generate_competitor_search_queries(target_url: str, target_service: str) -> list[str]:
    """
    対象URLとサービスから、競合調査用の検索クエリを生成
    
    例：
    - "マニュアル作成代行" -> ["マニュアル作成代行", "マニュアル制作支援", "マニュアル作成サービス", ...]
    """
    
    prompt = f"""
あなたはマーケティング専門家です。以下のサービスについて、競合他社やベストプラクティス例を調査するための検索クエリを5～8個生成してください。

【対象サービス】
URL: {target_url}
サービス概要: {target_service}

【要件】
- 競合他社のサービスサイトが見つかりやすいクエリ
- 業界のベストプラクティス例が見つかるクエリ
- 成功事例が見つかるクエリ

【出力形式】
JSON形式で以下を返してください：
{{
    "queries": [
        {{"query": "検索クエリ1", "intent": "競合調査" or "ベストプラクティス" or "成功事例"}},
        ...
    ]
}}
"""
    
    try:
        response = ask_llm(prompt)
        result = json.loads(response)
        return [q["query"] for q in result.get("queries", [])]
    except Exception as e:
        logger.error(f"Failed to generate competitor search queries: {e}")
        # フォールバック
        return [
            "マニュアル作成代行 成功事例",
            "LP最適化 BtoB",
            "ランディングページ改善",
        ]


def analyze_competitor_pattern(competitor_url: str, target_industry: str) -> dict:
    """
    競合サイトのパターンを分析（実際にクロールはせず、LLMベースで分析戦略を提案）
    """
    
    prompt = f"""
あなたはLP最適化のスペシャリストです。以下の競合サイトをベンチマーク対象として、分析戦略を提案してください。

【競合サイト】
URL: {competitor_url}
業界: {target_industry}

【分析対象項目】
1. H1・キャッチコピーの戦略（何を訴求しているか）
2. ファーストビューの構成（視覚的工夫は何か）
3. CTA戦略（どのように行動を促しているか）
4. 信頼形成要素（何で信頼を形成しているか）
5. テキスト量・情報構成（スクロール負荷への工夫）

【出力形式】
JSON形式で以下を返してください：
{{
    "competitor_url": "{competitor_url}",
    "analysis_strategy": {{
        "h1_strategy": "推定されるH1戦略の説明",
        "cta_strategy": "推定されるCTA戦略",
        "trust_strategy": "推定される信頼形成戦略",
        "differentiation": "想定される差別化ポイント"
    }},
    "best_practices": [
        "ベストプラクティス1",
        "ベストプラクティス2",
        ...
    ],
    "warnings": ["注意点1", "注意点2"]
}}
"""
    
    try:
        response = ask_llm(prompt)
        return json.loads(response)
    except Exception as e:
        logger.error(f"Failed to analyze competitor pattern: {e}")
        return {
            "competitor_url": competitor_url,
            "status": "error",
            "error": str(e)
        }


def generate_improvement_patterns(
    target_url: str,
    lp_analysis: dict,
    industry_context: str,
    num_patterns: int = 3
) -> list[dict]:
    """
    複数の改善案パターンを生成し、優先度付けして返す
    """
    
    prompt = f"""
あなたはLPコンバージョン最適化（CRO）の専門家です。以下の情報に基づいて、複数の改善案を生成してください。

【対象LP】
URL: {target_url}
業界: {industry_context}

【現状分析結果】
{json.dumps(lp_analysis, ensure_ascii=False, indent=2)[:2000]}

【要件】
- 複数の改善パターンを提案してください（少なくとも{num_patterns}パターン）
- 各パターンは実装容易性（小/中/大）と期待効果を明示してください
- 優先度をつけてください（高/中/低）
- 各パターンはA/Bテスト対象になるべきです
- 業界のベストプラクティスに基づいてください

【出力形式】
JSON形式で以下を返してください：
{{
    "improvement_patterns": [
        {{
            "id": "pattern_001",
            "title": "改善パターンのタイトル",
            "description": "詳細な説明（5-10文）",
            "category": "messaging|cta|structure|visual|trust",
            "priority": "high|medium|low",
            "effort": "small|medium|large",
            "expected_impact": {{
                "bounce_rate": "-20%",
                "ctr": "+50%",
                "cvr": "+15%"
            }},
            "implementation_details": [
                "実装STEP1",
                "実装STEP2",
                ...
            ],
            "ab_test_design": {{
                "test_name": "A/Bテスト名",
                "variant_a": "現状（コントロール）",
                "variant_b": "改善案",
                "metrics": ["直帰率", "CTA CTR", "CVR"],
                "sample_size": "最低〇〇セッション推奨",
                "duration_days": "推奨テスト期間（日）"
            }}
        }},
        ...
    ]
}}
"""
    
    try:
        response = ask_llm(prompt)
        result = json.loads(response)
        return result.get("improvement_patterns", [])
    except Exception as e:
        logger.error(f"Failed to generate improvement patterns: {e}")
        return []


def generate_ab_test_plan(lp_analysis: dict, improvement_patterns: list[dict]) -> dict:
    """
    複数の改善案に基づいて、A/Bテスト実行計画を生成
    """
    
    prompt = f"""
あなっはA/Bテスト設計の専門家です。以下の改善案に基づいて、A/Bテスト実行計画を設計してください。

【現状分析】
{json.dumps(lp_analysis, ensure_ascii=False, indent=2)[:1000]}

【改善案一覧】
{json.dumps([{k: v for k, v in p.items() if k != 'ab_test_design'} for p in improvement_patterns[:3]], ensure_ascii=False, indent=2)}

【要件】
- 最初に実施すべきテストから順序付けしてください
- 並列実施可能なテストと直列化が必要なテストを区別してください
- 各テストの統計的有意性判定基準を明示してください
- テスト期間が短いものから提案してください

【出力形式】
JSON形式で以下を返してください：
{{
    "test_plan": {{
        "phase_1_quick_wins": [
            {{
                "test_id": "TEST_001",
                "title": "テストタイトル",
                "duration_days": 7-14,
                "priority": "high|medium|low",
                "success_criteria": {{"metric": "threshold"}},
                "execution_order": 1,
                "dependencies": []
            }}
        ],
        "phase_2_core_tests": [...]
    }},
    "measurement_framework": {{
        "primary_metrics": ["直帰率", "CTA CTR", "CVR"],
        "secondary_metrics": ["滞在時間", "スクロール深度"],
        "statistical_threshold": "95%信頼度, p<0.05"
    }}
}}
"""
    
    try:
        response = ask_llm(prompt)
        return json.loads(response)
    except Exception as e:
        logger.error(f"Failed to generate A/B test plan: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def predict_improvement_impact(
    baseline_metrics: dict,
    improvement_pattern: dict,
    industry_benchmarks: Optional[dict] = None
) -> dict:
    """
    改善のインパクトを定量予測
    
    baseline_metrics: {"bounce_rate": 65, "ctr": 5, "cvr": 2.5}
    improvement_pattern: {"expected_impact": {"bounce_rate": "-20%", "ctr": "+50%"}}
    """
    
    prompt = f"""
あなたは数据分析とマーケティング最適化の専門家です。以下の改善実施による定量的インパクトを予測してください。

【現状メトリクス】
{json.dumps(baseline_metrics, ensure_ascii=False, indent=2)}

【改善パターンの期待効果】
{json.dumps(improvement_pattern.get('expected_impact', {}), ensure_ascii=False, indent=2)}

【改善内容】
{improvement_pattern.get('description', 'N/A')}

業界ベンチマーク: {industry_benchmarks or '利用可能なベンチマークなし'}

【要件】
- 改善実施後の予測メトリクスを計算してください
- 実現可能性（低/中/高）を明示してください
- 前提条件を列挙してください
- 類似事例があれば言及してください

【出力形式】
JSON形式で以下を返してください：
{{
    "predicted_metrics": {{
        "bounce_rate": 予測値,
        "ctr": 予測値,
        "cvr": 予測値
    }},
    "improvement_vs_baseline": {{
        "bounce_rate_lift": "削減率（%）",
        "ctr_lift": "向上率（%）",
        "revenue_impact": "売上への想定インパクト"
    }},
    "feasibility": "low|medium|high",
    "confidence_level": "低/中/高",
    "assumptions": ["前提1", "前提2"],
    "risk_factors": ["リスク1", "リスク2"]
}}
"""
    
    try:
        response = ask_llm(prompt)
        return json.loads(response)
    except Exception as e:
        logger.error(f"Failed to predict improvement impact: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
