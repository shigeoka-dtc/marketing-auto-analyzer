from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from src.llm_client import OLLAMA_ENABLED, VISION_ANALYSIS_ENABLED, ask_llm, ask_llm_vision
from src.llm_helper import load_prompt
from src.report import save_report, save_report_json

BASE_NUMERIC_METRICS = [
    "impressions",
    "clicks",
    "sessions",
    "users",
    "conversions",
    "revenue",
    "cost",
]
RATE_METRICS = ["ctr", "cvr", "cpa", "roas", "cpc"]
ALL_METRICS = [*BASE_NUMERIC_METRICS, *RATE_METRICS]

ALIAS_PATTERNS = {
    "date": ["date", "day", "timestamp", "time", "datetime", "日付", "年月日"],
    "channel": ["channel", "source", "media", "platform", "媒体", "流入元"],
    "campaign": ["campaign", "campaignname", "adgroup", "adset", "広告", "キャンペーン"],
    "impressions": ["impressions", "impression", "imp", "表示回数"],
    "clicks": ["clicks", "click", "クリック"],
    "sessions": ["sessions", "session", "visits", "traffic", "アクセス", "訪問"],
    "users": ["users", "user", "visitors", "visitor", "uu", "ユーザー"],
    "conversions": [
        "conversions",
        "conversion",
        "orders",
        "order",
        "purchases",
        "purchase",
        "leads",
        "lead",
        "cv",
        "成果件数",
        "成約",
        "申込",
        "問い合わせ",
    ],
    "revenue": ["revenue", "sales", "gmv", "value", "売上", "売上金額"],
    "cost": ["cost", "spend", "adspend", "広告費", "費用", "利用額"],
    "ctr": ["ctr", "clickthroughrate", "クリック率"],
    "cvr": ["cvr", "conversionrate", "convrate", "cv率", "成約率", "申込率"],
    "cpa": ["cpa", "cac", "獲得単価"],
    "roas": ["roas", "roi", "投資対効果"],
    "cpc": ["cpc", "クリック単価"],
}


@dataclass
class CsvIssue:
    severity: int
    issue_code: str
    subject: str
    symptom: str
    evidence: str
    root_cause: str
    recommendation: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "issue_code": self.issue_code,
            "subject": self.subject,
            "symptom": self.symptom,
            "evidence": self.evidence,
            "root_cause": self.root_cause,
            "recommendation": self.recommendation,
        }


def _normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[^a-z0-9一-龠ぁ-んァ-ヴー]+", "", text)


