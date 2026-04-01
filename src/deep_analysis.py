import os
from urllib.parse import urlparse

from src.llm_client import ask_llm, ask_llm_with_consistency, _wrap_cot_prompt
from src.site_results_service import is_actionable_site_result, site_result_status

DEEP_ANALYSIS_ENABLED = os.getenv("DEEP_ANALYSIS_ENABLED", "true").lower() not in {"0", "false", "no"}
DEEP_ANALYSIS_NUM_PREDICT = int(os.getenv("DEEP_ANALYSIS_NUM_PREDICT", "1200"))

# LLM品質向上設定
SELF_CONSISTENCY_ENABLED = os.getenv("SELF_CONSISTENCY_ENABLED", "false").lower() not in {"0", "false", "no"}
CHAIN_OF_THOUGHT_ENABLED = os.getenv("CHAIN_OF_THOUGHT_ENABLED", "false").lower() not in {"0", "false", "no"}


def _top_recommendations(recommendations: list) -> list[dict]:
    return recommendations[:5]


def _weakest_site(url_results: list) -> dict | None:
    actionable_results = [result for result in url_results if is_actionable_site_result(result)]
    if not actionable_results:
        return None
    return min(actionable_results, key=lambda item: item.get("score", 0))


def _unique_channels(recommendations: list, diagnostics) -> list[str]:
    result = []
    for rec in recommendations:
        channel = rec.get("channel")
        if channel and channel != "overall" and channel not in result:
            result.append(channel)

    if diagnostics is not None and not diagnostics.empty:
        for channel in diagnostics["channel"].tolist():
            if channel and channel not in result:
                result.append(channel)

    return result[:3]


def _infer_page_role(url: str) -> str:
    path = urlparse(url).path.strip("/").lower()
    if not path:
        return "トップページ"
    if "faq" in path:
        return "不安解消ページ"
    if "contact" in path or "inquiry" in path:
        return "CVページ"
    if "service" in path or "lp" in path or "product" in path:
        return "主LP"
    if "case" in path or "works" in path:
        return "事例ページ"
    return "下層ページ"


def _page_topic(url: str) -> str:
    path = urlparse(url).path.strip("/").lower()
    if not path:
        return "サービス全体"
    last = path.split("/")[-1]
    mapping = {
        "service": "サービス導入",
        "faq": "導入前の不安解消",
        "contact": "問い合わせ",
        "lp": "主力訴求",
        "manual-production": "マニュアル制作",
        "support": "制作支援",
    }
    return mapping.get(last, last.replace("-", " ") or "サービス全体")


def _site_context(url_results: list) -> list[dict]:
    result = []
    for site in url_results[:3]:
        result.append(
            {
                "url": site.get("url"),
                "score": site.get("score"),
                "page_count": site.get("page_count"),
                "analysis_status": site_result_status(site),
                "analyzed_at": site.get("analyzed_at"),
                "site_findings": site.get("site_findings", [])[:5],
                "site_improvements": site.get("site_improvements", [])[:5],
                "weak_pages": [
                    {
                        "url": page.get("url"),
                        "score": page.get("score"),
                        "cta_count": page.get("cta_count"),
                        "findings": page.get("findings", [])[:5],
                        "improvements": page.get("improvements", [])[:5],
                    }
                    for page in site.get("weak_pages", [])[:3]
                ],
            }
        )
    return result


def build_deep_analysis_context(snapshot: dict, recommendations: list, url_results: list) -> str:
    diagnostics = snapshot["diagnostics"]
    diagnostics_rows = []
    if diagnostics is not None and not diagnostics.empty:
        columns = [
            "channel",
            "status",
            "revenue",
            "cost",
            "roas",
            "cvr",
            "revenue_delta_pct",
            "cvr_delta_pct",
            "reason",
            "recommended_action",
        ]
        diagnostics_rows = diagnostics[columns].head(5).to_dict(orient="records")

    # Extract strategic LP analyses from url_results
    strategic_lp_analyses = []
    for site_result in url_results:
        if site_result.get("strategic_lp_analyses"):
            strategic_lp_analyses.extend(site_result["strategic_lp_analyses"])
    
    # Limit to top 2 or 3 for context size
    limited_strategic_lp_analyses = strategic_lp_analyses[:2]

    return f"""
Latest Snapshot:
{snapshot["latest"]}

Period KPI:
{snapshot["kpis"]}

Alerts:
{snapshot["alerts"]}

Recommendations:
{_top_recommendations(recommendations)}

Channel Diagnostics:
{diagnostics_rows}

Site Diagnostics:
{_site_context(url_results)}

Strategic LP Analyses (Top {len(limited_strategic_lp_analyses)}):
{limited_strategic_lp_analyses}
"""


