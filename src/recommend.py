import pandas as pd


def generate_recommendations(channel_df: pd.DataFrame):
    recs = []

    for _, row in channel_df.iterrows():
        channel = row["channel"]
        roas = row["roas"]
        cpa = row["cpa"]
        cvr = row["cvr"]
        revenue = row["revenue"]
        cost = row["cost"]

        if roas < 1.5:
            recs.append(f"{channel}: ROASが低いため、配信面・訴求・LPの見直し候補")
        if cvr < 0.02:
            recs.append(f"{channel}: CVRが低いため、LP改善かターゲティング再設計を優先")
        if cost > 0 and revenue == 0:
            recs.append(f"{channel}: コスト発生に対し売上ゼロ。停止または入札抑制を検討")
        if roas >= 3.0 and cvr >= 0.03:
            recs.append(f"{channel}: 効率良好。予算増額テスト候補")
        if cpa > 10000:
            recs.append(f"{channel}: CPA高騰。キーワード、オーディエンス、クリエイティブ精査が必要")

    if not recs:
        recs.append("大きな異常はなし。日別推移とチャネル別の差分を継続監視")

    return recs