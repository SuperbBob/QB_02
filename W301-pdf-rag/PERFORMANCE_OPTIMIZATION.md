# Performance Optimization Guide

## 🐌 Common Slow Operations & Solutions

### Problem: "Step 4: Generating answer" is Too Slow

This typically happens during the LLM answer generation phase. Here are the causes and solutions:

## 🔍 Diagnose the Issue

### Check 1: What LLM Are You Using?

```bash
# Check your configuration
cat .env | grep -E "(OPENAI_BASE_URL|LLM_MODEL)"
```

**Expected times:**
- OpenAI GPT-4: 2-5 seconds ⚡
- OpenAI GPT-3.5: 1-3 seconds ⚡⚡
- Ollama (local): 10-60 seconds 🐌
- Large local models: 30-120 seconds 🐌🐌

### Check 2: How Much Context Are You Sending?

Too much context = slower generation

```python
# Add this to see context size
answer = pipeline.query("your question", top_k=5)  # Try smaller top_k
```

## 🚀 Quick Fixes (Try These First!)

### Fix 1: Reduce Retrieved Documents

**Problem:** Sending too many documents to LLM

**Solution:** Reduce `top_k` and `TOP_K_RERANK`

Edit `config.py`:
```python
class RAGConfig:
    TOP_K_RETRIEVAL = 5   # Was: 10 (reduce this)
    TOP_K_RERANK = 3      # Was: 5 (reduce this)
```

Or in your query:
```python
answer = pipeline.query(
    "your question",
    top_k=3  # Start small!
)
```

**Expected improvement:** 2-3x faster

### Fix 2: Use Faster Model

**If using OpenAI:**
```bash
# Edit .env
LLM_MODEL=gpt-3.5-turbo  # Instead of gpt-4 (10x faster!)
```

**If using Ollama:**
```bash
# Switch to smaller/faster model
ollama pull llama3.2   # 2GB, fast
ollama pull phi         # 1.5GB, even faster!

# Update .env
LLM_MODEL=llama3.2
```

**Expected improvement:** 5-10x faster

### Fix 3: Disable Advanced Features (for testing)

**Disable RAG Fusion and Query Decomposition:**
```python
answer = pipeline.query(
    "your question",
    use_rag_fusion=False,              # Disable multi-query
    use_query_decomposition=False,     # Disable sub-queries
    use_reranking=False                # Skip reranking (optional)
)
```

**Expected improvement:** 3-5x faster

## 🎯 Specific Solutions by Scenario

### Scenario 1: Using Ollama (Local LLM)

**Why it's slow:**
- Running on CPU (not GPU)
- Large model
- Too much context

**Solutions:**

#### A. Use Smaller Model
```bash
# Fastest models for Ollama
ollama pull phi           # 1.5GB, fastest
ollama pull llama3.2      # 2GB, fast & good
ollama pull tinyllama     # 600MB, very fast but lower quality

# Update .env
LLM_MODEL=phi
```

#### B. Reduce Context Window
```python
# In answer_generation.py, modify format_context()
def format_context(documents: List[Dict[str, Any]], max_docs: int = 3):
    # Only use top 3 documents instead of all
    documents = documents[:max_docs]
    # ... rest of code
```

#### C. Use GPU (if available)
```bash
# Check if GPU is being used
ollama ps

# Ollama automatically uses GPU if available
# Make sure you have Metal (Mac) or CUDA (Linux/Windows) support
```

#### D. Increase Ollama Performance
```bash
# Set environment variables for better performance
export OLLAMA_NUM_PARALLEL=4
export OLLAMA_MAX_LOADED_MODELS=1

# Restart Ollama
pkill ollama
ollama serve
```

### Scenario 2: Using OpenAI API

**Why it's slow:**
- Using GPT-4 (slower but more accurate)
- Sending too much context
- Network latency

**Solutions:**

#### A. Use GPT-3.5 Turbo
```bash
# Edit .env
LLM_MODEL=gpt-3.5-turbo
```

#### B. Reduce Context
Same as above - use smaller `top_k`

#### C. Enable Streaming (future enhancement)
```python
# For real-time responses (not currently implemented)
# This would show partial answers as they generate
```

### Scenario 3: Complex Queries

**Why it's slow:**
- RAG Fusion generates multiple queries
- Query Decomposition creates sub-queries
- Each variation needs separate processing

**Solutions:**

#### Disable for Simple Queries
```python
# Only use advanced features for complex questions
if "compare" in query.lower() or "difference" in query.lower():
    use_query_decomposition = True
else:
    use_query_decomposition = False

answer = pipeline.query(
    query,
    use_query_decomposition=use_query_decomposition,
    use_rag_fusion=False  # Often not needed
)
```

## 🔧 Advanced Optimizations

### 1. Optimize Chunking (Fewer, Larger Chunks)

Edit `config.py`:
```python
class RAGConfig:
    CHUNK_SIZE = 2048      # Increase from 1024
    CHUNK_OVERLAP = 200    # Increase from 100
```

**Effect:** Fewer chunks to search through, faster retrieval

### 2. Cache Embeddings

