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


# ===== Vision AI Analysis Functions =====

def analyze_vision_lp(screenshot_path: str, page_data: Dict) -> Dict:
    """
    LPのスクリーンショットを Vision モデルで分析
    
    Args:
        screenshot_path: スクリーンショットの保存パス
        page_data: ページ分析結果（title, h1, cta_count等）
    
    Returns:
        {"skipped": bool, "vision_analysis": str or reason}
    """
    from src.llm_client import ask_llm_vision
    
    vision_enabled = os.getenv("VISION_ANALYSIS_ENABLED", "false").lower() in ("1", "true", "yes")
    if not vision_enabled:
        return {"skipped": True, "reason": "VISION_ANALYSIS_ENABLED=false"}
    
    if not Path(screenshot_path).exists():
        return {"skipped": True, "reason": f"Screenshot not found: {screenshot_path}"}
    
    try:
        vision_prompt_file = os.getenv("VISION_PROMPT_FILE", "prompts/vision_lp_analysis.md")
        vision_prompt = load_prompt(vision_prompt_file)
        
        # ページデータをコンテキストとして埋め込む
        context_str = json.dumps({
            "title": page_data.get("title", ""),
            "h1_list": page_data.get("h1", []),
            "cta_count": page_data.get("cta_count", 0),
            "text_length": page_data.get("text_length", 0),
        }, ensure_ascii=False, indent=2)
        
        filled_prompt = vision_prompt.replace("{{context}}", context_str)
        
        # Vision LLM 呼び出し
        analysis = ask_llm_vision(
            filled_prompt,
            [screenshot_path],
            num_predict=2000
        )
        
        return {
            "skipped": False,
            "vision_analysis": analysis
        }
    except FileNotFoundError as e:
        return {"skipped": True, "reason": f"Prompt not found: {e}"}
    except Exception as e:
        return {"skipped": True, "reason": f"Vision analysis error: {e}"}


# ===== RAG Utility Functions =====

def init_rag_collection() -> Optional[object]:
    """
    ChromaDB コレクションを初期化して返す
    None を返す場合は RAG 無効
    """
    rag_enabled = os.getenv("RAG_ENABLED", "false").lower() in ("1", "true", "yes")
    if not rag_enabled:
        return None
    
    try:
        import chromadb
        
        persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
        collection_name = os.getenv("RAG_COLLECTION_NAME", "marketing_knowledge")
        
        # ChromaDB クライアントを初期化（持続化あり）
        client = chromadb.PersistentClient(path=persist_dir)
        collection = client.get_or_create_collection(name=collection_name)
        
        return collection
    except ImportError:
        return None
    except Exception as e:
        print(f"[RAG] ChromaDB initialization failed: {e}")
        return None


def add_documents_to_rag(collection: object, documents: List[str], ids: List[str]) -> bool:
    """
    RAG コレクションにドキュメントを追加
    """
    if collection is None:
        return False
    
    try:
        collection.add(ids=ids, documents=documents)
        return True
    except Exception as e:
        print(f"[RAG] Failed to add documents: {e}")
        return False


def retrieve_rag_context(collection: object, query: str, top_k: int = 5) -> List[str]:
    """
    RAG コレクションから関連ドキュメントを検索
    """
    if collection is None:
        return []
    
    try:
        top_k = int(os.getenv("RAG_TOP_K", str(top_k)))
        results = collection.query(query_texts=[query], n_results=top_k)
        
        if results and "documents" in results:
            return results["documents"][0]  # List[str]
        return []
    except Exception as e:
        print(f"[RAG] Query failed: {e}")
        return []


# ===== Multi-Agent Functions =====

def build_agent_prompt(agent_role: str, task_description: str, context: Dict) -> str:
    """
    エージェント用プロンプト組み立て
    
    Args:
        agent_role: "planner" | "analyst" | "copywriter" | "validator"
        task_description: タスク説明
        context: エージェント用コンテキスト辞書
    
    Returns:
        組み立てられたプロンプト文字列
    """
    agent_prompt_file = f"prompts/agent_{agent_role}.md"
    
    try:
        base_prompt = load_prompt(agent_prompt_file)
    except FileNotFoundError:
        base_prompt = f"# {agent_role.upper()} Agent\n\n{{{{prompt}}}}\n\n## Context\n{{{{context}}}}"
    
    filled = base_prompt.replace("{{task}}", task_description)
    filled = filled.replace("{{context}}", json.dumps(context, ensure_ascii=False, indent=2))
    
    return filled