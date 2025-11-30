#!/usr/bin/env python3
"""
LangChain RAG Demo - Interactive Question Answering
LangChain RAG 演示 - 交互式问答系统

This script provides an interactive interface for the LangChain RAG system.
"""

import os
import sys
from pathlib import Path


# ANSI Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'


def print_banner():
    """Print welcome banner"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          🤖 LangChain RAG 问答系统                           ║")
    print("║          Simple PDF Question Answering                       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(Colors.END)


def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def print_info(msg: str):
    print(f"{Colors.CYAN}ℹ {msg}{Colors.END}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


def check_ollama():
    """Check if Ollama is running"""
    import requests
    try:
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return True, [m["name"] for m in models]
        return False, []
    except:
        return False, []


def main():
    print_banner()
    
    # Check Ollama
    print_info("Checking Ollama connection...")
    ollama_ok, available_models = check_ollama()
    
    if not ollama_ok:
        print_warning("Ollama is not running. Please start Ollama first:")
        print(f"  {Colors.DIM}brew services start ollama{Colors.END}")
        print(f"  {Colors.DIM}or: ollama serve{Colors.END}")
        print_info("Will try to continue anyway...")
    else:
        print_success(f"Ollama connected. Available models: {', '.join(available_models[:5])}")
    
    # Import RAG module
    try:
        from langchain_rag import LangChainRAG, create_rag
        print_success("LangChain RAG module loaded")
    except ImportError as e:
        print_error(f"Failed to import RAG module: {e}")
        print_info("Install dependencies: pip install -r requirements.txt")
        sys.exit(1)
    
    # Initialize RAG
    print_info("Initializing RAG system...")
    try:
        rag = create_rag(
            use_ollama=True,
            ollama_model="llama3.2",
            persist_directory="./faiss_db"
        )
        doc_count = rag.get_document_count()
        print_success(f"RAG initialized. Documents in store: {doc_count}")
    except Exception as e:
        print_error(f"Failed to initialize RAG: {e}")
        sys.exit(1)
    
    # Main menu
    while True:
        print(f"\n{Colors.BOLD}{'─'*60}{Colors.END}")
        print(f"{Colors.BOLD}主菜单 / Main Menu:{Colors.END}")
        print("  1. 📄 加载 PDF 文档 (Load PDF)")
        print("  2. 📁 加载文件夹 (Load Directory)")
        print("  3. ❓ 提问 (Ask Question)")
        print("  4. 🔍 搜索相关内容 (Search)")
        print("  5. 📊 查看状态 (Status)")
        print("  6. 🗑️  清除数据库 (Clear Database)")
        print("  7. 👋 退出 (Exit)")
        print(f"{Colors.BOLD}{'─'*60}{Colors.END}")
        
        choice = input(f"\n{Colors.GREEN}请选择 (1-7): {Colors.END}").strip()
        
        if choice == "1":
            # Load single PDF
            pdf_path = input(f"\n{Colors.CYAN}请输入 PDF 文件路径: {Colors.END}").strip()
            if not pdf_path:
                print_warning("路径不能为空")
                continue
            
            if not os.path.exists(pdf_path):
                print_error(f"文件不存在: {pdf_path}")
                continue
            
            try:
                print_info("正在处理 PDF...")
                rag.ingest_pdf(pdf_path)
                print_success("PDF 加载完成!")
            except Exception as e:
                print_error(f"加载失败: {e}")
        
        elif choice == "2":
            # Load directory
            dir_path = input(f"\n{Colors.CYAN}请输入文件夹路径: {Colors.END}").strip()
            if not dir_path:
                print_warning("路径不能为空")
                continue
            
            if not os.path.isdir(dir_path):
                print_error(f"文件夹不存在: {dir_path}")
                continue
            
            try:
                print_info("正在处理文件夹中的 PDF 文件...")
                rag.ingest_directory(dir_path)
                print_success("文件夹加载完成!")
            except Exception as e:
                print_error(f"加载失败: {e}")
        
        elif choice == "3":
            # Ask question
            if rag.get_document_count() == 0:
                print_warning("请先加载文档!")
                continue
            
            print(f"\n{Colors.CYAN}进入问答模式 (输入 'exit' 返回菜单){Colors.END}")
            
            while True:
                question = input(f"\n{Colors.GREEN}问题: {Colors.END}").strip()
                
                if question.lower() in ['exit', 'quit', 'q', '退出']:
                    break
                
                if not question:
                    continue
                
                try:
                    result = rag.query(question)
                    
                    print(f"\n{Colors.BOLD}{Colors.CYAN}回答:{Colors.END}")
                    print(f"{result['answer']}")
                    
                    # Show sources
                    if result['source_documents']:
                        print(f"\n{Colors.DIM}📚 参考来源 ({len(result['source_documents'])} 个):{Colors.END}")
                        for i, doc in enumerate(result['source_documents'][:3], 1):
                            source = doc.metadata.get('source', 'Unknown')
                            page = doc.metadata.get('page', '?')
                            snippet = doc.page_content[:100].replace('\n', ' ')
                            print(f"  {Colors.DIM}[{i}] {Path(source).name}, p.{page}: {snippet}...{Colors.END}")
                
                except Exception as e:
                    print_error(f"查询失败: {e}")
        
        elif choice == "4":
            # Similarity search
            if rag.get_document_count() == 0:
                print_warning("请先加载文档!")
                continue
            
            query = input(f"\n{Colors.CYAN}搜索内容: {Colors.END}").strip()
            if not query:
                continue
            
            try:
                docs = rag.similarity_search(query, k=5)
                
                print(f"\n{Colors.BOLD}找到 {len(docs)} 个相关片段:{Colors.END}")
                for i, doc in enumerate(docs, 1):
                    source = doc.metadata.get('source', 'Unknown')
                    page = doc.metadata.get('page', '?')
                    print(f"\n{Colors.CYAN}[{i}] {Path(source).name}, 第 {page} 页{Colors.END}")
                    print(f"{Colors.DIM}{doc.page_content[:300]}...{Colors.END}")
            
            except Exception as e:
                print_error(f"搜索失败: {e}")
        
        elif choice == "5":
            # Show status
            print(f"\n{Colors.BOLD}系统状态:{Colors.END}")
            print(f"  向量数据库: {rag.persist_directory}")
            print(f"  文档数量: {rag.get_document_count()}")
            print(f"  使用 Ollama: {rag.use_ollama}")
            print(f"  Chunk 大小: {rag.chunk_size}")
            print(f"  Chunk 重叠: {rag.chunk_overlap}")
        
        elif choice == "6":
            # Clear database
            confirm = input(f"\n{Colors.YELLOW}确定要清除所有数据吗? (yes/no): {Colors.END}").strip()
            if confirm.lower() == 'yes':
                rag.clear_database()
                print_success("数据库已清除")
            else:
                print_info("取消操作")
        
        elif choice == "7":
            print(f"\n{Colors.BOLD}👋 再见! Goodbye!{Colors.END}\n")
            break
        
        else:
            print_warning("无效选项,请输入 1-7")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.BOLD}👋 Interrupted. Goodbye!{Colors.END}\n")
        sys.exit(0)

