import os

import requests

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
    """Vision モデルを使用してプロンプト + 画像を処理"""
    if not VISION_ANALYSIS_ENABLED or not OLLAMA_ENABLED:
        return "[Vision LLM skipped] VISION_ANALYSIS_ENABLED=false or OLLAMA_ENABLED=false"
    
    try:
        # 画像を base64 エンコード
        import base64
        images_data = []
        for img_path in image_paths:
            if not os.path.exists(img_path):
                continue
            with open(img_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                images_data.append(img_b64)
        
        if not images_data:
            return "[Vision LLM unavailable] no valid images"
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_VISION_MODEL,
                "prompt": prompt,
                "stream": False,
                "images": images_data,
                "options": _build_options(num_predict),
            },
            timeout=(5, VISION_ANALYSIS_TIMEOUT),
        )
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        if not text:
            return "[Vision LLM unavailable] empty response"
        return text
    except Exception as exc:
        return f"[Vision LLM unavailable] {exc}"
