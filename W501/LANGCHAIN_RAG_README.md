# LangChain RAG 问答系统

一个简单的基于 LangChain 的 RAG（Retrieval-Augmented Generation）问答应用。

## 功能特点

- 📄 **PDF 文档加载**: 支持加载单个 PDF 或整个文件夹
- 🔍 **智能分块**: 使用 RecursiveCharacterTextSplitter 进行文本分块
- 💾 **向量存储**: 使用 Chroma 作为本地向量数据库（无需外部服务）
- 🤖 **灵活的 LLM**: 支持 Ollama（本地）和 OpenAI
- 🔄 **持久化存储**: 自动保存向量数据库，下次启动时自动加载

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 确保 Ollama 正在运行

```bash
# 启动 Ollama
ollama serve

# 拉取需要的模型
ollama pull llama3.2
ollama pull nomic-embed-text
```

### 3. 运行交互式演示

```bash
cd W501
python langchain_demo.py
```

## 代码使用示例

### 基本用法

```python
from langchain_rag import create_rag

# 创建 RAG 实例（使用 Ollama）
rag = create_rag(use_ollama=True)

# 加载 PDF 文档
rag.ingest_pdf("path/to/document.pdf")

# 提问
result = rag.query("这篇文档讲了什么？")
print(result["answer"])
```

### 加载多个文档

```python
# 加载整个文件夹的 PDF
rag.ingest_directory("path/to/pdf_folder/")

# 或者加载多个指定文件
from langchain_rag import LangChainRAG

rag = LangChainRAG()
chunks = rag.load_multiple_pdfs([
    "doc1.pdf",
    "doc2.pdf",
    "doc3.pdf"
])
rag.add_documents(chunks)
```

### 使用 OpenAI

```python
# 设置环境变量
import os
os.environ["OPENAI_API_KEY"] = "your-api-key"

# 创建使用 OpenAI 的 RAG
rag = create_rag(use_ollama=False)
```

### 相似度搜索

```python
# 不使用 LLM，直接搜索相关内容
docs = rag.similarity_search("关键词", k=5)
for doc in docs:
    print(doc.page_content)
```

## 配置选项

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `persist_directory` | `./chroma_db` | 向量数据库存储路径 |
| `chunk_size` | 1000 | 文本分块大小 |
| `chunk_overlap` | 200 | 分块重叠大小 |
| `use_ollama` | True | 是否使用 Ollama |
| `ollama_model` | `llama3.2` | Ollama LLM 模型 |
| `embedding_model` | `nomic-embed-text` | Embedding 模型 |

## 目录结构

```
W501/
├── langchain_rag.py          # RAG 核心模块
├── langchain_demo.py         # 交互式演示脚本
├── requirements.txt          # 依赖列表
├── chroma_db/                # 向量数据库（自动创建）
└── LANGCHAIN_RAG_README.md   # 本文档
```

## 环境变量

可选的环境变量配置：

```bash
# Ollama 配置
OLLAMA_URL=http://localhost:11434

# OpenAI 配置（如果使用 OpenAI）
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

## 注意事项

1. 首次运行时需要下载 embedding 模型，可能需要几分钟
2. 向量数据库会自动持久化到 `chroma_db` 目录
3. 使用 `rag.clear_database()` 可以清除所有已索引的文档

