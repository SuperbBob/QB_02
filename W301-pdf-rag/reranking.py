"""
Reranking module for improving retrieval results
Supports both API-based and local reranking
"""
import requests
from typing import List, Dict, Any
from config import ModelConfig, RAGConfig


def rerank_with_api(query: str, documents: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]:
    """
    Rerank documents using an external reranking API
    
    Args:
        query: Search query
        documents: List of retrieved documents
        top_k: Number of top results to return
        
    Returns:
        Reranked list of documents
    """
    if top_k is None:
        top_k = RAGConfig.TOP_K_RERANK
    
    if not documents:
        return []
    
    try:
        # Extract text from documents
        doc_texts = [doc.get('text', '') for doc in documents]
        
        # Call reranking API
        response = requests.post(
            ModelConfig.RERANK_URL,
            json={"query": query, "documents": doc_texts},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        # Add rerank scores to documents
        if result and 'scores' in result and len(result['scores']) == len(documents):
            for idx, doc in enumerate(documents):
                documents[idx]['rerank_score'] = result['scores'][idx]
            
            # Sort by rerank score (descending)
            documents.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)
        
        return documents[:top_k]
        
    except Exception as e:
        print(f"[Reranking Error] {e}, returning original order")
        return documents[:top_k]


def rerank_with_cross_encoder(query: str, documents: List[Dict[str, Any]], top_k: int = None, model_name: str = None) -> List[Dict[str, Any]]:
    """
    Rerank documents using a local cross-encoder model
    
    Args:
        query: Search query
        documents: List of retrieved documents
        top_k: Number of top results to return
        model_name: Name of the cross-encoder model
        
    Returns:
        Reranked list of documents
    """
    if top_k is None:
        top_k = RAGConfig.TOP_K_RERANK
    
    if not documents:
        return []
    
    try:
        from sentence_transformers import CrossEncoder
        
        # Use default model if not specified
        if model_name is None:
            model_name = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
        
        # Load model (consider caching this)
        model = CrossEncoder(model_name)
        
        # Prepare query-document pairs
        pairs = [[query, doc.get('text', '')] for doc in documents]
        
        # Get reranking scores
        scores = model.predict(pairs)
        
        # Add scores to documents
        for idx, doc in enumerate(documents):
            documents[idx]['rerank_score'] = float(scores[idx])
        
        # Sort by rerank score (descending)
        documents.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)
        
        return documents[:top_k]
        
    except Exception as e:
        print(f"[Cross-Encoder Reranking Error] {e}, returning original order")
        return documents[:top_k]


def rerank_documents(query: str, documents: List[Dict[str, Any]], method: str = 'api', top_k: int = None) -> List[Dict[str, Any]]:
    """
    Rerank documents using specified method
    
    Args:
        query: Search query
        documents: List of retrieved documents
        method: Reranking method ('api' or 'cross_encoder')
        top_k: Number of top results to return
        
    Returns:
        Reranked list of documents
    """
    if not documents:
        return []
    
    if method == 'api':
        return rerank_with_api(query, documents, top_k)
    elif method == 'cross_encoder':
        return rerank_with_cross_encoder(query, documents, top_k)
    else:
        print(f"[Warning] Unknown reranking method: {method}, returning original order")
        return documents[:top_k if top_k else RAGConfig.TOP_K_RERANK]


if __name__ == "__main__":
    # Test reranking
    test_query = "What is artificial intelligence?"
    test_docs = [
        {
            'id': '1',
            'text': 'Artificial intelligence (AI) is intelligence demonstrated by machines.',
            'rank': 1
        },
        {
            'id': '2',
            'text': 'Machine learning is a subset of AI that focuses on learning from data.',
            'rank': 2
        },
        {
            'id': '3',
            'text': 'Deep learning uses neural networks with multiple layers.',
            'rank': 3
        }
    ]
    
    print("Testing API-based reranking...")
    try:
        reranked = rerank_with_api(test_query, test_docs.copy(), top_k=3)
        print(f"Reranked {len(reranked)} documents")
        for i, doc in enumerate(reranked):
            print(f"{i+1}. (Score: {doc.get('rerank_score', 'N/A'):.4f}) {doc['text'][:50]}...")
    except Exception as e:
        print(f"API reranking failed: {e}")
    
    print("\nTesting Cross-Encoder reranking...")
    try:
        reranked = rerank_with_cross_encoder(test_query, test_docs.copy(), top_k=3)
        print(f"Reranked {len(reranked)} documents")
        for i, doc in enumerate(reranked):
            print(f"{i+1}. (Score: {doc.get('rerank_score', 'N/A'):.4f}) {doc['text'][:50]}...")
    except Exception as e:
        print(f"Cross-encoder reranking failed: {e}")

