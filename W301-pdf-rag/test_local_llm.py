#!/usr/bin/env python3
"""
Test Local LLM Setup
Verify that the system works without OpenAI API key
"""
import os
import sys

def test_ollama_connection():
    """Test if Ollama is accessible"""
    print("\n" + "="*70)
    print("Testing Local LLM (Ollama)")
    print("="*70 + "\n")
    
    try:
        import requests
        
        # Test Ollama API
        print("Checking Ollama service...")
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✓ Ollama is running")
            print(f"  Available models: {len(models)}")
            for model in models:
                print(f"    - {model.get('name', 'unknown')}")
            return True
        else:
            print(f"✗ Ollama responded with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to Ollama")
        print("\nOllama is not running. To fix:")
        print("  1. Install: brew install ollama")
        print("  2. Start: ollama serve")
        print("  3. Or run: ./setup_local_llm.sh")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_local_llm_chat():
    """Test chat completion with local LLM"""
    print("\n" + "="*70)
    print("Testing Chat Completion")
    print("="*70 + "\n")
    
    try:
        from openai import OpenAI
        
        # Configure for Ollama
        client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"  # Ollama doesn't need a real key
        )
        
        print("Sending test message to LLM...")
        response = client.chat.completions.create(
            model="llama3.2",  # or whatever model you have
            messages=[
                {"role": "user", "content": "Say 'Hello! I am working!' and nothing else."}
            ],
            max_tokens=20
        )
        
        answer = response.choices[0].message.content
        print(f"✓ LLM Response: {answer}")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nPossible issues:")
        print("  - Ollama not running (run: ollama serve)")
        print("  - Model not downloaded (run: ollama pull llama3.2)")
        print("  - Wrong model name in config")
        return False

def test_pipeline_config():
    """Test that pipeline can load with local LLM config"""
    print("\n" + "="*70)
    print("Testing Pipeline Configuration")
    print("="*70 + "\n")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        base_url = os.getenv('OPENAI_BASE_URL')
        api_key = os.getenv('OPENAI_API_KEY')
        model = os.getenv('LLM_MODEL')
        
        print(f"Configuration:")
        print(f"  Base URL: {base_url}")
        print(f"  API Key: {api_key}")
        print(f"  Model: {model}")
        
        if base_url == "http://localhost:11434/v1":
            print("✓ Configured for Ollama (local LLM)")
            return True
        else:
            print("⚠️  Not configured for Ollama")
            print("\nTo configure:")
            print("  Run: ./setup_local_llm.sh")
            print("  Or manually edit .env:")
            print("    OPENAI_BASE_URL=http://localhost:11434/v1")
            print("    OPENAI_API_KEY=ollama")
            print("    LLM_MODEL=llama3.2")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_simple_rag():
    """Test simple RAG without PDF processing"""
    print("\n" + "="*70)
    print("Testing Simple RAG Query")
    print("="*70 + "\n")
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"
        )
        
        # Simulate a RAG query
        context = """
        Machine learning is a subset of artificial intelligence that focuses on 
        enabling computers to learn from data without being explicitly programmed.
        """
        
        query = "What is machine learning?"
        
        prompt = f"""Based on the following context, answer the question.

Context: {context}

Question: {query}

Answer:"""
        
        print(f"Query: {query}")
        print("Generating answer...")
        
        response = client.chat.completions.create(
            model="llama3.2",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=100
        )
        
        answer = response.choices[0].message.content
        print(f"\n✓ Answer: {answer}")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*15 + "LOCAL LLM TEST (No OpenAI Needed!)" + " "*20 + "║")
    print("╚" + "="*68 + "╝")
    
    results = []
    
    # Run tests
    results.append(("Ollama Connection", test_ollama_connection()))
    
    if results[-1][1]:  # Only continue if Ollama is accessible
        results.append(("Chat Completion", test_local_llm_chat()))
        results.append(("Pipeline Config", test_pipeline_config()))
        results.append(("Simple RAG", test_simple_rag()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:<10} {test_name}")
    
    print("="*70)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    if passed == total:
        print(f"\n✅ All tests passed! ({passed}/{total})")
        print("\nYou can now use the PDF RAG system without OpenAI!")
        print("\nNext steps:")
        print("  python3 simple_test.py")
    else:
        print(f"\n⚠️  Some tests failed ({passed}/{total} passed)")
        print("\nTo fix:")
        print("  1. Run: ./setup_local_llm.sh")
        print("  2. Or manually:")
        print("     - Install Ollama: brew install ollama")
        print("     - Start service: ollama serve")
        print("     - Pull model: ollama pull llama3.2")
        print("     - Update .env file")
    
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted.\n")
        sys.exit(0)

