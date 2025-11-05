"""
Elasticsearch index management module
Handles index creation, deletion, and document indexing
"""
from config import get_es, ModelConfig, RAGConfig
from typing import Dict, List, Any
import time


def create_index(index_name: str, include_metadata: bool = True) -> bool:
    """
    Create Elasticsearch index with appropriate mappings for hybrid search
    
    Args:
        index_name: Name of the index to create
        include_metadata: Whether to include metadata fields
        
    Returns:
        True if successful, False otherwise
    """
    es = get_es()
    
    # Auto-detect embedding dimension based on model
    import os
    use_ollama = os.getenv('USE_OLLAMA_EMBEDDINGS', 'false').lower() == 'true'
    embedding_dim = 768 if use_ollama else ModelConfig.EMBEDDING_DIM
    
    # Base mappings for text and vector
    mappings = {
        "properties": {
            "text": {
                "type": "text"
            }, 
            "vector": {
                "type": "dense_vector",
                "dims": embedding_dim,
                "index": True,
                "similarity": "cosine"
            },
            "doc_type": {
                "type": "keyword"  # text, image, table
            },
            "page_num": {
                "type": "integer"
            }
        }
    }
    
    # Add optional metadata fields
    if include_metadata:
        mappings["properties"].update({
            "file_name": {
                "type": "keyword"
            },
            "file_path": {
                "type": "keyword"
            },
            "chunk_id": {
                "type": "keyword"
            },
            "image_path": {
                "type": "keyword"
            },
            "table_markdown": {
                "type": "text"
            },
            "original_summary": {
                "type": "text"
            },
            "metadata": {
                "type": "object",
                "enabled": True
            }
        })
    
    try:
        # Check if index already exists
        if es.indices.exists(index=index_name):
            print(f"[Info] Index '{index_name}' already exists")
            return True
            
        es.indices.create(index=index_name, mappings=mappings)
        print(f"[Success] Index '{index_name}' created")
        return True
    except Exception as e:
        print(f"[Error] Failed to create index '{index_name}': {e}")
        return False


def delete_index(index_name: str) -> bool:
    """
    Delete an Elasticsearch index
    
    Args:
        index_name: Name of the index to delete
        
    Returns:
        True if successful, False otherwise
    """
    es = get_es()
    try:
        if es.indices.exists(index=index_name):
            es.indices.delete(index=index_name)
            print(f"[Success] Index '{index_name}' deleted")
            return True
        else:
            print(f"[Info] Index '{index_name}' does not exist")
            return False
    except Exception as e:
        print(f"[Error] Failed to delete index '{index_name}': {e}")
        return False


def index_document(index_name: str, document: Dict[str, Any], doc_id: str = None) -> bool:
    """
    Index a single document in Elasticsearch
    
    Args:
        index_name: Name of the index
        document: Document to index
        doc_id: Optional document ID
        
    Returns:
        True if successful, False otherwise
    """
    es = get_es()
    retry = 0
    max_retries = 5
    
    while retry < max_retries:
        try:
            if doc_id:
                es.index(index=index_name, id=doc_id, document=document)
            else:
                es.index(index=index_name, document=document)
            return True
        except Exception as e:
            retry += 1
            if retry < max_retries:
                print(f"[Retry {retry}/{max_retries}] Failed to index document: {e}")
                time.sleep(1)
            else:
                print(f"[Error] Failed to index document after {max_retries} attempts: {e}")
                return False


def bulk_index_documents(index_name: str, documents: List[Dict[str, Any]]) -> int:
    """
    Bulk index multiple documents in Elasticsearch
    
    Args:
        index_name: Name of the index
        documents: List of documents to index
        
    Returns:
        Number of successfully indexed documents
    """
    es = get_es()
    success_count = 0
    
    # Prepare bulk operations
    from elasticsearch.helpers import bulk
    
    actions = []
    for doc in documents:
        action = {
            "_index": index_name,
            "_source": doc
        }
        if "doc_id" in doc:
            action["_id"] = doc.pop("doc_id")
        actions.append(action)
    
    try:
        success, failed = bulk(es, actions, raise_on_error=False)
        success_count = success
        if failed:
            print(f"[Warning] {len(failed)} documents failed to index")
    except Exception as e:
        print(f"[Error] Bulk indexing failed: {e}")
    
    print(f"[Success] Indexed {success_count}/{len(documents)} documents")
    return success_count


def get_index_stats(index_name: str) -> Dict[str, Any]:
    """
    Get statistics about an index
    
    Args:
        index_name: Name of the index
        
    Returns:
        Dictionary with index statistics
    """
    es = get_es()
    try:
        if not es.indices.exists(index=index_name):
            return {"error": "Index does not exist"}
        
        stats = es.indices.stats(index=index_name)
        count = es.count(index=index_name)
        
        return {
            "document_count": count['count'],
            "size_in_bytes": stats['indices'][index_name]['total']['store']['size_in_bytes'],
            "index_name": index_name
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == '__main__':
    # Test index operations
    test_index = 'test_pdf_rag'
    
    print("Testing index creation...")
    create_index(test_index)
    
    print("\nTesting index stats...")
    stats = get_index_stats(test_index)
    print(stats)
    
    print("\nTesting document indexing...")
    test_doc = {
        "text": "This is a test document",
        "vector": [0.1] * ModelConfig.EMBEDDING_DIM,
        "doc_type": "text",
        "page_num": 1,
        "file_name": "test.pdf"
    }
    index_document(test_index, test_doc)
    
    print("\nFinal index stats...")
    stats = get_index_stats(test_index)
    print(stats)
    
    # Uncomment to clean up
    # print("\nDeleting test index...")
    # delete_index(test_index)

