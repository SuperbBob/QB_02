"""
Query enhancement module
Implements RAG Fusion and Query Decomposition
"""
import json
from typing import List, Dict, Any
from openai import OpenAI
from config import ModelConfig


def rag_fusion(query: str, num_variations: int = 2) -> List[str]:
    """
    Generate multiple query variations for RAG Fusion
    
    Args:
        query: Original query
        num_variations: Number of query variations to generate
        
    Returns:
        List of query variations
    """
    prompt = f'''请根据用户的查询，将其重新改写为 {num_variations} 个不同的查询。这些改写后的查询应当尽可能覆盖原始查询中的不同方面或角度，以便更全面地获取相关信息。请确保每个改写后的查询仍然与原始查询相关，并且在内容上有所不同。

用JSON的格式输出：
{{
    "queries": ["query1", "query2", ...]
}}

原始查询：{query}
'''
    
    try:
        client = OpenAI(
            api_key=ModelConfig.OPENAI_API_KEY,
            base_url=ModelConfig.OPENAI_BASE_URL
        )
        
        response = client.chat.completions.create(
            model=ModelConfig.FAST_LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一个智能AI助手，专注于改写用户查询，并以 JSON 格式输出"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        parsed_result = json.loads(result)
        variations = parsed_result.get("queries", [query])
        
        # Ensure we return the original query plus variations
        if query not in variations:
            variations.insert(0, query)
        
        return variations
        
    except Exception as e:
        print(f"[RAG Fusion Error] {e}, returning original query")
        return [query]


def query_decomposition(query: str) -> List[str]:
    """
    Decompose complex query into sub-queries
    
    Args:
        query: Original complex query
        
    Returns:
        List of sub-queries (empty list if no decomposition needed)
    """
    prompt = f'''目标：分析用户的问题，判断其是否需要拆分为子问题以提高信息检索的准确性。如果需要拆分，提供拆分后的子问题列表；如果不需要，直接返回空列表。

说明：
- 用户的问题可能含糊不清或包含多个概念，导致难以直接回答。
- 为提高知识库查询的质量和相关性，需评估问题是否应分解为更具体的子问题。
- 根据问题的复杂性和广泛性，判断是否需要拆分：
  - 如果问题涉及多个方面（如比较多个实体、包含多个独立步骤），需要拆分为子问题。
  - 如果问题已集中且明确，返回空列表。
- 输出结果必须为 JSON 格式。请直接输出JSON，不需要做任何解释。

输出格式：
{{
  "queries": ["子问题1", "子问题2", ...] 或 []
}}  

案例 1
---
用户问题: "林冲、关羽、孙悟空的性格有什么不同？"
推理过程: 该问题涉及多个实体的比较，需要分别了解每个实体的性格。
输出:
{{
  "queries": ["林冲的性格是什么？", "关羽的性格是什么？", "孙悟空的性格是什么？"]
}}

案例 2
---
用户问题: "Covid对经济的影响是什么？"
推理过程: 问题集中且明确，无需拆分。
输出:
{{
  "queries": []
}}

用户问题:
"{query}"
'''
    
    try:
        client = OpenAI(
            api_key=ModelConfig.OPENAI_API_KEY,
            base_url=ModelConfig.OPENAI_BASE_URL
        )
        
        response = client.chat.completions.create(
            model=ModelConfig.LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一个智能AI助手，专注于做查询拆分，并以 JSON 格式输出"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        parsed_result = json.loads(result)
        sub_queries = parsed_result.get("queries", [])
        
        return sub_queries
        
    except Exception as e:
        print(f"[Query Decomposition Error] {e}, returning empty list")
        return []


def coreference_resolution(query: str, chat_history: List[Dict[str, str]]) -> str:
    """
    Resolve coreferences in query using chat history
    
    Args:
        query: User query with potential coreferences
        chat_history: List of previous conversation turns
        
    Returns:
        Resolved query
    """
    # Format chat history
    history_str = "\n".join([f"{turn['role']}: {turn['content']}" for turn in chat_history])
    
    prompt = f'''目标：根据提供的用户与知识库助手的历史记录，做指代消解，将用户最新问题中出现的代词或指代内容替换为历史记录中的明确对象，生成一条完整的独立问题。

说明：
- 将用户问题中的指代词替换为历史记录中的具体内容，生成一条独立问题。

以JSON的格式输出
{{"query": "替换指代后的完整问题"}}

以下是一些案例

----------
历史记录：
user: Milvus是什么?
assistant: Milvus 是一个向量数据库
用户问题：怎么使用它？

输出JSON：{{"query": "怎么使用Milvus?"}}
----------

历史记录：
{history_str}

用户问题：{query}

输出JSON：
'''
    
    try:
        client = OpenAI(
            api_key=ModelConfig.OPENAI_API_KEY,
            base_url=ModelConfig.OPENAI_BASE_URL
        )
        
        response = client.chat.completions.create(
            model=ModelConfig.LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一个智能AI助手，专注于做指代消解，并以 JSON 格式输出"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        parsed_result = json.loads(result)
        resolved_query = parsed_result.get("query", query)
        
        return resolved_query
        
    except Exception as e:
        print(f"[Coreference Resolution Error] {e}, returning original query")
        return query


if __name__ == "__main__":
    # Test query enhancement
    test_query = "比较Python和Java的区别"
    
    print("Testing RAG Fusion...")
    try:
        variations = rag_fusion(test_query, num_variations=2)
        print(f"Generated {len(variations)} query variations:")
        for i, var in enumerate(variations):
            print(f"  {i+1}. {var}")
    except Exception as e:
        print(f"RAG Fusion failed: {e}")
    
    print("\nTesting Query Decomposition...")
    try:
        sub_queries = query_decomposition(test_query)
        if sub_queries:
            print(f"Decomposed into {len(sub_queries)} sub-queries:")
            for i, sq in enumerate(sub_queries):
                print(f"  {i+1}. {sq}")
        else:
            print("No decomposition needed")
    except Exception as e:
        print(f"Query Decomposition failed: {e}")
    
    print("\nTesting Coreference Resolution...")
    try:
        history = [
            {"role": "user", "content": "什么是机器学习？"},
            {"role": "assistant", "content": "机器学习是人工智能的一个分支，专注于让计算机从数据中学习。"}
        ]
        test_query_coref = "它有哪些应用？"
        resolved = coreference_resolution(test_query_coref, history)
        print(f"Original: {test_query_coref}")
        print(f"Resolved: {resolved}")
    except Exception as e:
        print(f"Coreference Resolution failed: {e}")