def build_deep_analysis_prompt(snapshot: dict, recommendations: list, url_results: list) -> str:
    context = build_deep_analysis_context(snapshot, recommendations, url_results)
    return f"""
あなたはB2Bマーケティング責任者、LPO/CROコンサルタント、コピーライターを兼ねる戦略アナリストです。
以下のデータだけを使って、日本語で、実務でそのまま使える深い改善提言を書いてください。
推測が入る箇所は必ず「仮説」と明記してください。
不要な前置きは禁止です。Markdownで出力してください。

必ず以下の見出しをこの順番で出してください。

## Executive Call
- 経営視点での結論を3-5点

## Funnel Diagnosis
- 流入、LP、CTA、信頼形成、CV導線のどこが詰まっているか

## Message-Market Fit Hypotheses
- 広告や検索意図とLPのメッセージのズレ仮説
- 流入チャネル別に優先仮説を書く

## LP Strategic Insights
- 戦略的LP分析結果から得られる示唆

## Channel-Specific Messaging Packs
- google / meta など主要チャネルごとに
- 狙う意図
- 訴求軸
- 見出しトーン
- オファー案
- 着地ページ改善

## Page-Level Breakdown
- 主要な弱いページごとに
- 問題
- なぜ問題か
- 何を変えるか
- 優先度

## Copy Rewrite Pack
- 主LP向けに H1案を5つ
- サブコピー案を5つ
- CTA文言案を8つ
- それぞれターゲット意図も短く書く

## Page Copy Packs
- 弱いページごとに
- H1案を5つ
- サブコピー案を3つ
- CTA案を6つ
- 実績見出し案を3つ
- FAQ種を5つ

## Conversion Architecture
- 主CTA
- 副CTA
- セクション順
- フォーム改善
- 資料DLや中間CVの役割

## 30-Day Execution Plan
- 0-3日
- 1-2週間
- 2-4週間
- それぞれ担当、実装内容、KPI

## 90-Day Transformation Program
- 0-30日
- 31-60日
- 61-90日
- 各フェーズのテーマ、責任者、成功指標を書く

## Experiment Backlog
- ABテストを最低6本
- 仮説、A/B案、成功指標を書く

## Instrumentation Checklist
- 追加すべきイベント計測と週次で見るダッシュボード項目を書く

## Implementation Ticket Breakdown
- 実装タスクを最低8本
- owner
- effort
- dependency
- Definition of Done

## Risk Notes
- この分析の限界
- 今すぐ追加で取るべきデータ

データ:
{context}
"""


