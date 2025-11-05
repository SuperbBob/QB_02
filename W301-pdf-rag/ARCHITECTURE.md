# System Architecture

Detailed architecture documentation for the PDF RAG system.

## Overview

The PDF RAG system is a modular, scalable document processing and retrieval system that combines traditional information retrieval (BM25) with modern vector search and neural reranking.

## System Components

### 1. PDF Processing Layer (`pdf_processor.py`)

**Purpose:** Extract and process content from PDF documents

**Components:**
- **Text Extraction:** Uses PyMuPDF to extract text from PDF pages
- **Image Extraction:** 
  - Identifies and extracts images above size thresholds
  - Filters small/decorative images
  - Generates captions using vision models
  - Augments captions with page context
- **Table Extraction:**
  - Uses PyMuPDF's table detection
  - Converts tables to Markdown format
  - Generates natural language summaries

**Key Technologies:**
- PyMuPDF (fitz) for PDF parsing
- Vision models for image captioning
- LLM for context augmentation

### 2. Chunking Layer (`chunking.py`)

**Purpose:** Split content into retrievable units

**Strategy:**
- **Text Chunking:**
  - Recursive character splitting
  - Token-aware chunking using tiktoken
  - Configurable chunk size and overlap
  - Semantic-aware separators (paragraphs, sentences)
  
- **Image Preparation:**
  - Uses context-augmented captions as searchable text
  - Preserves image metadata
  
- **Table Preparation:**
  - Uses natural language summaries as searchable text
  - Preserves markdown table structure

**Configuration:**
```python
CHUNK_SIZE = 1024  # tokens
CHUNK_OVERLAP = 100  # tokens
```

### 3. Embedding Layer (`embedding.py`)

**Purpose:** Generate vector representations of text

**Supported Backends:**
- Local embedding service (custom API)
- OpenAI embeddings (text-embedding-3-large)

**Features:**
- Batch processing for efficiency
- Retry logic for robustness
- Configurable embedding dimensions

**Vector Dimensions:** 1024 (configurable)

### 4. Storage Layer (`es_index.py`)

**Purpose:** Manage Elasticsearch indices

**Index Schema:**
```json
{
  "text": "text",              // Full-text search
  "vector": "dense_vector",    // Vector similarity
  "doc_type": "keyword",       // text/image/table
  "page_num": "integer",       // Source page
  "file_name": "keyword",      // Source file
  "metadata": "object"         // Flexible metadata
}
```

**Features:**
- Automatic index creation
- Bulk indexing
- Index statistics
- Error handling and retries

### 5. Retrieval Layer (`retrieval.py`)

**Purpose:** Hybrid search combining keyword and vector search

**Search Methods:**

1. **BM25 Keyword Search:**
   - Jieba tokenization for Chinese
   - Fuzzy matching
   - Stop word filtering
   - Multi-keyword OR queries

2. **Vector Similarity Search:**
   - Cosine similarity
   - Dense vector retrieval
   - Configurable top-k

3. **Reciprocal Rank Fusion (RRF):**
   ```
   RRF_score(d) = Σ 1/(k + rank_i(d))
   ```
   - Combines keyword and vector results
   - Configurable k parameter (default: 60)
   - Deduplication of results

**Algorithm:**
```python
# For each document d:
score(d) = 1/(k + keyword_rank(d)) + 1/(k + vector_rank(d))
```

### 6. Reranking Layer (`reranking.py`)

**Purpose:** Improve retrieval precision

**Methods:**

1. **API-based Reranking:**
   - External reranking service
   - Cross-attention scoring
   - Query-document relevance

2. **Cross-Encoder Reranking:**
   - Local transformer model
   - Fine-grained relevance scoring
   - ms-marco-MiniLM-L-6-v2 default

**Process:**
1. Retrieve top-k candidates (e.g., 10)
2. Rerank to top-n (e.g., 5)
3. Use reranked results for generation

### 7. Query Enhancement Layer (`query_enhancement.py`)

**Purpose:** Improve query understanding and coverage

**Techniques:**

1. **RAG Fusion:**
   - Generates multiple query variations
   - Retrieves for each variation
   - Fuses results using RRF
   - Increases recall

2. **Query Decomposition:**
   - Identifies complex queries
   - Breaks into sub-queries
   - Answers each independently
   - Synthesizes final answer

3. **Coreference Resolution:**
   - Resolves pronouns and references
   - Uses conversation history
   - Creates standalone queries

### 8. Answer Generation Layer (`answer_generation.py`)

**Purpose:** Generate natural language answers with citations

**Features:**
- **Context Formatting:**
  - Numbered citations [1], [2], etc.
  - Document type indicators
  - Page number references
  
- **Answer Generation:**
  - GPT-4 or custom LLM
  - Source attribution
  - Grounded responses
  
- **Citation Extraction:**
  - Automatic citation parsing
  - Source linking
  - Evidence tracking

**Prompt Structure:**
```
System: You are a knowledge assistant...
User: 
  Context: [1] (Page 5) ...
           [2] (Page 8) ...
  Question: ...
```

### 9. Pipeline Orchestrator (`pipeline.py`)

