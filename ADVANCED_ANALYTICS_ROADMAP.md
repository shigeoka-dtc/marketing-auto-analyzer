# Advanced Analytics Roadmap
## 高度なマーケティング分析機能 - 実装優先度ガイド

**対象**: V2.0 完成後（5月末以降）の拡張分析機能ロードマップ  
**完成日**: 2026年4月1日  
**バージョン**: Phase 2-3 Analytics Extensions

---

## 📊 優先度マトリックス & 実装タイムライン

### 📍 **PHASE 2（即座実装 - 5月中旬～下旬）**
#### 基本的なユーザー行動分析の可視化 - これなしに本気の LP 改善はできない

| 優先度 | 項目 | 難易度 | 工数 | 期待効果 | 実装方法 |
|--------|------|--------|------|--------|---------|
| ⭐⭐⭐⭐⭐ | **ユーザー行動フロー / ファネル分析** | 中 | 3-4d | 離脱ボトルネック特定（+35%の施策効率） | GA4連携 or `bounce_rate, avg_session_duration` をCSVに追加 |
| ⭐⭐⭐⭐⭐ | **コホート分析（Cohort）** | 中～高 | 4-5d | 長期LTV傾向把握（+40%の戦略精度） | 日付ごとグループ化 → 保持率計算 → LLMで解釈 |
| ⭐⭐⭐⭐☆ | **CAC vs LTV 比較分析** | 低～中 | 2-3d | ROI判定の定量化（利益性可視化） | LTV簡易推定（CV価値×保持率×期間）実装 |
| ⭐⭐⭐⭐☆ | **季節性・曜日・時間帯分析** | 低 | 2d | マーケティング最適タイミング発見 | date列から weekday, hour 抽出 + 可視化 |

**PHASE 2 の目標**: *ユーザーが「どこで」「いつ」「なぜ」離脱するかを定量化*

---

### 📍 **PHASE 3（6月～7月初旬）**
#### 競争優位性を確立する高度な分析 - 競合情報と自社の統合分析

| 優先度 | 項目 | 難易度 | 工数 | 期待効果 | 実装方法 |
|--------|------|--------|------|--------|---------|
| ⭐⭐⭐⭐ | **競合サイト分析の自動化 & 自社比較** | 中～高 | 5-6d | 競争優位性の定量化（+25%の LP改善精度） | Playwright でクロール → 差分分析 → LLM比較プロンプト |
| ⭐⭐⭐ | **クリエイティブ分析（広告文・画像）** | 中 | 3-4d | 広告テキスト/画像の訴求分析 | 広告文CSVインポート or GA Ads API連携 |
| ⭐⭐⭐ | **外部要因分析（市場トレンド・イベント検知）** | 高 | 4-5d | ニュース/イベント由来の変動を説明可能に | LLMプロンプトに「業界ニュース」サマリー追加 or 簡易RSS機能 |
| ⭐⭐ | **マルチタッチアトリビューション** | 高 | 5-6d | チャネル間貢献度の正確測定（ラストクリック脱却） | データに touchpoints 列 → 線形アトリビューション実装 |

**PHASE 3 の目標**: *競合比較と外部要因を含めた「360度マーケティング分析」を実現*

---

### 📍 **PHASE 4（7月中旬～下旬）**
#### ユーザー体験の予測と最適化 - AI による行動予測

| 優先度 | 項目 | 難易度 | 工数 | 期待効果 | 実装方法 |
|--------|------|--------|------|--------|---------|
| ⭐⭐☆ | **ヒートマップ・スクロール分析シミュレーション** | 中 | 3-4d | 「ユーザーがどこに注目するか」を予測 | LLM + ページ構造から注目エリア推定 |
| ⭐⭐ | **価格感応度・オファー分析** | 低 | 1-2d | 価格表示強度と CV 相関の発見 | LP分析プロンプトに「価格/オファー強度」スコア追加 |

**PHASE 4の目標**: *予測分析による「先制的な LP 最適化」*

---

## 🔧 各機能の詳細実装ガイド

### **PHASE 2-1: ユーザー行動フロー / ファネル分析**

#### 現状の問題点
```
現在: CVR, ROAS など「結果指標」のみ
課題: どのステップで 30% が離脱するのか、その理由は何か不明
```

#### 実装アプローチ

