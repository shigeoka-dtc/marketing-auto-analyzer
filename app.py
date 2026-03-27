import streamlit as st
import plotly.express as px

from src.analysis import read_mart, total_kpis, channel_summary, detect_anomalies
from src.recommend import generate_recommendations
from src.url_analyzer import analyze_url
from src.etl import load_csv_to_duckdb

st.set_page_config(page_title="Marketing Auto Analyzer", layout="wide")
st.title("Marketing Auto Analyzer")

load_csv_to_duckdb()
df = read_mart()
kpis = total_kpis(df)
channels = channel_summary(df)
alerts = detect_anomalies(df)
recs = generate_recommendations(channels)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Sessions", f'{kpis["sessions"]:,}')
c2.metric("Conversions", f'{kpis["conversions"]:,}')
c3.metric("Revenue", f'¥{kpis["revenue"]:,.0f}')
c4.metric("Cost", f'¥{kpis["cost"]:,.0f}')
c5.metric("ROAS", f'{kpis["roas"]:.2f}')

st.subheader("日次売上推移")
daily = df.groupby("date", as_index=False)["revenue"].sum()
fig = px.line(daily, x="date", y="revenue")
st.plotly_chart(fig, width="stretch")

st.subheader("チャネル別サマリー")
st.dataframe(channels, width="stretch")

st.subheader("異常検知")
if alerts:
    for a in alerts:
        st.warning(a)
else:
    st.success("大きな異常は見つかりませんでした。")

st.subheader("改善提案")
for r in recs:
    st.write(f"- {r}")

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
        st.json({
            "has_faq": result["has_faq"],
            "has_case": result["has_case"],
            "has_pdf": result["has_pdf"]
        })

        st.write("**改善提案**")
        for item in result["improvements"]:
            st.write(f"- {item}")

    except Exception as e:
        st.error(f"URL診断でエラー: {e}")
