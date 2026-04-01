from datetime import UTC, datetime
from pathlib import Path
import logging
import json
import csv
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from src.site_results_service import is_actionable_site_result, site_result_status

logger = logging.getLogger(__name__)


def save_report(title: str, body: str):
    Path("reports").mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = Path("reports") / f"{ts}_{title}.md"
    path.write_text(body, encoding="utf-8")
    return str(path)


def save_report_json(title: str, data: dict, latest: bool = False):
    """Save report data as JSON for machine consumption."""
    Path("reports").mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    
    path = Path("reports") / f"{ts}_{title}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    if latest:
        latest_path = Path("reports") / f"{title}_latest.json"
        latest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return str(path)


def save_report_csv(title: str, rows: list[dict], latest: bool = False):
    """Save action queue as CSV for task management tools."""
    Path("reports").mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    
    path = Path("reports") / f"{ts}_{title}.csv"
    
    if rows:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    
    if latest:
        latest_path = Path("reports") / f"{title}_latest.csv"
        if rows:
            with open(latest_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
    
    return str(path)


def _fmt_int(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{int(value):,}"


def _fmt_currency(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"¥{float(value):,.0f}"


def _fmt_ratio(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.2f}"


def _fmt_pct(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def _fmt_delta(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    sign = "+" if value > 0 else ""
    return f"{sign}{float(value) * 100:.1f}%"


def _markdown_table(headers, rows):
    if not rows:
        return "_なし_"

    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = []
    for row in rows:
        cleaned = []
        for value in row:
            text = str(value).replace("\n", "<br>").replace("|", "/")
            cleaned.append(text)
        body.append("| " + " | ".join(cleaned) + " |")

    return "\n".join([header_line, separator, *body])


def _issue_channels(diagnostics: pd.DataFrame | None) -> pd.DataFrame:
    if diagnostics is None or diagnostics.empty:
        return pd.DataFrame()
    return diagnostics[diagnostics["status"].isin(["critical", "warning"])].head(3)


def _opportunity_channels(diagnostics: pd.DataFrame | None) -> pd.DataFrame:
    if diagnostics is None or diagnostics.empty:
        return pd.DataFrame()
    return diagnostics[diagnostics["status"] == "opportunity"].head(2)


def _get_vision_analyses(url_results: list) -> list:
    """Extract Vision LP analysis results from url_results."""
    vision_rows = []
    for result in url_results:
        vision_analyses = result.get("vision_analyses", [])
        for vision in vision_analyses:
            vision_rows.append([
                result.get("url", "-"),
                vision.get("url", "-"),
                vision.get("vision_analysis", "No analysis") if vision.get("vision_analysis") else "Skipped"
            ])
    return vision_rows


def _weakest_site(url_results: list) -> dict | None:
    actionable_results = [result for result in url_results if is_actionable_site_result(result)]
    if not actionable_results:
        return None
    return min(actionable_results, key=lambda item: item.get("score", 0))


def _fmt_analysis_status(value: str) -> str:
    return {
        "success": "analyzed",
        "error": "error",
        "pending": "pending",
    }.get(value, value or "-")


def _build_evidence_base(snapshot: dict, url_results: list, deep_analysis_mode: str) -> str:
    status_counts = {"success": 0, "error": 0, "pending": 0}
    analyzed_at_values = []
    for result in url_results:
        status = site_result_status(result)
        status_counts[status] = status_counts.get(status, 0) + 1
        if result.get("analyzed_at"):
            analyzed_at_values.append(result["analyzed_at"])

    latest_analyzed_at = max(analyzed_at_values) if analyzed_at_values else "-"
    latest_snapshot = snapshot.get("latest", {})

    return "\n".join(
        [
            f"- KPI基準日: {latest_snapshot.get('latest_date') or '-'}",
            f"- 対象サイト数: {len(url_results)}",
            f"- サイト分析カバレッジ: analyzed={status_counts.get('success', 0)} / error={status_counts.get('error', 0)} / pending={status_counts.get('pending', 0)}",
            f"- 直近のサイト分析時刻: {latest_analyzed_at}",
            f"- 深掘り分析モード: {deep_analysis_mode}",
            "- 解釈ルール: KPI表とSite Resultsは事実、Strategic Diagnosis以降はその事実にもとづく解釈と改善提案",
        ]
    )


def _build_executive_diagnosis(snapshot: dict, recommendations: list, url_results: list) -> str:
    latest = snapshot["latest"]
    latest_totals = latest.get("latest", {})
    latest_delta = latest.get("delta_vs_previous", {})
    weakest_site = _weakest_site(url_results)

    lines = [
        "- 収益性の現状",
        f"  売上 {_fmt_currency(latest_totals.get('revenue'))} / CV {_fmt_int(latest_totals.get('conversions'))} / ROAS {_fmt_ratio(latest_totals.get('roas'))}",
        f"  前日比 売上 {_fmt_delta(latest_delta.get('revenue'))} / CVR {_fmt_delta(latest_delta.get('cvr'))} / ROAS {_fmt_delta(latest_delta.get('roas'))}",
    ]

    if recommendations:
        top = recommendations[0]
        lines.append(
            f"- 最優先で触るべき論点: {top['channel']} / {top['issue']} / {top['action']}"
        )

    if weakest_site:
        lines.append(
            f"- LP/サイトの最重要ボトルネック: {weakest_site.get('url')} "
            f"(平均score={weakest_site.get('score')}, 分析ページ数={weakest_site.get('page_count', 0)})"
        )

    lines.append(
        "- 総評: チャネル改善とLP改善を別々に見るのではなく、流入品質・訴求・CTA導線を一気通貫で最適化する段階です。"
    )
    return "\n".join(lines)


def _build_channel_deep_dive(diagnostics: pd.DataFrame | None) -> str:
    if diagnostics is None or diagnostics.empty:
        return "- チャネル別データが不足しているため、深掘りは保留です。"

    lines = []
    issue_rows = _issue_channels(diagnostics)
    opportunity_rows = _opportunity_channels(diagnostics)

    if issue_rows.empty and opportunity_rows.empty:
        return "- 大きな悪化チャネルはありません。現状は計測強化と勝ちパターンの再現性確保が主課題です。"

    for _, row in issue_rows.iterrows():
        lines.append(
            f"- 要改善チャネル {row['channel']}: "
            f"売上 {_fmt_currency(row['revenue'])} / 費用 {_fmt_currency(row['cost'])} / "
            f"ROAS {_fmt_ratio(row['roas'])} / CVR変化 {_fmt_delta(row['cvr_delta_pct'])} / "
            f"論点 {row['reason']} / 対応 {row['recommended_action']}"
        )

    for _, row in opportunity_rows.iterrows():
        lines.append(
            f"- 伸長候補 {row['channel']}: "
            f"ROAS {_fmt_ratio(row['roas'])} / CVR {_fmt_pct(row['cvr'])} / "
            f"理由 {row['reason']} / 次アクション {row['recommended_action']}"
        )

    return "\n".join(lines)


def _build_site_deep_dive(url_results: list) -> str:
    weakest_site = _weakest_site(url_results)
    if weakest_site is None:
        return "- サイト診断結果がまだないため、LP深掘りは保留です。"

    lines = [
        f"- 最優先サイト: {weakest_site.get('url')}",
        f"- サイト平均score: {weakest_site.get('score')} / 分析ページ数: {weakest_site.get('page_count', 0)}",
        f"- 全体所見: {', '.join(weakest_site.get('site_findings', [])[:4]) or '-'}",
        f"- 横断改善: {', '.join(weakest_site.get('site_improvements', [])[:4]) or '-'}",
    ]

    for page in weakest_site.get("weak_pages", [])[:3]:
        lines.append(
            f"- 弱いページ {page.get('url')}: "
            f"score={page.get('score')} / CTA={page.get('cta_count', 0)} / "
            f"指摘={', '.join(page.get('findings', [])[:3]) or '-'} / "
            f"改善={', '.join(page.get('improvements', [])[:3]) or '-'}"
        )

    lines.append(
        "- 解釈: 現状の課題はデザイン単体よりも、ファーストビューの価値訴求、CTAの明確さ、信頼形成コンテンツの順番に集中しています。"
    )
    return "\n".join(lines)


def _build_cro_perspectives(url_results: list) -> str:
    weakest_site = _weakest_site(url_results)
    weakest_page = None
    if weakest_site and weakest_site.get("weak_pages"):
        weakest_page = weakest_site["weak_pages"][0]

    if weakest_page is None:
        return "\n".join(
            [
                "- ファーストビュー: 3秒以内に価値提案・対象者・CTAが伝わる構造かを確認する",
                "- CTA設計: 問い合わせ一本ではなく、資料DLや診断オファーなど低ハードルCVを用意する",
                "- 信頼形成: 事例、FAQ、実績数字、導入企業ロゴを上部から段階的に配置する",
            ]
        )

    lines = []
    findings = set(weakest_page.get("findings", []))

    if "h1が抽象的" in findings or "h1なし" in findings:
        lines.append("- ファーストビュー課題: H1が弱く、検索意図との一致が不足しています。ベネフィット主導の見出しに刷新するべきです。")
    if "CTAなし" in findings or "CTAが分散" in findings:
        lines.append("- コンバージョン課題: CTA設計が不足または分散しています。主CTAを1つ決め、資料DLなど副CTAを補助導線として整理するべきです。")
    if "事例なし" in findings:
        lines.append("- 信頼形成課題: 事例が不足しています。ヒーロー直後に成果事例を配置し、詳細は中盤で深掘りする構成が有効です。")
    if "FAQなし" in findings:
        lines.append("- 不安解消課題: FAQ不足により検討障壁を残しています。主要懸念を開閉式FAQで処理するべきです。")
    if "本文量が少ない" in findings:
        lines.append("- 情報設計課題: ページの説得材料が足りません。比較軸、進め方、導入後の変化を追加するべきです。")

    if not lines:
        lines.append("- CRO観点では致命傷は小さいため、CTA文言とオファー設計のABテストで積み上げ改善を狙う段階です。")

    return "\n".join(lines)


def _build_roadmap_rows(recommendations: list, url_results: list) -> list[list[str]]:
    weakest_site = _weakest_site(url_results)
    weakest_page = None
    if weakest_site and weakest_site.get("weak_pages"):
        weakest_page = weakest_site["weak_pages"][0]

    top_action = recommendations[0]["action"] if recommendations else "大きな異常がないため監視体制を整える"
    site_action = (
        weakest_site.get("site_improvements", ["事例・FAQ・CTAの配置を再整理する"])[0]
        if weakest_site else "主要ページの訴求順とCTA導線を見直す"
    )
    weak_page_label = weakest_page.get("url") if weakest_page else "主要LP"

    return [
        [
            "0-3日",
            "即効改善",
            f"{weak_page_label} のH1/FV/主CTAを最優先で修正し、{top_action}",
            "直帰率 / CTA CTR / フォーム開始率",
        ],
        [
            "1-2週間",
            "信頼形成",
            f"{site_action}。あわせて事例、FAQ、資料DLなどの中間CVを追加",
            "CVR / フォーム完了率 / 事例到達率",
        ],
        [
            "2-4週間",
            "再現性構築",
            "流入キーワード別の訴求分岐、ABテスト運用、計測整備を行い勝ちパターンを横展開",
            "CPA / ROAS / MQL数",
        ],
    ]


def _build_90_day_program_rows(recommendations: list, url_results: list) -> list[list[str]]:
    weakest_site = _weakest_site(url_results)
    weakest_page = None
    if weakest_site and weakest_site.get("weak_pages"):
        weakest_page = weakest_site["weak_pages"][0]

    top_action = recommendations[0]["action"] if recommendations else "監視体制を整える"
    weak_page_label = weakest_page.get("url") if weakest_page else "主要LP"
    weakest_site_label = weakest_site.get("url") if weakest_site else "主要サイト"

    return [
        [
            "0-30日",
            "現状是正",
            f"{weak_page_label} のFV/H1/CTAと、{top_action} を最優先で実行する",
            "マーケ / 制作 / 広告運用",
            "直帰率 / CTA CTR / CVR",
        ],
        [
            "31-60日",
            "信頼形成と計測",
            f"{weakest_site_label} に事例、FAQ、中間CV、イベント計測を横断導入する",
            "マーケ / 営業 / 分析",
            "フォーム開始率 / 完了率 / 事例到達率",
        ],
        [
            "61-90日",
            "再現性構築",
            "流入別訴求分岐、ABテスト定着、週次レビューを運用に組み込む",
            "責任者 / 分析 / 広告運用",
            "CPA / ROAS / MQL数",
        ],
    ]


def _build_ab_test_rows(url_results: list) -> list[list[str]]:
    weakest_site = _weakest_site(url_results)
    weakest_page = None
    if weakest_site and weakest_site.get("weak_pages"):
        weakest_page = weakest_site["weak_pages"][0]

    page_label = weakest_page.get("url") if weakest_page else "主要LP"
    findings = set(weakest_page.get("findings", [])) if weakest_page else set()

    h1_b = "課題解決型H1 + ベネフィット訴求 + 実績補足"
    cta_b = "無料診断 / 資料DL / 問い合わせの役割分担CTA"
    trust_b = "ヒーロー直後に実績・事例・ロゴを追加"
    if "h1が抽象的" not in findings and "h1なし" not in findings:
        h1_b = "現状H1よりも対象業種・成果を明記した具体見出し"
    if "CTAなし" not in findings and "CTAが分散" not in findings:
        cta_b = "CTA文言をより低ハードルなオファーに変更"
    if "事例なし" not in findings:
        trust_b = "事例の配置を上段化し、成果数字を強調"

    return [
        [
            "P1",
            page_label,
            "ファーストビューをベネフィット訴求型にすると直帰率が改善する",
            "現状FV",
            h1_b,
            "直帰率 / 滞在時間 / スクロール率",
        ],
        [
            "P1",
            page_label,
            "CTA設計を整理するとCVRが改善する",
            "現状CTA",
            cta_b,
            "CTA CTR / フォーム開始率 / CVR",
        ],
        [
            "P2",
            page_label,
            "信頼形成コンテンツを上段配置すると検討深度が上がる",
            "現状の事例配置",
            trust_b,
            "事例到達率 / フォーム完了率 / 再訪率",
        ],
    ]


def _build_measurement_lines() -> str:
    return "\n".join(
        [
            "- 流入別KPI: source / medium / landing page 単位で CVR, CPA, ROAS を切り分ける",
            "- LP行動KPI: CTAクリック率、フォーム開始率、フォーム完了率、資料DL率を必須計測にする",
            "- スクロールKPI: 25% / 50% / 75% / 100% 到達率を取り、離脱ポイントを可視化する",
            "- UX計測: ヒートマップ、クリックマップ、セッションリプレイで視認性と迷いを確認する",
            "- 技術KPI: LCP, CLS, モバイル表示崩れ、主要ページの表示速度を週次で監視する",
        ]
    )


def _build_expected_impact(snapshot: dict, url_results: list) -> str:
    latest = snapshot["latest"]
    latest_delta = latest.get("delta_vs_previous", {})
    weakest_site = _weakest_site(url_results)

    lines = [
        "- 短期: H1 / FV / CTA修正だけでも直帰率とCTA CTRの改善余地が大きい状態です。",
        "- 中期: 事例・FAQ・資料DLを加えることで、比較検討層のCVR改善が狙えます。",
        "- 長期: 流入訴求とLP訴求を一致させることで、CPAとROASの改善再現性が高まります。",
    ]

    if latest_delta.get("revenue") is not None and latest_delta["revenue"] < 0:
        lines.append("- 補足: 売上が直近で落ちているため、LP改善と同時に配信面・訴求面の見直しも並走すべきです。")

    if weakest_site and weakest_site.get("score", 100) < 80:
        lines.append(
            f"- 補足: {weakest_site.get('url')} はサイト平均scoreが低く、ページ単位改善の優先度が高いです。"
        )

    return "\n".join(lines)


def _calculate_confidence(evidence_count: int, source_types: int = 1) -> float:
    """Calculate confidence score based on evidence count and source diversity."""
    if evidence_count >= 5 and source_types >= 2:
        return 0.90
    elif evidence_count >= 3 and source_types >= 2:
        return 0.80
    elif evidence_count >= 3 or source_types >= 2:
        return 0.70
    elif evidence_count >= 1:
        return 0.60
    else:
        return 0.40


def _build_do_watch_ignore(
    recommendations: list,
    alerts: list,
    diagnostics: pd.DataFrame | None,
    url_results: list,
) -> tuple[list[str], list[str], list[str]]:
    """Build Do/Watch/Ignore priority buckets."""
    do_actions = []
    watch_actions = []
    ignore_actions = []

    # Collect all possible actions
    all_candidates = []

    # From recommendations
    for rec in recommendations[:5]:
        priority = rec.get("priority", "")
        all_candidates.append({
            "severity": 0 if priority == "P1" else (1 if priority == "P2" else 2),
            "text": f"{rec.get('channel')} / {rec.get('issue')} → {rec.get('action')}",
            "type": "recommendation",
        })

    # From alerts
    for alert in alerts[:3]:
        severity_map = {"critical": 0, "warning": 1, "info": 2}
        all_candidates.append({
            "severity": severity_map.get(alert.get("severity", "info"), 2),
            "text": f"{alert.get('message')}",
            "type": "alert",
        })

    # From weak pages
    weakest_site = _weakest_site(url_results)
    if weakest_site:
        for page in weakest_site.get("weak_pages", [])[:2]:
            improvements = page.get("improvements", [])
            if improvements:
                all_candidates.append({
                    "severity": 0 if page.get("score", 100) < 60 else 1,
                    "text": f"{page.get('url')} / {improvements[0]}",
                    "type": "page",
                })

    # Sort by severity and distribute
    all_candidates.sort(key=lambda x: x["severity"])

    for i, candidate in enumerate(all_candidates):
        if i < 3:
            do_actions.append(candidate["text"])
        elif i < 6:
            watch_actions.append(candidate["text"])
        else:
            ignore_actions.append(candidate["text"])

    return (
        do_actions or ["特に即実行すべき項目がない場合は、現状監視体制を整える"],
        watch_actions or ["特に確認待ちなし"],
        ignore_actions or ["無視してよい項目なし"],
    )


def _build_root_cause_table(
    recommendations: list,
    diagnostics: pd.DataFrame | None,
    url_results: list,
) -> list[list[str]]:
    """Build Root Cause analysis table with confidence scores."""
    rows = []

    for rec in recommendations[:5]:
        evidence_count = 1  # At minimum, the recommendation itself is evidence
        source_types = 1

        # Check if there's supporting data
        if diagnostics is not None and not diagnostics.empty:
            matching = diagnostics[diagnostics["channel"] == rec.get("channel")]
            if not matching.empty:
                evidence_count += 1
                source_types += 1

        # Check if there's LP/site evidence
        weakest_site = _weakest_site(url_results)
        if weakest_site and rec.get("channel") in ["LP", "Site"]:
            evidence_count += len(weakest_site.get("weak_pages", []))
            source_types += 1

        confidence = _calculate_confidence(evidence_count, source_types)
        estimated_impact = f"月商 {_fmt_currency(rec.get('impact_value', 0))}"

        rows.append([
            rec.get("priority", "-"),
            rec.get("issue", "-"),
            rec.get("reason", "-"),
            f"{evidence_count}件",
            f"{confidence:.2f}",
            estimated_impact,
            rec.get("action", "-"),
            "マーケ/制作" if rec.get("channel") in ["LP", "Site"] else "広告運用",
        ])

    return rows


def _build_action_queue(
    recommendations: list,
    url_results: list,
) -> list[dict]:
    """Build actionable queue with ticket-like format."""
    actions = []

    weakest_site = _weakest_site(url_results)
    weakest_page = None
    if weakest_site and weakest_site.get("weak_pages"):
        weakest_page = weakest_site["weak_pages"][0]

    for i, rec in enumerate(recommendations[:3]):
        action_item = {
            "index": i + 1,
            "title": rec.get("action", "-"),
            "why_now": f"{rec.get('issue')} / {rec.get('reason')}",
            "exact_change": rec.get("reason", "-"),
            "target": rec.get("channel", "-"),
            "kpi": "CVR / ROAS / CPA",
            "effort": "S" if i == 0 else ("M" if i == 1 else "L"),
            "due": "今週" if i == 0 else ("来週" if i == 1 else "2週間以内"),
            "dependency": "なし" if i == 0 else (f"Task {i}" if i > 0 else ""),
        }
        actions.append(action_item)

    return actions


def _build_strategic_lp_section(url_results: list) -> str:
    """Build strategic LP analysis section from site results."""
    content_lines = []
    
    for result in url_results:
        strategic_analyses = result.get("strategic_lp_analyses", [])
        if not strategic_analyses:
            continue
        
        for analysis in strategic_analyses:
            url = analysis.get("url", "-")
            sections = analysis.get("sections", {})
            
            # Format each section
            for section_name, section_content in sections.items():
                if section_content:
                    content_lines.append(f"#### {url} - {section_name}")
                    if isinstance(section_content, dict):
                        for key, value in section_content.items():
                            content_lines.append(f"- **{key}**: {value}")
                    elif isinstance(section_content, list):
                        for item in section_content:
                            content_lines.append(f"- {item}")
                    else:
                        content_lines.append(str(section_content))
                    content_lines.append("")
    
    if not content_lines:
        return "_戦略的LP分析はまだ完了していません_"
    
    return "\n".join(content_lines)


def render_marketing_report(
    *,
    snapshot: dict,
    recommendations: list,
    url_results: list,
    llm_summary: str,
    deep_analysis: dict | None = None,
):
    """新しいレポート構造: 決めるもの → 根拠 → 詳細"""
    latest = snapshot["latest"]
    kpis = snapshot["kpis"]
    alerts = snapshot["alerts"]
    diagnostics = snapshot["diagnostics"]

    latest_totals = latest.get("latest", {})
    latest_delta = latest.get("delta_vs_previous", {})

    # === DECISION BRIEF ===
    do_actions, watch_actions, ignore_actions = _build_do_watch_ignore(
        recommendations, alerts, diagnostics, url_results
    )

    decision_brief = "\n".join(
        [
            "### 今日やること",
            *[f"{i+1}. {action}" for i, action in enumerate(do_actions[:3])],
            "",
            "### 監視する（確認待ち）",
            *[f"- {action}" for action in watch_actions[:3]],
            "",
            "### 無視していい（単日ブレ）",
            *[f"- {action}" for action in ignore_actions[:3]],
        ]
    )

    # === ROOT CAUSE TABLE ===
    root_cause_rows = _build_root_cause_table(recommendations, diagnostics, url_results)
    root_cause_table = _markdown_table(
        ["Priority", "Symptom", "Root Cause", "Evidence", "Confidence", "Est. Impact", "Action", "Owner"],
        root_cause_rows,
    )

    # === ACTION QUEUE ===
    action_queue_items = _build_action_queue(recommendations, url_results)
    action_queue_body = ""
    for item in action_queue_items:
        action_queue_body += f"""
**{item['index']}. {item['title']}**
- why_now: {item['why_now']}
- exact_change: {item['exact_change']}
- target: {item['target']}
- expected_kpi: {item['kpi']}
- effort: {item['effort']} | due: {item['due']} | dependency: {item['dependency']}
"""

    # === EVIDENCE BASE ===
    deep_analysis = deep_analysis or {}
    deep_analysis_mode = deep_analysis.get("mode", "n/a")
    evidence_base = _build_evidence_base(snapshot, url_results, deep_analysis_mode)

    # === CHANNEL / LP DIAGNOSTICS ===
    diagnostic_rows = []
    if diagnostics is not None and not diagnostics.empty:
        for _, row in diagnostics.iterrows():
            diagnostic_rows.append(
                [
                    row["channel"],
                    row["status"],
                    _fmt_currency(row["revenue"]),
                    _fmt_ratio(row["roas"]),
                    _fmt_delta(row["revenue_delta_pct"]),
                    _fmt_delta(row["cvr_delta_pct"]),
                    row["reason"],
                ]
            )

    channel_diagnostics_table = _markdown_table(
        ["Channel", "Status", "Revenue", "ROAS", "Revenue Δ", "CVR Δ", "Reason"],
        diagnostic_rows,
    )

    site_rows = []
    weak_page_rows = []
    for result in url_results:
        site_rows.append(
            [
                result.get("url"),
                _fmt_analysis_status(site_result_status(result)),
                result.get("score", "-") if result.get("score") is not None else "-",
                result.get("page_count", 0),
                ", ".join(result.get("site_findings", [])[:3]) or "-",
            ]
        )

        for page in result.get("weak_pages", []):
            weak_page_rows.append(
                [
                    result.get("url"),
                    page.get("url"),
                    page.get("score"),
                    page.get("cta_count", 0),
                    ", ".join(page.get("findings", [])[:3]) or "-",
                ]
            )

    site_results_table = _markdown_table(
        ["Site", "Status", "Avg Score", "Pages", "Findings"],
        site_rows,
    )

    weak_pages_table = _markdown_table(
        ["Site", "Page", "Score", "CTA", "Findings"],
        weak_page_rows,
    ) if weak_page_rows else "_弱いページなし_"

    # === AB TEST BACKLOG ===
    ab_test_rows = _build_ab_test_rows(url_results)

    # === APPENDIX: 30-Day Roadmap, 90-Day Program ===
    roadmap_rows = _build_roadmap_rows(recommendations, url_results)
    transformation_rows = _build_90_day_program_rows(recommendations, url_results)

    # === LATEST SNAPSHOT (移動: Appendix へ) ===
    latest_lines = [
        f"- 最新日: {latest.get('latest_date') or '-'}",
        f"- 比較基準日: {latest.get('previous_date') or 'なし'}",
    ]
    if latest_totals:
        latest_lines.extend([
            f"- 売上: {_fmt_currency(latest_totals.get('revenue'))} ({_fmt_delta(latest_delta.get('revenue'))})",
            f"- CV: {_fmt_int(latest_totals.get('conversions'))} ({_fmt_delta(latest_delta.get('conversions'))})",
            f"- ROAS: {_fmt_ratio(latest_totals.get('roas'))} ({_fmt_delta(latest_delta.get('roas'))})",
            f"- CVR: {_fmt_pct(latest_totals.get('cvr'))} ({_fmt_delta(latest_delta.get('cvr'))})",
        ])

    kpi_lines = [
        f"- Sessions: {_fmt_int(kpis.get('sessions'))}",
        f"- Users: {_fmt_int(kpis.get('users'))}",
        f"- Conversions: {_fmt_int(kpis.get('conversions'))}",
        f"- Revenue: {_fmt_currency(kpis.get('revenue'))}",
        f"- ROAS: {_fmt_ratio(kpis.get('roas'))}",
        f"- CPA: {_fmt_currency(kpis.get('cpa'))}",
    ]

    alert_lines = [
        f"- [{alert['severity'].upper()}] {alert['message']}"
        for alert in alerts
    ] or ["- 大きな異常は検出されませんでした。"]

    vision_rows = _get_vision_analyses(url_results)

    error_lines = []
    for result in url_results:
        for error in result.get("errors", []):
            error_lines.append(f"- {error.get('url')}: {error.get('error')}")
    if not error_lines:
        error_lines = ["- サイト巡回エラーなし"]

    # === BUILD FINAL REPORT ===
    markdown_report = f"""# Daily Marketing Analysis

Generated: {datetime.now(UTC).isoformat()}

## Decision Brief

{decision_brief}

---

## Root Cause Analysis

分析者がすぐに判断できるよう、原因・根拠・信頼度を一覧化します。

{root_cause_table}

---

## Action Queue

チケット化形式。そのまま Jira / Notion に貼れます。

{action_queue_body}

---

## Evidence Base

分析の基礎データです。

{evidence_base}

### Period KPI
{chr(10).join(kpi_lines)}

### Latest Snapshot
{chr(10).join(latest_lines)}

### Alerts
{chr(10).join(alert_lines)}

---

## Channel Diagnostics

{channel_diagnostics_table}

---

## Site & LP Analysis

### Site Results
{site_results_table}

### Weak Pages
{weak_pages_table}

### Vision LP Analysis
{_markdown_table(["Site", "Page", "Design Analysis"], vision_rows) if vision_rows else "_Vision analysis not available_"}

---

## AB Test Backlog

{_markdown_table(["Priority", "Page", "Hypothesis", "Pattern A", "Pattern B", "Measure"], ab_test_rows)}

---

## Strategic Diagnosis

### Executive Diagnosis
{_build_executive_diagnosis(snapshot, recommendations, url_results)}

### Channel Deep Dive
{_build_channel_deep_dive(diagnostics)}

### LP / Site Deep Dive
{_build_site_deep_dive(url_results)}

### CRO Perspective
{_build_cro_perspectives(url_results)}

---

## Appendix

### 30-Day Roadmap
{_markdown_table(["Phase", "Goal", "What To Change", "KPI"], roadmap_rows)}

### 90-Day Transformation Program
{_markdown_table(["Window", "Theme", "Focus", "Owner", "Success Signal"], transformation_rows)}

### Measurement Plan
{_build_measurement_lines()}

### Expected Impact
{_build_expected_impact(snapshot, url_results)}

### Deep AI Analysis
- mode: {deep_analysis_mode}
- note: {deep_analysis.get("note", "deep analysis unavailable")}

{deep_analysis.get("body", "_deep analysis unavailable_")}

### Strategic LP Analysis

{_build_strategic_lp_section(url_results)}

### Site Crawl Errors
{chr(10).join(error_lines)}

### LLM Summary
{llm_summary or "LLM summary unavailable"}
"""

    # === SAVE MACHINE-READABLE OUTPUTS ===
    # Prepare JSON data
    report_json_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "generated_at": latest.get("latest_date"),
        "kpi": kpis,
        "latest": latest_totals,
        "latest_delta": latest_delta,
        "alerts": alerts,
        "do_actions": do_actions,
        "watch_actions": watch_actions,
        "ignore_actions": ignore_actions,
        "root_causes": root_cause_rows,
        "action_queue": action_queue_items,
    }
    
    # Prepare CSV data (action queue)
    action_csv_rows = [
        {
            "no": item["index"],
            "title": item["title"],
            "why_now": item["why_now"],
            "exact_change": item["exact_change"],
            "target": item["target"],
            "expected_kpi": item["kpi"],
            "effort": item["effort"],
            "due": item["due"],
            "dependency": item["dependency"],
        }
        for item in action_queue_items
    ]
    
    # Save JSON and CSV (async, non-blocking)
    
    def save_sidecars():
        try:
            save_report_json("daily_analysis", report_json_data, latest=True)
            save_report_csv("daily_analysis_actions", action_csv_rows, latest=True)
        except Exception as e:
            logger.warning(f"Failed to save JSON/CSV sidecars: {e}")
    
    # Use thread pool to save sidecars without blocking main report generation
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(save_sidecars)
    executor.shutdown(wait=False)
    
    return markdown_report
