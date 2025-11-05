# Getting Started with PDF RAG System

A step-by-step guide for beginners.

## 🚀 Quick Start (5 Steps)

### Step 1: Install Dependencies

```bash
cd /Users/peixingao/cursor-git/QB_02/W301-pdf-rag

# Option A: Use the setup script (recommended)
./setup.sh

# Option B: Manual installation
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Set Up OpenAI API Key

1. **Get your API key:**
   - Go to https://platform.openai.com/api-keys
   - Click "Create new secret key"
   - Copy the key (starts with `sk-`)

2. **Add it to `.env` file:**
   ```bash
   # Edit the .env file
   nano .env
   
   # Change this line:
   OPENAI_API_KEY=your-openai-api-key-here
   
   # To:
   OPENAI_API_KEY=sk-your-actual-key-here
   ```

### Step 3: Verify Elasticsearch is Running

```bash
# Check if Elasticsearch is running
curl http://localhost:9200

# If not running, start it:
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 \
  -e "discovery.type=single-node" -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

### Step 4: Test Your Setup

```bash
# Run the setup verification
python test_setup.py
```

This will check:
- ✓ All packages installed
- ✓ Environment configured
- ✓ Elasticsearch connected
- ✓ OpenAI API working

### Step 5: Try the Interactive Demo

```bash
# Run the quick demo
python quick_demo.py
```

## 📖 Basic Usage Examples

### Example 1: Simple PDF Query

```python
from pipeline import PDFRAGPipeline

# Initialize
pipeline = PDFRAGPipeline(index_name='my_docs')

# Process a PDF
pipeline.ingest_pdf('document.pdf')

# Ask a question
answer = pipeline.query("What is this document about?")
print(answer['answer'])
```

### Example 2: With All Features

```python
# Use advanced features
answer = pipeline.query(
    query="Compare the advantages and disadvantages",
    use_rag_fusion=True,              # Better retrieval
    use_query_decomposition=True,     # Handle complex queries
    use_reranking=True,                # Better ranking
    rerank_method='api'                # Use neural reranker
)

print(f"Answer: {answer['answer']}")
print(f"\nSources used: {answer['num_sources']}")
```

### Example 3: Multi-turn Conversation

```python
# First question
answer1 = pipeline.query("What is machine learning?")
print(f"Assistant: {answer1['answer']}")

# Build conversation history
history = [
    {"role": "user", "content": "What is machine learning?"},
    {"role": "assistant", "content": answer1['answer']}
]

# Follow-up question
answer2 = pipeline.query(
    query="What are its main applications?",
    chat_history=history
)
print(f"Assistant: {answer2['answer']}")
```

### Example 4: Batch Processing

```python
import glob

pipeline = PDFRAGPipeline(index_name='research_papers')

# Process all PDFs in a folder
for pdf_file in glob.glob('pdfs/*.pdf'):
    print(f"Processing {pdf_file}...")
    result = pipeline.ingest_pdf(pdf_file)
    print(f"  ✓ Indexed {result['indexed']} chunks")

# Now query across all documents
answer = pipeline.query("What are the common themes across these papers?")
```

## 🎯 Common Use Cases

### Use Case 1: Research Assistant

```python
# Index research papers
pipeline = PDFRAGPipeline(index_name='research')
pipeline.ingest_pdf('paper1.pdf')
pipeline.ingest_pdf('paper2.pdf')

# Find specific information
answer = pipeline.query(
    "What methods were used for data analysis?",
    use_reranking=True
)
```

### Use Case 2: Document Q&A

```python
# Index company documents
pipeline = PDFRAGPipeline(index_name='company_docs')
pipeline.ingest_pdf('employee_handbook.pdf')
pipeline.ingest_pdf('policies.pdf')

# Answer employee questions
answer = pipeline.query(
    "What is the vacation policy?",
    use_rag_fusion=True
)
```

### Use Case 3: Technical Documentation Search

```python
# Index technical manuals
pipeline = PDFRAGPipeline(index_name='tech_docs')
pipeline.ingest_pdf('user_manual.pdf')
pipeline.ingest_pdf('api_documentation.pdf')

# Complex technical queries
answer = pipeline.query(
    "How do I configure the API authentication settings?",
    use_query_decomposition=True
)
```

## 🔧 Configuration Tips

### Adjust Chunk Size

Edit `config.py`:
```python
class RAGConfig:
    CHUNK_SIZE = 512        # Smaller chunks (more precise)
    CHUNK_OVERLAP = 50      # Less overlap
```

### Use Cheaper Models

