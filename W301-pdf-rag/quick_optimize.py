#!/usr/bin/env python3
"""
Quick Optimization Script
Automatically optimize your PDF RAG system for better performance
"""
import os
import sys

def current_config():
    """Show current configuration"""
    print("\n" + "="*70)
    print("CURRENT CONFIGURATION")
    print("="*70 + "\n")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    model = os.getenv('LLM_MODEL', 'not set')
    base_url = os.getenv('OPENAI_BASE_URL', 'not set')
    
    print(f"LLM Model: {model}")
    print(f"Base URL: {base_url}")
    
    # Check if using OpenAI or Ollama
    if 'localhost' in base_url or 'ollama' in base_url.lower():
        print("\n✓ Using LOCAL LLM (Ollama)")
        
        # Check which Ollama model
        if 'phi' in model.lower():
            print("  → phi (fastest local model)")
        elif 'llama3.2' in model.lower():
            print("  → llama3.2 (fast & good balance)")
        elif 'mistral' in model.lower():
            print("  → mistral (slower but better quality)")
        else:
            print(f"  → {model}")
    else:
        print("\n✓ Using OpenAI API")
        if 'gpt-4' in model.lower():
            print("  → GPT-4 (slower but best quality)")
        elif 'gpt-3.5' in model.lower():
            print("  → GPT-3.5 Turbo (faster)")
    
    # Check config.py settings
    try:
        from config import RAGConfig
        print(f"\nRetrieval Settings:")
        print(f"  TOP_K_RETRIEVAL: {RAGConfig.TOP_K_RETRIEVAL}")
        print(f"  TOP_K_RERANK: {RAGConfig.TOP_K_RERANK}")
    except:
        print("\n⚠️  Could not load config.py")

def recommend_optimizations():
    """Provide optimization recommendations"""
    print("\n" + "="*70)
    print("OPTIMIZATION RECOMMENDATIONS")
    print("="*70 + "\n")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    model = os.getenv('LLM_MODEL', '')
    base_url = os.getenv('OPENAI_BASE_URL', '')
    
    recommendations = []
    
    # Check model choice
    if 'localhost' in base_url or 'ollama' in base_url.lower():
        if 'mistral' in model.lower() or 'llama3' in model.lower():
            recommendations.append({
                'priority': 'HIGH',
                'issue': 'Using slower local model',
                'solution': 'Switch to faster model',
                'action': 'Run: ollama pull llama3.2 or ollama pull phi'
            })
        elif 'llama3.2' not in model.lower() and 'phi' not in model.lower():
            recommendations.append({
                'priority': 'MEDIUM',
                'issue': 'Model not optimized',
                'solution': 'Use recommended fast models',
                'action': 'Edit .env: LLM_MODEL=llama3.2 or phi'
            })
    elif 'gpt-4' in model.lower():
        recommendations.append({
            'priority': 'MEDIUM',
            'issue': 'Using GPT-4 (slower)',
            'solution': 'Switch to GPT-3.5 for testing',
            'action': 'Edit .env: LLM_MODEL=gpt-3.5-turbo'
        })
    
    # Check config
    try:
        from config import RAGConfig
        if RAGConfig.TOP_K_RETRIEVAL > 10:
            recommendations.append({
                'priority': 'HIGH',
                'issue': f'Retrieving too many documents ({RAGConfig.TOP_K_RETRIEVAL})',
                'solution': 'Reduce to 5-10 documents',
                'action': 'Edit config.py: TOP_K_RETRIEVAL = 5'
            })
        
        if RAGConfig.TOP_K_RERANK > 5:
            recommendations.append({
                'priority': 'MEDIUM',
                'issue': f'Reranking too many documents ({RAGConfig.TOP_K_RERANK})',
                'solution': 'Reduce to 3-5 documents',
                'action': 'Edit config.py: TOP_K_RERANK = 3'
            })
    except:
        pass
    
    if not recommendations:
        print("✅ Configuration looks good!")
        print("\nIf still slow, try:")
        print("  • Use top_k=3 in queries")
        print("  • Disable advanced features for testing")
        print("  • Check system resources (CPU, RAM)")
    else:
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. [{rec['priority']}] {rec['issue']}")
            print(f"   Solution: {rec['solution']}")
            print(f"   Action: {rec['action']}")
            print()