Currently not implemented, but you could add:
```python
# Create a simple cache
embedding_cache = {}

def cached_embed(text):
    if text in embedding_cache:
        return embedding_cache[text]
    embedding = local_embedding([text])[0]
    embedding_cache[text] = embedding
    return embedding
```

### 3. Skip Image/Table Processing (if not needed)

In `pdf_processor.py`, comment out:
```python
def process_pdf(pdf_path: str):
    text_content = extract_text_from_pdf(pdf_path)
    # images = extract_images_from_pdf(pdf_path)  # SKIP THIS
    # tables = extract_tables_from_pdf(pdf_path)  # SKIP THIS
    images = []
    tables = []
    return text_content, images, tables
```

**Effect:** 5-10x faster ingestion

### 4. Use Async Operations (Advanced)

Currently synchronous. Could parallelize:
```python
import asyncio

async def parallel_queries(queries):
    tasks = [query_async(q) for q in queries]
    return await asyncio.gather(*tasks)
```

### 5. Batch Processing

Process multiple queries together:
```python
queries = ["question 1", "question 2", "question 3"]
answers = [pipeline.query(q, top_k=3) for q in queries]
```

## 📊 Performance Benchmarks

### Typical Times (for 5 retrieved documents):

| Configuration | Answer Generation Time |
|--------------|----------------------|
| OpenAI GPT-4 | 3-5 seconds |
| OpenAI GPT-3.5 | 1-2 seconds |
| Ollama llama3.2 (M1 Mac) | 10-20 seconds |
| Ollama phi (M1 Mac) | 5-10 seconds |
| Ollama mistral (M1 Mac) | 30-60 seconds |

### Factors Affecting Speed:

1. **LLM Model**: Biggest factor (10x difference)
2. **Context Size**: 2-3x difference
3. **Hardware**: CPU vs GPU (5-10x difference)
4. **Network**: OpenAI API latency (1-2 seconds)

## 🎯 Recommended Settings by Use Case

### For Testing/Development (FAST)
```python
# config.py
class RAGConfig:
    TOP_K_RETRIEVAL = 3
    TOP_K_RERANK = 2

# .env
LLM_MODEL=gpt-3.5-turbo  # or phi/llama3.2 for local

# Usage
answer = pipeline.query(
    query,
    top_k=3,
    use_reranking=False,
    use_rag_fusion=False,
    use_query_decomposition=False
)
```

**Expected time:** 1-5 seconds

### For Production/Quality (BALANCED)
```python
# config.py
class RAGConfig:
    TOP_K_RETRIEVAL = 10
    TOP_K_RERANK = 5

# .env
LLM_MODEL=gpt-4  # or mistral for local

# Usage
answer = pipeline.query(
    query,
    top_k=10,
    use_reranking=True,
    use_rag_fusion=False,  # Only for complex queries
    use_query_decomposition=False
)
```

**Expected time:** 3-10 seconds (OpenAI) or 20-60 seconds (local)

### For Maximum Quality (SLOW)
```python
# Use all features
answer = pipeline.query(
    query,
    top_k=20,
    use_reranking=True,
    use_rag_fusion=True,
    use_query_decomposition=True
)
```

**Expected time:** 10-30 seconds (OpenAI) or 1-5 minutes (local)

## 🔍 Debug Slow Performance

### Add Timing to Your Code

```python
import time

def timed_query(query):
    start = time.time()
    
    print("Starting retrieval...")
    t1 = time.time()
    # Retrieval happens
    print(f"Retrieval took: {time.time() - t1:.2f}s")
    
    print("Starting reranking...")
    t2 = time.time()
    # Reranking happens
    print(f"Reranking took: {time.time() - t2:.2f}s")
    
    print("Starting answer generation...")
    t3 = time.time()
    answer = pipeline.query(query)
    print(f"Answer generation took: {time.time() - t3:.2f}s")
    
    print(f"Total time: {time.time() - start:.2f}s")
    return answer
```

### Check System Resources

```bash
# Check CPU usage
top -l 1 | grep "CPU usage"

# Check memory
top -l 1 | grep "PhysMem"

# Check if Ollama is using resources
ps aux | grep ollama
```

## 💡 Quick Win Checklist

Try these in order:

- [ ] Use smaller `top_k` (try 3-5 instead of 10)
- [ ] Switch to faster model (gpt-3.5-turbo or llama3.2/phi)
- [ ] Disable RAG Fusion and Query Decomposition
- [ ] Skip reranking for testing
- [ ] Reduce chunk size in config
- [ ] Use GPU if available (for local models)
- [ ] Close other heavy applications
- [ ] Restart Ollama service

## 🆘 Still Too Slow?

### Last Resort Options:

1. **Use OpenAI API** (fastest, but costs money)
2. **Use Groq API** (free tier, very fast)
3. **Upgrade hardware** (more RAM, GPU)
4. **Simplify queries** (ask simpler questions)
5. **Pre-compute answers** (for common questions)

### Contact for Help:

If still having issues, provide:
- Your `.env` configuration
- Hardware specs (CPU, RAM)
- Query example
- Timing breakdown

---

**Most Common Fix:** Use `top_k=3` and `gpt-3.5-turbo` or `llama3.2`

