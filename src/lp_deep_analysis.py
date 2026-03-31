"""
LP深掘り分析エンジン
見出し、CTA、テキスト、構成などの詳細要素を分析し、ユーザー提供レベルの詳細な分析を生成
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup

from src.llm_client import ask_llm

logger = logging.getLogger(__name__)


@dataclass
class LPElement:
    """LP要素の抽出結果"""
    h1: Optional[str]
    h2_list: list[str]
    main_message: Optional[str]
    cta_buttons: list[dict]
    text_length: int
    paragraph_count: int
    section_count: int
    images_count: int
    first_view_elements: list[str]


def extract_lp_elements(html: str) -> LPElement:
    """HTMLからLP要素を詳細に抽出"""
    soup = BeautifulSoup(html, "html.parser")
    
    # H1を取得
    h1_elem = soup.find("h1")
    h1_text = (h1_elem.get_text(strip=True) if h1_elem else None) or ""
    
    # H2一覧を取得
    h2_list = [h2.get_text(strip=True) for h2 in soup.find_all("h2")[:10]]
    
    # メインメッセージ（通常はH1直後のテキスト）
    main_message = None
    if h1_elem:
        next_elem = h1_elem.find_next(["p", "div"])
        if next_elem:
            main_message = next_elem.get_text(strip=True)[:200]
    
    # CTAボタン抽出
    cta_buttons = []
    for link in soup.find_all("a"):
        link_text = link.get_text(strip=True)
        # CTA的なものを判定
        cta_keywords = ["申込", "問い合わせ", "相談", "ダウンロード", "資料", "お問合せ"]
        if any(kw in link_text for kw in cta_keywords) and len(link_text) < 50:
            cta_buttons.append({
                "text": link_text,
                "href": link.get("href", "#"),
                "color_class": link.get("class", []),
            })
    cta_buttons = cta_buttons[:10]  # 最大10個
    
    # テキスト量と段落数
    body_text = soup.get_text(separator=" ", strip=True)
    text_length = len(body_text)
    paragraph_count = len(soup.find_all("p"))
    
    # セクション数（h2の数 + その他セクション）
    section_count = len(soup.find_all(["h2", "section", "article"]))
    
    # 画像数
    images_count = len(soup.find_all("img"))
    
    # ファーストビュー要素（h1の直下にある主要要素）
    first_view_elements = []
    if h1_elem:
        parent = h1_elem.find_parent(["div", "section", "header"])
        if parent:
            for elem in parent.find_all(["h2", "p", "img", "button"], recursive=True)[:5]:
                first_view_elements.append(elem.name)
    
    return LPElement(
        h1=h1_text,
        h2_list=h2_list,
        main_message=main_message,
        cta_buttons=cta_buttons,
        text_length=text_length,
        paragraph_count=paragraph_count,
        section_count=section_count,
        images_count=images_count,
        first_view_elements=first_view_elements,
    )


def _build_lp_analysis_prompt(url: str, lp_element: LPElement, body_excerpt: str) -> str:
    """LP詳細分析用プロンプトを構築"""
    return f"""
あなたはLP（ランディングページ）最適化の専門家です。以下のLPを詳細に分析してください。

対象URL: {url}

【抽出されたLP要素】
- H1: {lp_element.h1}
- H2一覧: {str(lp_element.h2_list[:5])}
- メインメッセージ: {lp_element.main_message}
- CTAボタン数: {len(lp_element.cta_buttons)}
  - CTAテキスト: {[c['text'] for c in lp_element.cta_buttons[:5]]}
- テキスト総量: {lp_element.text_length}文字
- 段落数: {lp_element.paragraph_count}
- セクション数: {lp_element.section_count}
- 画像数: {lp_element.images_count}

【ページ本文の先頭部分】
{body_excerpt[:500]}

【分析項目】
1. H1/見出しの具体性評価（ユーザーの検索意図にマッチしているか、サービスが直感的に伝わるか）
2. CTAの効果性評価（目立っているか、分散していないか、文言は行動を促しているか）
3. テキスト量と情報構成の評価（スクロール負荷、重要情報の優先順位）
4. ファーストビューの構成評価（訪問者の興味を引きつけられるか）
5. 信頼形成要素の有無（実績、事例、数字の可視化）

【出力形式】
JSON形式で以下を含めてください：
{{
    "h1_assessment": "H1の具体性と効果性の評価（3-5文）",
    "h1_score": 1-10のスコア,
    "cta_assessment": "CTAの効果性の評価",
    "cta_score": 1-10のスコア,
    "text_assessment": "テキスト量と構成の評価",
    "text_score": 1-10のスコア,
    "first_view_assessment": "ファーストビューの評価",
    "first_view_score": 1-10のスコア,
    "trust_elements": "信頼形成要素の評価と改善提案",
    "trust_score": 1-10のスコア,
    "overall_score": 全体スコア（1-10）,
    "key_issues": ["課題1", "課題2", "課題3"],
    "improvement_patterns": [
        {{
            "title": "改善パターン1",
            "description": "詳細",
            "priority": "high/medium/low",
            "expected_impact": "直帰率30%低下、CTR50%向上など"
        }}
    ]
}}
"""


def analyze_lp_deep(url: str, html: str, body_excerpt: str = "") -> dict:
    """LPを詳細に分析し、ユーザーレベルの詳細な評価を返す"""
    try:
        # LP要素を抽出
        lp_element = extract_lp_elements(html)
        
        # LLMに分析させる
        prompt = _build_lp_analysis_prompt(url, lp_element, body_excerpt or html[:1000])
        response = ask_llm(prompt)
        
        # JSON応答をパース
        try:
            analysis = json.loads(response)
        except json.JSONDecodeError:
            # JSON抽出を試みる
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {
                    "h1_assessment": response[:500],
                    "overall_score": 5,
                    "key_issues": ["分析パース失敗"],
                    "improvement_patterns": []
                }
        
        return {
            "url": url,
            "lp_elements": {
                "h1": lp_element.h1,
                "h2_count": len(lp_element.h2_list),
                "cta_count": len(lp_element.cta_buttons),
                "text_length": lp_element.text_length,
                "paragraph_count": lp_element.paragraph_count,
                "section_count": lp_element.section_count,
                "images_count": lp_element.images_count,
            },
            "analysis": analysis,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"LP deep analysis failed for {url}: {e}")
        return {
            "url": url,
            "status": "error",
            "error": str(e)
        }
