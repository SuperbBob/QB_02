# PDF RAG System

A comprehensive Retrieval-Augmented Generation (RAG) system for processing PDF documents with support for text, images, and tables.

## Features

- **PDF Ingestion**: Extract and process text, images, and tables from any PDF document
- **Intelligent Chunking**: Smart text splitting with configurable chunk size and overlap
- **Image Captioning**: Automatic image description using vision models
- **Table Extraction**: Extract and summarize tables with context awareness
- **Hybrid Search**: Combine BM25 keyword search with vector similarity search
- **Reciprocal Rank Fusion (RRF)**: Intelligent result fusion from multiple search methods
- **Reranking**: Neural reranking for improved retrieval accuracy
- **RAG Fusion**: Multi-query generation for comprehensive information retrieval
- **Query Decomposition**: Break down complex queries into manageable sub-queries
- **Answer Generation**: Generate responses with citations and source attribution
- **Coreference Resolution**: Handle multi-turn conversations with context awareness

## Architecture

```
┌─────────────┐
│   PDF File  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│      PDF Processor                  │
│  • Text Extraction                  │
│  • Image Extraction & Captioning    │
│  • Table Extraction & Summarization │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────┐
│   Chunking Module   │
│  • Text Chunking    │
│  • Prepare Images   │
│  • Prepare Tables   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Embedding Module   │
│  • Generate Vectors │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Elasticsearch     │
│  • Store Chunks     │
│  • Store Embeddings │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│         Query Processing            │
│  • Coreference Resolution           │
│  • RAG Fusion                       │
│  • Query Decomposition              │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│        Hybrid Search                │
│  • BM25 Keyword Search              │
│  • Vector Similarity Search         │
│  • RRF Fusion                       │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────┐
│   Reranking Module  │
│  • Neural Reranker  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Answer Generation   │
│  • LLM Response     │
│  • Citations        │
└─────────────────────┘
```

## Prerequisites

- Python 3.8+
- Elasticsearch 8.0+
- OpenAI API key (for LLM operations)
- Optional: Local embedding model service
- Optional: Local reranking model service
- Optional: Local vision model service

## Installation

### 1. Install Elasticsearch

#### Using Docker (Recommended)

```bash
# Pull Elasticsearch image
docker pull docker.elastic.co/elasticsearch/elasticsearch:8.11.0

# Run Elasticsearch
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0

# Verify installation
curl http://localhost:9200
```

#### Using Homebrew (macOS)

```bash
brew tap elastic/tap
brew install elastic/tap/elasticsearch-full
brew services start elasticsearch
```

#### Manual Installation

