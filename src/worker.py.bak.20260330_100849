import time
from datetime import datetime

from src.state import init_state, enqueue_url, fetch_next_urls, mark_url_done
from src.etl import load_csv_to_duckdb
from src.analysis import read_mart, total_kpis, channel_summary, detect_anomalies
from src.recommend import generate_recommendations
from src.url_analyzer import analyze_url
from src.report import save_report
from src.llm_client import ask_llm

SLEEP_SECONDS = 600

SEED_URLS = [
    "https://service.daitecjp.com/index.php/manual-production/"
]

def run_cycle():
    init_state()

    for url in SEED_URLS:
        enqueue_url(url, priority=10)

    load_csv_to_duckdb()

    df = read_mart()
    kpis = total_kpis(df)
    channels = channel_summary(df)
    alerts = detect_anomalies(df)
    recs = generate_recommendations(channels)

    url_results = []
    for url in fetch_next_urls(limit=3):
        result = analyze_url(url)
        url_results.append(result)
        mark_url_done(url)

    prompt = f"""
あなたはB2Bマーケ分析官です。
以下の数値とURL診断から、今日やるべき改善を優先順で3つに絞ってください。

KPI:
{kpis}

Alerts:
{alerts}

Recommendations:
{recs}

URL Results:
{url_results}
"""
    llm_summary = ask_llm(prompt)

    report = f"""# Daily Marketing Analysis
Generated: {datetime.utcnow().isoformat()}

## KPI
{kpis}

## Alerts
{alerts}

## Rule-based Recommendations
{recs}

## URL Results
{url_results}

## LLM Summary
{llm_summary}
"""
    save_report("daily_analysis", report)

if __name__ == "__main__":
    while True:
        try:
            run_cycle()
        except Exception as e:
            save_report("worker_error", f"# Worker Error\n\n{e}")
        time.sleep(SLEEP_SECONDS)