def _build_channel_pack_lines(snapshot: dict, recommendations: list) -> list[str]:
    diagnostics = snapshot.get("diagnostics")
    lines = ["## Channel-Specific Messaging Packs"]
    channels = _unique_channels(recommendations, diagnostics)

    if not channels:
        lines.append("- チャネル別の差分データが薄いため、まず source/medium/campaign の粒度で計測を増やします。")
        return lines

    for channel in channels:
        if channel == "google":
            lines.extend(
                [
                    f"- {channel}",
                    "  狙う意図: 顕在課題の解決先を探している比較検討層",
                    "  訴求軸: 早く立ち上がる / 品質が安定する / 外注負荷が減る",
                    "  見出しトーン: 課題を即座に言語化し、導入後の業務改善を数字で約束する",
                    "  オファー案: 無料診断 / 見積もり相談 / 導入事例集",
                    "  着地ページ改善: H1で対象者と成果を明記し、FV直下に事例を置く",
                ]
            )
            continue

        if channel == "meta":
            lines.extend(
                [
                    f"- {channel}",
                    "  狙う意図: 課題を自覚し始めた潜在層から準顕在層",
                    "  訴求軸: 属人化の解消 / 現場混乱の削減 / 手戻りコストの圧縮",
                    "  見出しトーン: 共感から入り、放置コストと改善後の安心感を対比する",
                    "  オファー案: 事例集DL / 課題チェックリスト / 無料相談",
                    "  着地ページ改善: 共感型FVとFAQを強化し、問い合わせ前の不安を先回りで解消する",
                ]
            )
            continue

        lines.extend(
            [
                f"- {channel}",
                "  狙う意図: 流入経路ごとのニーズ差分を整理し、勝ち訴求を見極める",
                "  訴求軸: 導入負荷の低さ / 成果の再現性 / 社内展開のしやすさ",
                "  見出しトーン: 課題を具体化し、導入後の変化を短く約束する",
                "  オファー案: 無料診断 / 事例確認 / 課題整理相談",
                "  着地ページ改善: 流入訴求とLP冒頭の意味ズレを減らし、主CTAを1つに寄せる",
            ]
        )

    return lines


def _build_page_copy_lines(url_results: list) -> list[str]:
    lines = ["## Page Copy Packs"]
    page_count = 0

    for site in url_results[:2]:
        for page in site.get("weak_pages", [])[:2]:
            page_count += 1
            topic = _page_topic(page.get("url", ""))
            role = _infer_page_role(page.get("url", ""))
            findings = ", ".join(page.get("findings", [])[:3]) or "訴求不足"

            lines.extend(
                [
                    f"- ページ: {page.get('url')}",
                    f"  役割: {role}",
                    f"  問題の芯: {findings}",
                    f"  H1案: {topic}の属人化を減らし、伝わる成果物まで伴走する",
                    f"  H1案: {topic}の負担を減らし、現場で使われる形まで整える",
                    f"  H1案: {topic}を早く・正確に・継続しやすくする支援",
                    f"  H1案: {topic}の品質と制作スピードを同時に引き上げる",
                    f"  H1案: {topic}の課題整理から制作運用までまとめて支援",
                    "  サブコピー案: 課題整理、構成設計、制作、改善まで一気通貫で支援します。",
                    f"  サブコピー案: 現場が迷わず使える状態まで見据えて、{topic}の整備を進めます。",
                    "  サブコピー案: 属人化、更新負荷、品質ばらつきを減らし、社内展開しやすい形をつくります。",
                    "  CTA案: 無料で課題診断を受ける",
                    "  CTA案: 成功事例をダウンロード",
                    "  CTA案: 自社に合う進め方を相談する",
                    "  CTA案: 改善の優先順位を相談する",
                    "  CTA案: まずは見積もりを依頼する",
                    "  CTA案: 現状の課題を整理する",
                    f"  実績見出し案: {topic}改善で工数削減と品質安定を実現した事例",
                    f"  実績見出し案: {topic}の見直しで問い合わせ前の不安を減らした事例",
                    f"  実績見出し案: {topic}を短期間で立て直したプロジェクト事例",
                    "  FAQ種: 費用感はどう決まるか",
                    "  FAQ種: どこまで支援範囲に含まれるか",
                    "  FAQ種: 納期の目安はどれくらいか",
                    "  FAQ種: 既存資料の整理から依頼できるか",
                    "  FAQ種: 社内レビュー体制がなくても進められるか",
                ]
            )

            if page_count >= 2:
                return lines

    if page_count == 0:
        lines.append("- 弱いページがまだ特定されていないため、主LPに対してH1/CTA/FAQの3点から先に改善します。")
    return lines


