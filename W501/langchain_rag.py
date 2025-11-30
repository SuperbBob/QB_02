"""
Simple LangChain-based RAG (Retrieval-Augmented Generation) Application
一个简单的基于 LangChain 的 RAG 问答应用

Features:
- PDF document loading and processing
- Text chunking with configurable parameters
- Vector store using FAISS (local, easy to install)
- Retrieval-augmented question answering
- Support for both OpenAI and local LLM (Ollama)
"""

import os
import pickle
from typing import List, Optional, Dict, Any
from pathlib import Path

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# For embeddings and LLM
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

from dotenv import load_dotenv

load_dotenv()


def format_docs(docs: List[Document]) -> str:
    """Format documents into a single string for context"""
    return "\n\n".join(doc.page_content for doc in docs)


class LangChainRAG:
    """
    A simple RAG application using LangChain
    简单的 LangChain RAG 应用
    """
    
    def __init__(
        self,
        persist_directory: str = "./faiss_db",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        use_ollama: bool = True,
        ollama_model: str = "llama3.2",
        embedding_model: str = "nomic-embed-text",
        openai_model: str = "gpt-3.5-turbo"
    ):
        """
        Initialize the RAG system
        
        Args:
            persist_directory: Directory to store the vector database
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            use_ollama: Whether to use Ollama (local) or OpenAI
            ollama_model: Ollama model name for LLM
            embedding_model: Model name for embeddings
            openai_model: OpenAI model name (if use_ollama=False)
        """
        self.persist_directory = persist_directory
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_ollama = use_ollama
        self._document_count = 0
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )
        
        # Initialize embeddings
        if use_ollama:
            self.embeddings = OllamaEmbeddings(
                model=embedding_model,
                base_url=os.getenv("OLLAMA_URL", "http://localhost:11434")
            )
            self.llm = OllamaLLM(
                model=ollama_model,
                base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
                temperature=0.7
            )
        else:
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_api_base=os.getenv("OPENAI_BASE_URL")
            )
            self.llm = ChatOpenAI(
                model=openai_model,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_api_base=os.getenv("OPENAI_BASE_URL"),
                temperature=0.7
            )
        
        # Vector store (will be initialized when documents are loaded)
        self.vectorstore: Optional[FAISS] = None
        self.rag_chain = None
        
        # Try to load existing vector store
        self._load_existing_vectorstore()
    
    def _load_existing_vectorstore(self):
        """Load existing vector store if available"""
        index_path = os.path.join(self.persist_directory, "index.faiss")
        if os.path.exists(index_path):
            try:
                self.vectorstore = FAISS.load_local(
                    self.persist_directory,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                # Load document count
                count_file = os.path.join(self.persist_directory, "doc_count.pkl")
                if os.path.exists(count_file):
                    with open(count_file, "rb") as f:
                        self._document_count = pickle.load(f)
                self._setup_rag_chain()
                print(f"✓ Loaded existing vector store from {self.persist_directory}")
            except Exception as e:
                print(f"⚠ Could not load existing vector store: {e}")
    
    def _save_vectorstore(self):
        """Save vector store to disk"""
        if self.vectorstore is not None:
            os.makedirs(self.persist_directory, exist_ok=True)
            self.vectorstore.save_local(self.persist_directory)
            # Save document count
            count_file = os.path.join(self.persist_directory, "doc_count.pkl")
            with open(count_file, "wb") as f:
                pickle.dump(self._document_count, f)
    
    def _setup_rag_chain(self):
        """Set up the RAG chain using LCEL (LangChain Expression Language)"""
        if self.vectorstore is None:
            return
        
        # Custom prompt template for better answers
        prompt = ChatPromptTemplate.from_template("""使用以下检索到的上下文来回答问题。如果你不知道答案，就说你不知道，不要试图编造答案。
请用中文回答，并尽可能详细和准确。

上下文信息:
{context}

问题: {question}

回答:""")
        
        # Create retriever
        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}  # Return top 4 relevant chunks
        )
        
        # Create RAG chain using LCEL
        self.rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        # Store retriever for later use
        self._retriever = retriever
    
    def load_pdf(self, pdf_path: str) -> List[Document]:
        """
        Load a PDF file and split into chunks
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of Document objects
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        print(f"📄 Loading PDF: {pdf_path}")
        
        # Load PDF using PyMuPDF
        loader = PyMuPDFLoader(pdf_path)
        documents = loader.load()
        
        print(f"   Loaded {len(documents)} pages")
        
        # Split into chunks
        chunks = self.text_splitter.split_documents(documents)
        print(f"   Split into {len(chunks)} chunks")
        
        return chunks
    
    def load_multiple_pdfs(self, pdf_paths: List[str]) -> List[Document]:
        """
        Load multiple PDF files
        
        Args:
            pdf_paths: List of PDF file paths
            
        Returns:
            List of all Document chunks
        """
        all_chunks = []
        for pdf_path in pdf_paths:
            try:
                chunks = self.load_pdf(pdf_path)
                all_chunks.extend(chunks)
            except Exception as e:
                print(f"⚠ Error loading {pdf_path}: {e}")
        
        return all_chunks
    
    def load_directory(self, directory: str) -> List[Document]:
        """
        Load all PDF files from a directory
        
        Args:
            directory: Path to directory containing PDFs
            
        Returns:
            List of all Document chunks
        """
        pdf_files = list(Path(directory).glob("*.pdf"))
        print(f"📁 Found {len(pdf_files)} PDF files in {directory}")
        
        return self.load_multiple_pdfs([str(f) for f in pdf_files])
    
    def add_documents(self, documents: List[Document]):
        """
        Add documents to the vector store
        
        Args:
            documents: List of Document objects to add
        """
        if not documents:
            print("⚠ No documents to add")
            return
        
        print(f"📥 Adding {len(documents)} documents to vector store...")
        
        if self.vectorstore is None:
            # Create new vector store
            self.vectorstore = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
        else:
            # Add to existing vector store
            self.vectorstore.add_documents(documents)
        
        self._document_count += len(documents)
        
        # Persist the vector store
        self._save_vectorstore()
        
        # Setup RAG chain
        self._setup_rag_chain()
        
        print(f"✓ Documents added and persisted to {self.persist_directory}")
    
    def ingest_pdf(self, pdf_path: str):
        """
        Convenience method to load and add a PDF in one step
        
        Args:
            pdf_path: Path to the PDF file
        """
        chunks = self.load_pdf(pdf_path)
        self.add_documents(chunks)
    
    def ingest_directory(self, directory: str):
        """
        Convenience method to load and add all PDFs from a directory
        
        Args:
            directory: Path to directory containing PDFs
        """
        chunks = self.load_directory(directory)
        self.add_documents(chunks)
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        Query the RAG system
        
        Args:
            question: The question to ask
            
        Returns:
            Dictionary with 'answer' and 'source_documents'
        """
        if self.rag_chain is None:
            return {
                "answer": "⚠ 请先加载文档。使用 ingest_pdf() 或 ingest_directory() 方法加载PDF文档。",
                "source_documents": []
            }
        
        print(f"🔍 Searching for: {question}")
        
        # Get the answer
        answer = self.rag_chain.invoke(question)
        
        # Get source documents separately
        source_docs = self._retriever.invoke(question)
        
        return {
            "answer": answer,
            "source_documents": source_docs
        }
    
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """
        Perform similarity search without LLM generation
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant Document objects
        """
        if self.vectorstore is None:
            print("⚠ No documents loaded")
            return []
        
        return self.vectorstore.similarity_search(query, k=k)
    
    def clear_database(self):
        """Clear the vector database"""
        import shutil
        if os.path.exists(self.persist_directory):
            shutil.rmtree(self.persist_directory)
            self.vectorstore = None
            self.rag_chain = None
            self._document_count = 0
            print(f"✓ Cleared database at {self.persist_directory}")
    
    def get_document_count(self) -> int:
        """Get the number of documents in the vector store"""
        return self._document_count


def create_rag(
    use_ollama: bool = True,
    ollama_model: str = "llama3.2",
    persist_directory: str = "./faiss_db"
) -> LangChainRAG:
    """
    Factory function to create a RAG instance
    
    Args:
        use_ollama: Whether to use Ollama (local) or OpenAI
        ollama_model: Ollama model name
        persist_directory: Where to store the vector database
        
    Returns:
        Configured LangChainRAG instance
    """
    return LangChainRAG(
        use_ollama=use_ollama,
        ollama_model=ollama_model,
        persist_directory=persist_directory
    )


# Quick usage example
if __name__ == "__main__":
    # Create RAG instance (using Ollama by default)
    rag = create_rag(use_ollama=True)
    
    print("\n" + "="*50)
    print("LangChain RAG System Initialized")
    print("="*50)
    print(f"Vector store: {rag.persist_directory}")
    print(f"Documents loaded: {rag.get_document_count()}")
    print("\nUsage:")
    print("  rag.ingest_pdf('path/to/file.pdf')  # Load a PDF")
    print("  rag.query('your question')           # Ask a question")
    print("="*50)
