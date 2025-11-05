# Setup PDF RAG Without OpenAI (100% Free & Local)

This guide shows you how to run the PDF RAG system completely free, without needing an OpenAI API key.

## 🎯 What You'll Use Instead

| Component | OpenAI | Free Alternative |
|-----------|---------|------------------|
| **LLM** | GPT-4/GPT-3.5 ($$$) | Ollama with Llama 3.2 (Free!) |
| **Embeddings** | OpenAI Embeddings | Local embedding service (Already configured) |
| **Everything** | Paid API | 100% Local & Free |

## 🚀 Quick Setup (3 Steps)

### Option 1: Automated Setup (Easiest)

```bash
# Run the setup script
./setup_local_llm.sh

# Test it works
python3 test_local_llm.py
```

That's it! The script will:
- ✓ Install Ollama
- ✓ Download a good LLM model
- ✓ Configure your system
- ✓ Test everything works

### Option 2: Manual Setup

#### Step 1: Install Ollama

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from https://ollama.ai/download

#### Step 2: Start Ollama & Download Model

```bash
# Start Ollama service
ollama serve

# In another terminal, download a model
ollama pull llama3.2    # Fast & good (2GB)
# OR
ollama pull mistral     # More capable (7GB)
# OR
ollama pull llama3      # Balanced (4GB)
```

#### Step 3: Update Configuration

Edit `.env` file:
```bash
# Change these lines:
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=llama3.2
FAST_LLM_MODEL=llama3.2
```

## 📊 Model Comparison

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| **llama3.2** | 2GB | ⚡⚡⚡ Fast | ⭐⭐⭐ Good | General use, quick answers |
| **mistral** | 7GB | ⚡⚡ Medium | ⭐⭐⭐⭐ Great | Complex questions, detailed answers |
| **llama3** | 4GB | ⚡⚡ Medium | ⭐⭐⭐⭐ Great | Balanced performance |
| **codellama** | 7GB | ⚡⚡ Medium | ⭐⭐⭐⭐ Great | Code-related documents |

## ✅ Verify Setup

```bash
# Test Ollama is running
curl http://localhost:11434/api/tags

# Run test script
python3 test_local_llm.py

# Quick Python test
python3 << 'EOF'
from openai import OpenAI
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
response = client.chat.completions.create(
    model="llama3.2",
    messages=[{"role": "user", "content": "Say hello!"}]
)
print(response.choices[0].message.content)
EOF
```

## 🎮 Using the System

Everything works the same way, just without OpenAI costs!

```python
from pipeline import PDFRAGPipeline

# Initialize (works exactly the same)
pipeline = PDFRAGPipeline(index_name='my_docs')

# Process PDF (works exactly the same)
pipeline.ingest_pdf('document.pdf')

# Query (works exactly the same)
answer = pipeline.query("What is this about?", use_reranking=True)
print(answer['answer'])
```

## ⚠️ Limitations & Solutions

### 1. Image Processing

**Issue:** Image captioning requires vision model (not free by default)

**Solutions:**
- Use the configured vision service: `IMAGE_MODEL_URL=http://test.2brain.cn:23333/v1`
- Or skip images: Comment out image extraction in `pdf_processor.py`
- Or use LLaVA (Ollama vision model): `ollama pull llava`

### 2. Slower Than GPT-4

**Issue:** Local models are slower than OpenAI API

**Solutions:**
- Use smaller models (llama3.2 is fast)
- Use GPU if available
- Accept slower but free tradeoff

### 3. Different Quality

**Issue:** Free models aren't as good as GPT-4

**Solutions:**
- Use larger models (mistral, llama3)
- Adjust prompts for better results
- For critical work, use GPT-4; for testing, use local

## 💰 Cost Comparison

### With OpenAI:
- Setup: $0
- Per document (100 pages): $0.05-0.20
- Per query: $0.01-0.03
- **Monthly (moderate use): $20-50**

### With Local (Ollama):
- Setup: $0
- Per document: $0
- Per query: $0
- **Monthly: $0** 🎉

Only cost: Electricity (~$1/month if running 24/7)

## 🔧 Troubleshooting

### Ollama Not Starting

```bash
# Check if already running
pgrep ollama

# Kill and restart
pkill ollama
ollama serve
```

### Model Not Found

```bash
# List available models
ollama list

# Pull the model
ollama pull llama3.2
```

### Connection Error

```bash
# Check Ollama is accessible
curl http://localhost:11434/api/tags

# Check .env configuration
cat .env | grep OPENAI
```

### Out of Memory

**Solutions:**
- Use smaller model (llama3.2 instead of mistral)
- Close other applications
- Add more RAM

## 🚀 Advanced: Running Multiple Models

You can run different models for different purposes:

```bash
# Edit .env
LLM_MODEL=mistral              # Use for complex answers
FAST_LLM_MODEL=llama3.2        # Use for quick tasks
```

Or switch models dynamically:

```python
# Use specific model for a query
answer = pipeline.query(
    "Complex question",
    model="mistral"  # Override default
)
```

## 📈 Performance Tips

### 1. Use GPU (if available)

Ollama automatically uses GPU if available. Check:
```bash
ollama ps
```

### 2. Adjust Context Length

Larger context = slower but better understanding:
```bash
# When pulling model
ollama pull llama3.2
# Then run with custom context
# (This is handled automatically by the system)
```

### 3. Batch Queries

Process multiple questions at once for better efficiency.

### 4. Keep Ollama Running

Don't stop/start Ollama repeatedly:
```bash
# Run in background at startup
ollama serve &
```

## 🎯 Recommended Setup

For best free experience:

```bash
# 1. Install Ollama
brew install ollama

# 2. Start service
ollama serve

# 3. Pull recommended model
ollama pull llama3.2

# 4. Configure system
./setup_local_llm.sh

# 5. Test
python3 test_local_llm.py

# 6. Use it!
python3 simple_test.py
```

## ✨ Benefits of Local LLM

1. **$0 Cost** - Completely free
2. **Privacy** - Data never leaves your computer
3. **No Limits** - No rate limits or quotas
4. **Offline** - Works without internet
5. **Customizable** - Choose your model

## 📚 Additional Resources

- **Ollama**: https://ollama.ai
- **Available Models**: https://ollama.ai/library
- **Model Comparison**: https://ollama.ai/blog/models
- **Community**: https://github.com/ollama/ollama

## 🆘 Need Help?

1. Run diagnostics: `python3 test_local_llm.py`
2. Check Ollama: `ollama list`
3. View logs: `ollama logs`
4. Restart service: `pkill ollama && ollama serve`

---

**Ready to start?** Run:
```bash
./setup_local_llm.sh
```

