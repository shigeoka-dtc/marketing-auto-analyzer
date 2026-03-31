name: deep_analysis.md
---
# Evidence-first 深掘り分析テンプレート

Instructions:
- 必ず Evidence セクションを先頭に配置すること
- Evidence は「URL, スニペット, 数値, Lighthouse 指標, スクリーンショットパス」の形で列挙する
- LLM は Evidence を参照して「考察」「改善提案」「優先度」「実装タスク（GitHub issue 風）」を出力する

Evidence:
{{evidence}}

Context:
{{context}}

Output Format (strict JSON):
{
  "summary": "<短い要約: 1-2 文>",
  "evidence_summary": [ "<根拠1 の短い行>", "<根拠2>" ],
  "insights": [ { "insight": "...", "impact_estimate": "sessions:+10%", "certainty": "low/medium/high" } ],
  "recommendations": [
    {
      "title": "<提案タイトル>",
      "description": "<詳細>",
      "priority": "high|medium|low",
      "effort": "small|medium|large",
      "acceptance_criteria": [ "<受け入れ条件1>", "<受け入れ条件2>" ]
    }
  ],
  "implementation_tasks": [
    {
      "title": "<実装タスクタイトル>",
      "type": "frontend/backend/seo/analytics",
      "estimate_days": 1,
      "details": "<実装手順やファイル例>"
    }
  ]
}

Rules:
- Evidence が提示されていない場合は必ず "ERROR: NO EVIDENCE" を返す
- 出力は上記 JSON 形式で返すこと（LLM に強制）