**ステップ 1: データ構造拡張**
```python
# marketing.csv に以下を追加
# Date, Sessions, Users, Page_Views, Add_to_Cart, Checkout, Conversions, Revenue
# これにより Funnel 計算が可能に

# または GA4 API から直接取得
import google.analytics.data_v1beta

client = google.analytics.data_v1beta.BetaAnalyticsDataClient()
request = google.analytics.data_v1beta.RunReportRequest(...)
response = client.run_report(request=request)
```

**ステップ 2: Funnel 計算モジュール**
```python
# src/funnel_analysis.py (新規作成)

def calculate_funnel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Funnel 各段階の conversion rate を計算
    Sessions → Users → Page Views → Add to Cart → Checkout → CV
    """
    funnel_stages = {
        'sessions': df['sessions'].sum(),
        'users': df['users'].sum(),
        'page_views': df['page_views'].sum(),
        'add_to_cart': df['add_to_cart'].sum(),
        'checkout': df['checkout'].sum(),
        'conversions': df['conversions'].sum(),
    }
    
    conversion_rates = {
        'users_per_session': funnel_stages['users'] / funnel_stages['sessions'],
        'page_views_per_user': funnel_stages['page_views'] / funnel_stages['users'],
        'atc_per_pageview': funnel_stages['add_to_cart'] / funnel_stages['page_views'],
        'checkout_per_atc': funnel_stages['checkout'] / funnel_stages['add_to_cart'],
        'cv_per_checkout': funnel_stages['conversions'] / funnel_stages['checkout'],
    }
    
    return conversion_rates

def identify_bottleneck(conversion_rates: dict) -> str:
    """最も落ち込みが大きいステップを特定"""
    bottleneck_stage = min(conversion_rates, key=conversion_rates.get)
    return f"最大の離脱は {bottleneck_stage} フェーズ: {conversion_rates[bottleneck_stage]:.1%}"
```

**ステップ 3: LLM による原因分析**
```python
# prompts/funnel_analysis.md (新規作成)

# プロンプトテンプレート例
"""
以下は LP のファネル分析結果です:
{funnel_data}

最大の離脱ポイント: {bottleneck_stage}
ユーザーが放棄する理由として最も可能性がある要因を、以下の証拠に基づいて分析してください:
- ページ構造
- Call-to-Action の強度
- 競合との比較データ

改善提案を 5 つ、期待 CV 向上率とともに提示
"""
```

**期待効果**: 
- ✅ 離脱ポイント特定時間が 80% 短縮
- ✅ 施策の質が +35% 向上（ボトルネック特定→高 ROI 施策集中）
- ✅ A/B テスト提案の精度 +40%

---

### **PHASE 2-2: コホート分析（Cohort）**

#### 現状の問題点
```
現在: 全体平均の LTV のみ
課題: 獲得月ごとの定着率が違う場合、長期 ROI 判定ができない
```

#### 実装アプローチ

**ステップ 1: コホート定義**
```python
# src/cohort_analysis.py (新規作成)

def create_cohorts(df: pd.DataFrame, cohort_interval: str = 'M') -> pd.DataFrame:
    """
    cohort_interval: 'W' (週), 'M' (月), 'Q' (四半期)
    
    例: 2024-01 acquisition → その後のユーザーの保持率追跡
    """
    df['acquisition_cohort'] = df['date'].dt.to_period(cohort_interval)
    df['cohort_age'] = (df.groupby('acquisition_cohort')['date'].rank() - 1).astype(int)
    
    return df

def calculate_retention(df: pd.DataFrame, metric: str = 'users') -> pd.DataFrame:
    """
    各コホートの時系列保持率を計算
    
    Example:
         cohort_0  cohort_1  cohort_2  ...
    age_0   1000     1200     1100
    age_1    800      900      850
    age_2    700      750      720
    """
    cohort_retention = df.groupby(['acquisition_cohort', 'cohort_age'])[metric].sum().unstack()
    
    # 初期値で正規化
    cohort_retention_pct = cohort_retention.divide(cohort_retention.iloc[:, 0], axis=0) * 100
    
    return cohort_retention_pct
```

