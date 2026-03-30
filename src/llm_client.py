import os

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "45"))
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "false").lower() not in {"0", "false", "no"}
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "300"))


def ask_llm(prompt: str) -> str:
    if not OLLAMA_ENABLED:
        return "[LLM skipped] OLLAMA_ENABLED=false"

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": OLLAMA_NUM_PREDICT,
                },
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
