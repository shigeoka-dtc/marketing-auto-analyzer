# Next Steps - 実装アクションプラン

**作成日**: 2026年4月1日  
**対象**: Product Team / Engineering Team  

---

## 🎯 現在地の整理

### ✅ 完成しました

1. **V2.0 ロードマップ** (IMPLEMENTATION_PRIORITY.md)
   - P0-1: プロンプト CoT 化
   - P0-2: llm_helper.build_agent_prompt() 実装
   - P0-3: Vision LLM Few-shot 実装
   - P1-1~P1-3: エージェント・Self-Consistency・検証層
   - **期間**: 4月1日～5月31日
   - **見込みリリース**: V2.0（5月末）

2. **高度な分析ロードマップ** (ADVANCED_ANALYTICS_ROADMAP.md) ⭐ 新作
   - PHASE 2（5月末）: ユーザー行動分析（ファネル・コホート・CAC/LTV・季節性）
   - PHASE 3（6月～7月）: 競争力分析（競合・クリエイティブ・外部要因・アトリビューション）
   - PHASE 4（7月～）: 予測・最適化（ヒートマップ・価格感応度）
   - **期間**: 6月1日～7月31日
   - **見込みリリース**: V2.5→V3.0

---

## 📋 即座に実行すべきこと（優先度順）

### **今週（4月1日～4月7日）**

#### Task 1: プロンプト改善（P0-1）
- **難易度**: 🟢 低
- **工数**: 1-2 日
- **参考**: [PROMPT_IMPROVEMENT_GUIDE.md](PROMPT_IMPROVEMENT_GUIDE.md) Pattern 1-5
- **チェックリスト**:
  - [ ] `prompts/deep_analysis.md` に Chain-of-Thought セクション追加
  - [ ] `prompts/vision_lp_analysis.md` に Few-shot 例追加（2-3 例）
  - [ ] `prompts/agent_analyst.md` に JSON schema 追加
  - [ ] テスト実行: `python main.py --enable-deep-analysis` で出力確認
  - [ ] 精度測定: 既存テスト vs CoT テスト で改善度を定量化

#### Task 2: llm_helper.build_agent_prompt() 実装（P0-2）
- **難易度**: 🟡 中
- **工数**: 1 日
- **参考**: [COMPREHENSIVE_ANALYSIS.md](COMPREHENSIVE_ANALYSIS.md) Part 3
- **チェックリスト**:
  - [ ] `src/llm_helper.py` に `build_agent_prompt()` 関数実装
  - [ ] Analyst/Copywriter/Planner/Validator の 4 ロール対応
  - [ ] Evidence/Context 埋め込みロジック実装
  - [ ] テスト: `python -c "from src.llm_helper import build_agent_prompt; print(build_agent_prompt(...))"` で動作確認
  - [ ] エージェント層が Ollama に接続可能か確認

### **翌週（4月8日～4月14日）**

#### Task 3: Vision LLM Few-shot 実装（P0-3）
- **難易度**: 🟢 低
- **工数**: 1 日
- **参考**: [PROMPT_IMPROVEMENT_GUIDE.md](PROMPT_IMPROVEMENT_GUIDE.md) Pattern 2
- **チェックリスト**:
  - [ ] `prompts/vision_lp_analysis.md` にスコア 8/10 事例を 2-3 個追加
  - [ ] スコア 4/10 の反例も追加（何が悪いのか明確化）
  - [ ] テスト実行: `python main.py --enable-vision-analysis` で出力確認
  - [ ] 出力の一貫性測定: 同じ画像を 3 回入力 → Score variance を計測

#### Task 4: エージェント実装テスト（P1-1 準備）
- **難易度**: 🟡 中
- **工数**: 2-3 日
- **チェックリスト**:
  - [ ] `MULTI_AGENT_ENABLED=true` を .env に設定
  - [ ] `src/agents/analyst.py` が build_agent_prompt() を呼び出しているか確認
  - [ ] 簡単な分析タスクで Analyst → Copywriter → Planner → Validator の流れをテスト
  - [ ] ログ出力で各エージェントの処理状況確認
  - [ ] 問題があれば COMPREHENSIVE_ANALYSIS.md Part 3 のコード例で修正

### **2週間目（4月15日～4月21日）**

#### Task 5: Self-Consistency 実装（P1-2）
- **難易度**: 🟡 中
- **工数**: 2 日
- **参考**: [PROMPT_IMPROVEMENT_GUIDE.md](PROMPT_IMPROVEMENT_GUIDE.md) Pattern 3
- **チェックリスト**:
  - [ ] `src/llm_helper.py` に `generate_with_consistency_voting()` 関数実装
  - [ ] 異なる temperature で 3 回 LLM 呼び出し
  - [ ] 投票ロジック実装（複数出力の中から最多票を選択）
  - [ ] テスト: `python main.py --enable-self-consistency` で動作確認
  - [ ] Hallucination rate を測定（改善幅が -60% 達成されているか）

