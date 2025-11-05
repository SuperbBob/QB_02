"""
Retrieval module with hybrid search (BM25 + vector) and RRF
"""
import re
import jieba
from typing import List, Dict, Any
from config import get_es, RAGConfig
from embedding import local_embedding


# Chinese stop words for keyword extraction
STOP_WORDS = set([
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "与", "如何",
    "为", "得", "里", "后", "自己", "之", "过", "给", "然后", "那", "下", "能", "而", "来", "个", "这", "之间", "应该", "可以", "到", "由", "及", "对", "中", "会",
    "但", "年", "还", "并", "如果", "我们", "为了", "而且", "或者", "因为", "所以", "对于", "而言", "与否", "只是", "已经", "可能", "同时", "比如", "这样", "当然",
    "并且", "大家", "之后", "那么", "越", "虽然", "比", "还是", "只有", "现在", "应该", "由于", "尽管", "除了", "以外", "然而", "哪些", "这些", "所有", "并非",
    "例如", "尤其", "哪里", "那里", "何时", "多少", "以至", "以至于", "几乎", "已经", "仍然", "甚至", "更加", "无论", "不过", "不是", "从来", "何处", "到底", 
    "尽管", "何况", "不会", "何以", "怎样", "为何", "此外", "其中", "怎么", "什么", "为什么", "是否", '。', '？', '！', '.', '?', '!', '，', ',', " ", ""
])


def get_keywords(query: str) -> List[str]:
    """
    Extract keywords from query using jieba
    
    Args:
        query: Search query
        
    Returns:
        List of keywords
    """
    if not isinstance(query, str):
        query = str(query) if query is not None else ''
    
    if not query.strip():
        return []
    
    try:
        # Use search mode for better keyword extraction
        seg_list = jieba.cut_for_search(query)
        # Filter out stop words
        filtered_keywords = [word for word in seg_list if word not in STOP_WORDS and word.strip()]
        return filtered_keywords
    except Exception as e:
        print(f'[Get Keywords Error] {e}')
        return [query]


def keyword_search(query: str, index_name: str, top_k: int = None) -> List[Dict[str, Any]]:
    """
    Perform BM25 keyword search
    
    Args:
        query: Search query
        index_name: Elasticsearch index name
        top_k: Number of results to return
        
    Returns:
        List of search results with ranks
    """
    if top_k is None:
        top_k = RAGConfig.TOP_K_RETRIEVAL
    
    es = get_es()
    keywords = get_keywords(query)
    
    if not keywords:
        keywords = [query]
    
    # Build BM25 query
    keyword_query = {
        "bool": {
            "should": [
                {"match": {"text": {"query": keyword, "fuzziness": "AUTO"}}} 
                for keyword in keywords
            ],
            "minimum_should_match": 1
        }
    }
    
    res = es.search(index=index_name, query=keyword_query, size=top_k)
    
    # Format results
    hits = []
    for idx, hit in enumerate(res['hits']['hits']):
        hits.append({
            'id': hit['_id'],
            'text': hit['_source'].get('text', ''),
            'doc_type': hit['_source'].get('doc_type', 'text'),
            'page_num': hit['_source'].get('page_num', 0),
            'metadata': hit['_source'],
            'rank': idx + 1,
            'score': hit['_score']
        })
    
    return hits


def vector_search(query: str, index_name: str, top_k: int = None, use_openai: bool = False) -> List[Dict[str, Any]]:
    """
    Perform vector similarity search
    
    Args:
        query: Search query
        index_name: Elasticsearch index name
        top_k: Number of results to return
        use_openai: Whether to use OpenAI embeddings
        
    Returns:
        List of search results with ranks
    """
    if top_k is None:
        top_k = RAGConfig.TOP_K_RETRIEVAL
    
    es = get_es()
    
    # Get query embedding
    if use_openai:
        from embedding import openai_embedding
        embedding = openai_embedding([query])[0]
    else:
        embedding = local_embedding([query])[0]
    
    # Build vector query
    vector_query = {
        "script_score": {
            "query": {"match_all": {}},
            "script": {
                "source": "cosineSimilarity(params.queryVector, 'vector') + 1.0",
                "params": {"queryVector": embedding}
            }
        }
    }
    
    res = es.search(index=index_name, query=vector_query, size=top_k)
    
    # Format results
    hits = []
    for idx, hit in enumerate(res['hits']['hits']):
        hits.append({
            'id': hit['_id'],
            'text': hit['_source'].get('text', ''),
            'doc_type': hit['_source'].get('doc_type', 'text'),
            'page_num': hit['_source'].get('page_num', 0),
            'metadata': hit['_source'],
            'rank': idx + 1,
            'score': hit['_score']
        })
    
    return hits


