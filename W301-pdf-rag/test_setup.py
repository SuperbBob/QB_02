"""
Test script to verify the PDF RAG system setup
Checks all components and dependencies
"""
import sys
import os


def test_imports():
    """Test that all required packages can be imported"""
    print("\n" + "="*60)
    print("Testing Package Imports")
    print("="*60)
    
    packages = [
        ('elasticsearch', 'Elasticsearch'),
        ('openai', 'OpenAI'),
        ('fitz', 'PyMuPDF'),
        ('tiktoken', 'tiktoken'),
        ('jieba', 'jieba'),
        ('requests', 'requests'),
        ('langchain', 'LangChain'),
        ('langchain_community', 'LangChain Community'),
    ]
    
    failed = []
    for module_name, display_name in packages:
        try:
            __import__(module_name)
            print(f"✓ {display_name}")
        except ImportError as e:
            print(f"✗ {display_name} - {e}")
            failed.append(display_name)
    
    if failed:
        print(f"\n⚠️  Failed to import: {', '.join(failed)}")
        print("Run: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All packages imported successfully")
        return True


def test_environment():
    """Test environment configuration"""
    print("\n" + "="*60)
    print("Testing Environment Configuration")
    print("="*60)
    
    required_vars = [
        'ELASTICSEARCH_URL',
        'OPENAI_API_KEY',
    ]
    
    optional_vars = [
        'EMBEDDING_URL',
        'RERANK_URL',
        'IMAGE_MODEL_URL',
    ]
    
    # Try to load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✓ .env file loaded")
    except Exception as e:
        print(f"⚠️  Could not load .env: {e}")
    
    # Check required variables
    missing_required = []
    for var in required_vars:
        value = os.getenv(var)
        if value and value != 'your-openai-api-key-here':
            print(f"✓ {var} is set")
        else:
            print(f"✗ {var} is not set or using default value")
            missing_required.append(var)
    
    # Check optional variables
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var} is set (optional)")
        else:
            print(f"⚠️  {var} is not set (optional)")
    
    if missing_required:
        print(f"\n⚠️  Missing required variables: {', '.join(missing_required)}")
        print("Please set them in .env file")
        return False
    else:
        print("\n✅ All required environment variables are set")
        return True


def test_elasticsearch():
    """Test Elasticsearch connection"""
    print("\n" + "="*60)
    print("Testing Elasticsearch Connection")
    print("="*60)
    
    try:
        from config import get_es
        es = get_es()
        info = es.info()
        print(f"✓ Connected to Elasticsearch")
        print(f"  Cluster: {info['cluster_name']}")
        print(f"  Version: {info['version']['number']}")
        return True
    except Exception as e:
        print(f"✗ Failed to connect to Elasticsearch: {e}")
        print("\nTo start Elasticsearch:")
        print("  docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 \\")
        print("    -e \"discovery.type=single-node\" -e \"xpack.security.enabled=false\" \\")
        print("    docker.elastic.co/elasticsearch/elasticsearch:8.11.0")
        return False


def test_modules():
    """Test that all custom modules can be imported"""
    print("\n" + "="*60)
    print("Testing Custom Modules")
    print("="*60)
    
    modules = [
        'config',
        'embedding',
        'pdf_processor',
        'chunking',
        'es_index',
        'retrieval',
        'reranking',
        'query_enhancement',
        'answer_generation',
        'pipeline',
    ]
    
    failed = []
    for module_name in modules:
        try:
            __import__(module_name)
            print(f"✓ {module_name}.py")
        except Exception as e:
            print(f"✗ {module_name}.py - {e}")
            failed.append(module_name)
    
    if failed:
        print(f"\n⚠️  Failed to import modules: {', '.join(failed)}")
        return False
    else:
        print("\n✅ All custom modules imported successfully")
        return True


def test_embedding_service():
    """Test embedding generation (optional)"""
    print("\n" + "="*60)
    print("Testing Embedding Service (Optional)")
    print("="*60)
    
    try:
        from embedding import local_embedding
        test_text = ["This is a test sentence."]
        embeddings = local_embedding(test_text)
        print(f"✓ Local embedding service is working")
        print(f"  Embedding dimension: {len(embeddings[0])}")
        return True
    except Exception as e:
        print(f"⚠️  Local embedding service not available: {e}")
        print("You can still use OpenAI embeddings")
        return None


def test_openai_connection():
    """Test OpenAI API connection"""
    print("\n" + "="*60)
    print("Testing OpenAI Connection")
    print("="*60)
    
    try:
        from openai import OpenAI
        from config import ModelConfig
        
        client = OpenAI(
            api_key=ModelConfig.OPENAI_API_KEY,
            base_url=ModelConfig.OPENAI_BASE_URL
        )
        
        # Test with a minimal request
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        print("✓ OpenAI API is working")
        print(f"  Response: {response.choices[0].message.content[:50]}")
        return True
    except Exception as e:
        print(f"✗ OpenAI API connection failed: {e}")
        print("Please check your OPENAI_API_KEY in .env")
        return False


def test_index_operations():
    """Test Elasticsearch index operations"""
    print("\n" + "="*60)
    print("Testing Elasticsearch Index Operations")
    print("="*60)
    
    try:
        from es_index import create_index, delete_index, get_index_stats
        
        test_index = 'test_setup_index'
        
        # Create index
        create_index(test_index)
        print(f"✓ Created test index: {test_index}")
        
        # Get stats
        stats = get_index_stats(test_index)
        print(f"✓ Retrieved index stats")
        
        # Delete index
        delete_index(test_index)
        print(f"✓ Deleted test index")
        
        print("\n✅ Elasticsearch index operations working")
        return True
    except Exception as e:
        print(f"✗ Index operations failed: {e}")
        return False


def run_all_tests():
    """Run all tests and provide summary"""
    print("\n" + "="*80)
    print("PDF RAG SYSTEM - SETUP VERIFICATION")
    print("="*80)
    
    results = {
        'Imports': test_imports(),
        'Environment': test_environment(),
        'Elasticsearch': test_elasticsearch(),
        'Custom Modules': test_modules(),
        'Embedding Service': test_embedding_service(),
        'OpenAI': test_openai_connection(),
        'Index Operations': test_index_operations(),
    }
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⚠ SKIP"
        print(f"{status:<10} {test_name}")
    
    print(f"\n{'='*80}")
    print(f"Total: {len(results)} tests | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    print(f"{'='*80}")
    
    if failed == 0:
        print("\n✅ All critical tests passed! System is ready to use.")
        print("\nNext steps:")
        print("1. Run: python example_usage.py")
        print("2. Or: python pipeline.py")
        print("3. Check QUICKSTART.md for usage examples")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above before using the system.")
        print("\nCommon fixes:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Configure .env file with your API keys")
        print("3. Start Elasticsearch: see README.md for instructions")
    
    print()
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

