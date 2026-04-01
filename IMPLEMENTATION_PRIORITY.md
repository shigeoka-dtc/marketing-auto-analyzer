# Marketing Auto Analyzer - 実装優先度クイックガイド

**対象**: Product Team / Engineering Team の意思決定用  
**更新日**: 2026年4月1日

---

## 🚨 緊急度 TOP 3（今週実装すべき）

### P0-1: プロンプト品質 CoT 化
**現状問題**: LLM が Funnel のどこが重要か判断できていない  
**改善内容**: `prompts/deep_analysis.md` に Step-by-Step の思考プロセスを追加  
**期待効果**: 精度 +30%, Hallucination -50%  
**難易度**: 🟢 低（1-2 日）

```markdown
# 実装手順
1. deep_analysis.md に "分析アプローチ（Chain-of-Thought）" セクション追加
2. Step 1: Funnel 詰まり箇所特定
3. Step 2: チャネル別特性解析
4. Step 3: 改善案の期待効果推定（理由付き）
```

**ファイル**: [PROMPT_IMPROVEMENT_GUIDE.md#パターン1](PROMPT_IMPROVEMENT_GUIDE.md)

---

### P0-2: llm_helper.build_agent_prompt() 実装
**現状問題**: `agents/` ディレクトリの実装が incomplete（build_agent_prompt が未実装）  
**改善内容**: Role-specific プロンプト テンプレート + Evidence/Context 埋め込み  
**期待効果**: エージェント層が機能化  
**難易度**: 🟡 中（1 日）

```python
# src/llm_helper.py に追加する関数
def build_agent_prompt(
    agent_role: str,  # "analyst", "copywriter", "planner", "validator"
    task_description: str,
    context: Dict,
    output_schema: Optional[Dict] = None,
    evidence: Optional[List[str]] = None,
) -> str:
    """エージェント固有のプロンプト構築"""
    # ... (詳細は COMPREHENSIVE_ANALYSIS.md Part 3 参照)
```

**ファイル**: [COMPREHENSIVE_ANALYSIS.md#32-マルチエージェント完全実装案](COMPREHENSIVE_ANALYSIS.md)

---

### P0-3: Vision LLM Few-shot 実装
**現状問題**: `vision_lp_analysis.md` の採点基準が主観的→LLM の出力がばらつく  
**改善内容**: 具体的な採点例（スコア 8/10 の事例、スコア 4/10 の事例など）を 5 個追加  
**期待効果**: スコア一貫性 +90%, variance -80%  
**難易度**: 🟢 低（1 日）

**ファイル**: [PROMPT_IMPROVEMENT_GUIDE.md#パターン2](PROMPT_IMPROVEMENT_GUIDE.md)

---

## 🎯 中期(2-4週) 実装項目- P1 Level

### P1-1: エージェント完全実装
**現状**: Analyst, Copywriter, Planner, Validator クラスがある但し、llm_helper との連携がない  
**目標**: 全4エージェントが Ollama に接続可能な状態  
**工数**: 3-4 日  
**期待効果**: マルチエージェント ワークフロー稼働

---

### P1-2: Self-Consistency 投票メカニズム
**現状**: 単一の LLM 呼び出ししかしていない→Hallucination リスク  
**目標**: 複数温度設定で複数回生成→投票で最適案を決定  
**工数**: 2 日  
**期待効果**: Hallucination -60%, Confidence +40%

**ファイル**: [PROMPT_IMPROVEMENT_GUIDE.md#パターン3](PROMPT_IMPROVEMENT_GUIDE.md)

---

### P1-3: LLM 出力検証層
**現状**: JSON パーズ失敗時のみ fallback。Evidence との矛盾検出なし  
**目標**: Evidence-Consistency 検証 + Overconfidence 検出  
**工数**: 3 日  
**期待効果**: Trust score 表示可能, Human review workload -30%

**ファイル**: [COMPREHENSIVE_ANALYSIS.md#Part-4-LLM出力検証層の実装](COMPREHENSIVE_ANALYSIS.md)

---

## 📊 長期(1-3ヶ月) ビジョン

### V2.0 目標（5月末）
- ✅ プロンプト全面改訂（CoT + Few-shot）
- ✅ エージェント稼働
- ✅ LLM 出力検証

### V2.5 目標（6月末）
- 🆕 **高度なマーケティング分析** (PHASE 2 - 基本分析強化)
  - ユーザー行動フロー / ファネル分析（⭐⭐⭐⭐⭐ 優先度 P2-1）
  - コホート分析 + LTV 推定（⭐⭐⭐⭐⭐ 優先度 P2-2）
  - CAC vs LTV 比較（⭐⭐⭐⭐ 優先度 P2-3）
  - 季節性・曜日・時間帯分析（⭐⭐⭐⭐ 優先度 P2-4）
- 🆕 マルチLLM対応（OpenAI + Anthropic）
- 🆕 並列処理強化
- 🆕 RAG 統合強化

**詳細**: [ADVANCED_ANALYTICS_ROADMAP.md](ADVANCED_ANALYTICS_ROADMAP.md#-phase-2実装チェックリスト) 参照

### **V3.0 キラー機能** (7月以降)
1. **Agentic Loop**: エージェント間の自動反復改善 ⭐⭐⭐
2. **競争優位性分析**: 競合サイト自動化 + 自社比較（⭐⭐⭐⭐ P3-1）
3. **クリエイティブ分析**: 広告文・画像の訴求力採点（⭐⭐⭐ P3-2）
4. **外部要因統合**: 市場トレンド・ニュース考慮（⭐⭐⭐ P3-3）
5. **マルチタッチアトリビューション**: ラストクリック脱却（⭐⭐ P3-4）

**詳細**: [ADVANCED_ANALYTICS_ROADMAP.md](ADVANCED_ANALYTICS_ROADMAP.md#-phase-3詳細開発ガイド) 参照

---

## 💰 投資対効果（ROI）ランキング

| 項目 | 工数 | 期待効果 | ROI |
|------|------|--------|------|
| **CoT 化** | 1d | +30% 精度 | 🔴 最高 |
| **Few-shot** | 1d | +90% 一貫性 | 🔴 最高 |
| **build_agent_prompt** | 1d | エージェント稼働 | 🔴 最高 |
| **Self-Consistency** | 2d | -60% hallucination | 🟠 高 |
| **検証層** | 3d | Trust score可視化 | 🟠 高 |
| **マルチLLM** | 5d | 柔軟性+40% | 🟡 中 |
| **並列処理** | 3d | スピード+50% | 🟡 中 |

**推奨**: 上から順に実装。ROI が高い順序で optimize

---

## 🔗 参考ファイル

```
リポジトリ直下
├─ COMPREHENSIVE_ANALYSIS.md (本体)
│  ├─ Part 1-2: 全体アーキテクチャ評価
│  ├─ Part 3: マルチエージェント完成化
│  ├─ Part 4: LLM出力検証層
│  ├─ Part 5: スケーラビリティ
│  ├─ Part 6: キラー機能TOP5
│  ├─ Part 7: セキュリティ
│  └─ Part 8: SWOT分析
│
└─ PROMPT_IMPROVEMENT_GUIDE.md (実装例)
   ├─ Prompt改善パターン1-5
   ├─ Before/After 比較
   └─ 実装プロセス（優先度順）
```

---

## ✅ Next Actions

**今日**: `COMPREHENSIVE_ANALYSIS.md` と `PROMPT_IMPROVEMENT_GUIDE.md` を Product Team で共有  
**明日**: P0-1, P0-2, P0-3 の実装を開始  
**1週間後**: PR/レビュー  
**2週間後**: V2.0 リリース候補

---

**最後に**: このリポートの**最も重要なメッセージ**

> 「AI による改善提案の品質は、プロンプトエンジニアリングで 30-50% 向上する。」
>
> スケーラビリティやアーキテクチャの改善も重要だが、  
> **プロンプト品質の向上（CoT + Few-shot）が、  
> 即座に実装可能で、最も高い投資効率を生む。**

推奨開始日: **今週中**