**ステップ 2: LTV 推定**
```python
def estimate_ltv_by_cohort(cohort_retention: pd.DataFrame, 
                          monthly_revenue: float,
                          lookback_period: int = 12) -> dict:
    """
    コホート別の LTV を推定
    簡易式: LTV = 初期ユーザー × 平均月単価 × 平均保持月数
    """
    cohort_ltv = {}
    
    for cohort in cohort_retention.index:
        avg_retention = cohort_retention.loc[cohort, :lookback_period].mean()
        estimated_ltv = monthly_revenue * avg_retention
        cohort_ltv[cohort] = estimated_ltv
    
    return cohort_ltv
```

**ステップ 3: LLM による傾向分析**
```python
# prompts/cohort_trend_analysis.md

"""
以下は月別コホートの保持率データです:

{cohort_retention_table}

各コホートの LTV 推定値:
{ltv_estimates}

質問:
1. 保持率が低下しているコホートはどれか
2. その原因として何が考えられるか（マーケティング施策変更、プロダクト変更など）
3. 長期 ROI を改善するための改提案を 3 つ提示してください
"""
```

**期待効果**:
- ✅ 長期 ROI 判定精度 +40%
- ✅ 獲得コストと LTV のバランス最適化
- ✅ 施策の長期効果測定が可能に（従前は短期指標のみ）

---

### **PHASE 2-3: CAC vs LTV 比較分析**

#### 現状の問題点
```
現在: ROAS だけで判定（短期利益率）
課題: 長期採算性（LTV > CAC×margin）が不明確
```

#### 実装アプローチ

**ステップ 1: CAC 計算**
```python
# src/cac_ltv_analysis.py (新規作成)

def calculate_cac(
    total_marketing_spend: float,
    new_customers_acquired: int,
    channel: Optional[str] = None
) -> float:
    """
    Customer Acquisition Cost (CAC)
    
    全体 CAC = Total Marketing Spend / New Customers
    チャネル別 CAC = Channel Spend / Channel New Customers
    """
    return total_marketing_spend / new_customers_acquired

def calculate_ltv_simple(
    avg_order_value: float,
    purchase_frequency_per_year: float,
    avg_customer_lifetime_years: float,
    gross_margin: float = 0.40
) -> float:
    """
    簡易 LTV 計算
    LTV = AOV × Frequency × Lifetime × Margin%
    """
    gross_profit_per_transaction = avg_order_value * gross_margin
    return gross_profit_per_transaction * purchase_frequency_per_year * avg_customer_lifetime_years
```

**ステップ 2: LTV/CAC 比率判定**
```python
def ltv_cac_health_check(ltv: float, cac: float, threshold: float = 3.0) -> dict:
    """
    ビジネス健全性判定
    
    LTV/CAC > 3: 健全（ユニット経済学 OK）
    LTV/CAC = 1-3: 注意（改善の余地あり）
    LTV/CAC < 1: 危険（赤字）
    """
    ratio = ltv / cac if cac > 0 else 0
    
    if ratio >= 3:
        health = "🟢 Healthy"
    elif ratio >= 1:
        health = "🟡 At Risk"
    else:
        health = "🔴 Critical"
    
    return {
        'ltv': ltv,
        'cac': cac,
        'ratio': ratio,
        'health_status': health
    }
```

**ステップ 3: LLM による改善提案**
```
LTV/CAC の比率から、以下を提案してください:
- LTV を上げる施策（リテンション改善、AOV 増加）
- CAC を下げる施策（効率的なチャネル選択、ターゲティング改善）
"""
```

**期待効果**:
- ✅ ビジネスサステナビリティの判定が可能に
- ✅ 施策の ROI 判定が「短期」から「長期」へ進化
- ✅ マーケティング予算配分最適化

---

### **PHASE 2-4: 季節性・曜日・時間帯分析**

#### 実装アプローチ

