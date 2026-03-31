"""
LLM 呼び出しの組み立てと安全化。Evidence が必須。
- prompts/ 以下のテンプレートを読み込み、Evidence を埋めたプロンプトを作る
- 環境変数で LLM の有効無効や設定を管理
- 実際の LLM 呼び出しは環境に依存するため、ここではローカル呼び出しの雛形を提供
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
import json
import subprocess

PROMPTS_DIR = Path("prompts")

def load_prompt(name: str) -> str:
    p = PROMPTS_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"Prompt template not found: {p}")
    return p.read_text(encoding="utf-8")

def assemble_prompt(template_name: str, evidence: List[str], context: Optional[Dict]=None) -> str:
    """
    テンプレートに evidence を差し込み、LLM に渡す文字列を返す。
    Evidence が空なら例外を投げて LLM 実行を防ぐ。
    """
    if not evidence:
        raise ValueError("Evidence is required to run LLM. Provide at least one evidence item.")
    tpl = load_prompt(template_name)
    ctx = context or {}
    # Simple placeholder replacement: {{evidence}} and JSON-encoded context for structured fields
    filled = tpl.replace("{{evidence}}", "\n".join(evidence))
    filled = filled.replace("{{context}}", json.dumps(ctx, ensure_ascii=False, indent=2))
    return filled

def call_local_ollama(prompt: str, model: str, ollama_url: Optional[str]=None, timeout: int=60) -> Dict:
    """
    Ollama 等のローカル LLM を呼ぶ雛形。
    環境によって API が異なるため、ここは利用者側で必要に合わせて修正してください。
    例:
      - ollama CLI がある環境では subprocess で `ollama generate` を呼ぶ方法
      - HTTP API がある場合は requests.post を使う方法
    ここでは ollama CLI を想定する簡易実装を用意（無ければ例外）。
    """
    # Try CLI fallback
    try:
        proc = subprocess.run(
            ["ollama", "generate", model, prompt],
            capture_output=True, text=True, timeout=timeout
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Ollama CLI error: {proc.stderr}")
        out = proc.stdout
        # 出力整形は実際のモデル出力形式に依存
        return {"text": out}
    except FileNotFoundError:
        raise RuntimeError("Local Ollama CLI not found. Integrate your LLM call here (HTTP or CLI).")

def generate_analysis(prompt_name: str, evidence: List[str], model: str="phi3:mini") -> Dict:
    """
    Evidence を必須にして LLM 呼び出しを行う高レベル関数。
    - .env の OLLAMA_ENABLED が真でなければスキップする（安全策）
    """
    from dotenv import load_dotenv
    load_dotenv()

    ollama_enabled = os.getenv("OLLAMA_ENABLED", "false").lower() in ("1","true","yes")
    if not ollama_enabled:
        return {"skipped": True, "reason": "OLLAMA_DISABLED"}

    prompt = assemble_prompt(prompt_name, evidence)
    model_name = os.getenv("OLLAMA_MODEL", model)
    try:
        res = call_local_ollama(prompt, model_name)
        return {"skipped": False, "result": res}
    except Exception as e:
        # フォールバック: 失敗したらスキップ（あるいは短いルールベース要約を返す実装に変更可）
        return {"skipped": True, "reason": f"llm_error:{str(e)}"}