def hybrid_search_rrf(keyword_hits: List[Dict], vector_hits: List[Dict], k: int = None) -> List[Dict[str, Any]]:
    """
    Combine keyword and vector search results using Reciprocal Rank Fusion (RRF)
    
    Args:
        keyword_hits: Results from keyword search
        vector_hits: Results from vector search
        k: RRF constant (default from config)
        
    Returns:
        Combined and ranked results
    """
    if k is None:
        k = RAGConfig.RRF_K
    
    # Initialize score dictionary
    scores = {}
    
    # Process keyword hits
    for hit in keyword_hits:
        doc_id = hit['id']
        if doc_id not in scores:
            scores[doc_id] = {
                'score': 0,
                'text': hit['text'],
                'id': doc_id,
                'doc_type': hit['doc_type'],
                'page_num': hit['page_num'],
                'metadata': hit['metadata']
            }
        scores[doc_id]['score'] += 1 / (k + hit['rank'])
    
    # Process vector hits
    for hit in vector_hits:
        doc_id = hit['id']
        if doc_id not in scores:
            scores[doc_id] = {
                'score': 0,
                'text': hit['text'],
                'id': doc_id,
                'doc_type': hit['doc_type'],
                'page_num': hit['page_num'],
                'metadata': hit['metadata']
            }
        scores[doc_id]['score'] += 1 / (k + hit['rank'])
    
    # Sort by RRF score
    ranked_docs = sorted(scores.values(), key=lambda x: x['score'], reverse=True)
    
    # Clean up text (remove timestamps if any)
    timestamp_pattern = re.compile(r'\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}\.\d{3}')
    for doc in ranked_docs:
        doc['text'] = re.sub(timestamp_pattern, '', doc['text'])
    
    # Format final results
    final_results = []
    for idx, doc in enumerate(ranked_docs):
        final_results.append({
            'id': doc['id'],
            'text': doc['text'],
            'doc_type': doc['doc_type'],
            'page_num': doc['page_num'],
            'metadata': doc['metadata'],
            'rank': idx + 1,
            'rrf_score': doc['score']
        })
    
    return final_results


def hybrid_search(query: str, index_name: str, top_k: int = None, use_openai: bool = False) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining BM25 and vector search with RRF
    
    Args:
        query: Search query
        index_name: Elasticsearch index name
        top_k: Number of results to return
        use_openai: Whether to use OpenAI embeddings
        
    Returns:
        Ranked search results
    """
    if top_k is None:
        top_k = RAGConfig.TOP_K_RETRIEVAL
    
    # Perform both searches
    keyword_hits = keyword_search(query, index_name, top_k)
    vector_hits = vector_search(query, index_name, top_k, use_openai)
    
    # Combine with RRF
    combined_results = hybrid_search_rrf(keyword_hits, vector_hits)
    
    # Return top-k
    return combined_results[:top_k]


if __name__ == "__main__":
    # Test retrieval
    test_index = 'test_pdf_rag'
    test_query = '什么是人工智能？'
    
    print(f"Testing keyword extraction...")
    keywords = get_keywords(test_query)
    print(f"Keywords: {keywords}")
    
    print(f"\nTesting hybrid search...")
    try:
        results = hybrid_search(test_query, test_index, top_k=5)
        print(f"Found {len(results)} results")
        for i, result in enumerate(results[:3]):
            print(f"\nResult {i+1}:")
            print(f"  Type: {result['doc_type']}")
            print(f"  Page: {result['page_num']}")
            print(f"  Text: {result['text'][:100]}...")
            print(f"  RRF Score: {result['rrf_score']:.4f}")
    except Exception as e:
        print(f"Search failed: {e}")