Download from [Elasticsearch Downloads](https://www.elastic.co/downloads/elasticsearch) and follow the installation guide for your operating system.

### 2. Install Python Dependencies

```bash
# Clone the repository
cd W301-pdf-rag

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

Update the following in `.env`:
- `ELASTICSEARCH_URL`: Your Elasticsearch connection URL
- `OPENAI_API_KEY`: Your OpenAI API key
- Model URLs if using custom services

## Usage

### Quick Start

```python
from pipeline import PDFRAGPipeline

# Initialize pipeline
pipeline = PDFRAGPipeline(index_name='my_pdf_index')

# Ingest a PDF
result = pipeline.ingest_pdf('path/to/document.pdf')
print(f"Indexed {result['indexed']} chunks")

# Query the system
answer = pipeline.query(
    query="What is this document about?",
    use_reranking=True,
    use_rag_fusion=True
)

print(f"Answer: {answer['answer']}")
print(f"Citations: {len(answer['citations'])}")
```

### Ingesting PDFs

```python
from pipeline import PDFRAGPipeline

pipeline = PDFRAGPipeline(index_name='documents')

# Ingest single PDF
result = pipeline.ingest_pdf('document.pdf')

# Ingest multiple PDFs
import glob
for pdf_path in glob.glob('pdfs/*.pdf'):
    pipeline.ingest_pdf(pdf_path)
```

### Querying

#### Basic Query

```python
result = pipeline.query("What are the main findings?")
print(result['answer'])
```

#### With RAG Fusion

```python
result = pipeline.query(
    query="Compare the advantages and disadvantages",
    use_rag_fusion=True
)
```

#### With Query Decomposition

```python
result = pipeline.query(
    query="What are the differences between method A, B, and C?",
    use_query_decomposition=True
)
```

#### Multi-turn Conversation

```python
chat_history = [
    {"role": "user", "content": "What is machine learning?"},
    {"role": "assistant", "content": "Machine learning is..."}
]

result = pipeline.query(
    query="What are its applications?",
    chat_history=chat_history
)
```

### Using Individual Modules

#### PDF Processing

```python
from pdf_processor import process_pdf

text_pages, images, tables = process_pdf('document.pdf')
print(f"Extracted {len(text_pages)} pages, {len(images)} images, {len(tables)} tables")
```

#### Chunking

```python
from chunking import prepare_all_chunks

chunks = prepare_all_chunks(text_pages, images, tables)
print(f"Created {len(chunks)} chunks")
```

#### Hybrid Search

```python
from retrieval import hybrid_search

results = hybrid_search(
    query="machine learning",
    index_name="documents",
    top_k=10
)
```

#### Reranking

```python
from reranking import rerank_documents

reranked = rerank_documents(
    query="machine learning",
    documents=results,
    method='api',  # or 'cross_encoder'
    top_k=5
)
```

## Configuration

### RAG Parameters

Edit `config.py` to adjust system parameters:

```python
class RAGConfig:
    # Chunking
    CHUNK_SIZE = 1024
    CHUNK_OVERLAP = 100
    
    # Retrieval
    TOP_K_RETRIEVAL = 10
    TOP_K_RERANK = 5
    RRF_K = 60
    
    # Image extraction
    MIN_IMAGE_WIDTH = 200
    MIN_IMAGE_HEIGHT = 100
```

### Model Configuration

```python
class ModelConfig:
    LLM_MODEL = 'gpt-4'
    FAST_LLM_MODEL = 'gpt-3.5-turbo'
    EMBEDDING_DIM = 1024
```

## Advanced Features

### Custom System Prompts

```python
from answer_generation import generate_answer

custom_prompt = """You are a technical documentation assistant.
Provide detailed, accurate answers with code examples when relevant."""

result = generate_answer(
    query=query,
    documents=documents,
    system_prompt=custom_prompt
)
```

### Metadata Filtering

When creating the index, you can add metadata fields for filtering:

```python
from es_index import create_index

create_index('documents', include_metadata=True)

# Later, when searching, you can filter by metadata
# (Implementation depends on your specific needs)
```

## Project Structure

```
W301-pdf-rag/
├── config.py                 # Configuration and settings
├── embedding.py              # Embedding generation
├── pdf_processor.py          # PDF content extraction
├── chunking.py               # Text chunking and preparation
├── es_index.py               # Elasticsearch index management
├── retrieval.py              # Hybrid search with RRF
├── reranking.py              # Document reranking
├── query_enhancement.py      # RAG Fusion and Query Decomposition
├── answer_generation.py      # Answer generation with citations
├── pipeline.py               # Main RAG pipeline orchestrator
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
└── README.md                 # This file
```

## Testing

Run individual modules to test functionality:

```bash
# Test PDF processing
python pdf_processor.py

# Test retrieval
python retrieval.py

# Test reranking
python reranking.py

# Test query enhancement
python query_enhancement.py

# Test full pipeline
python pipeline.py
```

## Troubleshooting

### Elasticsearch Connection Issues

```python
# Check Elasticsearch status
curl http://localhost:9200/_cluster/health

# Check if index exists
curl http://localhost:9200/_cat/indices
```

### Memory Issues with Large PDFs

- Adjust `CHUNK_SIZE` in `config.py`
- Process PDFs in batches
- Increase available memory for Elasticsearch

### Image Extraction Fails

- Ensure vision model service is running
- Check `IMAGE_MODEL_URL` in `.env`
- Verify image quality and size thresholds in `config.py`

### Slow Query Performance

- Enable reranking for better top results
- Adjust `TOP_K_RETRIEVAL` and `TOP_K_RERANK`
- Use RAG Fusion for complex queries
- Optimize Elasticsearch settings

## Performance Optimization

1. **Batch Processing**: Process multiple PDFs in parallel
2. **Embedding Cache**: Cache embeddings for frequently used texts
3. **Index Optimization**: Configure Elasticsearch for your data size
4. **Reranking**: Use cross-encoder reranking for better accuracy
5. **Query Caching**: Cache results for common queries

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is provided as-is for educational and research purposes.

## References

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)
- [OpenAI API Documentation](https://platform.openai.com/docs/introduction)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)

## Citation

If you use this system in your research, please cite:

```bibtex
@software{pdf_rag_system,
  title = {PDF RAG System: A Comprehensive Retrieval-Augmented Generation System},
  year = {2025},
  url = {https://github.com/your-repo/W301-pdf-rag}
}
```

## Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation
- Review existing issues for solutions

## Changelog

### Version 1.0.0 (2025-11-04)
- Initial release
- PDF text, image, and table extraction
- Hybrid search with RRF
- Neural reranking
- RAG Fusion and Query Decomposition
- Answer generation with citations

