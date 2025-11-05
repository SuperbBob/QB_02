"""
Embedding generation module
Supports multiple embedding backends
"""
import requests
import time
from config import ModelConfig
from typing import List


def local_embedding(inputs: List[str]) -> List[List[float]]:
    """
    Get embeddings from a local/custom embedding service
    
    Args:
        inputs: List of text strings to embed
        
    Returns:
        List of embedding vectors
    """
    headers = {"Content-Type": "application/json"}
    data = {"texts": inputs}
    
    retry = 0
    max_retries = 3
    
    while retry < max_retries:
        try:
            response = requests.post(
                ModelConfig.EMBEDDING_URL, 
                headers=headers, 
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result['data']['text_vectors']
        except Exception as e:
            retry += 1
            if retry < max_retries:
                print(f"Embedding request failed (attempt {retry}/{max_retries}): {e}")
                time.sleep(1)
            else:
                raise Exception(f"Failed to get embeddings after {max_retries} attempts: {e}")


def ollama_embedding(inputs: List[str], model: str = "nomic-embed-text") -> List[List[float]]:
    """
    Get embeddings from Ollama (local, free)
    
    Args:
        inputs: List of text strings to embed
        model: Ollama embedding model name
        
    Returns:
        List of embedding vectors
    """
    import os
    ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    all_embeddings = []
    
    for text in inputs:
        retry = 0
        max_retries = 3
        
        while retry < max_retries:
            try:
                response = requests.post(
                    f'{ollama_url}/api/embeddings',
                    json={"model": model, "prompt": text},
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
                all_embeddings.append(result['embedding'])
                break
            except Exception as e:
                retry += 1
                if retry < max_retries:
                    print(f"Ollama embedding failed (attempt {retry}/{max_retries}): {e}")
                    time.sleep(1)
                else:
                    raise Exception(f"Failed to get Ollama embeddings after {max_retries} attempts: {e}")
    
    return all_embeddings


def openai_embedding(inputs: List[str], model: str = "text-embedding-3-large") -> List[List[float]]:
    """
    Get embeddings from OpenAI API
    
    Args:
        inputs: List of text strings to embed
        model: OpenAI embedding model name
        
    Returns:
        List of embedding vectors
    """
    from openai import OpenAI
    
    client = OpenAI(
        api_key=ModelConfig.OPENAI_API_KEY,
        base_url=ModelConfig.OPENAI_BASE_URL
    )
    
    retry = 0
    max_retries = 3
    
    while retry < max_retries:
        try:
            response = client.embeddings.create(
                input=inputs,
                model=model
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            retry += 1
            if retry < max_retries:
                print(f"OpenAI embedding request failed (attempt {retry}/{max_retries}): {e}")
                time.sleep(1)
            else:
                raise Exception(f"Failed to get OpenAI embeddings after {max_retries} attempts: {e}")


def batch_embed(texts: List[str], batch_size: int = 25, use_openai: bool = False, use_ollama: bool = None) -> List[List[float]]:
    """
    Embed texts in batches for efficiency
    
    Args:
        texts: List of texts to embed
        batch_size: Number of texts to embed in each batch
        use_openai: Whether to use OpenAI embeddings
        use_ollama: Whether to use Ollama embeddings (auto-detected if None)
        
    Returns:
        List of embedding vectors
    """
    import os
    
    # Auto-detect Ollama if not specified
    if use_ollama is None:
        use_ollama = os.getenv('USE_OLLAMA_EMBEDDINGS', 'false').lower() == 'true'
    
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"Embedding batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
        
        if use_ollama:
            embeddings = ollama_embedding(batch)
        elif use_openai:
            embeddings = openai_embedding(batch)
        else:
            embeddings = local_embedding(batch)
            
        all_embeddings.extend(embeddings)
    
    return all_embeddings


if __name__ == '__main__':
    # Test embedding
    inputs = ["Hello, world!", "This is a test sentence."]
    
    print("Testing Ollama embedding (recommended)...")
    try:
        output = ollama_embedding(inputs)
        print(f"✅ Success! Embedding dimension: {len(output[0])}")
        print(f"   Model: nomic-embed-text (local, free)")
    except Exception as e:
        print(f"❌ Ollama embedding failed: {e}")
        print("   Make sure Ollama is running and nomic-embed-text is installed")
        print("   Run: ollama pull nomic-embed-text")
    
    print("\nTesting OpenAI embedding...")
    try:
        output = openai_embedding(inputs)
        print(f"✅ Success! Embedding dimension: {len(output[0])}")
    except Exception as e:
        print(f"❌ OpenAI embedding failed: {e}")
    
    print("\nTesting local embedding...")
    try:
        output = local_embedding(inputs)
        print(f"✅ Success! Embedding dimension: {len(output[0])}")
    except Exception as e:
        print(f"❌ Local embedding failed: {e}")

