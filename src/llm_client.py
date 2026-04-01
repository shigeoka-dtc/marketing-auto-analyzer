import os
import logging

import requests

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "45"))
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "false").lower() not in {"0", "false", "no"}
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "300"))

# ===== Ollama 細かい制御設定 =====
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.95"))
OLLAMA_SEED = int(os.getenv("OLLAMA_SEED", "-1"))

# Vision AI 設定
VISION_ANALYSIS_ENABLED = os.getenv("VISION_ANALYSIS_ENABLED", "false").lower() not in {"0", "false", "no"}
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava:13b")
VISION_ANALYSIS_TIMEOUT = int(os.getenv("VISION_ANALYSIS_TIMEOUT", "180"))

# RAG 設定
RAG_ENABLED = os.getenv("RAG_ENABLED", "false").lower() not in {"0", "false", "no"}

# Self-Consistency 設定
SELF_CONSISTENCY_ENABLED = os.getenv("SELF_CONSISTENCY_ENABLED", "false").lower() not in {"0", "false", "no"}
SELF_CONSISTENCY_NUM_GENERATIONS = int(os.getenv("SELF_CONSISTENCY_NUM_GENERATIONS", "3"))
GENERATION_TEMPERATURES = os.getenv("GENERATION_TEMPERATURES", "0.5,0.6,0.7").split(",")

# Chain-of-Thought 設定
CHAIN_OF_THOUGHT_ENABLED = os.getenv("CHAIN_OF_THOUGHT_ENABLED", "false").lower() not in {"0", "false", "no"}
PROMPT_ENABLE_CHAIN_OF_THOUGHT = os.getenv("PROMPT_ENABLE_CHAIN_OF_THOUGHT", "false").lower() not in {"0", "false", "no"}


def _build_options(num_predict: int | None = None) -> dict:
    """オプション辞書を構築（temperature, top_p, seed を含む）"""
    opts = {
        "num_predict": num_predict or OLLAMA_NUM_PREDICT,
        "temperature": OLLAMA_TEMPERATURE,
        "top_p": OLLAMA_TOP_P,
    }
    if OLLAMA_SEED >= 0:
        opts["seed"] = OLLAMA_SEED
    return opts


def ask_llm(prompt: str, *, num_predict: int | None = None, model: str | None = None, use_rag: bool = False) -> str:
    if not OLLAMA_ENABLED:
        return "[LLM skipped] OLLAMA_ENABLED=false"

    # RAG コンテキスト追加（オプション）
    final_prompt = prompt
    if use_rag and RAG_ENABLED:
        try:
            from src import rag_utils
            collection = rag_utils.get_rag_collection()
            rag_context = rag_utils.build_rag_context_prompt(collection, prompt[:100])
            if rag_context:
                final_prompt = rag_context + "\n---\n\n" + prompt
        except Exception as e:
            import logging
            logging.warning(f"RAG context retrieval failed: {e}")

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model or OLLAMA_MODEL,
                "prompt": final_prompt,
                "stream": False,
                "options": _build_options(num_predict),
            },
            timeout=(5, OLLAMA_TIMEOUT),
        )
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        if not text:
            return "[LLM unavailable] empty response"
        return text
    except Exception as exc:
        return f"[LLM unavailable] {exc}"


def ask_llm_vision(prompt: str, image_paths: list[str], *, num_predict: int | None = None) -> str:
    """Vision モデルを使用してプロンプト + 画像を処理
    
    Args:
        prompt: プロンプト文字列
        image_paths: スクリーンショットファイルパスのリスト
        num_predict: トークン予測数（デフォルト: OLLAMA_NUM_PREDICT）
    
    Returns:
        Vision LLM の応答文字列、またはエラーメッセージ
    """
    if not VISION_ANALYSIS_ENABLED or not OLLAMA_ENABLED:
        msg = "[Vision LLM skipped] VISION_ANALYSIS_ENABLED=false or OLLAMA_ENABLED=false"
        logger.debug(msg)
        return msg
    
    try:
        # 画像を base64 エンコード
        import base64
        images_data = []
        for img_path in image_paths:
            if not os.path.exists(img_path):
                logger.warning(f"Image file not found: {img_path}")
                continue
            with open(img_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                images_data.append(img_b64)
                logger.debug(f"Encoded image: {img_path} ({len(img_b64)} bytes base64)")
        
        if not images_data:
            msg = "[Vision LLM unavailable] no valid images"
            logger.warning(msg)
            return msg
        
        logger.info(f"Calling Vision LLM: model={OLLAMA_VISION_MODEL}, images={len(images_data)}")
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_VISION_MODEL,
                "prompt": prompt,
                "stream": False,
                "images": images_data,
                "options": _build_options(num_predict),
            },
            timeout=(10, VISION_ANALYSIS_TIMEOUT),  # (connect, read) timeouts
        )
        response.raise_for_status()
        
        result = response.json()
        text = result.get("response", "").strip()
        
        if not text:
            msg = "[Vision LLM unavailable] empty response"
            logger.warning(msg)
            return msg
        
        logger.info(f"Vision analysis complete: {len(text)} chars")
        return text
        
    except requests.exceptions.Timeout as e:
        msg = f"[Vision LLM timeout] {str(e)}"
        logger.error(msg)
        return msg
    except requests.exceptions.ConnectionError as e:
        msg = f"[Vision LLM connection error] {str(e)}"
        logger.error(msg)
        return msg
    except Exception as exc:
        msg = f"[Vision LLM unavailable] {type(exc).__name__}: {str(exc)}"
        logger.error(msg, exc_info=True)
        return msg