**ステップ 1: 時系列パターン抽出**
```python
# src/temporal_analysis.py (新規作成)

import pandas as pd

def extract_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """日付から時系列特性を抽出"""
    df['date'] = pd.to_datetime(df['date'])
    df['day_of_week'] = df['date'].dt.day_name()
    df['hour'] = df['date'].dt.hour
    df['week_of_year'] = df['date'].dt.isocalendar().week
    df['month'] = df['date'].dt.month
    df['quarter'] = df['date'].dt.quarter
    
    return df

def analyze_weekday_performance(df: pd.DataFrame) -> pd.DataFrame:
    """曜日ごとのパフォーマンス集計"""
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    weekday_analysis = df.groupby('day_of_week')[[
        'sessions', 'users', 'conversions', 'revenue', 'cost'
    ]].agg(['sum', 'mean'])
    
    weekday_analysis = weekday_analysis.reindex(weekday_order)
    return weekday_analysis

def analyze_hourly_performance(df: pd.DataFrame) -> pd.DataFrame:
    """時間帯ごとのパフォーマンス集計"""
    hourly_analysis = df.groupby('hour')[[
        'sessions', 'conversions', 'revenue', 'cost'
    ]].agg(['sum', 'mean'])
    
    return hourly_analysis

def analyze_seasonality(df: pd.DataFrame) -> pd.Series:
    """月/四半期ベースの季節性検出"""
    seasonal_patterns = df.groupby('month')['conversions'].sum()
    seasonal_index = seasonal_patterns / seasonal_patterns.mean()
    
    return seasonal_index
```

**ステップ 2: 最適タイミング提案**
```python
def identify_peak_windows(df: pd.DataFrame) -> dict:
    """最も CV が出やすい日時の組み合わせを特定"""
    
    # 曜日 × 時間帯のマトリックス
    optimal_matrix = df.pivot_table(
        values='conversions', 
        index='day_of_week', 
        columns='hour', 
        aggfunc='sum'
    )
    
    # 最適な曜日・時間を特定
    top_window = optimal_matrix.stack().nlargest(5)
    
    return top_window
```

**期待効果**:
- ✅ マーケティング施策のタイミング最適化（+15～25% の効率向上）
- ✅ 季節変動への対応戦略が立案可能に
- ✅ 曜日・時間帯ごとの予算配分最適化

---

## 📌 PHASE 3 詳細開発ガイド

### **PHASE 3-1: 競合サイト分析の自動化 & 自社比較**

#### 実装アプローチ

**ステップ 1: 競合 URL リスト管理**
```python
# src/competitor_config.py (新規作成)

COMPETITOR_URLS = {
    '業界大手A': 'https://competitor-a.com/lp',
    '業界大手B': 'https://competitor-b.com/service',
    'スタートアップ': 'https://startup.com/pricing',
}

def get_competitor_urls(category: str = 'all') -> dict:
    """カテゴリ別に競合 URL を取得"""
    return COMPETITOR_URLS
```

**ステップ 2: 統一分析パイプライン**
```python
# src/competitive_benchmark.py (新規作成)

async def analyze_competitor_landscape(
    our_url: str,
    competitor_urls: dict,
    analysis_depth: str = 'detailed'
) -> pd.DataFrame:
    """
    自社 URL と競合を統一基準で分析
    返り値: 比較テーブル
    """
    
    our_analysis = await run_url_analyzer(our_url)
    
    competitor_analyses = {}
    for name, url in competitor_urls.items():
        competitor_analyses[name] = await run_url_analyzer(url)
    
    # 統一フォーマットで集計
    comparison_table = create_comparison_matrix(
        our_analysis, 
        competitor_analyses
    )
    
    return comparison_table

def create_comparison_matrix(our: dict, competitors: dict) -> pd.DataFrame:
    """
    比較マトリックス生成
    
    Metrics:
    - CTA 強度
    - ページ speed
    - セキュリティスコア（SSL）
    - Mobile 対応度
    - UX スコア
    - コンテンツボリューム
    - 信頼要素（レビュー、実績）
    """
    
    metrics_to_compare = [
        'cta_strength', 'page_speed', 'ssl_score', 
        'mobile_optimization', 'ux_score', 'content_volume', 'trust_score'
    ]
    
    comparison_df = pd.DataFrame(
        {name: {m: competitors[name].get(m) for m in metrics_to_compare} 
         for name in competitors},
        index=metrics_to_compare
    )
    
    # 自社を追加
    comparison_df.insert(0, 'Our Site', 
        {m: our.get(m) for m in metrics_to_compare}
    )
    
    return comparison_df
```

**ステップ 3: LLM による差分分析と施策提案**
```python
# prompts/competitive_advantage.md (新規作成)

"""
以下は我社と競合 3 社の LP 比較分析です:

{comparison_table}

強み・弱み分析:
1. スコアで我社が上回っている項目は何か（競争優位性）
2. スコアで劣後している項目は何か（改善が必要な項目）
3. 競合が使っている工夫（我社で採用可能なベストプラクティス）を 5 つ提示

具体的な改善施策を 3 つ、期待 CV 向上率とともに提示
"""
```