def apply_fast_config():
    """Apply fastest configuration"""
    print("\n" + "="*70)
    print("APPLYING FAST CONFIGURATION")
    print("="*70 + "\n")
    
    choice = input("This will modify your .env and config.py. Continue? (y/n): ").strip().lower()
    if choice != 'y':
        print("Cancelled.")
        return
    
    # Update .env
    print("\n1. Checking for fast local model...")
    
    import subprocess
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if 'phi' in result.stdout:
            model = 'phi'
            print("   ✓ Found phi (fastest)")
        elif 'llama3.2' in result.stdout:
            model = 'llama3.2'
            print("   ✓ Found llama3.2 (fast)")
        else:
            print("   ⚠️  No fast models found")
            print("   Run: ollama pull llama3.2")
            model = 'llama3.2'
    except:
        print("   ⚠️  Ollama not found, will use OpenAI")
        model = 'gpt-3.5-turbo'
    
    # Read current .env
    env_lines = []
    try:
        with open('.env', 'r') as f:
            env_lines = f.readlines()
    except:
        print("   ⚠️  .env file not found")
        return
    
    # Update model line
    new_lines = []
    for line in env_lines:
        if line.startswith('LLM_MODEL='):
            new_lines.append(f'LLM_MODEL={model}\n')
            print(f"   ✓ Set LLM_MODEL={model}")
        elif line.startswith('FAST_LLM_MODEL='):
            new_lines.append(f'FAST_LLM_MODEL={model}\n')
        else:
            new_lines.append(line)
    
    # Write back
    with open('.env', 'w') as f:
        f.writelines(new_lines)
    
    print("\n2. Optimizing config.py...")
    
    # Read config.py
    try:
        with open('config.py', 'r') as f:
            config_content = f.read()
        
        # Replace values
        config_content = config_content.replace(
            'TOP_K_RETRIEVAL = 10',
            'TOP_K_RETRIEVAL = 5'
        )
        config_content = config_content.replace(
            'TOP_K_RERANK = 5',
            'TOP_K_RERANK = 3'
        )
        
        with open('config.py', 'w') as f:
            f.write(config_content)
        
        print("   ✓ Reduced TOP_K_RETRIEVAL to 5")
        print("   ✓ Reduced TOP_K_RERANK to 3")
    except:
        print("   ⚠️  Could not update config.py automatically")
        print("   Please manually edit:")
        print("     TOP_K_RETRIEVAL = 5")
        print("     TOP_K_RERANK = 3")
    
    print("\n" + "="*70)
    print("✅ OPTIMIZATION COMPLETE!")
    print("="*70)
    print("\nYour system is now configured for maximum speed.")
    print("Try running a query now - it should be much faster!")

def test_performance():
    """Test query performance"""
    print("\n" + "="*70)
    print("PERFORMANCE TEST")
    print("="*70 + "\n")
    
    try:
        from pipeline import PDFRAGPipeline
        import time
        
        # Check if index exists
        from config import get_es
        es = get_es()
        
        # Get list of indices
        indices = es.indices.get_alias(index="*")
        if not indices:
            print("⚠️  No indices found. Please ingest a PDF first.")
            return
        
        # Use first index
        index_name = list(indices.keys())[0]
        print(f"Using index: {index_name}")
        
        pipeline = PDFRAGPipeline(index_name=index_name)
        
        test_query = "test query"
        
        print(f"\nRunning test query: '{test_query}'")
        print("This will show you current performance...\n")
        
        start = time.time()
        
        answer = pipeline.query(
            test_query,
            top_k=3,
            use_reranking=False,
            use_rag_fusion=False,
            use_query_decomposition=False
        )
        
        elapsed = time.time() - start
        
        print(f"\n✓ Query completed in {elapsed:.2f} seconds")
        
        if elapsed < 5:
            print("   🚀 FAST - Performance is good!")
        elif elapsed < 15:
            print("   ⚡ MODERATE - Could be optimized")
        else:
            print("   🐌 SLOW - Needs optimization")
            print("\nTry:")
            print("  python3 quick_optimize.py")
            print("  Select option 3 to apply fast config")
        
    except Exception as e:
        print(f"⚠️  Could not run test: {e}")
        print("\nMake sure you have:")
        print("  1. Ingested at least one PDF")
        print("  2. Elasticsearch running")
        print("  3. LLM configured")

def main():
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*20 + "QUICK OPTIMIZATION TOOL" + " "*26 + "║")
    print("╚" + "="*68 + "╝")
    
    while True:
        print("\n" + "="*70)
        print("OPTIONS:")
        print("  1. View current configuration")
        print("  2. Get optimization recommendations")
        print("  3. Apply fast configuration (automatic)")
        print("  4. Test current performance")
        print("  5. Exit")
        print("="*70)
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            current_config()
        elif choice == '2':
            current_config()
            recommend_optimizations()
        elif choice == '3':
            apply_fast_config()
        elif choice == '4':
            test_performance()
        elif choice == '5':
            print("\n👋 Goodbye!\n")
            break
        else:
            print("\n⚠️  Invalid option.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted.\n")
        sys.exit(0)

