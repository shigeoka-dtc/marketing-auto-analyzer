import os
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))

def ask_llm(prompt: str) -> str:
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=OLLAMA_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("response", "")
    except Exception as e:
        return f"[LLM unavailable] {e}"
