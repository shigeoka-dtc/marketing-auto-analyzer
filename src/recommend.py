import pandas as pd


def _append_recommendation(recs, priority, channel, issue, action, reason, score):
    recs.append(
        {
            "priority": priority,
            "channel": channel,
            "issue": issue,
            "action": action,
            "reason": reason,
            "score": score,
        }
    )


def generate_recommendations(
    channel_df: pd.DataFrame,
    diagnostics_df: pd.DataFrame | None = None,
    alerts: list | None = None,
):
    recs = []
    covered_channels = set()
    diagnostics_df = diagnostics_df if diagnostics_df is not None else pd.DataFrame()
    alerts = alerts or []

    if not diagnostics_df.empty:
        for _, row in diagnostics_df.iterrows():
            channel = row["channel"]
            status = row["status"]
            revenue = float(row["revenue"])
            cost = float(row["cost"])
            roas = float(row["roas"])
            cvr = float(row["cvr"])
            score = int(row.get("priority_score", 0))

            if cost > 0 and revenue == 0:
                _append_recommendation(
                    recs,
                    "P1",
                    channel,
                    "費用発生に対して売上ゼロ",
                    "停止候補の広告セットを抽出し、入札・配信面・訴求を即時見直す",
                    row["reason"],
                    score + 100,
                )
                covered_channels.add(channel)
                continue

            if status == "critical":
                _append_recommendation(
                    recs,
                    "P1",
                    channel,
                    "効率悪化が大きい",
                    row["recommended_action"],
                    row["reason"],
                    score + 80,
                )
                covered_channels.add(channel)
                continue

            if status == "warning":
                if pd.notna(row.get("cvr_delta_pct")) and row["cvr_delta_pct"] <= -0.10:
                    issue = "CVRが落ちている"
                    action = "LP、フォーム、CTA導線を優先的に確認する"
                elif pd.notna(row.get("roas_delta_pct")) and row["roas_delta_pct"] <= -0.15:
                    issue = "ROASが悪化している"
                    action = "配信面、入札、訴求を絞って効率を戻す"
                else:
                    issue = "成果の鈍化が見える"
                    action = row["recommended_action"]

                _append_recommendation(
                    recs,
                    "P2",
                    channel,
                    issue,
                    action,
                    row["reason"],
                    score + 40,
                )
                covered_channels.add(channel)
                continue

            if status == "opportunity" or (roas >= 3.0 and cvr >= 0.03):
                _append_recommendation(
                    recs,
                    "P3",
                    channel,
                    "増額テスト候補",
                    "勝ち訴求を保ちながら予算を段階的に増やし、配信先を横展開する",
                    row["reason"],
                    score + 10,
                )
                covered_channels.add(channel)

    for _, row in channel_df.iterrows():
        channel = row["channel"]
        if channel in covered_channels:
            continue

        roas = float(row["roas"])
        cpa = float(row["cpa"])
        cvr = float(row["cvr"])
        revenue = float(row["revenue"])
        cost = float(row["cost"])

        if cost > 0 and revenue == 0:
            _append_recommendation(
                recs,
                "P1",
                channel,
                "費用発生に対して売上ゼロ",
                "停止または入札抑制を検討する",
                "売上が確認できていないため",
                100,
            )
        elif roas < 1.5:
            _append_recommendation(
                recs,
                "P2",
                channel,
                "ROASが低い",
                "配信面、訴求、LPのどこで効率が落ちているかを切り分ける",
                "ROASが1.5未満のため",
                60,
            )
        elif cvr < 0.02:
            _append_recommendation(
                recs,
                "P2",
                channel,
                "CVRが低い",
                "LP改善かターゲティング再設計を優先する",
                "CVRが2%未満のため",
                50,
            )
        elif cpa > 10000:
            _append_recommendation(
                recs,
                "P2",
                channel,
                "CPAが高い",
                "キーワード、オーディエンス、クリエイティブを精査する",
                "CPAが高騰しているため",
                45,
            )
        elif roas >= 3.0 and cvr >= 0.03:
            _append_recommendation(
                recs,
                "P3",
                channel,
                "効率良好",
                "予算増額テストを行う",
                "ROASとCVRが良好なため",
                20,
            )

    if not recs and not alerts:
        recs.append(
            {
                "priority": "P3",
                "channel": "overall",
                "issue": "大きな異常なし",
                "action": "日別推移とチャネル差分を継続監視する",
                "reason": "目立った悪化シグナルがないため",
                "score": 0,
            }
        )

    priority_rank = {"P1": 0, "P2": 1, "P3": 2}
    deduped = []
    seen = set()
    for rec in sorted(recs, key=lambda x: (priority_rank.get(x["priority"], 99), -x["score"], x["channel"])):
        key = (rec["priority"], rec["channel"], rec["issue"], rec["action"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rec)

    return deduped