Edit `.env`:
```bash
# Use GPT-3.5 instead of GPT-4 (10x cheaper)
LLM_MODEL=gpt-3.5-turbo
FAST_LLM_MODEL=gpt-3.5-turbo
```

### Adjust Retrieval Parameters

```python
# Retrieve more documents
answer = pipeline.query(
    "Your question",
    top_k=20  # Default is 10
)
```

## 🐛 Troubleshooting

### Problem: "Cannot connect to Elasticsearch"

**Solution:**
```bash
# Check if Elasticsearch is running
curl http://localhost:9200

# Start Elasticsearch if needed
docker start elasticsearch

# Or create new container
docker run -d --name elasticsearch -p 9200:9200 \
  -e "discovery.type=single-node" docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

### Problem: "OpenAI API error"

**Solutions:**
1. Check your API key in `.env`
2. Verify you have credits: https://platform.openai.com/usage
3. Check rate limits: https://platform.openai.com/account/rate-limits

### Problem: "Module not found"

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Problem: "PDF processing is slow"

**Solutions:**
1. Skip image processing if not needed:
   - Comment out image extraction in `pdf_processor.py`
2. Use smaller chunk size in `config.py`
3. Process PDFs in parallel

### Problem: "Out of memory"

**Solutions:**
1. Increase chunk size (process less chunks)
2. Process PDFs one at a time
3. Increase system memory
4. Use smaller batch size for embeddings

## 📊 Understanding the Output

### Query Response Structure

```python
{
    'answer': '...',              # The generated answer
    'citations': [                # Sources used
        {
            'citation_number': 1,
            'doc_type': 'text',    # or 'image', 'table'
            'page_num': 5,
            'text': '...'
        }
    ],
    'num_sources': 5,             # Number of sources
    'model': 'gpt-4'              # Model used
}
```

### Ingestion Result Structure

```python
{
    'success': True,
    'file_name': 'document.pdf',
    'chunks': 150,                # Total chunks
    'text_chunks': 140,           # Text chunks
    'image_chunks': 5,            # Image chunks
    'table_chunks': 5,            # Table chunks
    'indexed': 150                # Successfully indexed
}
```

## 💡 Best Practices

### 1. Start Small
- Test with a single small PDF first
- Verify results before processing many documents

### 2. Monitor Costs
- Check OpenAI usage: https://platform.openai.com/usage
- Use GPT-3.5 for testing
- Switch to GPT-4 for production

### 3. Optimize for Your Use Case
- Enable reranking for better quality
- Use RAG Fusion for complex topics
- Use query decomposition for multi-part questions

### 4. Handle Errors Gracefully
- Check for empty results
- Validate PDF files before processing
- Log errors for debugging

### 5. Test Different Configurations
- Try different chunk sizes
- Experiment with top-k values
- Test with/without advanced features

## 🎓 Learning Path

1. **Day 1**: Get basic system working
   - Run `test_setup.py`
   - Try `quick_demo.py`
   - Process one PDF

2. **Day 2**: Understand components
   - Read through module files
   - Modify configuration
   - Test different queries

3. **Day 3**: Advanced features
   - Try RAG Fusion
   - Test query decomposition
   - Experiment with reranking

4. **Week 2**: Customize
   - Adjust prompts
   - Add custom features
   - Optimize for your data

5. **Week 3**: Deploy
   - Create REST API
   - Set up monitoring
   - Deploy to production

## 📚 Additional Resources

- **Full Documentation**: `README.md`
- **Architecture Details**: `ARCHITECTURE.md`
- **5-Minute Setup**: `QUICKSTART.md`
- **Project Overview**: `PROJECT_SUMMARY.md`
- **Code Examples**: `example_usage.py`

## ❓ FAQ

**Q: Do I need GPT-4 or can I use GPT-3.5?**
A: GPT-3.5 works fine and is much cheaper. GPT-4 gives better answers but costs 10x more.

**Q: Can I use this without OpenAI?**
A: Yes! Use Ollama with local models. See README.md for setup.

**Q: How much does it cost per document?**
A: About $0.05-0.20 per 100-page PDF for ingestion, $0.01-0.03 per query with GPT-4.

**Q: Can I process images in PDFs?**
A: Yes! The system automatically extracts and captions images.

**Q: How accurate is the system?**
A: Very accurate when properly configured. Use reranking for best results.

**Q: Can I search across multiple PDFs?**
A: Yes! Index multiple PDFs into the same index, then query them all.

## 🚀 Ready to Start?

Run this now:
```bash
python quick_demo.py
```

Or jump straight to testing:
```python
from pipeline import PDFRAGPipeline
pipeline = PDFRAGPipeline(index_name='test')
# Your code here...
```

Good luck! 🎉