# ===== Self-Consistency 投票メカニズム =====

def _extract_consensus_phrases(text: str, min_phrase_length: int = 3) -> list[str]:
    """テキストから重要フレーズを抽出
    
    Args:
        text: 分析テキスト
        min_phrase_length: 最小フレーズ単語数
    
    Returns:
        キーフレーズのリスト
    """
    # 日本語と英語の両方のキーフレーズを抽出
    import re
    
    # 句点で区切った文の中から名詞句やキーフレーズを抽出
    sentences = re.split(r'[。！\n]', text)
    phrases = []
    
    for sentence in sentences:
        # 5文字以上のフレーズを抽出（日本語対応）
        if len(sentence.strip()) >= min_phrase_length:
            phrases.append(sentence.strip()[:50])  # 最初の50文字をキーフレーズとして使用
    
    return phrases[:10]  # 最大10フレーズ


def _voting_consensus(generations: list[str]) -> tuple[str, float]:
    """複数の LLM 生成結果から投票で最適案を選択
    
    Args:
        generations: LLM生成結果のリスト
    
    Returns:
        (最高投票獲得テキスト, 信頼度スコア 0.0-1.0)
    """
    if not generations:
        return "[No generations]", 0.0
    
    if len(generations) == 1:
        return generations[0], 0.5  # 単一出力は信頼度低め
    
    # 各生成テキストのキーフレーズを抽出
    all_phrases = []
    phrase_to_generation = {}  # フレーズ -> 生成テキストのインデックス
    
    for idx, text in enumerate(generations):
        phrases = _extract_consensus_phrases(text)
        for phrase in phrases:
            all_phrases.append(phrase)
            if phrase not in phrase_to_generation:
                phrase_to_generation[phrase] = []
            phrase_to_generation[phrase].append(idx)
    
    # 投票数をカウント（複数の生成で出現したフレーズほど信頼度が高い）
    phrase_votes = {}
    for phrase, indices in phrase_to_generation.items():
        vote_count = len(set(indices))  # ユニークな生成の数
        phrase_votes[phrase] = vote_count
    
    if not phrase_votes:
        # フレーズ一致がない場合は、最初の生成を返す
        return generations[0], 0.3
    
    # 最も投票が多いフレーズを見つける
    max_votes = max(phrase_votes.values())
    top_phrases = {p: v for p, v in phrase_votes.items() if v == max_votes}
    
    # 最高投票フレーズを含む生成テキストを特定
    best_generation_indices = set()
    for phrase in top_phrases:
        best_generation_indices.update(phrase_to_generation[phrase])
    
    # 該当する生成テキストの中から、フレーズ数が最も多いものを選択
    best_idx = max(best_generation_indices, key=lambda i: len(_extract_consensus_phrases(generations[i])))
    
    # 信頼度スコア = 最高投票数 / 全生成数
    confidence_score = max_votes / len(generations)
    
    return generations[best_idx], confidence_score