def _safe_ratio(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


def _fmt_number(value: float | int | None, digits: int = 0) -> str:
    if value is None or pd.isna(value):
        return "-"
    if digits == 0:
        return f"{float(value):,.0f}"
    return f"{float(value):,.{digits}f}"


def _fmt_currency(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"¥{float(value):,.0f}"


def _fmt_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def _fmt_ratio(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.2f}"


def _shorten(text: str, limit: int = 1200) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _infer_column_map(columns: Sequence[str]) -> dict[str, str]:
    normalized = {column: _normalize_label(column) for column in columns}
    mapping: dict[str, str] = {}
    used_columns: set[str] = set()

    for key, aliases in ALIAS_PATTERNS.items():
        best_column = None
        best_score = -1
        for column, label in normalized.items():
            if column in used_columns:
                continue
            score = -1
            for alias in aliases:
                if label == alias:
                    score = max(score, 100 + len(alias))
                elif alias and alias in label:
                    score = max(score, 50 + len(alias))
            if score > best_score:
                best_column = column
                best_score = score
        if best_column and best_score > 0:
            mapping[key] = best_column
            used_columns.add(best_column)

    return mapping


def _coerce_numeric(series: pd.Series, metric: str) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(series, errors="coerce")
    else:
        percent_like = series.astype(str).str.contains(r"%|％", regex=True, na=False).mean() >= 0.3
        numeric = pd.to_numeric(
            series.astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("¥", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.replace("％", "", regex=False)
            .str.replace(r"[^\d\.\-]", "", regex=True),
            errors="coerce",
        )
        if percent_like and metric in {"ctr", "cvr"}:
            numeric = numeric / 100.0

    if metric in {"ctr", "cvr"}:
        sample = numeric.dropna()
        if not sample.empty and sample.median() > 1.5:
            numeric = numeric / 100.0
    return numeric


def _prepare_dataframe(df: pd.DataFrame, column_map: dict[str, str]) -> tuple[pd.DataFrame, dict[str, str]]:
    prepared = df.copy()
    meta: dict[str, str] = {}

    for key, column in column_map.items():
        if key == "date":
            parsed = pd.to_datetime(prepared[column], errors="coerce")
            if parsed.notna().sum() >= max(2, len(prepared) * 0.6):
                prepared["__date"] = parsed
                meta["date"] = "__date"
        elif key in {"channel", "campaign"}:
            prepared[f"__{key}"] = prepared[column].fillna("unknown").astype(str).str.strip()
            meta[key] = f"__{key}"
        else:
            prepared[f"__{key}"] = _coerce_numeric(prepared[column], key)
            meta[key] = f"__{key}"

    return prepared, meta


def _aggregate_metrics(df: pd.DataFrame, meta: dict[str, str]) -> dict[str, float | None]:
    metrics: dict[str, float | None] = {}
    for metric in BASE_NUMERIC_METRICS:
        column = meta.get(metric)
        metrics[metric] = float(df[column].sum()) if column else None

    ctr = None
    cvr = None
    cpa = None
    roas = None
    cpc = None

    if meta.get("ctr"):
        ctr = float(df[meta["ctr"]].mean())
    elif metrics.get("clicks") is not None and metrics.get("impressions") is not None:
        ctr = _safe_ratio(metrics["clicks"], metrics["impressions"])

    if meta.get("cvr"):
        cvr = float(df[meta["cvr"]].mean())
    elif metrics.get("conversions") is not None:
        if metrics.get("clicks"):
            cvr = _safe_ratio(metrics["conversions"], metrics["clicks"])
        elif metrics.get("sessions"):
            cvr = _safe_ratio(metrics["conversions"], metrics["sessions"])

    if meta.get("cpa"):
        cpa = float(df[meta["cpa"]].mean())
    elif metrics.get("cost") is not None and metrics.get("conversions") is not None:
        cpa = _safe_ratio(metrics["cost"], metrics["conversions"])

    if meta.get("roas"):
        roas = float(df[meta["roas"]].mean())
    elif metrics.get("revenue") is not None and metrics.get("cost") is not None:
        roas = _safe_ratio(metrics["revenue"], metrics["cost"])

    if meta.get("cpc"):
        cpc = float(df[meta["cpc"]].mean())
    elif metrics.get("cost") is not None and metrics.get("clicks") is not None:
        cpc = _safe_ratio(metrics["cost"], metrics["clicks"])

    metrics.update(
        {
            "ctr": ctr,
            "cvr": cvr,
            "cpa": cpa,
            "roas": roas,
            "cpc": cpc,
        }
    )
    return metrics


def _pick_primary_dimension(df: pd.DataFrame, meta: dict[str, str]) -> tuple[str | None, str | None]:
    for key in ("channel", "campaign"):
        column = meta.get(key)
        if column and df[column].nunique(dropna=True) >= 2:
            return key, column

    object_columns = [
        column
        for column in df.columns
        if not column.startswith("__")
        and df[column].dtype == "object"
        and 1 < df[column].nunique(dropna=True) <= min(20, max(len(df) // 2, 2))
    ]
    if object_columns:
        return object_columns[0], object_columns[0]
    return None, None


def _group_dimension_summary(df: pd.DataFrame, meta: dict[str, str], dimension_column: str | None) -> pd.DataFrame:
    if not dimension_column:
        overall = _aggregate_metrics(df, meta)
        overall["segment"] = "overall"
        return pd.DataFrame([overall])

    rows: list[dict[str, Any]] = []
    for segment, segment_df in df.groupby(dimension_column, dropna=False):
        row = _aggregate_metrics(segment_df, meta)
        row["segment"] = str(segment)
        rows.append(row)

    summary = pd.DataFrame(rows)
    total_cost = float(summary["cost"].sum()) if "cost" in summary.columns else 0.0
    total_revenue = float(summary["revenue"].sum()) if "revenue" in summary.columns else 0.0
    if total_cost:
        summary["cost_share"] = summary["cost"].fillna(0.0) / total_cost
    else:
        summary["cost_share"] = 0.0
    if total_revenue:
        summary["revenue_share"] = summary["revenue"].fillna(0.0) / total_revenue
    else:
        summary["revenue_share"] = 0.0

    sort_columns = [column for column in ["cost", "revenue", "conversions", "clicks"] if column in summary.columns]
    if sort_columns:
        summary = summary.sort_values(sort_columns, ascending=False).reset_index(drop=True)
    return summary


def _detect_segment_issues(grouped: pd.DataFrame, overall_metrics: dict[str, Any]) -> tuple[list[CsvIssue], list[str]]:
    issues: list[CsvIssue] = []
    opportunities: list[str] = []
    if grouped.empty:
        return issues, opportunities

    overall_ctr = overall_metrics.get("ctr")
    overall_cvr = overall_metrics.get("cvr")
    overall_roas = overall_metrics.get("roas")

    for _, row in grouped.iterrows():
        segment = row["segment"]
        cost = row.get("cost")
        revenue = row.get("revenue")
        conversions = row.get("conversions")
        ctr = row.get("ctr")
        cvr = row.get("cvr")
        roas = row.get("roas")
        cost_share = float(row.get("cost_share", 0.0) or 0.0)
        revenue_share = float(row.get("revenue_share", 0.0) or 0.0)

        if cost and cost > 0 and (conversions is None or conversions <= 0):
            issues.append(
                CsvIssue(
                    severity=100,
                    issue_code="zero_conversion",
                    subject=segment,
                    symptom="費用投下があるのにCVが発生していません。",
                    evidence=f"費用 { _fmt_currency(cost) } / CV {_fmt_number(conversions)}",
                    root_cause="計測漏れか、訴求とLPオファーのミスマッチが強い可能性があります。",
                    recommendation="まず計測異常を確認し、その後このセグメントは一時抑制しつつ訴求とCTAを全面見直ししてください。",
                )
            )

        if cost_share >= 0.15 and roas is not None and roas < 1.2:
            issues.append(
                CsvIssue(
                    severity=85,
                    issue_code="low_roas_high_spend",
                    subject=segment,
                    symptom="大きな予算を使っている割にROASが低いです。",
                    evidence=f"ROAS {_fmt_ratio(roas)} / 費用シェア {_fmt_pct(cost_share)} / 売上シェア {_fmt_pct(revenue_share)}",
                    root_cause="予算配分が効率の低い配信面や訴求に寄っている可能性が高いです。",
                    recommendation="成果上位セグメントへ予算を再配分し、このセグメントは配信面・入札・クリエイティブを絞って再学習させてください。",
                )
            )

        if cost_share >= 0.1 and cvr is not None:
            cvr_threshold = min(0.02, (overall_cvr or 0.02) * 0.7) if overall_cvr else 0.02
            if cvr < cvr_threshold:
                issues.append(
                    CsvIssue(
                        severity=75,
                        issue_code="low_cvr",
                        subject=segment,
                        symptom="流入後のCVRが弱いです。",
                        evidence=f"CVR {_fmt_pct(cvr)} / 全体CVR {_fmt_pct(overall_cvr)} / 費用シェア {_fmt_pct(cost_share)}",
                        root_cause="LPのファーストビュー、オファー理解、CTA導線、フォーム摩擦のどこかで失速している可能性が高いです。",
                        recommendation="この流入向けにFVの訴求、主CTA、フォーム項目数をセットで見直してください。",
                    )
                )

        if ctr is not None:
            ctr_threshold = min(0.01, (overall_ctr or 0.01) * 0.7) if overall_ctr else 0.01
            if ctr < ctr_threshold:
                issues.append(
                    CsvIssue(
                        severity=60,
                        issue_code="low_ctr",
                        subject=segment,
                        symptom="流入前の反応率が弱いです。",
                        evidence=f"CTR {_fmt_pct(ctr)} / 全体CTR {_fmt_pct(overall_ctr)}",
                        root_cause="ターゲットに対するメッセージの刺さりやクリエイティブの視認性が不足している可能性があります。",
                        recommendation="見出し・サムネイル・オファーの一貫性を見直し、最上位のベネフィットを前面に出した訴求に差し替えてください。",
                    )
                )

        if (
            roas is not None
            and overall_roas is not None
            and roas >= max(overall_roas * 1.2, 2.5)
            and cost_share <= 0.25
        ):
            opportunities.append(
                f"{segment}: ROAS {_fmt_ratio(roas)} と効率が高く、費用シェア {_fmt_pct(cost_share)} のため段階的な増額候補です。"
            )

    issues.sort(key=lambda item: item.severity, reverse=True)
    seen = set()
    deduped: list[CsvIssue] = []
    for issue in issues:
        key = (issue.issue_code, issue.subject)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)

    return deduped[:5], opportunities[:3]


def _detect_time_signals(df: pd.DataFrame, meta: dict[str, str]) -> list[str]:
    date_column = meta.get("date")
    if not date_column:
        return []

    valid_df = df[df[date_column].notna()].copy()
    if valid_df.empty or valid_df[date_column].dt.date.nunique() < 2:
        return []

    rows: list[dict[str, Any]] = []
    for date_value, date_df in valid_df.groupby(valid_df[date_column].dt.date):
        metrics = _aggregate_metrics(date_df, meta)
        metrics["date"] = str(date_value)
        rows.append(metrics)
    daily = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    latest = daily.iloc[-1]
    previous = daily.iloc[-2]

    signals: list[str] = []
    latest_cost = latest.get("cost")
    previous_cost = previous.get("cost")
    latest_revenue = latest.get("revenue")
    previous_revenue = previous.get("revenue")
    latest_conversions = latest.get("conversions")
    previous_conversions = previous.get("conversions")

    if previous_cost and previous_revenue:
        if latest_cost and latest_cost > previous_cost * 1.15 and latest_revenue is not None and latest_revenue < previous_revenue * 0.9:
            signals.append(
                f"{latest['date']}: 費用は前期間比で増えている一方、売上は減少しています。配信効率悪化か学習の乱れを疑うべきです。"
            )

    if previous_conversions and latest_conversions is not None and latest_conversions < previous_conversions * 0.9:
        signals.append(
            f"{latest['date']}: CV数が直前期間より落ちています。流入品質の変化かLP摩擦の増加を確認してください。"
        )

    if previous.get("ctr") and latest.get("ctr") is not None and latest["ctr"] < previous["ctr"] * 0.85:
        signals.append(
            f"{latest['date']}: CTRが直前期間より落ちています。クリエイティブ疲弊やメッセージの鮮度低下が起きている可能性があります。"
        )

    return signals[:3]


def _build_csv_evidence(
    path: Path,
    df: pd.DataFrame,
    column_map: dict[str, str],
    overall_metrics: dict[str, Any],
    grouped: pd.DataFrame,
    dimension_name: str | None,
    time_signals: list[str],
) -> list[str]:
    evidence = [
        f"{path.name}: {len(df):,}行 x {len(df.columns)}列",
        f"認識カラム: {json.dumps(column_map, ensure_ascii=False)}",
    ]

    metric_parts = []
    if overall_metrics.get("cost") is not None:
        metric_parts.append(f"費用 {_fmt_currency(overall_metrics.get('cost'))}")
    if overall_metrics.get("revenue") is not None:
        metric_parts.append(f"売上 {_fmt_currency(overall_metrics.get('revenue'))}")
    if overall_metrics.get("conversions") is not None:
        metric_parts.append(f"CV {_fmt_number(overall_metrics.get('conversions'))}")
    if overall_metrics.get("roas") is not None:
        metric_parts.append(f"ROAS {_fmt_ratio(overall_metrics.get('roas'))}")
    if overall_metrics.get("cvr") is not None:
        metric_parts.append(f"CVR {_fmt_pct(overall_metrics.get('cvr'))}")
    if overall_metrics.get("ctr") is not None:
        metric_parts.append(f"CTR {_fmt_pct(overall_metrics.get('ctr'))}")
    if metric_parts:
        evidence.append(f"全体KPI: {' / '.join(metric_parts)}")

    if dimension_name and not grouped.empty:
        top_rows = grouped.head(3)
        for _, row in top_rows.iterrows():
            evidence.append(
                f"{dimension_name}={row['segment']}: 費用 {_fmt_currency(row.get('cost'))} / 売上 {_fmt_currency(row.get('revenue'))} / CV {_fmt_number(row.get('conversions'))} / ROAS {_fmt_ratio(row.get('roas'))} / CVR {_fmt_pct(row.get('cvr'))}"
            )

    evidence.extend(time_signals)
    return evidence


def _build_csv_markdown(
    path: Path,
    dimension_name: str | None,
    issues: list[CsvIssue],
    opportunities: list[str],
    time_signals: list[str],
    evidence: list[str],
) -> str:
    lines = [
        f"### CSV分析: {path.name}",
        "",
        "#### 主要所見",
    ]

    if issues:
        for issue in issues[:3]:
            lines.append(f"- {issue.subject}: {issue.symptom} 根拠: {issue.evidence}")
    else:
        lines.append("- 大きな悪化シグナルは限定的です。現状は勝ちセグメントの横展開が主テーマです。")

    if opportunities:
        lines.extend(["", "#### 伸ばせる論点"])
        for item in opportunities:
            lines.append(f"- {item}")

    if time_signals:
        lines.extend(["", "#### 時系列シグナル"])
        for signal in time_signals:
            lines.append(f"- {signal}")

    lines.extend(["", "#### 根拠データ"])
    for item in evidence:
        lines.append(f"- {item}")

    lines.extend(["", "#### 改善提案"])
    if issues:
        for issue in issues[:3]:
            lines.append(f"- {issue.subject}: {issue.recommendation}")
    else:
        scope = dimension_name or "主要セグメント"
        lines.append(f"- {scope}: 高効率セグメントの訴求と配信条件を基準化し、増額テストを行ってください。")

    return "\n".join(lines)


def analyze_uploaded_csv(csv_path: str | os.PathLike[str]) -> dict[str, Any]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"CSV is empty: {path}")

    column_map = _infer_column_map(df.columns)
    prepared, meta = _prepare_dataframe(df, column_map)
    overall_metrics = _aggregate_metrics(prepared, meta)
    dimension_name, dimension_column = _pick_primary_dimension(prepared, meta)
    grouped = _group_dimension_summary(prepared, meta, dimension_column)
    issues, opportunities = _detect_segment_issues(grouped, overall_metrics)
    time_signals = _detect_time_signals(prepared, meta)
    evidence = _build_csv_evidence(
        path=path,
        df=df,
        column_map=column_map,
        overall_metrics=overall_metrics,
        grouped=grouped,
        dimension_name=dimension_name,
        time_signals=time_signals,
    )
    markdown = _build_csv_markdown(
        path=path,
        dimension_name=dimension_name,
        issues=issues,
        opportunities=opportunities,
        time_signals=time_signals,
        evidence=evidence,
    )

    return {
        "path": str(path),
        "rows": len(df),
        "columns": list(df.columns),
        "column_map": column_map,
        "dimension": dimension_name,
        "overall_metrics": overall_metrics,
        "issues": [issue.as_dict() for issue in issues],
        "opportunities": opportunities,
        "time_signals": time_signals,
        "evidence": evidence,
        "markdown": markdown,
    }


def analyze_uploaded_image(
    image_path: str | os.PathLike[str],
    notes: str = "",
    skip_llm: bool = False,
) -> dict[str, Any]:
    path = Path(image_path)
    if not path.exists():
        return {
            "path": str(path),
            "status": "error",
            "reason": f"Image not found: {path}",
        }

    if skip_llm:
        return {
            "path": str(path),
            "status": "skipped",
            "reason": "skip_llm=true",
        }

    if not (OLLAMA_ENABLED and VISION_ANALYSIS_ENABLED):
        return {
            "path": str(path),
            "status": "skipped",
            "reason": "Vision analysis is disabled",
        }

    prompt_template = load_prompt("vision_heatmap_analysis.md")
    prompt = (
        prompt_template.replace("{{filename}}", path.name)
        .replace("{{notes}}", notes or "なし")
    )
    response = ask_llm_vision(prompt, [str(path)], num_predict=1400)
    if response.startswith("[Vision LLM"):
        return {
            "path": str(path),
            "status": "error",
            "reason": response,
        }

    return {
        "path": str(path),
        "status": "success",
        "analysis": response,
        "summary": _shorten(response, limit=700),
    }


def _build_cross_source_hypotheses(csv_analyses: list[dict[str, Any]], image_analyses: list[dict[str, Any]]) -> list[str]:
    hypotheses: list[str] = []

    csv_issue_codes = {
        issue["issue_code"]
        for analysis in csv_analyses
        for issue in analysis.get("issues", [])
    }
    image_text = " ".join(
        analysis.get("analysis", "")
        for analysis in image_analyses
        if analysis.get("status") == "success"
    ).lower()

    if "low_cvr" in csv_issue_codes:
        if any(keyword in image_text for keyword in ["cta", "first view", "ファーストビュー", "スクロール", "視線"]):
            hypotheses.append("CVR低下は、流入品質だけでなくLPの訴求順とCTA視認性の弱さが主因である可能性が高いです。")
        else:
            hypotheses.append("CVR低下が見えているため、LPのオファー理解不足かフォーム摩擦を最優先で疑うべきです。")

    if "low_ctr" in csv_issue_codes:
        hypotheses.append("CTR低下は、広告やクリエイティブのベネフィット提示が弱く、期待と実際のランディング内容にズレがある可能性があります。")

    if "low_roas_high_spend" in csv_issue_codes:
        hypotheses.append("高コスト低ROASの構造があるため、配信面の最適化より先に予算配分の是正を行う価値が高いです。")

    if "zero_conversion" in csv_issue_codes:
        hypotheses.append("CVゼロのセグメントは、まず計測異常の有無を確認し、その後に訴求・オファーの根本見直しを行うべきです。")

    if image_text and not hypotheses:
        hypotheses.append("画像所見からは、視線の集まり方とCTA導線の整理が成果改善の起点になりそうです。")

    return hypotheses[:4]


def _build_priority_actions(csv_analyses: list[dict[str, Any]], image_analyses: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    for analysis in csv_analyses:
        for issue in analysis.get("issues", [])[:3]:
            actions.append(f"{issue['subject']}: {issue['recommendation']}")
    for analysis in image_analyses:
        if analysis.get("status") == "success":
            actions.append("ヒートマップ画像: 視線集中エリアと無視領域をもとに、FVのコピーとCTA配置を再設計してください。")
            break

    deduped: list[str] = []
    seen = set()
    for action in actions:
        if action in seen:
            continue
        seen.add(action)
        deduped.append(action)
    return deduped[:5]


def _build_rule_based_report(
    csv_analyses: list[dict[str, Any]],
    image_analyses: list[dict[str, Any]],
    notes: str,
) -> str:
    cross_hypotheses = _build_cross_source_hypotheses(csv_analyses, image_analyses)
    actions = _build_priority_actions(csv_analyses, image_analyses)

    lines = [
        "# Uploaded Marketing Asset Analysis",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        "## 結論",
    ]

    if cross_hypotheses:
        for item in cross_hypotheses[:3]:
            lines.append(f"- {item}")
    else:
        lines.append("- まだ十分な根拠が少ないため、まずはCSVの主要KPIと画像所見を追加で確認してください。")

    lines.extend(["", "## 最優先アクション"])
    if actions:
        for item in actions[:3]:
            lines.append(f"1. {item}")
    else:
        lines.append("1. 追加データが少ないため、まずは費用・CV・売上のあるCSVを投入してください。")

    if notes:
        lines.extend(["", "## 依頼メモ", f"- {notes}"])

    lines.extend(["", "## CSV所見"])
    if csv_analyses:
        for analysis in csv_analyses:
            lines.append(analysis["markdown"])
            lines.append("")
    else:
        lines.append("- CSVは未投入です。")

    lines.extend(["## 画像所見"])
    if image_analyses:
        for analysis in image_analyses:
            path_label = Path(analysis["path"]).name
            if analysis.get("status") == "success":
                lines.extend(
                    [
                        f"### 画像分析: {path_label}",
                        "",
                        _shorten(analysis.get("analysis", ""), limit=1600),
                        "",
                    ]
                )
            else:
                lines.append(f"- {path_label}: {analysis.get('reason', '画像分析を実行できませんでした。')}")
    else:
        lines.append("- 画像は未投入です。")

    lines.extend(
        [
            "",
            "## 次に見るべき追加データ",
            "- クリエイティブ別 CTR / CVR",
            "- LP別の CTA クリック率、フォーム開始率、フォーム完了率",
            "- デバイス別のCVR差分とページ表示速度",
        ]
    )

    return "\n".join(lines).strip()


def _render_llm_synthesis(
    csv_analyses: list[dict[str, Any]],
    image_analyses: list[dict[str, Any]],
    notes: str,
    fallback_markdown: str,
) -> str:
    if not OLLAMA_ENABLED:
        return fallback_markdown

    csv_evidence = []
    for analysis in csv_analyses:
        csv_evidence.extend(analysis.get("evidence", []))
        for issue in analysis.get("issues", [])[:3]:
            csv_evidence.append(
                f"{Path(analysis['path']).name} / {issue['subject']} / 症状: {issue['symptom']} / 根本原因仮説: {issue['root_cause']} / 提案: {issue['recommendation']}"
            )

    image_evidence = []
    for analysis in image_analyses:
        if analysis.get("status") == "success":
            image_evidence.append(f"{Path(analysis['path']).name}: {_shorten(analysis.get('analysis', ''), 1200)}")
        else:
            image_evidence.append(f"{Path(analysis['path']).name}: {analysis.get('reason', 'skip')}")

    template = load_prompt("upload_marketing_analysis.md")
    prompt = (
        template.replace("{{notes}}", notes or "なし")
        .replace("{{csv_evidence}}", "\n".join(f"- {item}" for item in csv_evidence) or "- なし")
        .replace("{{image_evidence}}", "\n".join(f"- {item}" for item in image_evidence) or "- なし")
        .replace("{{fallback_markdown}}", fallback_markdown)
    )

    response = ask_llm(prompt, num_predict=1800)
    if response.startswith("[LLM"):
        return fallback_markdown
    return response.strip()


def analyze_uploaded_marketing_assets(
    *,
    csv_paths: Sequence[str] | None = None,
    image_paths: Sequence[str] | None = None,
    notes: str = "",
    skip_llm: bool = False,
    save_outputs: bool = True,
) -> dict[str, Any]:
    csv_paths = list(csv_paths or [])
    image_paths = list(image_paths or [])

    if not csv_paths and not image_paths:
        raise ValueError("At least one CSV or image path is required.")

    csv_analyses = [analyze_uploaded_csv(path) for path in csv_paths]
    image_analyses = [
        analyze_uploaded_image(path, notes=notes, skip_llm=skip_llm)
        for path in image_paths
    ]

    rule_based_markdown = _build_rule_based_report(csv_analyses, image_analyses, notes)
    final_markdown = rule_based_markdown if skip_llm else _render_llm_synthesis(
        csv_analyses=csv_analyses,
        image_analyses=image_analyses,
        notes=notes,
        fallback_markdown=rule_based_markdown,
    )

    report_path = None
    json_path = None
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "notes": notes,
        "csv_analyses": csv_analyses,
        "image_analyses": image_analyses,
        "rule_based_markdown": rule_based_markdown,
        "final_markdown": final_markdown,
    }

    if save_outputs:
        report_path = save_report("uploaded_marketing_asset_analysis", final_markdown)
        json_path = save_report_json("uploaded_marketing_asset_analysis", payload, latest=True)

    payload.update(
        {
            "status": "success",
            "report_path": report_path,
            "json_path": json_path,
        }
    )
    return payload
