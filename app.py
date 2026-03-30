import os

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis import build_analysis_snapshot, read_mart
from src.etl import load_csv_to_duckdb
from src.recommend import generate_recommendations
from src.state import init_state, list_url_queue, sync_url_queue
from src.url_analyzer import analyze_site
from src.url_security import assert_safe_target_url
from src.url_targets import (
    load_target_urls,
    normalize_target_url,
    save_target_urls,
    target_urls_to_text,
)

TARGET_SITE_MAX_PAGES = int(os.getenv("TARGET_SITE_MAX_PAGES", "5"))


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
    return f"{float(value) * 100:.2f}%"


def _fmt_delta(value):
    if value is None or pd.isna(value):
        return None
    return f"{float(value) * 100:+.1f}%"


def _site_pages_frame(site_result: dict) -> pd.DataFrame:
    pages = []
    for page in site_result.get("pages", []):
        pages.append(
            {
                "url": page.get("url"),
                "score": page.get("score"),
                "cta_count": page.get("cta_count"),
                "h1_count": len(page.get("h1", [])),
                "h2_count": page.get("h2_count"),
                "has_case": page.get("has_case"),
                "has_faq": page.get("has_faq"),
                "has_pdf": page.get("has_pdf"),
                "findings": ", ".join(page.get("findings", [])[:4]) or "-",
                "improvements": ", ".join(page.get("improvements", [])[:4]) or "-",
            }
        )
    return pd.DataFrame(pages)


@st.cache_resource(show_spinner=False)
def _ensure_state():
    init_state()


@st.cache_data(show_spinner=False, ttl=30)
def _load_dashboard_data(refresh_token: int = 0) -> dict:
    del refresh_token
    load_result = load_csv_to_duckdb()
    df = read_mart()
    snapshot = build_analysis_snapshot(df)
    recs = generate_recommendations(
        snapshot["channels"],
        snapshot["diagnostics"],
        snapshot["alerts"],
    )
    return {
        "load_result": load_result,
        "snapshot": snapshot,
        "recommendations": recs,
        "target_urls": load_target_urls(),
        "queue_rows": list_url_queue(),
    }


def _invalidate_dashboard_data():
    _load_dashboard_data.clear()
    st.session_state["dashboard_refresh_token"] = st.session_state.get("dashboard_refresh_token", 0) + 1


def _parse_target_url_input(text: str) -> tuple[list[str], list[str]]:
    urls = []
    invalid_lines = []
    seen = set()

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        normalized = normalize_target_url(line)
        if not normalized:
            invalid_lines.append(f"{line_number}行目: {line}")
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        urls.append(normalized)

    return urls, invalid_lines


st.set_page_config(page_title="Marketing Auto Analyzer", layout="wide")
st.title("Marketing Auto Analyzer")
st.caption("無料モードでは CSV 分析とサイト診断をAPIなしで自動化できます。ローカルLLMを使う場合だけ Ollama を有効化してください。")

_ensure_state()

controls = st.columns([1, 5])
with controls[0]:
    if st.button("再読込", use_container_width=True):
        _invalidate_dashboard_data()
        st.rerun()

try:
    dashboard_data = _load_dashboard_data(st.session_state.get("dashboard_refresh_token", 0))
except FileNotFoundError:
    st.error("`data/raw/marketing.csv` が見つかりません。CSV を配置してから再読込してください。")
    st.stop()
except Exception as exc:
    st.error(f"ダッシュボード初期化でエラー: {exc}")
    st.stop()

load_result = dashboard_data["load_result"]
snapshot = dashboard_data["snapshot"]
recs = dashboard_data["recommendations"]
target_urls = dashboard_data["target_urls"]
queue_rows = dashboard_data["queue_rows"]

latest = snapshot["latest"]
kpis = snapshot["kpis"]
daily = snapshot["daily"]
channels = snapshot["channels"]
diagnostics = snapshot["diagnostics"]
alerts = snapshot["alerts"]

latest_metrics = latest.get("latest", {})
latest_delta = latest.get("delta_vs_previous", {})

