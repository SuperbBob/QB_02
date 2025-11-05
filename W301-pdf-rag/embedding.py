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


def batch_embed(texts: List[str], batch_size: int = 25, use_openai: bool = False) -> List[List[float]]:
    """
    Embed texts in batches for efficiency
    
    Args:
        texts: List of texts to embed
        batch_size: Number of texts to embed in each batch
        use_openai: Whether to use OpenAI embeddings
        
    Returns:
        List of embedding vectors
    """
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"Embedding batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
        
        if use_openai:
            embeddings = openai_embedding(batch)
        else:
            embeddings = local_embedding(batch)
            
        all_embeddings.extend(embeddings)
    
    return all_embeddings


if __name__ == '__main__':
    # Test embedding
    inputs = ["Hello, world!", "This is a test sentence."]
    
    print("Testing local embedding...")
    try:
        output = local_embedding(inputs)
        print(f"Success! First embedding dimension: {len(output[0])}")
    except Exception as e:
        print(f"Local embedding failed: {e}")
    
    print("\nTesting OpenAI embedding...")
    try:
        output = openai_embedding(inputs)
        print(f"Success! First embedding dimension: {len(output[0])}")
    except Exception as e:
        print(f"OpenAI embedding failed: {e}")