def _build_ticket_breakdown_lines(recommendations: list, url_results: list) -> list[str]:
    weakest_site = _weakest_site(url_results)
    weakest_page = weakest_site["weak_pages"][0] if weakest_site and weakest_site.get("weak_pages") else None
    top_action = recommendations[0]["action"] if recommendations else "流入別の悪化要因を切り分ける"
    page_label = weakest_page.get("url") if weakest_page else (weakest_site.get("url") if weakest_site else "主要LP")

    return [
        "## Implementation Ticket Breakdown",
        f"- T1: `FV刷新` / owner=マーケ+制作 / effort=1日 / dependency=なし / DoD={page_label} のH1・サブコピー・主CTAが差し替わっている",
        "- T2: `CTA統合` / owner=マーケ+デザイナー / effort=0.5日 / dependency=T1 / DoD=主CTA1つ、副CTA2つの構成に整理されている",
        "- T3: `事例上段化` / owner=制作+営業 / effort=1日 / dependency=なし / DoD=成果数字つき事例がFV直下から確認できる",
        "- T4: `FAQ追加` / owner=マーケ / effort=0.5日 / dependency=なし / DoD=主要懸念5件に回答するFAQがLP下部に実装されている",
        "- T5: `中間CV追加` / owner=マーケ+営業 / effort=1日 / dependency=T2 / DoD=資料DLまたは診断オファーが副CTAとして配置されている",
        f"- T6: `チャネル別訴求分岐` / owner=広告運用 / effort=1日 / dependency=T1 / DoD={top_action} に合わせて google/meta などの着地見出し差分が用意されている",
        "- T7: `計測実装` / owner=分析 / effort=0.5日 / dependency=T2 / DoD=CTAクリック、フォーム開始、フォーム完了、FAQ開閉が計測される",
        "- T8: `ABテスト着手` / owner=分析+マーケ / effort=0.5日 / dependency=T1,T2 / DoD=FV、CTA、事例配置の3テストが開始されている",
        "- T9: `週次レビュー運用` / owner=責任者 / effort=0.5日 / dependency=T7 / DoD=source/medium別CVRとLP別CVRを毎週見る定例がある",
    ]


