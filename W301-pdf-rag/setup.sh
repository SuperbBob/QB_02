#!/bin/bash

# PDF RAG System Setup Script
# This script sets up the complete PDF RAG system

set -e  # Exit on error

echo "=========================================="
echo "PDF RAG System Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Create necessary directories
echo ""
echo "Creating necessary directories..."
mkdir -p pdf_images
mkdir -p logs
echo "✓ Directories created"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from template..."
    cat > .env << EOF
# Elasticsearch Configuration
ELASTICSEARCH_URL=http://elastic:password@localhost:9200

# Embedding Model Configuration
EMBEDDING_URL=http://localhost:9800/v1/emb

# Reranking Model Configuration
RERANK_URL=http://localhost:2260/rerank

# Vision Model Configuration (for image captioning)
IMAGE_MODEL_URL=http://localhost:23333/v1

# OpenAI Configuration (required for LLM-based operations)
OPENAI_API_KEY=your-openai-api-key-here

# LLM Models
LLM_MODEL=gpt-4
FAST_LLM_MODEL=gpt-3.5-turbo
EOF
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your API keys and configuration"
else
    echo "✓ .env file already exists"
fi

# Check if Elasticsearch is running
echo ""
echo "Checking Elasticsearch connection..."
if curl -s http://localhost:9200 > /dev/null 2>&1; then
    echo "✓ Elasticsearch is running"
else
    echo "⚠️  Elasticsearch is not running or not accessible at localhost:9200"
    echo ""
    echo "To start Elasticsearch using Docker:"
    echo "  docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e \"discovery.type=single-node\" -e \"xpack.security.enabled=false\" docker.elastic.co/elasticsearch/elasticsearch:8.11.0"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Ensure Elasticsearch is running"
echo "3. Activate the virtual environment: source venv/bin/activate"
echo "4. Run example_usage.py to test the system"
echo ""
echo "Usage:"
echo "  python example_usage.py"
echo "  python pipeline.py"
echo ""
echo "For more information, see README.md"
echo ""