**期待効果**:
- ✅ 競争優位性が定量化可能に
- ✅ ベストプラクティス採用までの時間 -80%
- ✅ LP 改善の ROI +25～30%

---

### **PHASE 3-2: クリエイティブ分析（広告文・画像）**

#### 実装アプローチ

```python
# src/creative_analysis.py (新規作成)

def score_ad_creative(
    ad_text: str,
    image_path: Optional[str] = None,
    historical_ctr: Optional[float] = None
) -> dict:
    """
    広告テキスト・画像の訴求力を採点
    
    評価軸:
    - 緊急性（FOMO）の強度
    - 数字/具体性
    - 感情的訴求
    - CTA の強さ
    - ブランド一貫性
    """
    
    scoring_prompt = f"""
    以下の広告クリエイティブを以下の軸で 10 点満点で採点してください:
    
    広告文: {ad_text}
    {"画像: " + image_path if image_path else "(画像なし)"}
    
    採点軸:
    1. 緊急性（FOMO）: いつまでに購入すべきか明確か
    2. 数字/具体性: 38% OFF など具体的数字があるか
    3. 感情: 希望/恐怖などの感情に訴えるか
    4. CTA: 「いますぐ購入」など行動喚起が明確か
    5. ブランド: 企業ブランドとの一貫性
    
    各軸で 1～10 のスコアと理由を提示
    """
    
    # LLM呼び出しは src/llm_client.py 経由
    scores = ask_llm_with_json_output(scoring_prompt)
    
    return scores
```

---

### **PHASE 3-3: 外部要因分析（市場トレンド・イベント検知）**

#### 実装アプローチ

```python
# src/external_factors.py (新規作成)

def fetch_industry_news_summary(industry: str, days_lookback: int = 7) -> str:
    """
    業界ニュースを簡易取得（RSS or API）
    例: tech news, marketing trends
    """
    # 簡易版: RSS の要約を LLM にサマリー
    # 本格版: News API, Twitter API との連携
    
    return industry_news_summary

def correlate_external_events_with_performance(
    df: pd.DataFrame,
    events: list[str],  # 例: ["Black Friday", "新製品発表"]
) -> pd.DataFrame:
    """
    外部イベントと CV/ROI の相関を検出
    
    例:
    CVR が 20% 上昇した日付 → その日のニュース/イベントを確認
    """
    
    correlation_analysis = df.merge(
        pd.DataFrame(events, columns=['event_date']),
        left_on='date',
        right_on='event_date'
    )
    
    return correlation_analysis

def generate_external_context_prompt(
    df: pd.DataFrame,
    industry_news: str,
    events: list[str]
) -> str:
    """
    LLM プロンプトに外部要因コンテキストを追加
    """
    
    context = f"""
    マーケティング分析の背景（外部要因）:
    
    最近の業界ニュース:
    {industry_news}
    
    分析対象期間の関連イベント:
    {", ".join(events)}
    
    これらを踏まえ、LP の分析結果を解釈してください。
    """
    
    return context
```

**期待効果**:
- ✅ データの変動理由が説明可能に（「なぜ CVR が +15% 上昇したのか」が分かる）
- ✅ 予測モデルの精度 +20%（外部要因を考慮）

---

### **PHASE 3-4: マルチタッチアトリビューション**

#### 実装アプローチ

```python
# src/attribution_model.py (新規作成)

def apply_linear_attribution(
    touchpoints: list[str],  # 例: ["Organic", "Paid Search", "Email"]
    conversion_value: float
) -> dict:
    """
    線形アトリビューション
    各タッチポイントに均等に貢献度を配分
    """
    
    credit_per_touchpoint = conversion_value / len(touchpoints)
    
    attribution = {
        touchpoint: credit_per_touchpoint 
        for touchpoint in touchpoints
    }
    
    return attribution

def apply_time_decay_attribution(
    touchpoints_with_dates: list[tuple],  # 例: [("2024-01-01", "Organic"), ...]
    conversion_date: str,
    conversion_value: float,
    decay_rate: float = 0.5
) -> dict:
    """
    時間減衰アトリビューション
    CV に近いタッチポイントに高いクレジットを付与
    """
    
    from datetime import datetime
    
    weights = []
    for touch_date, channel in touchpoints_with_dates:
        days_before_cv = (datetime.fromisoformat(conversion_date) - 
                         datetime.fromisoformat(touch_date)).days
        weight = decay_rate ** days_before_cv
        weights.append((channel, weight))
    
    total_weight = sum(w[1] for w in weights)
    
    attribution = {
        channel: (weight / total_weight) * conversion_value
        for channel, weight in weights
    }
    
    return attribution
```

