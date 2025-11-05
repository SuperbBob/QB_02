# Quick Start Guide

Get started with the PDF RAG system in 5 minutes!

## Prerequisites

- Python 3.8+
- Docker (for Elasticsearch)
- OpenAI API key

## 1. Start Elasticsearch

```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

Verify it's running:
```bash
curl http://localhost:9200
```

## 2. Install Dependencies

```bash
# Run the setup script
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure API Keys

Edit `.env`:
```bash
nano .env
```

Add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

## 4. Ingest Your First PDF

```python
from pipeline import PDFRAGPipeline

# Initialize
pipeline = PDFRAGPipeline(index_name='my_docs')

# Ingest PDF
result = pipeline.ingest_pdf('your_document.pdf')
print(f"Indexed {result['indexed']} chunks!")
```

## 5. Query the System

```python
# Simple query
answer = pipeline.query("What is this document about?")
print(answer['answer'])

# Advanced query with RAG Fusion
answer = pipeline.query(
    "Compare the pros and cons",
    use_rag_fusion=True,
    use_reranking=True
)
print(answer['answer'])
```

## Common Commands

### Check Elasticsearch
```bash
curl http://localhost:9200/_cluster/health
curl http://localhost:9200/_cat/indices
```

### Run Examples
```bash
python example_usage.py
python pipeline.py
```

### Stop Elasticsearch
```bash
docker stop elasticsearch
docker rm elasticsearch
```

## Troubleshooting

### Elasticsearch won't start
- Check if port 9200 is available: `lsof -i :9200`
- Check Docker logs: `docker logs elasticsearch`

### Import errors
- Activate virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### API errors
- Verify OpenAI API key in `.env`
- Check API key has sufficient credits
- Ensure `.env` is in the project root

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [example_usage.py](example_usage.py) for more examples
- Explore individual modules for customization

## System Requirements

**Minimum:**
- 4 GB RAM
- 10 GB disk space
- 2 CPU cores

**Recommended:**
- 8 GB+ RAM
- 50 GB+ disk space
- 4+ CPU cores
- SSD storage

## Support

- Issues: Open a GitHub issue
- Documentation: See README.md
- Examples: See example_usage.py

