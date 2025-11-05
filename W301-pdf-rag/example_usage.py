"""
Example usage of the PDF RAG system
Demonstrates all major features
"""
import os
from pipeline import PDFRAGPipeline


def example_1_basic_ingestion_and_query():
    """Example 1: Basic PDF ingestion and querying"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic PDF Ingestion and Query")
    print("="*80)
    
    # Initialize pipeline
    pipeline = PDFRAGPipeline(index_name='example_index')
    
    # Ingest a PDF (replace with your actual PDF path)
    pdf_path = "path/to/your/document.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"⚠️  PDF not found: {pdf_path}")
        print("Please update the pdf_path variable with a valid PDF file path.")
        return
    
    # Ingest the PDF
    print("\n📄 Ingesting PDF...")
    result = pipeline.ingest_pdf(pdf_path)
    
    print(f"\n✅ Ingestion complete!")
    print(f"   - Text chunks: {result['text_chunks']}")
    print(f"   - Image chunks: {result['image_chunks']}")
    print(f"   - Table chunks: {result['table_chunks']}")
    print(f"   - Total indexed: {result['indexed']}")
    
    # Query the system
    print("\n🔍 Querying the system...")
    query = "What is this document about?"
    
    answer = pipeline.query(query, top_k=5, use_reranking=True)
    
    print(f"\n❓ Query: {query}")
    print(f"\n💡 Answer:\n{answer['answer']}")
    
    if answer['citations']:
        print(f"\n📚 Citations ({len(answer['citations'])}):")
        for cite in answer['citations']:
            print(f"   [{cite['citation_number']}] {cite['doc_type']} - Page {cite['page_num']}")


def example_2_rag_fusion():
    """Example 2: Using RAG Fusion for better retrieval"""
    print("\n" + "="*80)
    print("EXAMPLE 2: RAG Fusion")
    print("="*80)
    
    pipeline = PDFRAGPipeline(index_name='example_index')
    
    query = "What are the key benefits and challenges?"
    
    print(f"\n🔍 Query with RAG Fusion: {query}")
    print("This will generate multiple query variations for comprehensive retrieval.")
    
    answer = pipeline.query(
        query=query,
        top_k=10,
        use_reranking=True,
        use_rag_fusion=True
    )
    
    print(f"\n💡 Answer:\n{answer['answer']}")


def example_3_query_decomposition():
    """Example 3: Using Query Decomposition for complex queries"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Query Decomposition")
    print("="*80)
    
    pipeline = PDFRAGPipeline(index_name='example_index')
    
    query = "Compare the advantages, disadvantages, and use cases of method A, B, and C"
    
    print(f"\n🔍 Complex query: {query}")
    print("This will be decomposed into sub-queries and answered comprehensively.")
    
    answer = pipeline.query(
        query=query,
        use_reranking=True,
        use_query_decomposition=True
    )
    
    print(f"\n💡 Answer:\n{answer['answer']}")
    
    if 'sub_queries' in answer:
        print(f"\n📋 Sub-queries used:")
        for i, sq in enumerate(answer['sub_queries']):
            print(f"   {i+1}. {sq}")


def example_4_multi_turn_conversation():
    """Example 4: Multi-turn conversation with coreference resolution"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Multi-turn Conversation")
    print("="*80)
    
    pipeline = PDFRAGPipeline(index_name='example_index')
    
    # First turn
    query1 = "What is machine learning?"
    print(f"\n👤 User: {query1}")
    
    answer1 = pipeline.query(query1, top_k=5, use_reranking=True)
    print(f"🤖 Assistant: {answer1['answer'][:200]}...")
    
    # Build chat history
    chat_history = [
        {"role": "user", "content": query1},
        {"role": "assistant", "content": answer1['answer']}
    ]
    
    # Second turn with coreference
    query2 = "What are its main applications?"
    print(f"\n👤 User: {query2}")
    print("(Note: 'its' refers to 'machine learning' from previous context)")
    
    answer2 = pipeline.query(
        query=query2,
        top_k=5,
        use_reranking=True,
        chat_history=chat_history
    )
    print(f"🤖 Assistant: {answer2['answer'][:200]}...")


def example_5_batch_processing():
    """Example 5: Batch processing multiple PDFs"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Batch Processing Multiple PDFs")
    print("="*80)
    
    pipeline = PDFRAGPipeline(index_name='batch_index')
    
    # List of PDFs to process (replace with actual paths)
    pdf_directory = "path/to/pdf/folder"
    
    if not os.path.exists(pdf_directory):
        print(f"⚠️  Directory not found: {pdf_directory}")
        print("Please update the pdf_directory variable with a valid path.")
        return
    
    import glob
    pdf_files = glob.glob(os.path.join(pdf_directory, "*.pdf"))
    
    if not pdf_files:
        print(f"⚠️  No PDF files found in {pdf_directory}")
        return
    
    print(f"\n📚 Found {len(pdf_files)} PDF files to process")
    
    total_chunks = 0
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {os.path.basename(pdf_path)}")
        try:
            result = pipeline.ingest_pdf(pdf_path)
            total_chunks += result['indexed']
            print(f"   ✅ Indexed {result['indexed']} chunks")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n✅ Batch processing complete!")
    print(f"   Total chunks indexed: {total_chunks}")


def example_6_custom_reranking():
    """Example 6: Comparing different reranking methods"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Comparing Reranking Methods")
    print("="*80)
    
    pipeline = PDFRAGPipeline(index_name='example_index')
    
    query = "What are the main findings?"
    
    # Without reranking
    print("\n1️⃣ Without reranking:")
    answer_no_rerank = pipeline.query(query, top_k=5, use_reranking=False)
    print(f"   Answer: {answer_no_rerank['answer'][:150]}...")
    
    # With API reranking
    print("\n2️⃣ With API reranking:")
    answer_api_rerank = pipeline.query(
        query, 
        top_k=10, 
        use_reranking=True, 
        rerank_method='api'
    )
    print(f"   Answer: {answer_api_rerank['answer'][:150]}...")
    
    # With cross-encoder reranking
    print("\n3️⃣ With Cross-Encoder reranking:")
    try:
        answer_ce_rerank = pipeline.query(
            query, 
            top_k=10, 
            use_reranking=True, 
            rerank_method='cross_encoder'
        )
        print(f"   Answer: {answer_ce_rerank['answer'][:150]}...")
    except Exception as e:
        print(f"   ⚠️ Cross-encoder not available: {e}")


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("PDF RAG SYSTEM - USAGE EXAMPLES")
    print("="*80)
    print("\nThis script demonstrates various features of the PDF RAG system.")
    print("Please update the PDF paths in the examples to use your own documents.")
    
    # Uncomment the examples you want to run
    
    # example_1_basic_ingestion_and_query()
    # example_2_rag_fusion()
    # example_3_query_decomposition()
    # example_4_multi_turn_conversation()
    # example_5_batch_processing()
    # example_6_custom_reranking()
    
    print("\n" + "="*80)
    print("To run an example, uncomment it in the main() function.")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