st.caption(
    f"最新日: {latest.get('latest_date') or '-'} / 比較基準日: {latest.get('previous_date') or 'なし'} / "
    f"CSV同期: {load_result['status']}"
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Latest Sessions", _fmt_int(latest_metrics.get("sessions")), _fmt_delta(latest_delta.get("sessions")))
c2.metric("Latest Conversions", _fmt_int(latest_metrics.get("conversions")), _fmt_delta(latest_delta.get("conversions")))
c3.metric("Latest Revenue", _fmt_currency(latest_metrics.get("revenue")), _fmt_delta(latest_delta.get("revenue")))
c4.metric("Latest Cost", _fmt_currency(latest_metrics.get("cost")), _fmt_delta(latest_delta.get("cost")))
c5.metric("Latest ROAS", _fmt_ratio(latest_metrics.get("roas")), _fmt_delta(latest_delta.get("roas")))

with st.expander("期間合計KPI", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sessions", _fmt_int(kpis["sessions"]))
    c2.metric("Conversions", _fmt_int(kpis["conversions"]))
    c3.metric("Revenue", _fmt_currency(kpis["revenue"]))
    c4.metric("Cost", _fmt_currency(kpis["cost"]))
    st.write(
        f"CVR {_fmt_pct(kpis['cvr'])} / CPA {_fmt_currency(kpis['cpa'])} / "
        f"ROAS {_fmt_ratio(kpis['roas'])} / AOV {_fmt_currency(kpis['aov'])}"
    )

st.subheader("日次推移")
daily_chart = daily.melt(
    id_vars="date",
    value_vars=["revenue", "cost", "conversions"],
    var_name="metric",
    value_name="value",
)
fig = px.line(daily_chart, x="date", y="value", color="metric", markers=True)
st.plotly_chart(fig, width="stretch")

st.subheader("チャネル別サマリー")
channels_view = channels.copy()
channels_view["revenue"] = channels_view["revenue"].map(_fmt_currency)
channels_view["cost"] = channels_view["cost"].map(_fmt_currency)
channels_view["profit"] = channels_view["profit"].map(_fmt_currency)
channels_view["cvr"] = channels_view["cvr"].map(_fmt_pct)
channels_view["cpa"] = channels_view["cpa"].map(_fmt_currency)
channels_view["roas"] = channels_view["roas"].map(_fmt_ratio)
channels_view["revenue_share"] = channels_view["revenue_share"].map(_fmt_pct)
st.dataframe(
    channels_view[
        ["channel", "sessions", "conversions", "revenue", "cost", "profit", "cvr", "cpa", "roas", "revenue_share"]
    ],
    width="stretch",
)

st.subheader("チャネル診断")
diagnostics_view = diagnostics.copy()
if not diagnostics_view.empty:
    diagnostics_view["revenue"] = diagnostics_view["revenue"].map(_fmt_currency)
    diagnostics_view["cost"] = diagnostics_view["cost"].map(_fmt_currency)
    diagnostics_view["roas"] = diagnostics_view["roas"].map(_fmt_ratio)
    diagnostics_view["cvr"] = diagnostics_view["cvr"].map(_fmt_pct)
    diagnostics_view["revenue_delta_pct"] = diagnostics_view["revenue_delta_pct"].map(_fmt_delta)
    diagnostics_view["cost_delta_pct"] = diagnostics_view["cost_delta_pct"].map(_fmt_delta)
    diagnostics_view["cvr_delta_pct"] = diagnostics_view["cvr_delta_pct"].map(_fmt_delta)
    diagnostics_view["roas_delta_pct"] = diagnostics_view["roas_delta_pct"].map(_fmt_delta)
    st.dataframe(
        diagnostics_view[
            [
                "channel",
                "status",
                "revenue",
                "cost",
                "roas",
                "cvr",
                "revenue_delta_pct",
                "cost_delta_pct",
                "cvr_delta_pct",
                "roas_delta_pct",
                "reason",
                "recommended_action",
            ]
        ],
        width="stretch",
    )
else:
    st.info("診断できるチャネルデータがありません。")

st.subheader("異常検知")
if alerts:
    for alert in alerts:
        text = f"[{alert['severity'].upper()}] {alert['message']}"
        if alert["severity"] == "high":
            st.error(text)
        elif alert["severity"] == "medium":
            st.warning(text)
        else:
            st.info(text)
else:
    st.success("大きな異常は見つかりませんでした。")

st.subheader("優先アクション")
recs_view = pd.DataFrame(recs)
if not recs_view.empty:
    st.dataframe(
        recs_view[["priority", "channel", "issue", "action", "reason"]],
        width="stretch",
    )
else:
    st.info("改善提案はありません。")

st.subheader("対象サイト設定")
st.caption("1行に1URLで登録してください。public な http/https のみ許可し、保存すると worker が即再解析できる状態に戻します。")

url_text = st.text_area(
    "対象サイトURL一覧",
    value=target_urls_to_text(target_urls),
    height=140,
    help="例: https://example.com/service",
)

if st.button("対象サイト一覧を保存"):
    parsed_urls, invalid_lines = _parse_target_url_input(url_text)
    invalid_urls = [f"- {line}: URL形式が不正です" for line in invalid_lines]
    for url in parsed_urls:
        try:
            assert_safe_target_url(url)
        except ValueError as exc:
            invalid_urls.append(f"- {url}: {exc}")

    if invalid_urls:
        st.error("保存できないURLがあります。\n" + "\n".join(invalid_urls))
    else:
        save_target_urls(parsed_urls)
        sync_url_queue(parsed_urls, base_priority=10, reset_existing=True)
        _invalidate_dashboard_data()
        st.success(f"{len(parsed_urls)}件の対象サイトを保存しました。")
        st.rerun()

if queue_rows:
    queue_df = pd.DataFrame(queue_rows)
    st.dataframe(queue_df, width="stretch")
else:
    st.info("まだ対象サイトが登録されていません。")

st.subheader("サイト診断")
default_site_url = target_urls[0] if target_urls else "https://service.daitecjp.com/index.php/manual-production/"
site_url = st.text_input("診断する起点URL", default_site_url)
site_page_limit = st.slider("巡回ページ数", min_value=1, max_value=10, value=min(max(TARGET_SITE_MAX_PAGES, 1), 10))

if st.button("サイト全体を診断"):
    try:
        assert_safe_target_url(site_url)
        result = analyze_site(site_url, max_pages=site_page_limit)
        weakest_page = (result.get("weak_pages") or [None])[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("平均Score", result["score"])
        c2.metric("分析ページ数", result["page_count"])
        c3.metric("弱いページScore", weakest_page.get("score") if weakest_page else "-")
        c4.metric("巡回エラー数", len(result.get("errors", [])))

        st.write("**サイト所見**")
        for item in result.get("site_findings", []):
            st.write(f"- {item}")

        st.write("**サイト改善提案**")
        for item in result.get("site_improvements", []):
            st.write(f"- {item}")

        pages_df = _site_pages_frame(result)
        if not pages_df.empty:
            st.write("**ページ別詳細**")
            st.dataframe(pages_df, width="stretch")

        if result.get("errors"):
            st.write("**巡回エラー**")
            for error in result["errors"]:
                st.write(f"- {error['url']}: {error['error']}")

    except Exception as exc:
        st.error(f"サイト診断でエラー: {exc}")
