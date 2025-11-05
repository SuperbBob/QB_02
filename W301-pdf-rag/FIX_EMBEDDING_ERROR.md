# Fix: Embedding Connection Error

## 🔴 Problem

You're getting this error:
```
Failed to get embeddings: HTTPConnectionPool(host='test.2brain.cn', port=9800): 
Max retries exceeded... Failed to resolve 'test.2brain.cn'
```

This means the system is trying to connect to a remote embedding service that you don't have access to.

## ✅ Solution: Use FREE Local Embeddings with Ollama

### Step 1: Install Embedding Model

```bash
# Pull the embedding model (only ~274MB, fast download)
ollama pull nomic-embed-text
```

### Step 2: Verify Model is Installed

```bash
ollama list
```

You should see `nomic-embed-text` in the list.

### Step 3: Configuration is Already Done!

The `.env` file has been updated with:
```bash
USE_OLLAMA_EMBEDDINGS=true
OLLAMA_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIM=768
```

### Step 4: Test Embeddings

```bash
python3 -c "
import os
os.environ['USE_OLLAMA_EMBEDDINGS'] = 'true'
from embedding import ollama_embedding
result = ollama_embedding(['Hello world'])
print(f'✅ Success! Embedding dimension: {len(result[0])}')
"
```

### Step 5: Recreate Your Index

**Important:** The embedding dimension changed from 1024 to 768, so you need to recreate the index:

```bash
python3 main.py
# Choose: 1. Index Management
# Choose: 3. Delete index
# Choose: 1. Create new index
```

### Step 6: Ingest PDFs Again

Now you can ingest PDFs with FREE local embeddings!

```bash
python3 main.py
# Choose: 2. PDF Ingestion
```

## 🚀 Quick Test

Run this to verify everything works:

```python
python3 << 'EOF'
import os
os.environ['USE_OLLAMA_EMBEDDINGS'] = 'true'

# Test embedding
from embedding import ollama_embedding
texts = ["Hello", "World"]
embeddings = ollama_embedding(texts)
print(f"✅ Embeddings work! Dimension: {len(embeddings[0])}")

# Test Elasticsearch
from config import get_es
es = get_es()
print(f"✅ Elasticsearch connected!")

print("\n🎉 System is ready!")
EOF
```

## 📊 What Changed?

| Before | After |
|--------|-------|
| Remote embeddings (test.2brain.cn) | Local Ollama embeddings |
| Dimension: 1024 | Dimension: 768 |
| Requires network | 100% local |
| Not accessible | FREE & fast |

## ⚠️ Common Issues

### Issue 1: "Ollama embedding failed"

**Solution:** Make sure Ollama is running
```bash
# Check if running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve
```

### Issue 2: "Model not found"

**Solution:** Pull the embedding model
```bash
ollama pull nomic-embed-text
ollama list  # Verify it's there
```

### Issue 3: "Dimension mismatch"

**Solution:** Delete and recreate the Elasticsearch index
```bash
python3 main.py
# -> Index Management -> Delete index -> Create new index
```

## 🎯 Complete Fresh Start

If you want to start completely fresh:

```bash
# 1. Delete old index
python3 main.py
# Choose: 1. Index Management -> 3. Delete index

# 2. Pull embedding model
ollama pull nomic-embed-text

# 3. Create new index (will use correct dimension)
python3 main.py
# Choose: 1. Index Management -> 1. Create new index

# 4. Ingest PDFs
python3 main.py
# Choose: 2. PDF Ingestion

# 5. Query
python3 main.py
# Choose: 3. Query System
```

## 💡 Why This is Better

✅ **FREE**: No API costs
✅ **FAST**: Local processing, no network latency
✅ **PRIVATE**: Data never leaves your machine
✅ **RELIABLE**: No dependency on external services
✅ **SIMPLE**: One-time setup

## 🔧 Technical Details

**Embedding Model:** nomic-embed-text
- Dimension: 768
- Speed: ~1000 texts/minute
- Quality: Comparable to OpenAI text-embedding-3-small
- Size: 274 MB
- Cost: FREE

**How it Works:**
1. Text goes to local Ollama (localhost:11434)
2. Ollama generates 768-dimensional vector
3. Vector stored in Elasticsearch
4. Used for semantic search

## 📚 Next Steps

Once embeddings work:

1. **Ingest PDFs** (fast with text-only, default settings)
2. **Query documents** (hybrid search with BM25 + vectors)
3. **Get answers** (using local LLM)

Everything runs locally and is FREE! 🎉

## ⁉️ Still Having Issues?

Run the diagnostic:

```bash
python3 -c "
import requests
import os

# Check Ollama
try:
    r = requests.get('http://localhost:11434/api/tags', timeout=2)
    print('✅ Ollama is running')
    models = [m['name'] for m in r.json().get('models', [])]
    if 'nomic-embed-text' in ' '.join(models):
        print('✅ nomic-embed-text is installed')
    else:
        print('❌ nomic-embed-text NOT installed. Run: ollama pull nomic-embed-text')
except:
    print('❌ Ollama is NOT running. Run: ollama serve')

# Check Elasticsearch
try:
    from config import get_es
    es = get_es()
    print('✅ Elasticsearch is connected')
except Exception as e:
    print(f'❌ Elasticsearch error: {e}')

# Check .env
if os.path.exists('.env'):
    with open('.env') as f:
        if 'USE_OLLAMA_EMBEDDINGS=true' in f.read():
            print('✅ .env is configured for Ollama')
        else:
            print('⚠️ .env may need update')
else:
    print('❌ .env file not found')
"
```

This will show you exactly what needs to be fixed!

