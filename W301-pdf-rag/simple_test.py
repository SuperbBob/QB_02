#!/usr/bin/env python3
"""
Simple Test - PDF RAG System
The absolute simplest way to test the system
"""

def main():
    print("\n" + "="*70)
    print("  PDF RAG SYSTEM - SIMPLE TEST")
    print("="*70 + "\n")
    
    # Step 1: Check imports
    print("Step 1: Checking imports...")
    try:
        from pipeline import PDFRAGPipeline
        print("  ✓ Pipeline module loaded successfully")
    except ImportError as e:
        print(f"  ✗ Error: {e}")
        print("\n  Please install dependencies:")
        print("    pip install -r requirements.txt")
        return
    
    # Step 2: Check Elasticsearch
    print("\nStep 2: Checking Elasticsearch...")
    try:
        from config import get_es
        es = get_es()
        info = es.info()
        print(f"  ✓ Connected to Elasticsearch {info['version']['number']}")
    except Exception as e:
        print(f"  ✗ Cannot connect to Elasticsearch: {e}")
        print("\n  Please start Elasticsearch:")
        print("    docker run -d --name elasticsearch -p 9200:9200 \\")
        print("      -e 'discovery.type=single-node' \\")
        print("      docker.elastic.co/elasticsearch/elasticsearch:8.11.0")
        return
    
    # Step 3: Check OpenAI API key
    print("\nStep 3: Checking OpenAI configuration...")
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your-openai-api-key-here':
        print("  ⚠️  OpenAI API key not configured")
        print("\n  To configure:")
        print("    1. Get API key from: https://platform.openai.com/api-keys")
        print("    2. Edit .env file and add your key")
        print("    3. Replace 'your-openai-api-key-here' with actual key")
        
        choice = input("\n  Do you want to continue anyway? (y/n): ").strip().lower()
        if choice != 'y':
            return
    else:
        print(f"  ✓ OpenAI API key configured (starts with: {api_key[:10]}...)")
    
    # Step 4: Initialize pipeline
    print("\nStep 4: Initializing PDF RAG pipeline...")
    try:
        pipeline = PDFRAGPipeline(index_name='simple_test')
        print("  ✓ Pipeline initialized successfully")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return
    
    # Step 5: Test with a PDF
    print("\n" + "="*70)
    print("READY TO TEST!")
    print("="*70)
    
    # Check for available test PDFs
    import os
    test_pdf_dir = "/Users/peixingao/Documents/RAG Demo/test_pdf"
    
    if os.path.exists(test_pdf_dir):
        pdf_files = [f for f in os.listdir(test_pdf_dir) if f.endswith('.pdf')]
        if pdf_files:
            print("\n📁 Found test PDFs:")
            for i, pdf in enumerate(pdf_files, 1):
                full_path = os.path.join(test_pdf_dir, pdf)
                size_mb = os.path.getsize(full_path) / (1024*1024)
                print(f"   {i}. {pdf} ({size_mb:.1f} MB)")
            
            choice = input("\n  Select a PDF to test (number or enter path): ").strip()
            
            if choice.isdigit() and 1 <= int(choice) <= len(pdf_files):
                pdf_path = os.path.join(test_pdf_dir, pdf_files[int(choice)-1])
            else:
                pdf_path = choice
    else:
        pdf_path = input("\n📄 Enter path to PDF file: ").strip()
    
    if not pdf_path or not os.path.exists(pdf_path):
        print("\n⏭️  Skipping PDF test.")
        print("\nYou can manually test with:")
        print("    from pipeline import PDFRAGPipeline")
        print("    pipeline = PDFRAGPipeline('test')")
        print("    pipeline.ingest_pdf('your_file.pdf')")
        print("    answer = pipeline.query('your question')")
        return
    
    # Ingest PDF
    print(f"\n{'='*70}")
    print(f"Processing: {os.path.basename(pdf_path)}")
    print(f"{'='*70}\n")
    
    try:
        print("📄 Ingesting PDF (this may take a few minutes)...")
        result = pipeline.ingest_pdf(pdf_path)
        
        print(f"\n✅ Success!")
        print(f"   Total chunks: {result['chunks']}")
        print(f"   - Text: {result['text_chunks']}")
        print(f"   - Images: {result['image_chunks']}")
        print(f"   - Tables: {result['table_chunks']}")
        
    except Exception as e:
        print(f"\n❌ Error during ingestion: {e}")
        print("\nThis could be because:")
        print("  - OpenAI API key is missing or invalid")
        print("  - Network connection issues")
        print("  - PDF file is corrupted")
        return
    
    # Query
    print(f"\n{'='*70}")
    print("QUERYING THE SYSTEM")
    print(f"{'='*70}\n")
    
    default_question = "What is this document about?"
    question = input(f"Enter your question (or press Enter for: '{default_question}'): ").strip()
    
    if not question:
        question = default_question
    
    try:
        print(f"\n🔍 Searching for: {question}")
        answer = pipeline.query(question, use_reranking=True)
        
        print(f"\n{'='*70}")
        print("ANSWER:")
        print(f"{'='*70}")
        print(answer['answer'])
        
        if answer.get('citations'):
            print(f"\n📚 Sources ({len(answer['citations'])}):")
            for cite in answer['citations']:
                print(f"   [{cite['citation_number']}] {cite['doc_type'].title()} - Page {cite['page_num']}")
        
        print(f"\n{'='*70}")
        print("✅ TEST COMPLETE!")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n❌ Error during query: {e}")
        print("\nThis could be because:")
        print("  - OpenAI API key issues")
        print("  - Network problems")
        return
    
    # Summary
    print("\n🎉 Congratulations! Your PDF RAG system is working!\n")
    print("Next steps:")
    print("  • Try more queries on this document")
    print("  • Process more PDFs into the same index")
    print("  • Explore advanced features (RAG Fusion, Query Decomposition)")
    print("  • Read GETTING_STARTED.md for more examples")
    print("  • Run 'python quick_demo.py' for interactive tutorial\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!\n")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check your setup and try again.\n")

