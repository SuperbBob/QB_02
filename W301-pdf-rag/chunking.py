"""
Text chunking module
Splits text content into retrievable chunks
"""
import tiktoken
from typing import List, Dict, Any
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import RAGConfig


def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """
    Count the number of tokens in a string
    
    Args:
        string: Text to count tokens for
        encoding_name: Tokenizer encoding name
        
    Returns:
        Number of tokens
    """
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def chunk_text(text: str, chunk_size: int = None, chunk_overlap: int = None) -> List[str]:
    """
    Split text into chunks using recursive character splitting
    
    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk (in tokens)
        chunk_overlap: Overlap between chunks (in tokens)
        
    Returns:
        List of text chunks
    """
    if chunk_size is None:
        chunk_size = RAGConfig.CHUNK_SIZE
    if chunk_overlap is None:
        chunk_overlap = RAGConfig.CHUNK_OVERLAP
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=num_tokens_from_string,
        separators=["\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", " ", ""]
    )
    
    chunks = text_splitter.split_text(text)
    return chunks


def chunk_page_content(page_data: Dict[str, Any], chunk_size: int = None, chunk_overlap: int = None) -> List[Dict[str, Any]]:
    """
    Chunk a single page's text content
    
    Args:
        page_data: Dictionary with 'text' and 'page_num'
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of chunk dictionaries
    """
    text = page_data.get('text', '')
    page_num = page_data.get('page_num', 0)
    
    chunks = chunk_text(text, chunk_size, chunk_overlap)
    
    result = []
    for i, chunk in enumerate(chunks):
        result.append({
            'text': chunk,
            'page_num': page_num,
            'chunk_index': i,
            'doc_type': 'text'
        })
    
    return result


def chunk_all_pages(pages: List[Dict[str, Any]], chunk_size: int = None, chunk_overlap: int = None) -> List[Dict[str, Any]]:
    """
    Chunk text from all pages
    
    Args:
        pages: List of page dictionaries
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of all chunks
    """
    all_chunks = []
    
    for page in pages:
        chunks = chunk_page_content(page, chunk_size, chunk_overlap)
        all_chunks.extend(chunks)
    
    return all_chunks


def prepare_image_chunks(images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prepare image data for indexing
    
    Args:
        images: List of image dictionaries with summaries
        
    Returns:
        List of prepared image chunks
    """
    result = []
    
    for img in images:
        # Use context-augmented summary as the searchable text
        text = img.get('context_augmented_summary', img.get('summary', ''))
        if not text:
            continue
            
        result.append({
            'text': text,
            'page_num': img.get('page_num', 0),
            'doc_type': 'image',
            'original_summary': img.get('summary', ''),
            'image_path': img.get('image_path', '')
        })
    
    return result


def prepare_table_chunks(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prepare table data for indexing
    
    Args:
        tables: List of table dictionaries with summaries
        
    Returns:
        List of prepared table chunks
    """
    result = []
    
    for table in tables:
        # Use context-augmented summary as the searchable text
        text = table.get('context_augmented_table', '')
        if not text:
            continue
            
        result.append({
            'text': text,
            'page_num': table.get('page_num', 0),
            'doc_type': 'table',
            'table_index': table.get('table_index', 0),
            'table_markdown': table.get('table_markdown', '')
        })
    
    return result


def prepare_all_chunks(text_pages: List[Dict], images: List[Dict], tables: List[Dict]) -> List[Dict[str, Any]]:
    """
    Prepare all content types for indexing
    
    Args:
        text_pages: List of text page dictionaries
        images: List of image dictionaries
        tables: List of table dictionaries
        
    Returns:
        Combined list of all chunks ready for indexing
    """
    # Chunk text content
    text_chunks = chunk_all_pages(text_pages)
    
    # Prepare image chunks
    image_chunks = prepare_image_chunks(images)
    
    # Prepare table chunks
    table_chunks = prepare_table_chunks(tables)
    
    # Combine all chunks
    all_chunks = text_chunks + image_chunks + table_chunks
    
    print(f"Prepared {len(text_chunks)} text chunks, {len(image_chunks)} image chunks, "
          f"{len(table_chunks)} table chunks (total: {len(all_chunks)})")
    
    return all_chunks


if __name__ == "__main__":
    # Test chunking
    sample_text = """This is a long document that needs to be split into smaller chunks for better retrieval.
    Each chunk should be of reasonable size and have some overlap with adjacent chunks.
    This helps maintain context when retrieving information.""" * 50
    
    chunks = chunk_text(sample_text, chunk_size=200, chunk_overlap=50)
    print(f"Split text into {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i+1} ({num_tokens_from_string(chunk)} tokens):")
        print(chunk[:100] + "...")

