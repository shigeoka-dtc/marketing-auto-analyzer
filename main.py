from src.analysis import build_analysis_snapshot, read_mart
from src.etl import load_csv_to_duckdb
from src.recommend import generate_recommendations
from src.report import render_marketing_report, save_report


if __name__ == "__main__":
    load_result = load_csv_to_duckdb()
    df = read_mart()
    snapshot = build_analysis_snapshot(df)
    recommendations = generate_recommendations(
        snapshot["channels"],
        snapshot["diagnostics"],
        snapshot["alerts"],
    )
    report = render_marketing_report(
        snapshot=snapshot,
        recommendations=recommendations,
        url_results=[],
        llm_summary="CLI実行のためLLM要約は未生成",
    )
    path = save_report("manual_analysis", report)
    print(f"CSV同期: {load_result['status']}")
    print(f"分析レポートを生成しました: {path}")