**Purpose:** Coordinate end-to-end workflow

**Main Operations:**

1. **Ingestion Pipeline:**
   ```
   PDF → Extract → Chunk → Embed → Index
   ```

2. **Query Pipeline:**
   ```
   Query → Enhance → Retrieve → Rerank → Generate
   ```

**Configuration Options:**
- Reranking on/off
- RAG Fusion on/off
- Query Decomposition on/off
- Coreference Resolution (with history)

## Data Flow

### Ingestion Flow

```
┌─────────────┐
│  PDF File   │
└─────┬───────┘
      │
      ▼
┌─────────────────────────────┐
│  PDF Processor              │
│  • Extract text (pages)     │
│  • Extract images (vision)  │
│  • Extract tables (detect)  │
└─────┬───────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│  Chunking                   │
│  • Split text (1024 tokens) │
│  • Prepare images (captions)│
│  • Prepare tables (summary) │
└─────┬───────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│  Embedding                  │
│  • Generate vectors (1024d) │
│  • Batch processing (25)    │
└─────┬───────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│  Elasticsearch              │
│  • Index documents          │
│  • Store vectors            │
│  • Store metadata           │
└─────────────────────────────┘
```

### Query Flow

```
┌─────────────┐
│  User Query │
└─────┬───────┘
      │
      ▼
┌─────────────────────────────┐
│  Query Enhancement          │
│  • Coreference resolution   │
│  • RAG Fusion (optional)    │
│  • Decomposition (optional) │
└─────┬───────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│  Hybrid Search              │
│  • BM25 search → rank_k     │
│  • Vector search → rank_v   │
│  • RRF fusion               │
└─────┬───────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│  Reranking (optional)       │
│  • Cross-encoder scoring    │
│  • Top-k selection          │
└─────┬───────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│  Answer Generation          │
│  • Format context           │
│  • LLM generation           │
│  • Extract citations        │
└─────┬───────────────────────┘
      │
      ▼
┌─────────────┐
│   Answer    │
└─────────────┘
```

## Configuration

### Environment Variables

```bash
# Core services
ELASTICSEARCH_URL=http://localhost:9200
OPENAI_API_KEY=sk-xxx

# Optional services
EMBEDDING_URL=http://localhost:9800/v1/emb
RERANK_URL=http://localhost:2260/rerank
IMAGE_MODEL_URL=http://localhost:23333/v1

# Model selection
LLM_MODEL=gpt-4
FAST_LLM_MODEL=gpt-3.5-turbo
```

### System Parameters

```python
class RAGConfig:
    # Chunking
    CHUNK_SIZE = 1024
    CHUNK_OVERLAP = 100
    
    # Retrieval
    TOP_K_RETRIEVAL = 10
    TOP_K_RERANK = 5
    RRF_K = 60
    
    # Image filtering
    MIN_IMAGE_WIDTH = 200
    MIN_IMAGE_HEIGHT = 100
    IMAGE_WIDTH_RATIO = 3
```

## Performance Considerations

### Ingestion Performance

- **Bottleneck:** Vision model for image captioning
- **Optimization:** 
  - Batch embeddings (25 at a time)
  - Async processing for multiple PDFs
  - Image size filtering

### Query Performance

- **Bottleneck:** LLM generation time
- **Optimization:**
  - Reranking reduces context size
  - Faster models for query enhancement
  - Caching for repeated queries

### Storage

- **Index Size:** ~2-5x original PDF size
  - Text: minimal overhead
  - Vectors: 1024d × 4 bytes = 4KB per chunk
  - Metadata: varies

## Scalability

### Horizontal Scaling

1. **Elasticsearch Cluster:**
   - Multiple nodes for storage
   - Sharding for large indices
   - Replication for availability

2. **Processing:**
   - Multiple workers for ingestion
   - Queue-based architecture
   - Distributed embedding generation

### Vertical Scaling

1. **Memory:**
   - Elasticsearch heap size
   - Model loading (cross-encoder)
   - Batch size tuning

2. **Compute:**
   - GPU for embeddings (optional)
   - Parallel PDF processing
   - Concurrent queries

## Security Considerations

1. **API Keys:** Store in environment variables
2. **Elasticsearch:** Enable authentication in production
3. **Data Privacy:** Consider data retention policies
4. **Input Validation:** Sanitize user queries

## Monitoring and Debugging

### Key Metrics

- Ingestion rate (docs/second)
- Query latency (p50, p95, p99)
- Retrieval precision@k
- Answer relevance scores

### Logging

- Module-level logging
- Error tracking
- Performance profiling

## Future Enhancements

1. **Advanced Retrieval:**
   - Metadata filtering
   - Date/time range queries
   - Multi-modal search

2. **Performance:**
   - Query result caching
   - Streaming responses
   - Async operations

3. **Features:**
   - Multilingual support
   - Custom document types
   - User feedback loop

## References

- [Elasticsearch Dense Vector Search](https://www.elastic.co/guide/en/elasticsearch/reference/current/dense-vector.html)
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [RAG Fusion](https://github.com/Raudaschl/RAG-Fusion)
- [LangChain Documentation](https://python.langchain.com/)