def build_rule_based_deep_analysis(snapshot: dict, recommendations: list, url_results: list) -> str:
    latest = snapshot["latest"]
    weakest_site = _weakest_site(url_results)
    weakest_page = weakest_site["weak_pages"][0] if weakest_site and weakest_site.get("weak_pages") else None

    top_rec = recommendations[0] if recommendations else None
    second_rec = recommendations[1] if len(recommendations) >= 2 else None

    lines = ["## Executive Call"]
    if top_rec:
        lines.append(f"- 最優先の事業課題は `{top_rec['channel']}` の `{top_rec['issue']}` です。まず `{top_rec['action']}` を実施します。")
    if second_rec:
        lines.append(f"- 次点では `{second_rec['channel']}` に伸長余地があります。`{second_rec['action']}` を小さく検証します。")
    lines.append(
        f"- 最新日 `{latest.get('latest_date') or '-'}` の全体ROASは `{latest.get('latest', {}).get('roas', 0):.2f}` で、LP改善と流入最適化を同時に進める局面です。"
    )
    if weakest_site:
        lines.append(
            f"- サイト面では `{weakest_site.get('url')}` が最優先です。平均score `{weakest_site.get('score')}` で、横断課題は `{', '.join(weakest_site.get('site_improvements', [])[:2]) or '導線整理'}` です。"
        )

    lines.extend(
        [
            "",
            "## Funnel Diagnosis",
            f"- 流入側: {top_rec['channel']} の効率改善が優先です。" if top_rec else "- 流入側: 大きな異常は小さいですが、流入別の訴求差分計測が必要です。",
            "- LP側: ファーストビューの価値提案とCTAの整理が最初のボトルネックです。",
            "- 信頼形成: 事例の定量成果とFAQが不足または弱く、比較検討層の背中押しが足りません。",
            "- CV導線: 問い合わせ一本ではなく、資料DLや無料診断などの中間CVを持つ構造にするべきです。",
            "",
            "## Message-Market Fit Hypotheses",
            f"- 仮説1: `{top_rec['channel']}` の流入訴求とLPトップのメッセージが一致していません。" if top_rec else "- 仮説1: 流入訴求とLPトップのメッセージ差分が潜在課題です。",
            "- 仮説2: 課題解決よりもサービス紹介が先に見えており、自己投影が起きにくいです。",
            "- 仮説3: CTAが多く、次の一歩が曖昧なため、比較検討の途中で離脱しています。",
            "",
            *_build_channel_pack_lines(snapshot, recommendations),
            "",
            "## Page-Level Breakdown",
        ]
    )

    if weakest_page:
        lines.append(f"- ページ: {weakest_page.get('url')}")
        lines.append(f"  問題: {', '.join(weakest_page.get('findings', [])[:4]) or '訴求不足'}")
        lines.append("  なぜ問題か: ユーザーが3秒以内に価値を理解できず、主CVに向かいにくいためです。")
        lines.append(f"  何を変えるか: {', '.join(weakest_page.get('improvements', [])[:4]) or 'H1/FV/CTAを再設計する'}")
        lines.append("  優先度: P1")
    else:
        lines.append("- ページ: 主要LP")
        lines.append("  問題: 流入訴求とファーストビューの意味が一致していません。")
        lines.append("  なぜ問題か: 自分向けのページだと判断されにくく、比較検討の初速が落ちるためです。")
        lines.append("  何を変えるか: H1、主CTA、事例、FAQの順で改善します。")
        lines.append("  優先度: P1")

    lines.extend(
        [
            "",
            "## Copy Rewrite Pack",
            "- H1案1: マニュアル作成の負担を減らす制作支援サービス",
            "- H1案2: 伝わるマニュアルを、業務理解から制作まで一括支援",
            "- H1案3: 製品・業務マニュアル作成をまとめて支援",
            "- H1案4: マニュアル制作の属人化を解消する支援サービス",
            "- H1案5: 取扱説明書・業務マニュアル制作を効率化",
            "- サブコピー案1: 取扱説明書、業務マニュアル、多言語展開まで対応。制作工数の削減と品質向上を支援します。",
            "- サブコピー案2: 業務理解から制作体制づくりまで支援し、古い・伝わらない・重いを改善します。",
            "- サブコピー案3: マニュアルの課題を、制作支援と運用設計で解決します。",
            "- サブコピー案4: 作るだけでなく、現場で伝わる状態まで見据えて支援します。",
            "- サブコピー案5: 外注、標準化、多言語対応の悩みをまとめて解消します。",
            "- CTA案1: 無料でマニュアル診断を受ける",
            "- CTA案2: 制作事例集をダウンロード",
            "- CTA案3: 相談・見積もりを依頼する",
            "- CTA案4: 自社に合う進め方を相談する",
            "- CTA案5: 課題整理から相談する",
            "- CTA案6: マニュアル改善の成功事例を見る",
            "- CTA案7: 今の課題を無料で確認する",
            "- CTA案8: 導入の流れを確認する",
            "",
            *_build_page_copy_lines(url_results),
            "",
            "## Conversion Architecture",
            "- 主CTA: 無料でマニュアル診断を受ける",
            "- 副CTA: 制作事例集をダウンロード / 相談・見積もりを依頼する",
            "- セクション順: FV → 課題訴求 → 解決策 → 事例 → 選ばれる理由 → FAQ → CTA",
            "- フォーム改善: 初回は入力項目を絞り、詳細は商談時に回す",
            "- 中間CV: 情報収集層は資料DLで捕捉する",
            "",
            "## 30-Day Execution Plan",
            "- 0-3日: 担当=マーケ/制作。H1、サブコピー、主CTA、ヒーロー下の信頼要素を修正。KPI=直帰率/CTA CTR/フォーム開始率",
            "- 1-2週間: 担当=マーケ/営業/制作。事例の上段化、FAQ追加、資料DL導線追加。KPI=CVR/フォーム完了率/事例到達率",
            "- 2-4週間: 担当=マーケ/分析。流入別訴求分岐、ABテスト、週次レビューを開始。KPI=CPA/ROAS/MQL数",
            "",
            "## 90-Day Transformation Program",
            "- 0-30日: テーマ=現状是正。責任者=マーケ責任者。成功指標=直帰率, CTA CTR, CVR",
            "- 31-60日: テーマ=信頼形成と計測整備。責任者=マーケ/営業/分析。成功指標=フォーム開始率, 完了率, 事例到達率",
            "- 61-90日: テーマ=再現性構築。責任者=責任者/広告運用/分析。成功指標=CPA, ROAS, MQL数",
            "",
            "## Experiment Backlog",
            "- 1. FV見出し: 現状 vs 課題解決型H1 / 指標=直帰率",
            "- 2. CTA文言: 問い合わせ vs 無料診断 / 指標=CTA CTR",
            "- 3. CTA構造: CTA多点分散 vs 主副CTA整理 / 指標=CVR",
            "- 4. 事例位置: 中盤 vs FV直下 / 指標=事例到達率, CVR",
            "- 5. FAQ形式: 通常表示 vs 開閉式 / 指標=スクロール率, CVR",
            "- 6. オファー: 問い合わせのみ vs 資料DL併設 / 指標=総CV数",
            "",
            "## Instrumentation Checklist",
            "- CTAクリック",
            "- 資料DLクリック",
            "- フォーム開始",
            "- フォーム完了",
            "- FAQ開閉",
            "- スクロール25/50/75/100",
            "- source/medium/campaign/landing page別CVRダッシュボード",
            "",
            *_build_ticket_breakdown_lines(recommendations, url_results),
            "",
            "## Risk Notes",
            "- 限界: 現在は広告キーワード、ヒートマップ、フォーム離脱データがありません。",
            "- 追加データ: source/medium/campaign別流入、CTAクリック、フォーム開始/完了、スクロール率、ヒートマップが必要です。",
        ]
    )
    return "\n".join(lines)


