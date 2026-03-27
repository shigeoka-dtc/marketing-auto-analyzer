import streamlit as st
import plotly.express as px

from src.analysis import read_mart, total_kpis, channel_summary, detect_anomalies
from src.recommend import generate_recommendations

st.set_page_config(page_title="Marketing Auto Analyzer", layout="wide")
st.title("Marketing Auto Analyzer")

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
st.plotly_chart(fig, use_container_width=True)

st.subheader("チャネル別サマリー")
st.dataframe(channels, use_container_width=True)

st.subheader("異常検知")
if alerts:
    for a in alerts:
        st.warning(a)
else:
    st.success("大きな異常は見つかりませんでした。")

st.subheader("改善提案")
for r in recs:
    st.write(f"- {r}")