#!/usr/bin/env python3
"""Quick test for embeddings"""

import os
import sys

# Set environment before importing
os.environ['USE_OLLAMA_EMBEDDINGS'] = 'true'
os.environ['OLLAMA_URL'] = 'http://localhost:11434'
os.environ['EMBEDDING_MODEL'] = 'nomic-embed-text'

print("="*70)
print("TESTING EMBEDDINGS")
print("="*70)

# Check if Ollama is running
import requests
try:
    response = requests.get('http://localhost:11434/api/tags', timeout=2)
    print("\n✅ Ollama is running")
    models = response.json().get('models', [])
    print(f"   Available models: {len(models)}")
    for model in models:
        print(f"   - {model['name']}")
except Exception as e:
    print(f"\n❌ Ollama is NOT running: {e}")
    print("   Please start Ollama: ollama serve")
    sys.exit(1)

# Test Ollama embeddings
print("\n" + "="*70)
print("TESTING OLLAMA EMBEDDINGS")
print("="*70)

try:
    from embedding import ollama_embedding
    
    test_texts = ["Hello, world!", "This is a test sentence."]
    print(f"\nEmbedding {len(test_texts)} test texts...")
    
    embeddings = ollama_embedding(test_texts)
    
    print(f"✅ SUCCESS!")
    print(f"   Number of embeddings: {len(embeddings)}")
    print(f"   Embedding dimension: {len(embeddings[0])}")
    print(f"   First 5 values: {embeddings[0][:5]}")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print("✅ ALL TESTS PASSED!")
print("="*70)
print("\nYou can now use the PDF RAG system with Ollama embeddings!")
print("Run: python3 main.py")