def ask_llm_with_consistency(
    prompt: str,
    *,
    num_predict: int | None = None,
    model: str | None = None,
    use_rag: bool = False,
) -> dict[str, str | float]:
    """Self-Consistency 投票メカニズム付きで LLM を呼び出す
    
    複数の異なる temperature で同じプロンプトを生成し、
    投票で最適案を選択。精度向上 + Hallucination 削減
    
    Args:
        prompt: プロンプト文字列
        num_predict: トークン予測数
        model: LLM モデル
        use_rag: RAG を使用するか
    
    Returns:
        {
            "response": 最高投票獲得のテキスト,
            "confidence": 信頼度スコア (0.0-1.0),
            "generation_count": 生成数,
            "generations": 全生成テキストのリスト (デバッグ用)
        }
    """
    if not OLLAMA_ENABLED or not SELF_CONSISTENCY_ENABLED:
        return {
            "response": "[Self-Consistency skipped] SELF_CONSISTENCY_ENABLED=false",
            "confidence": 0.0,
            "generation_count": 0,
            "generations": [],
        }
    
    # 温度設定のパース
    try:
        temps = [float(t.strip()) for t in GENERATION_TEMPERATURES[:SELF_CONSISTENCY_NUM_GENERATIONS]]
    except (ValueError, IndexError):
        temps = [0.5, 0.6, 0.7][:SELF_CONSISTENCY_NUM_GENERATIONS]
    
    logger.info(f"Self-Consistency: generating {len(temps)} candidates with temps={temps}")
    
    generations: list[str] = []
    
    # 複数の温度で並列生成（簡略版：順序実行）
    for temp in temps:
        try:
            # 元の temperature を保存
            original_temp = OLLAMA_TEMPERATURE
            
            # 一時的に temperature を変更してオプションを構築
            options = {
                "num_predict": num_predict or OLLAMA_NUM_PREDICT,
                "temperature": temp,
                "top_p": OLLAMA_TOP_P,
            }
            if OLLAMA_SEED >= 0:
                options["seed"] = OLLAMA_SEED
            
            # プロンプト準備
            final_prompt = prompt
            if use_rag and RAG_ENABLED:
                try:
                    from src import rag_utils
                    collection = rag_utils.get_rag_collection()
                    rag_context = rag_utils.build_rag_context_prompt(collection, prompt[:100])
                    if rag_context:
                        final_prompt = rag_context + "\n---\n\n" + prompt
                except Exception as e:
                    logger.warning(f"RAG context retrieval failed: {e}")
            
            # Ollama 呼び出し
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model or OLLAMA_MODEL,
                    "prompt": final_prompt,
                    "stream": False,
                    "options": options,
                },
                timeout=(5, OLLAMA_TIMEOUT),
            )
            response.raise_for_status()
            text = response.json().get("response", "").strip()
            if text and not text.startswith("["):
                generations.append(text)
                logger.debug(f"  Generation {len(generations)} (T={temp}): {len(text)} chars")
        except Exception as e:
            logger.warning(f"Generation with T={temp} failed: {e}")
            continue
    
    # 投票で最適案を選択
    if generations:
        best_response, confidence = _voting_consensus(generations)
        logger.info(f"Self-Consistency voting: selected response (confidence={confidence:.2f})")
        return {
            "response": best_response,
            "confidence": confidence,
            "generation_count": len(generations),
            "generations": generations,
        }
    else:
        return {
            "response": "[Self-Consistency unavailable] all generations failed",
            "confidence": 0.0,
            "generation_count": 0,
            "generations": [],
        }


def _wrap_cot_prompt(base_prompt: str, analysis_type: str = "general") -> str:
    """Chain-of-Thought (CoT) をプロンプトに統合
    
    LLM が段階的に思考プロセスを明示することで、
    Hallucination 削減 + 根拠明確化を実現
    
    Args:
        base_prompt: 元のプロンプト
        analysis_type: 分析タイプ ("deep_analysis", "lp_analysis", "general")
    
    Returns:
        CoT 統合後のプロンプト
    """
    if analysis_type == "deep_analysis":
        cot_instruction = """
## 分析アプローチ（Chain-of-Thought）

以下のステップを順番に実行してください。各ステップの思考過程を明示してください。

### Step 1: データの基本統計を確認
- 各チャネルの流入数、コンバージョン数、CVRを明記
- 最大ドロップ箇所を特定
- 前月比や業界平均との比較がある場合は記載

### Step 2: 問題の根本原因を診断
- 単なる「CVRが低い」ではなく、「なぜ低いのか」を3段階で掘り下げる
  1. 流入段階の問題か、ページ内の問題か、フォーム段階の問題か
  2. 各チャネル別の特性を考慮
  3. 過去のトレンドから悪化タイミングを特定

### Step 3: 改善案の優先度をつける
- 影響度大・実装難度低 の施策を最優先に
- 各施策の期待効果を数値で予測

### Step 4: 根拠を整理してから結論を書く
- 改善案を書く前に、「なぜその施策で効くか」を必ず記載
- 根拠: 「データより」「同業他社の事例より」などを明示

---
"""
        return cot_instruction + "\n" + base_prompt
    
    elif analysis_type == "lp_analysis":
        cot_instruction = """
## Visual 分析アプローチ（Chain-of-Thought）

以下のステップで画像とテキストを総合評価:

### Step 1: First View (FV) の評価
- H1/タイトルのサイズ、色、配置
- ヒーロー画像のサイズと視認性
- CTA ボタンの色・サイズ・配置
- ファーストビューに「信頼シグナル」があるか

### Step 2: 読み進め評価
- テキスト量 (FV と LTV のテキスト量比)
- ビジュアル階層（目線の流れが自然か）
- CTA の繰り返し登場（2 つ目の CTA の位置）

### Step 3: 改善機会の優先度
- 即座に効果が期待される改善 (CTA 色、位置)
- テスト価値がある改善 (H1 文言、ビジュアル)
- 低優先 (フォント、細部スタイル)

---
"""
        return cot_instruction + "\n" + base_prompt
    
    else:  # general
        cot_instruction = """
## 思考プロセス（Chain-of-Thought）

回答する前に、以下のステップを実行してください:

1. **情報整理**: 与えられたデータから重要情報を列挙
2. **仮説形成**: 観察から 1-3 個の主要仮説を立てる
3. **検証**: 各仮説をデータに照らし合わせて検証
4. **優先度付け**: 最も確からしい仮説から結論を導く

---
"""
        return cot_instruction + "\n" + base_prompt
