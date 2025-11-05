"""
Configuration file for PDF RAG System
Contains Elasticsearch connection settings and model URLs
"""
from elasticsearch import Elasticsearch
import time
import os
from dotenv import load_dotenv

load_dotenv()

class ElasticConfig:
    """Elasticsearch configuration"""
    # Update these values based on your local Elasticsearch setup
    url = os.getenv('ELASTICSEARCH_URL', 'http://elastic:2braintest@localhost:9200')
    
    
def get_es():
    """
    Get Elasticsearch connection with retry logic
    Returns:
        Elasticsearch: Connected Elasticsearch client
    """
    while True:
        try:    
            es = Elasticsearch([ElasticConfig.url]) 
            # Test connection
            es.info()
            return es
        except Exception as e:
            print(f'ElasticSearch connection failed: {e}, retrying in 3 seconds...')
            time.sleep(3)


class ModelConfig:
    """Configuration for various AI models"""
    # Embedding configuration
    EMBEDDING_URL = os.getenv('EMBEDDING_URL', 'http://test.2brain.cn:9800/v1/emb')
    EMBEDDING_DIM = int(os.getenv('EMBEDDING_DIM', '1024'))  # Dimension of embedding vectors
    USE_OLLAMA_EMBEDDINGS = os.getenv('USE_OLLAMA_EMBEDDINGS', 'false').lower() == 'true'
    OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'nomic-embed-text')  # For Ollama
    
    # Reranking model URL
    RERANK_URL = os.getenv('RERANK_URL', 'http://test.2brain.cn:2260/rerank')
    
    # Vision model URL for image captioning
    IMAGE_MODEL_URL = os.getenv('IMAGE_MODEL_URL', 'http://test.2brain.cn:23333/v1')
    
    # OpenAI API configuration (for LLM-based operations)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'YOUR_API_KEY')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', None)  # Optional custom base URL
    
    # LLM model names
    LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4')
    FAST_LLM_MODEL = os.getenv('FAST_LLM_MODEL', 'gpt-3.5-turbo')


class RAGConfig:
    """RAG system configuration"""
    # Chunking parameters
    CHUNK_SIZE = 1024
    CHUNK_OVERLAP = 100
    
    # Retrieval parameters
    TOP_K_RETRIEVAL = 10
    TOP_K_RERANK = 5
    RRF_K = 60  # RRF constant
    
    # Processing options (set to False for faster ingestion)
    PROCESS_IMAGES = False  # Set to True to extract and caption images (slower, requires vision model)
    PROCESS_TABLES = False  # Set to True to extract and summarize tables (slower, requires LLM)
    
    # Query optimization (set to False for faster queries)
    ENABLE_RAG_FUSION = False  # Set to True to enable multi-query variations (3-5x slower but better recall)
    ENABLE_QUERY_DECOMPOSITION = False  # Set to True to decompose complex queries (slower but handles multi-part questions)
    ENABLE_RERANKING = True  # Set to False to skip reranking (faster but lower relevance)
    
    # Image extraction parameters (only used if PROCESS_IMAGES = True)
    MIN_IMAGE_WIDTH = 200
    MIN_IMAGE_HEIGHT = 100
    IMAGE_WIDTH_RATIO = 3  # Minimum ratio of image width to page width
    
    # Directory for temporary image storage
    IMAGE_DIR = 'pdf_images'

