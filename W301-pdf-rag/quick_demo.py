#!/usr/bin/env python3
"""
Quick Demo - PDF RAG System
A simple interactive tutorial to get you started
"""
import os
import sys

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def print_step(step_num, text):
    """Print a step number"""
    print(f"\n📌 Step {step_num}: {text}")
    print("-" * 70)

def check_setup():
    """Check if the system is properly set up"""
    print_header("CHECKING SYSTEM SETUP")
    
    issues = []
    
    # Check Python packages
    print("Checking Python packages...")
    required_packages = [
        'elasticsearch', 'openai', 'fitz', 'tiktoken', 
        'jieba', 'requests', 'langchain'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - NOT INSTALLED")
            issues.append(f"Missing package: {package}")
    
    # Check .env file
    print("\nChecking configuration...")
    if os.path.exists('.env'):
        print("  ✓ .env file exists")
        
        # Check OpenAI API key
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        
        if api_key and api_key != 'your-openai-api-key-here':
            print("  ✓ OpenAI API key is configured")
        else:
            print("  ⚠️  OpenAI API key needs to be set in .env")
            issues.append("OpenAI API key not configured")
    else:
        print("  ✗ .env file not found")
        issues.append(".env file missing")
    
    # Check Elasticsearch
    print("\nChecking Elasticsearch...")
    try:
        from config import get_es
        es = get_es()
        info = es.info()
        print(f"  ✓ Connected to Elasticsearch {info['version']['number']}")
    except Exception as e:
        print(f"  ✗ Cannot connect to Elasticsearch: {e}")
        issues.append("Elasticsearch not accessible")
    
    # Summary
    print("\n" + "-"*70)
    if not issues:
        print("✅ All checks passed! System is ready to use.\n")
        return True
    else:
        print("⚠️  Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        print("\nPlease fix these issues before continuing.")
        print("Run: ./setup.sh or pip install -r requirements.txt\n")
        return False

def demo_basic_usage():
    """Demonstrate basic PDF ingestion and querying"""
    print_header("DEMO 1: BASIC USAGE")
    
    print("This demo shows how to:")
    print("  1. Initialize the RAG pipeline")
    print("  2. Ingest a PDF document")
    print("  3. Query the system")
    print("  4. Get answers with citations")
    
    print("\n" + "="*70)
    print("CODE EXAMPLE:")
    print("="*70)
    
    code = '''
from pipeline import PDFRAGPipeline

# Step 1: Initialize the pipeline
pipeline = PDFRAGPipeline(index_name='my_documents')

# Step 2: Ingest a PDF
result = pipeline.ingest_pdf('path/to/your/document.pdf')
print(f"✓ Indexed {result['indexed']} chunks")

# Step 3: Query the system
answer = pipeline.query(
    query="What is this document about?",
    use_reranking=True
)

# Step 4: View the answer
print(f"Answer: {answer['answer']}")
print(f"\\nCitations ({len(answer['citations'])}):")
for cite in answer['citations']:
    print(f"  [{cite['citation_number']}] Page {cite['page_num']}")
    '''
    
    print(code)
    
    print("\n" + "-"*70)
    input("Press Enter to continue...")

def demo_advanced_features():
    """Demonstrate advanced features"""
    print_header("DEMO 2: ADVANCED FEATURES")
    
    print("Advanced features include:")
    print("  1. RAG Fusion - multiple query variations")
    print("  2. Query Decomposition - break complex questions")
    print("  3. Multi-turn conversations")
    
    print("\n" + "="*70)
    print("CODE EXAMPLE - RAG Fusion:")
    print("="*70)
    
    code1 = '''
# Use RAG Fusion for better retrieval
answer = pipeline.query(
    query="Compare the advantages and disadvantages",
    use_rag_fusion=True,        # Generate multiple query variations
    use_reranking=True           # Use neural reranking
)
    '''
    print(code1)
    
    print("\n" + "="*70)
    print("CODE EXAMPLE - Query Decomposition:")
    print("="*70)
    
    code2 = '''
# Use Query Decomposition for complex queries
answer = pipeline.query(
    query="What are the differences between method A, B, and C?",
    use_query_decomposition=True  # Break into sub-queries
)
    '''
    print(code2)
    
    print("\n" + "="*70)
    print("CODE EXAMPLE - Multi-turn Conversation:")
    print("="*70)
    
    code3 = '''
# First question
answer1 = pipeline.query("What is machine learning?")

# Follow-up question with context
chat_history = [
    {"role": "user", "content": "What is machine learning?"},
    {"role": "assistant", "content": answer1['answer']}
]

# Ask follow-up (uses coreference resolution)
answer2 = pipeline.query(
    query="What are its applications?",  # "its" refers to ML
    chat_history=chat_history
)
    '''
    print(code3)
    
    print("\n" + "-"*70)
    input("Press Enter to continue...")

def demo_interactive():
    """Run an interactive demo"""
    print_header("INTERACTIVE DEMO")
    
    # Check if we can actually run
    try:
        from pipeline import PDFRAGPipeline
    except Exception as e:
        print(f"❌ Cannot import pipeline: {e}")
        print("\nPlease install dependencies first:")
        print("  pip install -r requirements.txt")
        return
    
    print("Let's try a real example!")
    print("\nYou'll need a PDF file to test with.")
    
    # Check for test PDFs in RAG Demo folder
    test_pdf_dir = "/Users/peixingao/Documents/RAG Demo/test_pdf"
    if os.path.exists(test_pdf_dir):
        print(f"\n📁 Found test PDFs in: {test_pdf_dir}")
        pdf_files = [f for f in os.listdir(test_pdf_dir) if f.endswith('.pdf')]
        if pdf_files:
            print("\nAvailable test PDFs:")
            for i, pdf in enumerate(pdf_files, 1):
                print(f"  {i}. {pdf}")
    
    pdf_path = input("\n📄 Enter path to your PDF file (or press Enter to skip): ").strip()
    
    if not pdf_path:
        print("\n⏭️  Skipping interactive demo.")
        print("You can run examples later with: python pipeline.py")
        return
    
    if not os.path.exists(pdf_path):
        print(f"\n❌ File not found: {pdf_path}")
        return
    
    try:
        print("\n🚀 Starting PDF RAG pipeline...")
        print("This may take a few minutes depending on PDF size...")
        
        # Initialize
        pipeline = PDFRAGPipeline(index_name='demo_index')
        
        # Ingest
        print(f"\n📄 Processing: {os.path.basename(pdf_path)}")
        result = pipeline.ingest_pdf(pdf_path)
        
        print(f"\n✅ Success!")
        print(f"   Text chunks: {result['text_chunks']}")
        print(f"   Image chunks: {result['image_chunks']}")
        print(f"   Table chunks: {result['table_chunks']}")
        print(f"   Total indexed: {result['indexed']}")
        
        # Query
        print("\n" + "="*70)
        query = input("\n❓ Enter your question (or press Enter for default): ").strip()
        if not query:
            query = "What is this document about?"
        
        print(f"\n🔍 Querying: {query}")
        answer = pipeline.query(query, use_reranking=True)
        
        print("\n" + "="*70)
        print("💡 ANSWER:")
        print("="*70)
        print(answer['answer'])
        
        if answer['citations']:
            print(f"\n📚 Citations ({len(answer['citations'])}):")
            for cite in answer['citations']:
                print(f"   [{cite['citation_number']}] {cite['doc_type']} - Page {cite['page_num']}")
        
        print("\n" + "="*70)
        print("✅ Demo complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nThis might be due to:")
        print("  - Missing API keys in .env")
        print("  - Elasticsearch not running")
        print("  - Network connectivity issues")

def show_next_steps():
    """Show what to do next"""
    print_header("NEXT STEPS")
    
    print("🎓 Learn more:")
    print("   - Read README.md for complete documentation")
    print("   - Check QUICKSTART.md for 5-minute setup")
    print("   - See example_usage.py for more examples")
    
    print("\n📝 Customize:")
    print("   - Edit config.py to adjust parameters")
    print("   - Modify prompts in answer_generation.py")
    print("   - Add custom features to pipeline.py")
    
    print("\n🚀 Deploy:")
    print("   - Create REST API with FastAPI")
    print("   - Deploy to cloud (AWS, GCP, Azure)")
    print("   - Use Docker for containerization")
    
    print("\n💡 Tips:")
    print("   - Start with small PDFs to test")
    print("   - Monitor your OpenAI API usage")
    print("   - Use GPT-3.5 for faster/cheaper queries")
    print("   - Enable reranking for better accuracy")
    
    print("\n📞 Get Help:")
    print("   - Run: python test_setup.py")
    print("   - Check logs for error messages")
    print("   - Review documentation files")

def main():
    """Main menu"""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*15 + "PDF RAG SYSTEM - QUICK DEMO" + " "*26 + "║")
    print("╚" + "="*68 + "╝")
    
    while True:
        print("\n" + "="*70)
        print("MENU:")
        print("  1. Check system setup")
        print("  2. View basic usage example")
        print("  3. View advanced features")
        print("  4. Run interactive demo")
        print("  5. Show next steps")
        print("  6. Exit")
        print("="*70)
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            check_setup()
        elif choice == '2':
            demo_basic_usage()
        elif choice == '3':
            demo_advanced_features()
        elif choice == '4':
            demo_interactive()
        elif choice == '5':
            show_next_steps()
        elif choice == '6':
            print("\n👋 Goodbye! Happy RAG-ing!\n")
            break
        else:
            print("\n⚠️  Invalid option. Please choose 1-6.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!\n")
        sys.exit(0)

