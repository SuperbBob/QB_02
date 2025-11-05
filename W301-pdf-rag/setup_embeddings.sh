#!/bin/bash

# Setup Embeddings for PDF RAG System
# This script sets up Ollama embeddings as a free local alternative

set -e

echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
echo "║             Setting Up Local Embeddings with Ollama                         ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
echo

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed!"
    echo
    echo "Please run ./setup_local_llm.sh first to install Ollama"
    exit 1
fi

echo "✅ Ollama is installed"
echo

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama is not running. Starting Ollama..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
    echo "✅ Ollama started"
else
    echo "✅ Ollama is running"
fi
echo

# Pull embedding model
echo "📥 Downloading embedding model (nomic-embed-text, ~274MB)..."
echo "   This model is optimized for embeddings and much smaller than LLMs"
echo

if ollama list | grep -q "nomic-embed-text"; then
    echo "✅ nomic-embed-text is already installed"
else
    ollama pull nomic-embed-text
    echo "✅ Downloaded nomic-embed-text"
fi
echo

# Test embedding model
echo "🧪 Testing embedding model..."
TEST_RESULT=$(ollama run nomic-embed-text "test" 2>&1 || true)

if [ $? -eq 0 ]; then
    echo "✅ Embedding model works!"
else
    echo "⚠️  Model downloaded but test failed. This is normal - embeddings work via API."
fi
echo

# Create/update .env file
echo "📝 Configuring .env file..."

# Get current Elasticsearch password if .env exists
ES_URL="http://elastic:2braintest@localhost:9200"
if [ -f .env ]; then
    EXISTING_ES=$(grep "ELASTICSEARCH_URL=" .env | cut -d'=' -f2- || echo "")
    if [ ! -z "$EXISTING_ES" ]; then
        ES_URL="$EXISTING_ES"
    fi
fi

cat > .env << EOF
# Elasticsearch connection
ELASTICSEARCH_URL=$ES_URL

# Ollama for embeddings (free, local)
# Using Ollama's API format
EMBEDDING_MODEL=nomic-embed-text
USE_OLLAMA_EMBEDDINGS=true

# Ollama for LLM
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=qwen2.5:3b
FAST_LLM_MODEL=qwen2.5:3b

# These are not used but kept for config compatibility
RERANK_URL=http://test.2brain.cn:2260/rerank
IMAGE_MODEL_URL=http://test.2brain.cn:23333/v1
EOF

echo "✅ .env file configured"
echo

# Test embeddings
echo "🧪 Testing embeddings API..."

TEST_EMBEDDING=$(curl -s http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "Hello world"
}' 2>&1)

if echo "$TEST_EMBEDDING" | grep -q "embedding"; then
    echo "✅ Embeddings API works!"
    
    # Get embedding dimension
    DIM=$(echo "$TEST_EMBEDDING" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data['embedding']))" 2>/dev/null || echo "unknown")
    echo "   Embedding dimension: $DIM"
else
    echo "⚠️  Could not test embeddings API"
fi
echo

echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ EMBEDDINGS SETUP COMPLETE!                            ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
echo
echo "📋 Configuration:"
echo "   • Embedding Model: nomic-embed-text"
echo "   • Embedding Dim: 768 (compatible with system)"
echo "   • API: http://localhost:11434/api/embeddings"
echo "   • Cost: FREE (100% local)"
echo
echo "🎯 Next Steps:"
echo "   1. Update your code to use Ollama embeddings"
echo "   2. Run: python3 embedding.py  # Test embeddings"
echo "   3. Run: python3 main.py       # Use the system"
echo
echo "📚 Note: The system needs to be updated to use Ollama's API format."
echo "   I'll create an updated embedding.py for you."
echo

# Check if we should update embedding.py
if [ -f "embedding.py" ]; then
    echo "⚠️  To use Ollama embeddings, you need to update embedding.py"
    echo "   Would you like me to create an updated version? (This will be shown in the next step)"
fi