#### Task 6: 検証層実装（P1-3）
- **難易度**: 🟡 中
- **工数**: 2-3 日
- **参考**: [COMPREHENSIVE_ANALYSIS.md](COMPREHENSIVE_ANALYSIS.md) Part 4
- **チェックリスト**:
  - [ ] `src/validator.py` で Evidence-Consistency チェック関数実装
  - [ ] Overconfidence 検出ロジック追加
  - [ ] LLM 出力に `confidence_score` と `trust_indicators` を追加
  - [ ] テスト: 複数の分析結果で検証層の動作確認

### **月末（4月22日～4月30日）**

#### Task 7: V2.0 統合テスト & ドキュメント作成
- **難易度**: 🟡 中
- **工数**: 3-4 日
- **チェックリスト**:
  - [ ] 全 P0/P1 タスク完了状態確認
  - [ ] エンド-to-エンド テスト: `python main.py --full-analysis` が成功するか
  - [ ] ダッシュボード表示が正常か確認
  - [ ] テストケース作成: `tests/test_v2_0_complete.py`
  - [ ] README.md に V2.0 完成の旧跡を追加
  - [ ] リリースノート作成（PR/Code Review 準備）

---

## 🚀 5月以降のロードマップ（PHASE 2-4）

### 5月1日～5月31日: PHASE 2 実装（V2.5 向け）

ユーザー行動分析の 4 つの基本機能を追加：

| 機能 | 難易度 | 工数 | 優先度 |
|------|--------|------|--------|
| ファネル分析 | 中 | 3-4d | ⭐⭐⭐⭐⭐ |
| コホート分析 | 中～高 | 4-5d | ⭐⭐⭐⭐⭐ |
| CAC/LTV 分析 | 低～中 | 2-3d | ⭐⭐⭐⭐ |
| 季節性分析 | 低 | 2d | ⭐⭐⭐⭐ |

**詳細実装ガイド**: [ADVANCED_ANALYTICS_ROADMAP.md#phase-2詳細開発ガイド](ADVANCED_ANALYTICS_ROADMAP.md)

### 6月1日～6月30日: PHASE 3 実装（V3.0 向け）

競争優位性と高度な分析 4 機能：

| 機能 | 難易度 | 工数 | 優先度 |
|------|--------|------|--------|
| 競合サイト分析 & 自社比較 | 中～高 | 5-6d | ⭐⭐⭐⭐ |
| クリエイティブ分析 | 中 | 3-4d | ⭐⭐⭐ |
| 外部要因統合 | 高 | 4-5d | ⭐⭐⭐ |
| マルチタッチアトリビューション | 高 | 5-6d | ⭐⭐ |

### 7月以降: PHASE 4 & 戦略機能

ヒートマップ・価格感応度の予測分析 + キラー機能検討

---

## 💰 期待効果（4月実装完了時）

| 指標 | 現在 | 4月末予測 | 改善幅 |
|------|------|---------|--------|
| **プロンプト品質** | 65% | 85-90% | +25% |
| **Hallucination 率** | 25% | 5-8% | -80% ✨ |
| **エージェント稼働** | ❌ | ✅ | 新機能 |
| **Human Review 時間** | 40分 | 10分/レポート | -75% |
| **信頼度スコア表示** | ❌ | ✅ | 新機能 |

---

## 📚 参考ドキュメント一覧

| ドキュメント | サイズ | 対象 | 優先度 |
|-------------|--------|------|--------|
| [IMPLEMENTATION_PRIORITY.md](IMPLEMENTATION_PRIORITY.md) | 6KB | Product Mgr | 🔴 必読 |
| [PROMPT_IMPROVEMENT_GUIDE.md](PROMPT_IMPROVEMENT_GUIDE.md) | 19KB | ML Engineer | 🔴 必読 |
| [COMPREHENSIVE_ANALYSIS.md](COMPREHENSIVE_ANALYSIS.md) | 53KB | CTO/Tech Lead | 🟠 推奨 |
| [ADVANCED_ANALYTICS_ROADMAP.md](ADVANCED_ANALYTICS_ROADMAP.md) | 30KB | Product/Eng | 🟡 参考 |

---

## 🎯 成功基準（4月末）

- [ ] P0-1/P0-2/P0-3 完了
- [ ] エージェント層が機能化
- [ ] Hallucination -80% 達成
- [ ] V2.0 候補版がリリース可能
- [ ] PHASE 2 実装計画が確定
- [ ] チーム全体で Roadmap alignment 完了

**推奨**: Team sync 定期開催（週 1 回）で進捗追跡

---

## ❓ Q&A

**Q: タスク 1-2 の同時実行は可能か？**  
A: はい。異なるエンジニアが担当できます。Task 1 を完了してから Task 2 を開始するのが理想的です。

**Q: テスト時間はどのくらい？**  
A: 各タスク完了後 30-60 分で動作確認可能。本格的なベンチマークは 2 週間単位で実施。

**Q: 現在の実装品質（LLM 出力）はどのレベル？**  
A: 現在 65% 程度。P0-1/P0-2/P0-3 完了後 85-90% に向上予定。

**Q: 既存 API 投資（OpenAI など）は活かせるか？**  
A: はい。`.env` で `OPENAI_ENABLED=true` に切り替えると自動切り替え可能。段階的な移行が容易。

---

**Last Updated**: 2026-04-01  
**Version**: Roadmap v1.0  
**Next Sync**: 2026-04-08（1 週間後）
