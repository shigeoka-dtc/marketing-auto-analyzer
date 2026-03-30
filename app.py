import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis import build_analysis_snapshot, read_mart
from src.etl import load_csv_to_duckdb
from src.recommend import generate_recommendations
from src.url_analyzer import analyze_url


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


st.set_page_config(page_title="Marketing Auto Analyzer", layout="wide")
st.title("Marketing Auto Analyzer")

load_result = load_csv_to_duckdb()
df = read_mart()
snapshot = build_analysis_snapshot(df)
latest = snapshot["latest"]
kpis = snapshot["kpis"]
daily = snapshot["daily"]
channels = snapshot["channels"]
diagnostics = snapshot["diagnostics"]
alerts = snapshot["alerts"]
recs = generate_recommendations(channels, diagnostics, alerts)

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

st.subheader("URL診断")
target_url = st.text_input("診断するURL", "https://service.daitecjp.com/index.php/manual-production/")

if st.button("URLを診断"):
    try:
        result = analyze_url(target_url)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Score", result["score"])
        c2.metric("CTA数", result["cta_count"])
        c3.metric("H1数", len(result["h1"]))
        c4.metric("H2数", result["h2_count"])

        st.write("**Title**")
        st.write(result["title"])

        st.write("**H1**")
        st.write(result["h1"] if result["h1"] else "なし")

        st.write("**CTA一覧**")
        st.write(result["unique_ctas"])

        st.write("**検出項目**")
        st.json(
            {
                "has_faq": result["has_faq"],
                "has_case": result["has_case"],
                "has_pdf": result["has_pdf"],
            }
        )

        st.write("**改善提案**")
        for item in result["improvements"]:
            st.write(f"- {item}")

    except Exception as e:
        st.error(f"URL診断でエラー: {e}")
