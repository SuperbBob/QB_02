#!/usr/bin/env python3
"""
PDF RAG System - Main Application
Interactive interface for the complete PDF RAG system
"""
import os
import sys
import glob
from typing import List, Dict
from pathlib import Path

# Color codes for better UX
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header(text: str):
    """Print a styled header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ {text}{Colors.END}")

class PDFRAGApp:
    """Main PDF RAG Application"""
    
    def __init__(self):
        self.pipeline = None
        self.current_index = None
        self.chat_history = []
        
    def check_dependencies(self) -> bool:
        """Check if all dependencies are available"""
        try:
            from pipeline import PDFRAGPipeline
            from config import get_es
            print_success("All dependencies loaded")
            return True
        except ImportError as e:
            print_error(f"Missing dependencies: {e}")
            print_info("Run: pip install -r requirements.txt")
            return False
    
    def check_elasticsearch(self) -> bool:
        """Check Elasticsearch connection"""
        try:
            from config import get_es
            es = get_es()
            info = es.info()
            print_success(f"Connected to Elasticsearch {info['version']['number']}")
            return True
        except Exception as e:
            print_error(f"Cannot connect to Elasticsearch: {e}")
            print_info("Make sure Elasticsearch is running")
            return False
    
    def check_llm(self) -> bool:
        """Check LLM configuration"""
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        base_url = os.getenv('OPENAI_BASE_URL')
        model = os.getenv('LLM_MODEL')
        
        if not api_key or api_key == 'your-openai-api-key-here':
            print_warning("OpenAI API key not configured")
            print_info("Using local LLM or configure API key in .env")
        else:
            print_success(f"LLM configured: {model}")
        
        return True
    
    def startup_check(self) -> bool:
        """Run all startup checks"""
        print_header("SYSTEM STARTUP CHECK")
        
        checks = [
            ("Dependencies", self.check_dependencies),
            ("Elasticsearch", self.check_elasticsearch),
            ("LLM Configuration", self.check_llm)
        ]
        
        all_passed = True
        for name, check_func in checks:
            print(f"\nChecking {name}...", end=" ")
            try:
                if check_func():
                    print_success("OK")
                else:
                    print_error("FAILED")
                    all_passed = False
            except Exception as e:
                print_error(f"ERROR: {e}")
                all_passed = False
        
        return all_passed
    
    def list_indices(self) -> List[str]:
        """List available Elasticsearch indices"""
        try:
            from config import get_es
            es = get_es()
            indices = es.indices.get_alias(index="*")
            return list(indices.keys())
        except:
            return []
    
    def select_index(self):
        """Select or create an index"""
        print_header("INDEX SELECTION")
        
        indices = self.list_indices()
        
        if indices:
            print("Available indices:")
            for i, idx in enumerate(indices, 1):
                print(f"  {i}. {idx}")
            print(f"  {len(indices) + 1}. Create new index")
        else:
            print_info("No existing indices found")
            print("Will create a new index")
        
        choice = input("\nSelect option or enter new index name: ").strip()
        
        if choice.isdigit() and indices:
            idx = int(choice) - 1
            if 0 <= idx < len(indices):
                self.current_index = indices[idx]
                print_success(f"Selected index: {self.current_index}")
            else:
                # Create new
                index_name = input("Enter new index name: ").strip()
                self.current_index = index_name
        else:
            self.current_index = choice if choice else "pdf_rag_default"
        
        # Initialize pipeline
        from pipeline import PDFRAGPipeline
        self.pipeline = PDFRAGPipeline(index_name=self.current_index)
        print_success(f"Pipeline initialized with index: {self.current_index}")
    
    def ingest_pdf_menu(self):
        """PDF ingestion menu"""
        print_header("PDF INGESTION")
        
        print("Options:")
        print("  1. Ingest single PDF")
        print("  2. Ingest all PDFs from folder")
        print("  3. Ingest from RAG Demo test PDFs")
        print("  4. Back to main menu")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            self.ingest_single_pdf()
        elif choice == '2':
            self.ingest_folder()
        elif choice == '3':
            self.ingest_demo_pdfs()
        elif choice == '4':
            return
        else:
            print_error("Invalid option")
    
    def ingest_single_pdf(self):
        """Ingest a single PDF file"""
        pdf_path = input("\nEnter PDF file path: ").strip()
        
        if not os.path.exists(pdf_path):
            print_error(f"File not found: {pdf_path}")
            return
        
        if not pdf_path.lower().endswith('.pdf'):
            print_error("File must be a PDF")
            return
        
        # Ask about processing options
        print("\n" + Colors.BOLD + "Processing Options:" + Colors.END)
        print("  Images and tables are skipped by default for faster processing (1-3 min)")
        print("  Enable them for comprehensive extraction (10-30 min, requires LLM)")
        
        process_images = input("\nProcess images? (y/N): ").strip().lower() == 'y'
        process_tables = input("Process tables? (y/N): ").strip().lower() == 'y'
        
        print_info(f"Processing: {os.path.basename(pdf_path)}")
        if process_images or process_tables:
            print_warning("This may take 10-30 minutes with images/tables enabled...")
        else:
            print_warning("This may take 1-3 minutes (text only)...")
        
        try:
            result = self.pipeline.ingest_pdf(pdf_path, 
                                             process_images=process_images,
                                             process_tables=process_tables)
            
            print_success("PDF processed successfully!")
            print(f"\n  File: {result['file_name']}")
            print(f"  Total chunks: {result['chunks']}")
            print(f"    - Text: {result['text_chunks']}")
            print(f"    - Images: {result['image_chunks']}")
            print(f"    - Tables: {result['table_chunks']}")
            print(f"  Indexed: {result['indexed']}")
            
        except Exception as e:
            print_error(f"Failed to process PDF: {e}")
    
    def ingest_folder(self):
        """Ingest all PDFs from a folder"""
        folder_path = input("\nEnter folder path: ").strip()
        
        if not os.path.exists(folder_path):
            print_error(f"Folder not found: {folder_path}")
            return
        
        pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
        
        if not pdf_files:
            print_error("No PDF files found in folder")
            return
        
        print_info(f"Found {len(pdf_files)} PDF files")
        
        # Ask about processing options
        print("\n" + Colors.BOLD + "Processing Options:" + Colors.END)
        print("  Default: Text only (fast, 1-3 min per PDF)")
        print("  With images/tables: Comprehensive (slow, 10-30 min per PDF)")
        
        process_images = input("\nProcess images? (y/N): ").strip().lower() == 'y'
        process_tables = input("Process tables? (y/N): ").strip().lower() == 'y'
        
        confirm = input(f"\nProcess all {len(pdf_files)} files? (y/n): ").strip().lower()
        
        if confirm != 'y':
            return
        
        success_count = 0
        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] Processing: {os.path.basename(pdf_path)}")
            try:
                result = self.pipeline.ingest_pdf(pdf_path,
                                                  process_images=process_images,
                                                  process_tables=process_tables)
                print_success(f"Indexed {result['indexed']} chunks")
                success_count += 1
            except Exception as e:
                print_error(f"Failed: {e}")
        
        print(f"\n{Colors.BOLD}Summary:{Colors.END}")
        print(f"  Successfully processed: {success_count}/{len(pdf_files)}")
    
    def ingest_demo_pdfs(self):
        """Ingest PDFs from RAG Demo folder"""
        demo_path = "/Users/peixingao/Documents/RAG Demo/test_pdf"
        
        if not os.path.exists(demo_path):
            print_error("RAG Demo folder not found")
            return
        
        pdf_files = glob.glob(os.path.join(demo_path, "*.pdf"))
        
        if not pdf_files:
            print_error("No demo PDFs found")
            return
        
        print("Available demo PDFs:")
        for i, pdf_path in enumerate(pdf_files, 1):
            size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            print(f"  {i}. {os.path.basename(pdf_path)} ({size_mb:.1f} MB)")
        
        choice = input("\nSelect PDF number (or 'all'): ").strip()
        
        if choice.lower() == 'all':
            files_to_process = pdf_files
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(pdf_files):
                files_to_process = [pdf_files[idx]]
            else:
                print_error("Invalid selection")
                return
        else:
            print_error("Invalid input")
            return
        
        # Ask about processing options
        print("\n" + Colors.BOLD + "Processing Options:" + Colors.END)
        print("  Default: Text only (fast)")
        process_images = input("Process images? (y/N): ").strip().lower() == 'y'
        process_tables = input("Process tables? (y/N): ").strip().lower() == 'y'
        
        for i, pdf_path in enumerate(files_to_process, 1):
            print(f"\n[{i}/{len(files_to_process)}] Processing: {os.path.basename(pdf_path)}")
            try:
                result = self.pipeline.ingest_pdf(pdf_path,
                                                  process_images=process_images,
                                                  process_tables=process_tables)
                print_success(f"Indexed {result['indexed']} chunks")
            except Exception as e:
                print_error(f"Failed: {e}")
    
    def query_menu(self):
        """Query interface"""
        print_header("QUERY SYSTEM")
        
        if not self.current_index:
            print_error("No index selected. Please select/create an index first.")
            return
        
        print(f"Current index: {Colors.BOLD}{self.current_index}{Colors.END}")
        print("\nQuery modes:")
        print("  1. Simple query")
        print("  2. Query with RAG Fusion")
        print("  3. Query with Query Decomposition")
        print("  4. Multi-turn conversation")
        print("  5. Back to main menu")
        
        choice = input("\nSelect mode (1-5): ").strip()
        
        if choice == '1':
            self.simple_query()
        elif choice == '2':
            self.rag_fusion_query()
        elif choice == '3':
            self.decomposition_query()
        elif choice == '4':
            self.conversation_mode()
        elif choice == '5':
            return
        else:
            print_error("Invalid option")
    
    def simple_query(self):
        """Execute a simple query"""
        query = input("\nEnter your question: ").strip()
        
        if not query:
            print_error("Query cannot be empty")
            return
        
        print_info("Searching...")
        
        try:
            answer = self.pipeline.query(
                query,
                top_k=5,
                use_reranking=True
            )
            
            self.display_answer(answer)
            
        except Exception as e:
            print_error(f"Query failed: {e}")
    
    def rag_fusion_query(self):
        """Execute query with RAG Fusion"""
        query = input("\nEnter your question: ").strip()
        
        if not query:
            return
        
        print_info("Using RAG Fusion (generating multiple query variations)...")
        
        try:
            answer = self.pipeline.query(
                query,
                top_k=10,
                use_rag_fusion=True,
                use_reranking=True
            )
            
            self.display_answer(answer)
            
        except Exception as e:
            print_error(f"Query failed: {e}")
    
    def decomposition_query(self):
        """Execute query with Query Decomposition"""
        query = input("\nEnter your complex question: ").strip()
        
        if not query:
            return
        
        print_info("Using Query Decomposition (breaking into sub-queries)...")
        
        try:
            answer = self.pipeline.query(
                query,
                use_query_decomposition=True,
                use_reranking=True
            )
            
            self.display_answer(answer)
            
            if 'sub_queries' in answer:
                print(f"\n{Colors.BOLD}Sub-queries used:{Colors.END}")
                for i, sq in enumerate(answer['sub_queries'], 1):
                    print(f"  {i}. {sq}")
            
        except Exception as e:
            print_error(f"Query failed: {e}")
    
    def conversation_mode(self):
        """Interactive conversation mode"""
        print_header("CONVERSATION MODE")
        print("Type 'exit' to return to main menu")
        print("Type 'clear' to clear conversation history\n")
        
        while True:
            query = input(f"{Colors.GREEN}You:{Colors.END} ").strip()
            
            if query.lower() == 'exit':
                break
            elif query.lower() == 'clear':
                self.chat_history = []
                print_info("Conversation history cleared")
                continue
            elif not query:
                continue
            
            try:
                answer = self.pipeline.query(
                    query,
                    top_k=5,
                    use_reranking=True,
                    chat_history=self.chat_history
                )
                
                print(f"\n{Colors.CYAN}Assistant:{Colors.END} {answer['answer']}\n")
                
                # Update history
                self.chat_history.append({"role": "user", "content": query})
                self.chat_history.append({"role": "assistant", "content": answer['answer']})
                
                # Keep history manageable (last 6 exchanges)
                if len(self.chat_history) > 12:
                    self.chat_history = self.chat_history[-12:]
                
            except Exception as e:
                print_error(f"Query failed: {e}")
    
    def display_answer(self, answer: Dict):
        """Display query answer with formatting"""
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}ANSWER:{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"\n{answer['answer']}\n")
        
        if answer.get('citations'):
            print(f"{Colors.BOLD}Sources ({len(answer['citations'])}):{Colors.END}")
            for cite in answer['citations']:
                doc_type = cite['doc_type'].upper()
                print(f"  [{cite['citation_number']}] {doc_type} - Page {cite['page_num']}")
                # Show snippet
                snippet = cite['text'][:100] + "..." if len(cite['text']) > 100 else cite['text']
                print(f"      {Colors.CYAN}{snippet}{Colors.END}")
        
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    def settings_menu(self):
        """Settings and configuration"""
        print_header("SETTINGS")
        
        from dotenv import load_dotenv
        load_dotenv()
        
        print("Current configuration:")
        print(f"  Index: {self.current_index or 'Not selected'}")
        print(f"  LLM Model: {os.getenv('LLM_MODEL', 'Not set')}")
        print(f"  Base URL: {os.getenv('OPENAI_BASE_URL', 'Not set')}")
        
        try:
            from config import RAGConfig
            print(f"\nRetrieval settings:")
            print(f"  TOP_K_RETRIEVAL: {RAGConfig.TOP_K_RETRIEVAL}")
            print(f"  TOP_K_RERANK: {RAGConfig.TOP_K_RERANK}")
            print(f"  CHUNK_SIZE: {RAGConfig.CHUNK_SIZE}")
        except:
            pass
        
        print("\nOptions:")
        print("  1. View index statistics")
        print("  2. Optimize for speed")
        print("  3. Back to main menu")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == '1':
            self.show_index_stats()
        elif choice == '2':
            self.optimize_settings()
    
    def show_index_stats(self):
        """Show index statistics"""
        if not self.current_index:
            print_error("No index selected")
            return
        
        try:
            from es_index import get_index_stats
            stats = get_index_stats(self.current_index)
            
            print(f"\n{Colors.BOLD}Index Statistics:{Colors.END}")
            print(f"  Name: {stats.get('index_name', 'N/A')}")
            print(f"  Documents: {stats.get('document_count', 'N/A')}")
            size_mb = stats.get('size_in_bytes', 0) / (1024 * 1024)
            print(f"  Size: {size_mb:.2f} MB")
            
        except Exception as e:
            print_error(f"Could not get stats: {e}")
    
    def optimize_settings(self):
        """Run optimization script"""
        print_info("Running optimization tool...")
        import subprocess
        subprocess.run(['python3', 'quick_optimize.py'])
    
    def main_menu(self):
        """Main application menu"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}")
        print("╔" + "="*68 + "╗")
        print("║" + " "*18 + "PDF RAG SYSTEM" + " "*36 + "║")
        print("╚" + "="*68 + "╝")
        print(Colors.END)
        
        if self.current_index:
            print(f"Current index: {Colors.BOLD}{self.current_index}{Colors.END}")
        else:
            print_warning("No index selected")
        
        print("\nMain Menu:")
        print("  1. Select/Create Index")
        print("  2. Ingest PDF Documents")
        print("  3. Query System")
        print("  4. Settings & Optimization")
        print("  5. Exit")
        
        return input("\nSelect option (1-5): ").strip()
    
    def run(self):
        """Main application loop"""
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("╔" + "="*68 + "╗")
        print("║" + " "*10 + "Welcome to PDF RAG System!" + " "*32 + "║")
        print("╚" + "="*68 + "╝")
        print(Colors.END)
        
        # Startup checks
        if not self.startup_check():
            print_error("\nStartup checks failed. Please fix issues before continuing.")
            sys.exit(1)
        
        print_success("\nAll systems ready!")
        
        # Main loop
        while True:
            choice = self.main_menu()
            
            if choice == '1':
                self.select_index()
            elif choice == '2':
                if not self.current_index:
                    print_error("Please select an index first (Option 1)")
                else:
                    self.ingest_pdf_menu()
            elif choice == '3':
                if not self.current_index:
                    print_error("Please select an index first (Option 1)")
                else:
                    self.query_menu()
            elif choice == '4':
                self.settings_menu()
            elif choice == '5':
                print(f"\n{Colors.BOLD}👋 Thank you for using PDF RAG System!{Colors.END}\n")
                break
            else:
                print_error("Invalid option. Please select 1-5.")

def main():
    """Entry point"""
    try:
        app = PDFRAGApp()
        app.run()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.BOLD}👋 Interrupted. Goodbye!{Colors.END}\n")
        sys.exit(0)
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

