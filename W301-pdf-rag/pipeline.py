"""
Main RAG pipeline orchestrator
Coordinates the entire PDF RAG workflow
"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from config import RAGConfig
from pdf_processor import process_pdf
from chunking import prepare_all_chunks
from embedding import batch_embed
from es_index import create_index, bulk_index_documents, get_index_stats
from retrieval import hybrid_search
from reranking import rerank_documents
from query_enhancement import rag_fusion, query_decomposition, coreference_resolution
from answer_generation import generate_answer, generate_multi_query_answer, generate_decomposed_answer


class PDFRAGPipeline:
    """Complete PDF RAG pipeline"""
    
    def __init__(self, index_name: str, use_openai_embedding: bool = False):
        """
        Initialize RAG pipeline
        
        Args:
            index_name: Name of Elasticsearch index
            use_openai_embedding: Whether to use OpenAI embeddings
        """
        self.index_name = index_name
        self.use_openai_embedding = use_openai_embedding
    
    def ingest_pdf(self, pdf_path: str, file_name: str = None, 
                   process_images: bool = None, process_tables: bool = None) -> Dict[str, Any]:
        """
        Ingest a PDF document into the RAG system
        
        Args:
            pdf_path: Path to PDF file
            file_name: Optional custom file name
            process_images: Whether to extract images (defaults to RAGConfig.PROCESS_IMAGES)
                          Set to True for documents with important diagrams/figures
            process_tables: Whether to extract tables (defaults to RAGConfig.PROCESS_TABLES)
                          Set to True for documents with important structured data
            
        Returns:
            Dictionary with ingestion statistics
            
        Note:
            By default, images and tables are skipped for faster processing.
            Enable them for comprehensive document understanding (5-10x slower).
        """
        print(f"\n{'='*60}")
        print(f"Starting PDF ingestion: {pdf_path}")
        print(f"{'='*60}\n")
        
        if file_name is None:
            file_name = Path(pdf_path).name
        
        # Step 1: Extract content from PDF
        print("Step 1: Extracting content from PDF...")
        text_pages, images, tables = process_pdf(pdf_path, process_images, process_tables)
        
        # Step 2: Chunk and prepare content
        print("\nStep 2: Chunking and preparing content...")
        chunks = prepare_all_chunks(text_pages, images, tables)
        
        if not chunks:
            return {
                'success': False,
                'message': 'No content extracted from PDF',
                'chunks': 0
            }
        
        # Step 3: Generate embeddings
        print("\nStep 3: Generating embeddings...")
        texts = [chunk['text'] for chunk in chunks]
        embeddings = batch_embed(texts, batch_size=25, use_openai=self.use_openai_embedding)
        
        # Step 4: Prepare documents for indexing
        print("\nStep 4: Preparing documents for indexing...")
        documents = []
        for chunk, embedding in zip(chunks, embeddings):
            doc = {
                'text': chunk['text'],
                'vector': embedding,
                'doc_type': chunk.get('doc_type', 'text'),
                'page_num': chunk.get('page_num', 0),
                'file_name': file_name,
                'file_path': pdf_path,
                'metadata': chunk
            }
            documents.append(doc)
        
        # Step 5: Create index if not exists
        print("\nStep 5: Creating Elasticsearch index...")
        create_index(self.index_name)
        
        # Step 6: Index documents
        print("\nStep 6: Indexing documents...")
        success_count = bulk_index_documents(self.index_name, documents)
        
        # Get final statistics
        stats = get_index_stats(self.index_name)
        
        print(f"\n{'='*60}")
        print("PDF Ingestion Complete!")
        print(f"{'='*60}")
        print(f"File: {file_name}")
        print(f"Chunks indexed: {success_count}/{len(chunks)}")
        print(f"Total documents in index: {stats.get('document_count', 'N/A')}")
        print(f"{'='*60}\n")
        
        return {
            'success': True,
            'file_name': file_name,
            'chunks': len(chunks),
            'text_chunks': len([c for c in chunks if c.get('doc_type') == 'text']),
            'image_chunks': len([c for c in chunks if c.get('doc_type') == 'image']),
            'table_chunks': len([c for c in chunks if c.get('doc_type') == 'table']),
            'indexed': success_count,
            'index_stats': stats
        }
    
    def query(self, query: str, 
             top_k: int = None,
             use_reranking: bool = True,
             rerank_method: str = 'api',
             use_rag_fusion: bool = False,
             use_query_decomposition: bool = False,
             chat_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Query the RAG system
        
        Args:
            query: User query
            top_k: Number of documents to retrieve
            use_reranking: Whether to apply reranking
            rerank_method: Reranking method ('api' or 'cross_encoder')
            use_rag_fusion: Whether to use RAG Fusion
            use_query_decomposition: Whether to use Query Decomposition
            chat_history: Chat history for coreference resolution
            
        Returns:
            Dictionary with answer and metadata
        """
        print(f"\n{'='*60}")
        print(f"Processing query: {query}")
        print(f"{'='*60}\n")
        
        if top_k is None:
            top_k = RAGConfig.TOP_K_RETRIEVAL
        
        # Step 1: Coreference resolution if chat history provided
        if chat_history:
            print("Step 1: Resolving coreferences...")
            query = coreference_resolution(query, chat_history)
            print(f"Resolved query: {query}\n")
        
        # Step 2: Query enhancement
        if use_query_decomposition:
            print("Step 2: Decomposing query...")
            sub_queries = query_decomposition(query)
            
            if sub_queries:
                print(f"Query decomposed into {len(sub_queries)} sub-queries:")
                for i, sq in enumerate(sub_queries):
                    print(f"  {i+1}. {sq}")
                
                # Process each sub-query
                sub_answers = []
                for sq in sub_queries:
                    print(f"\nProcessing sub-query: {sq}")
                    sub_result = self._single_query(sq, top_k, use_reranking, rerank_method)
                    sub_answers.append(sub_result)
                
                # Generate final answer
                print("\nGenerating final answer from sub-queries...")
                final_result = generate_decomposed_answer(query, sub_answers, sub_queries)
                
                print(f"\n{'='*60}")
                print("Query Processing Complete!")
                print(f"{'='*60}\n")
                
                return final_result
            else:
                print("No decomposition needed, proceeding with single query\n")
        
        if use_rag_fusion:
            print("Step 2: Generating query variations (RAG Fusion)...")
            queries = rag_fusion(query, num_variations=2)
            print(f"Generated {len(queries)} query variations:")
            for i, q in enumerate(queries):
                print(f"  {i+1}. {q}")
            
            # Retrieve documents for each query
            all_documents = []
            for q in queries:
                print(f"\nProcessing query: {q}")
                docs = hybrid_search(q, self.index_name, top_k, self.use_openai_embedding)
                all_documents.append(docs)
            
            # Apply reranking if requested
            if use_reranking:
                print("\nStep 3: Reranking documents...")
                # Combine all documents
                combined = []
                for docs in all_documents:
                    combined.extend(docs)
                # Deduplicate
                seen = set()
                unique_docs = []
                for doc in combined:
                    if doc['id'] not in seen:
                        seen.add(doc['id'])
                        unique_docs.append(doc)
                
                reranked = rerank_documents(query, unique_docs, method=rerank_method, 
                                          top_k=RAGConfig.TOP_K_RERANK)
                final_docs = reranked
            else:
                # Use combined documents without reranking
                combined = []
                for docs in all_documents:
                    combined.extend(docs)
                seen = set()
                unique_docs = []
                for doc in combined:
                    if doc['id'] not in seen:
                        seen.add(doc['id'])
                        unique_docs.append(doc)
                final_docs = unique_docs[:top_k]
            
            print(f"\nStep 4: Generating answer from {len(final_docs)} documents...")
            result = generate_answer(query, final_docs)
            
        else:
            # Standard single query processing
            result = self._single_query(query, top_k, use_reranking, rerank_method)
        
        print(f"\n{'='*60}")
        print("Query Processing Complete!")
        print(f"{'='*60}\n")
        
        return result
    
    def _single_query(self, query: str, top_k: int, use_reranking: bool, rerank_method: str) -> Dict[str, Any]:
        """Process a single query"""
        # Retrieve documents
        print(f"Step 2: Performing hybrid search...")
        documents = hybrid_search(query, self.index_name, top_k, self.use_openai_embedding)
        print(f"Retrieved {len(documents)} documents\n")
        
        # Rerank if requested
        if use_reranking and documents:
            print(f"Step 3: Reranking documents...")
            documents = rerank_documents(query, documents, method=rerank_method, 
                                        top_k=RAGConfig.TOP_K_RERANK)
            print(f"Reranked to top {len(documents)} documents\n")
        
        # Generate answer
        print(f"Step 4: Generating answer...")
        result = generate_answer(query, documents)
        
        return result


def main():
    """Example usage of the RAG pipeline"""
    # Initialize pipeline
    pipeline = PDFRAGPipeline(index_name='pdf_rag_demo')
    
    # Example 1: Ingest a PDF
    pdf_path = "/Users/peixingao/Documents/RAG Demo/test_pdf/image_extraction_example.pdf"
    
    if os.path.exists(pdf_path):
        print("Example 1: Ingesting PDF")
        result = pipeline.ingest_pdf(pdf_path)
        print(f"Ingestion result: {result}")
    
    # Example 2: Query the system
    print("\n\nExample 2: Querying the system")
    query = "这个文档主要讲了什么？"
    
    result = pipeline.query(
        query,
        top_k=5,
        use_reranking=True,
        rerank_method='api',
        use_rag_fusion=False,
        use_query_decomposition=False
    )
    
    print(f"\nQuery: {query}")
    print(f"\nAnswer:\n{result['answer']}")
    print(f"\nCitations ({len(result['citations'])}):")
    for cite in result['citations']:
        print(f"  [{cite['citation_number']}] {cite['doc_type']} - Page {cite['page_num']}")


if __name__ == "__main__":
    main()