**期待効果**:
- ✅ チャネル別の真の貢献度が判定可能
- ✅ 予算配分最適化で ROI +15～20%

---

## 📋 PHASE 2 実装チェックリスト

- [ ] `src/funnel_analysis.py` 作成 + テスト
- [ ] `prompts/funnel_analysis.md` 作成
- [ ] `src/cohort_analysis.py` 作成 + テスト
- [ ] `src/cac_ltv_analysis.py` 作成 + テスト
- [ ] `src/temporal_analysis.py` 作成 + テスト
- [ ] `src/analysis.py` に 4 つの分析関数を integrate
- [ ] README.md に新機能セクション追加
- [ ] テスト suite 作成（test_advanced_analytics.py）

---

## 📋 PHASE 3 実装チェックリスト

- [ ] `src/competitive_benchmark.py` 作成
- [ ] `prompts/competitive_advantage.md` 作成
- [ ] `src/creative_analysis.py` 作成
- [ ] `src/external_factors.py` 作成
- [ ] `src/attribution_model.py` 作成
- [ ] Competitive config 管理システム実装
- [ ] Integration テスト

---

## 💰 投資対効果 TOP 10 ランキング

| ランク | 機能 | 難易度 | 工数 | 実装期 | 期待効果 | ROI |
|--------|------|--------|------|-------|--------|-----|
| 1 | ファネル分析 | 中 | 3-4d | PHASE 2 | +35% 施策効率 | 🔴 最高 |
| 2 | コホート分析 | 中～高 | 4-5d | PHASE 2 | +40% 戦略精度 | 🔴 最高 |
| 3 | CAC/LTV 分析 | 低～中 | 2-3d | PHASE 2 | 採算性可視化 | 🟠 高 |
| 4 | 季節性分析 | 低 | 2d | PHASE 2 | +20% 最適化 | 🟠 高 |
| 5 | 競合比較 | 中～高 | 5-6d | PHASE 3 | +25% LP 精度 | 🟠 高 |
| 6 | クリエイティブ分析 | 中 | 3-4d | PHASE 3 | 広告効率化 | 🟡 中 |
| 7 | 外部要因分析 | 高 | 4-5d | PHASE 3 | +20% 予測精度 | 🟡 中 |
| 8 | アトリビューション | 高 | 5-6d | PHASE 3 | 真の ROI 把握 | 🟡 中 |
| 9 | ヒートマップ予測 | 中 | 3-4d | PHASE 4 | UX 最適化 | 🟡 中 |
| 10 | 価格感応度分析 | 低 | 1-2d | PHASE 4 | 価格戦略最適化 | 🟢 低 |

---

## 🎯 統合実装の推奨順序

### **月次スケジュール案**

**5月第1週**: PHASE 2-1（ファネル） + PHASE 2-2（コホート）の並列開発開始  
**5月第2週**: PHASE 2-3, 2-4 実装完了  
**5月第3週**: PHASE 2 統合テスト・ドキュメント作成  
**5月第4週**: PHASE 2 リリース（V2.5）  

**6月第1週**: PHASE 3-1（競合分析） 開発開始  
**6月第2週**: PHASE 3-2, 3-3 並列実装  
**6月第3週**: PHASE 3-4 実装  
**6月第4週**: PHASE 3 統合テスト  

**7月**: PHASE 3 リリース（V3.0） + PHASE 4 計画策定

---

## 🔗 既存ドキュメント との連携

```
現在のロードマップ
├─ IMPLEMENTATION_PRIORITY.md （V2.0 を 5月末までに）
└─ このドキュメント：ADVANCED_ANALYTICS_ROADMAP.md
   ├─ V2.5（PHASE 2）
   └─ V3.0（PHASE 3+）の詳細設計
```

このドキュメントを参照して、5月以降の高度な分析機能を段階的に追加してください。

---

**版管理**: v1.0 / 2026-04-01  
**次回更新**: 6月1日（PHASE 2 完成後）
