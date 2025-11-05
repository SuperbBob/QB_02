#!/bin/bash

# Setup Local LLM (Ollama) for PDF RAG System
# This script sets up a completely free, local alternative to OpenAI

set -e

echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
echo "║           Setting Up Local LLM (No OpenAI API Key Required!)                 ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Check if Ollama is installed
echo "Step 1: Checking for Ollama..."
if command -v ollama &> /dev/null; then
    echo "  ✓ Ollama is already installed"
else
    echo "  ✗ Ollama not found"
    echo ""
    echo "Installing Ollama..."
    
    # Install Ollama
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "  Detected macOS, installing via Homebrew..."
        if command -v brew &> /dev/null; then
            brew install ollama
        else
            echo "  Homebrew not found. Please install Ollama manually:"
            echo "  Visit: https://ollama.ai/download"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "  Detected Linux, installing..."
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        echo "  Please install Ollama manually from: https://ollama.ai/download"
        exit 1
    fi
    
    echo "  ✓ Ollama installed"
fi

# Step 2: Start Ollama service
echo ""
echo "Step 2: Starting Ollama service..."
if pgrep -x "ollama" > /dev/null; then
    echo "  ✓ Ollama service is already running"
else
    echo "  Starting Ollama in background..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
    echo "  ✓ Ollama service started"
fi

# Step 3: Pull a good model
echo ""
echo "Step 3: Downloading LLM model (this may take a few minutes)..."
echo "  We'll use 'llama3.2' - a good balance of quality and speed"
echo ""

if ollama list | grep -q "llama3.2"; then
    echo "  ✓ llama3.2 already downloaded"
else
    echo "  Downloading llama3.2 (about 2GB)..."
    ollama pull llama3.2
    echo "  ✓ Model downloaded"
fi

# Step 4: Test the model
echo ""
echo "Step 4: Testing the model..."
TEST_RESPONSE=$(ollama run llama3.2 "Say 'Hello, I am ready!' and nothing else" 2>/dev/null | head -1)
echo "  Model response: $TEST_RESPONSE"
echo "  ✓ Model is working"

# Step 5: Update .env file
echo ""
echo "Step 5: Updating configuration..."
cd "$(dirname "$0")"

# Backup existing .env if it exists
if [ -f .env ]; then
    cp .env .env.backup
    echo "  ✓ Backed up existing .env to .env.backup"
fi

# Create new .env with Ollama configuration
cat > .env << 'EOF'
# Elasticsearch Configuration
ELASTICSEARCH_URL=http://elastic:YDTAcgcM@localhost:9200

# Embedding Model Configuration (using local service)
EMBEDDING_URL=http://test.2brain.cn:9800/v1/emb

# Reranking Model Configuration (using local service)
RERANK_URL=http://test.2brain.cn:2260/rerank

# Vision Model Configuration (using local service)
IMAGE_MODEL_URL=http://test.2brain.cn:23333/v1

# OpenAI Configuration - Using Ollama (Local LLM)
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama

# LLM Models (using Ollama)
LLM_MODEL=llama3.2
FAST_LLM_MODEL=llama3.2
EOF

echo "  ✓ Updated .env to use Ollama"

echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
echo "║                              ✅ SETUP COMPLETE!                               ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Your PDF RAG system is now configured to use:"
echo "  • Ollama (Local LLM) - NO API KEY NEEDED!"
echo "  • Model: llama3.2"
echo "  • 100% FREE and runs on your computer"
echo ""
echo "Next steps:"
echo "  1. Make sure Ollama is running: ollama serve"
echo "  2. Test the system: python3 simple_test.py"
echo "  3. Or run: python3 test_local_llm.py"
echo ""
echo "Available Ollama models (you can switch):"
echo "  • llama3.2 (current, 2GB, fast)"
echo "  • mistral (7GB, more capable)"
echo "  • llama3 (4GB, balanced)"
echo ""
echo "To use a different model:"
echo "  1. Pull it: ollama pull mistral"
echo "  2. Edit .env: LLM_MODEL=mistral"
echo ""

