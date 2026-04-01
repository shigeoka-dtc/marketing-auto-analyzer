"""
RAG (Retrieval-Augmented Generation) ユーティリティ

ChromaDB を使用して、過去のレポート、業界知識、施策結果などを
ベクトルDB に保存し、LLM のコンテキストとして利用します。
"""

import os
import logging
from typing import Optional, List
from pathlib import Path
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


def get_rag_collection():
    """
    RAG コレクションを取得（初期化済み）
    """
    rag_enabled = os.getenv("RAG_ENABLED", "false").lower() in ("1", "true", "yes")
    if not rag_enabled:
        return None
    
    try:
        import chromadb
        
        persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
        collection_name = os.getenv("RAG_COLLECTION_NAME", "marketing_knowledge")
        
        # ディレクトリ作成
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        
        # ChromaDB クライアント初期化
        client = chromadb.PersistentClient(path=persist_dir)
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"RAG collection '{collection_name}' is ready")
        return collection
    except ImportError:
        logger.warning("chromadb not installed. RAG disabled.")
        return None
    except Exception as e:
        logger.error(f"Failed to init RAG: {e}")
        return None


def add_report_to_rag(collection: object, report_path: str, report_content: str) -> bool:
    """
    レポートを RAG に追加
    
    Args:
        collection: ChromaDB コレクション
        report_path: レポートファイルパス（ID用）
        report_content: レポート内容
    """
    if collection is None:
        return False
    
    try:
        doc_id = f"report_{Path(report_path).stem}_{datetime.now(UTC).timestamp()}"
        collection.add(
            ids=[doc_id],
            documents=[report_content],
            metadatas=[{
                "source": report_path,
                "type": "marketing_report",
                "timestamp": datetime.now(UTC).isoformat()
            }]
        )
        logger.info(f"Added report to RAG: {doc_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to add report to RAG: {e}")
        return False


def add_site_analysis_to_rag(collection: object, site_url: str, analysis: dict) -> bool:
    """
    サイト分析結果を RAG に追加
    
    Args:
        collection: ChromaDB コレクション
        site_url: 分析対象のサイトURL
        analysis: 分析結果辞書
    """
    if collection is None:
        return False
    
    try:
        # 分析結果をテキスト化
        pages_text = []
        for page in analysis.get("pages", [])[:5]:  # 最初の5ページまで
            page_text = f"""
URL: {page.get('url')}
Title: {page.get('title')}
H1: {', '.join(page.get('h1', []))}
CTAs: {', '.join(page.get('unique_ctas', []))}
Findings: {', '.join(page.get('findings', []))}
Improvements: {', '.join(page.get('improvements', []))}
Score: {page.get('score')}
"""
            pages_text.append(page_text)
        
        content = f"""
Site Analysis: {site_url}
Overall Score: {analysis.get('overall_score', 0)}

{chr(10).join(pages_text)}

LLM Analysis: {analysis.get('llm_analysis', {}).get('result', {}).get('text', '')}
"""
        
        doc_id = f"site_{site_url.replace('/', '_').replace(':', '_').replace('.', '_')}_{datetime.now(UTC).timestamp()}"
        collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[{
                "source": site_url,
                "type": "site_analysis",
                "timestamp": datetime.now(UTC).isoformat()
            }]
        )
        logger.info(f"Added site analysis to RAG: {site_url}")
        return True
    except Exception as e:
        logger.error(f"Failed to add site analysis to RAG: {e}")
        return False


def add_recommendations_to_rag(collection: object, recommendations: dict) -> bool:
    """
    レコメンデーション実績を RAG に追加
    （施策の背に後で参照できるように保存）
    """
    if collection is None:
        return False
    
    try:
        content = f"""
Recommendations Summary
Generated: {datetime.now(UTC).isoformat()}

Channel Recommendations:
"""
        for channel, recs in recommendations.items():
            if isinstance(recs, list):
                content += f"\n{channel}:\n" + "\n".join(f"  - {r}" for r in recs[:5])
        
        doc_id = f"recommendations_{datetime.now(UTC).timestamp()}"
        collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[{
                "type": "recommendations",
                "timestamp": datetime.now(UTC).isoformat()
            }]
        )
        logger.info("Added recommendations to RAG")
        return True
    except Exception as e:
        logger.error(f"Failed to add recommendations to RAG: {e}")
        return False


def retrieve_similar_contexts(collection: object, query: str, top_k: int = 5) -> List[str]:
    """
    RAG から関連コンテキストを検索
    
    Args:
        collection: ChromaDB コレクション
        query: 検索クエリ
        top_k: 取得ドキュメント数
    
    Returns:
        関連ドキュメントリスト（テキスト）
    """
    if collection is None:
        return []
    
    try:
        top_k = int(os.getenv("RAG_TOP_K", str(top_k)))
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas"]
        )
        
        if results and "documents" in results and results["documents"]:
            return results["documents"][0]  # List[str]
        return []
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        return []


def build_rag_context_prompt(collection: object, query: str) -> str:
    """
    RAG から関連コンテキストを取り出し、プロンプトに組み込む形式で返す
    """
    if collection is None:
        return ""
    
    contexts = retrieve_similar_contexts(collection, query, top_k=3)
    if not contexts:
        return ""
    
    prompt = "## 関連する過去分析・施策結果（RAG参照）\n\n"
    for i, ctx in enumerate(contexts, 1):
        prompt += f"### Reference {i}\n{ctx}\n\n"
    
    return prompt