def generate_deep_analysis(snapshot: dict, recommendations: list, url_results: list, skip_llm: bool = False) -> dict:
    if skip_llm or not DEEP_ANALYSIS_ENABLED:
        note = "skip_llm または DEEP_ANALYSIS_ENABLED=false のためルールベース深掘りを使用"
        return {
            "mode": "rule-based",
            "note": note,
            "body": build_rule_based_deep_analysis(snapshot, recommendations, url_results),
        }

    prompt = build_deep_analysis_prompt(snapshot, recommendations, url_results)
    
    # Chain-of-Thought を統合
    if CHAIN_OF_THOUGHT_ENABLED:
        prompt = _wrap_cot_prompt(prompt, analysis_type="deep_analysis")
    
    # Self-Consistency または通常の LLM 呼び出し
    if SELF_CONSISTENCY_ENABLED:
        result = ask_llm_with_consistency(
            prompt, 
            num_predict=DEEP_ANALYSIS_NUM_PREDICT,
            use_rag=True
        )
        response = result.get("response", "")
        confidence = result.get("confidence", 0.0)
        generation_count = result.get("generation_count", 0)
        
        if response.startswith("["):
            # Self-Consistency が失敗
            return {
                "mode": "rule-based",
                "note": response,
                "body": build_rule_based_deep_analysis(snapshot, recommendations, url_results),
            }
        
        return {
            "mode": "llm-with-consistency",
            "note": f"Self-Consistency投票 ({generation_count}生成, 信頼度={confidence:.2f}) + Chain-of-Thought",
            "body": response,
        }
    else:
        # 通常の LLM 呼び出し
        response = ask_llm(prompt, num_predict=DEEP_ANALYSIS_NUM_PREDICT, use_rag=True)
        if response.startswith("[LLM"):
            return {
                "mode": "rule-based",
                "note": response,
                "body": build_rule_based_deep_analysis(snapshot, recommendations, url_results),
            }

        note = f"local model generated deep analysis"
        if CHAIN_OF_THOUGHT_ENABLED:
            note += " with Chain-of-Thought"
        note += f" ({DEEP_ANALYSIS_NUM_PREDICT} tokens target)"
        
        return {
            "mode": "llm",
            "note": note,
            "body": response,
        }
