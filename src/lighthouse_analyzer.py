"""
Lighthouse CLI を npx 経由で呼び出して JSON を取得し、重要指標を抽出するラッパー。
- 実行には Node.js と npm が必要（npx を使用）
- 出力 JSON を読み取り、Core Web Vitals と主要な Audit の要点を返す
"""
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

def run_lighthouse(url: str, output_dir: Optional[Path]=None, chrome_flags: str="--headless") -> Dict[str, Any]:
    """
    Lighthouse を実行し、JSON を返す。npx が使える想定。
    戻り値は lighthouse の JSON パース結果。
    """
    output_dir = Path(output_dir or "reports/lighthouse_tmp")
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_json = output_dir / "lighthouse_report.json"

    # Use npx to run lighthouse; write to tmp_json
    cmd = [
        "npx", "lighthouse", url,
        "--output=json",
        f"--output-path={str(tmp_json)}",
        f"--chrome-flags={chrome_flags}"
    ]
    # Optionally set timeout env in caller
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        # capture_output contains stdout/stderr for debugging
        raise RuntimeError(f"Lighthouse failed: {e.stderr}") from e

    # read JSON
    with tmp_json.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    return data

def summarize_lighthouse(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lighthouse JSON から取り出す最小限のサマリ:
    - categories (performance, accessibility, seo ...)
    - core web vitals (largest-contentful-paint, cumulative-layout-shift, total-blocking-time)
    - 主要な audits の失敗メッセージ
    """
    summary = {}
    categories = json_data.get("categories", {})
    summary["scores"] = {k: v.get("score") for k, v in categories.items()}

    audits = json_data.get("audits", {})
    vitals = {}
    # keys vary; check safe extraction
    for key in ["largest-contentful-paint", "cumulative-layout-shift", "total-blocking-time", "first-contentful-paint"]:
        if key in audits:
            vitals[key] = audits[key].get("displayValue") or audits[key].get("numericValue")

    summary["vitals"] = vitals

    # collect top failing audits
    failing = []
    for audit_id, audit in audits.items():
        score = audit.get("score")
        if score is False or (isinstance(score, (int, float)) and score < 0.9):
            failing.append({
                "id": audit_id,
                "title": audit.get("title"),
                "description": audit.get("description"),
                "score": score,
                "displayValue": audit.get("displayValue"),
            })
    # sort by score asc (failures first)
    failing_sorted = sorted(failing, key=lambda x: (x["score"] if x["score"] is not None else 0))
    summary["failing_audits"] = failing_sorted[:20]

    return summary