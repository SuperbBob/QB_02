# Performance Settings Guide

## 🚀 Speed vs Completeness Trade-offs

The PDF RAG system allows you to balance speed and completeness based on your needs.

## ⚡ Default Settings (FAST)

By default, the system skips images and tables for **5-10x faster processing**:

```python
# In config.py
class RAGConfig:
    PROCESS_IMAGES = False  # Skip images (default)
    PROCESS_TABLES = False  # Skip tables (default)
```

### Performance:
- **Speed**: 1-3 minutes per 100-page PDF
- **Cost**: Minimal (only text embeddings)
- **Use case**: Text-heavy documents, testing, quick indexing

## 🎯 Full Processing (COMPREHENSIVE)

Enable images and tables for complete document understanding:

```python
# In config.py
class RAGConfig:
    PROCESS_IMAGES = True  # Extract and caption images
    PROCESS_TABLES = True  # Extract and summarize tables
```

### Performance:
- **Speed**: 10-30 minutes per 100-page PDF
- **Cost**: Higher (vision model + LLM for summaries)
- **Use case**: Technical documents, presentations, research papers

## 📊 Comparison Table

| Setting | Speed | Cost | Text | Images | Tables | Best For |
|---------|-------|------|------|--------|--------|----------|
| **Text Only** (default) | ⚡⚡⚡ Fast | $ Low | ✅ | ❌ | ❌ | Books, articles, reports |
| **Text + Tables** | ⚡⚡ Medium | $$ Medium | ✅ | ❌ | ✅ | Financial docs, data reports |
| **Text + Images** | ⚡ Slow | $$ Medium | ✅ | ✅ | ❌ | Presentations, diagrams |
| **Everything** | 🐌 Very Slow | $$$ High | ✅ | ✅ | ✅ | Scientific papers, manuals |

## 🔧 How to Configure

### Method 1: Configuration File (Global Setting)

Edit `config.py`:

```python
class RAGConfig:
    # For fast processing (default)
    PROCESS_IMAGES = False
    PROCESS_TABLES = False
    
    # For comprehensive processing
    # PROCESS_IMAGES = True
    # PROCESS_TABLES = True
```

### Method 2: Per-Document Override (Flexible)

In your code:

```python
from pipeline import PDFRAGPipeline

pipeline = PDFRAGPipeline(index_name='my_docs')

# Fast: Text only (default)
pipeline.ingest_pdf('document.pdf')

# Medium: Text + tables
pipeline.ingest_pdf('report.pdf', process_tables=True)

# Slow: Text + images
pipeline.ingest_pdf('presentation.pdf', process_images=True)

# Comprehensive: Everything
pipeline.ingest_pdf('manual.pdf', 
                   process_images=True, 
                   process_tables=True)
```

### Method 3: Interactive (main.py)

When using `main.py`, you'll be prompted:

```
Processing Options:
  Default: Text only (fast, 1-3 min per PDF)
  With images/tables: Comprehensive (slow, 10-30 min per PDF)

Process images? (y/N): n
Process tables? (y/N): n
```

## 💡 Recommendations by Document Type

### Text-Heavy Documents (default settings)
```python
# Books, articles, blog posts, news
PROCESS_IMAGES = False
PROCESS_TABLES = False
```
**Speed**: ⚡⚡⚡ 1-3 minutes per 100 pages

### Data Reports
```python
# Financial reports, data analysis
PROCESS_IMAGES = False
PROCESS_TABLES = True
```
**Speed**: ⚡⚡ 5-10 minutes per 100 pages

### Presentations & Slides
```python
# PowerPoint, keynote slides
PROCESS_IMAGES = True
PROCESS_TABLES = False
```
**Speed**: ⚡ 8-15 minutes per 100 pages

### Technical Documentation
```python
# Research papers, scientific articles, manuals
PROCESS_IMAGES = True
PROCESS_TABLES = True
```
**Speed**: 🐌 10-30 minutes per 100 pages

## 🎯 Optimization Strategies

### Strategy 1: Test with Text First
```python
# Phase 1: Quick indexing for testing
pipeline.ingest_pdf('doc.pdf')  # Text only, ~2 minutes

# Phase 2: Test queries
answer = pipeline.query("What is this about?")

# Phase 3: If you need visuals, reprocess
pipeline.ingest_pdf('doc.pdf', 
                   process_images=True, 
                   process_tables=True)  # ~20 minutes
```

### Strategy 2: Selective Processing
```python
# Process most docs quickly
for pdf in standard_docs:
    pipeline.ingest_pdf(pdf)  # Text only

# Full processing for important docs
for pdf in important_docs:
    pipeline.ingest_pdf(pdf, 
                       process_images=True, 
                       process_tables=True)
```

### Strategy 3: Batch by Type
```python
# Books and articles (text only)
batch_ingest(books, process_images=False, process_tables=False)

# Reports (with tables)
batch_ingest(reports, process_images=False, process_tables=True)

# Research papers (everything)
batch_ingest(papers, process_images=True, process_tables=True)
```

## ⚠️ Important Notes

### When Images Matter
✅ Enable if document has:
- Diagrams, charts, graphs
- Screenshots, illustrations
- Visual explanations
- Flow charts, architecture diagrams

### When Tables Matter
✅ Enable if document has:
- Data tables, spreadsheets
- Comparison tables
- Statistical data
- Structured information

### When to Skip (Default)
✅ Skip for:
- Text-heavy books
- News articles
- Blog posts
- Simple documents
- Testing phase
- Cost/time constraints

## 📈 Performance Tips

1. **Start Fast**: Use defaults (text only) for initial testing
2. **Batch Wisely**: Group similar documents together
3. **Monitor Costs**: Image/table processing uses more API calls
4. **Scale Gradually**: Add features as needed
5. **Use Local LLM**: For free processing (slower but no cost)

## 🔄 Changing Settings

### To Enable Everything (in config.py):
```python
PROCESS_IMAGES = True
PROCESS_TABLES = True
```

### To Disable Everything (default, in config.py):
```python
PROCESS_IMAGES = False
PROCESS_TABLES = False
```

### To Override Per Document:
```python
# Always overrides config.py defaults
pipeline.ingest_pdf('doc.pdf', 
                   process_images=True,  # Force enable
                   process_tables=False) # Force disable
```

## 💰 Cost Impact

### Text Only (default):
- **API Calls**: ~100-200 per 100 pages
- **Cost**: ~$0.05-0.10 per 100 pages
- **Time**: 1-3 minutes

### With Images:
- **API Calls**: +50-100 per 10 images
- **Cost**: +$0.50-1.00 per 10 images
- **Time**: +5-15 minutes

### With Tables:
- **API Calls**: +20-50 per 10 tables
- **Cost**: +$0.20-0.50 per 10 tables
- **Time**: +3-8 minutes

## 🎓 Summary

**Default (Fast)**: Text only - Perfect for most use cases
- Set once in `config.py`: `PROCESS_IMAGES = False`, `PROCESS_TABLES = False`
- 5-10x faster than full processing
- Great for testing and text-heavy documents

**Full (Comprehensive)**: Everything - For complete understanding
- Override per document or change config globally
- Slower but captures all document content
- Best for technical/scientific documents

**Recommendation**: Start with defaults (text only), enable images/tables only when needed! 🚀

