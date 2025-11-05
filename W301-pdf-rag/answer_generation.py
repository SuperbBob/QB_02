"""
Answer generation module with citations
Generates responses grounded in retrieved content
"""
from typing import List, Dict, Any
from openai import OpenAI
from config import ModelConfig


def format_context(documents: List[Dict[str, Any]], include_metadata: bool = True) -> str:
    """
    Format retrieved documents into context for LLM
    
    Args:
        documents: List of retrieved documents
        include_metadata: Whether to include metadata in context
        
    Returns:
        Formatted context string
    """
    context_parts = []
    
    for i, doc in enumerate(documents):
        doc_type = doc.get('doc_type', 'text')
        page_num = doc.get('page_num', 'N/A')
        text = doc.get('text', '')
        
        # Format based on document type
        if doc_type == 'image':
            prefix = f"[图片 - 第{page_num}页]"
        elif doc_type == 'table':
            prefix = f"[表格 - 第{page_num}页]"
            # Include table markdown if available
            table_md = doc.get('metadata', {}).get('table_markdown', '')
            if table_md:
                text = f"{text}\n\n表格内容：\n{table_md}"
        else:
            prefix = f"[文本 - 第{page_num}页]"
        
        if include_metadata:
            context_parts.append(f"[{i+1}] {prefix} {text}")
        else:
            context_parts.append(f"[{i+1}] {text}")
    
    return "\n\n".join(context_parts)


def generate_answer(query: str, documents: List[Dict[str, Any]], 
                    model: str = None, include_citations: bool = True,
                    system_prompt: str = None) -> Dict[str, Any]:
    """
    Generate answer based on retrieved documents with citations
    
    Args:
        query: User query
        documents: List of retrieved documents
        model: LLM model to use
        include_citations: Whether to include citations in answer
        system_prompt: Custom system prompt
        
    Returns:
        Dictionary with answer and metadata
    """
    if not documents:
        return {
            'answer': "抱歉，我没有找到相关的信息来回答您的问题。",
            'citations': [],
            'num_sources': 0
        }
    
    if model is None:
        model = ModelConfig.LLM_MODEL
    
    # Format context
    context = format_context(documents, include_metadata=True)
    
    # Default system prompt
    if system_prompt is None:
        system_prompt = """你是一个专业的知识助手，基于提供的文档内容回答用户问题。

要求：
1. 仅基于提供的文档内容回答问题，不要编造信息
2. 如果文档中没有相关信息，明确告知用户
3. 在回答中使用引用标记 [1], [2] 等来标注信息来源
4. 回答要准确、清晰、有条理
5. 如果文档中包含图片或表格的描述，请在回答中适当引用
6. 保持专业和客观的语气"""
    
    # User prompt with context
    user_prompt = f"""参考文档：

{context}

用户问题：{query}

请基于上述文档内容回答问题，并在答案中使用 [1], [2] 等标记引用相关文档。"""
    
    try:
        client = OpenAI(
            api_key=ModelConfig.OPENAI_API_KEY,
            base_url=ModelConfig.OPENAI_BASE_URL
        )
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        
        # Extract citations from answer
        import re
        citation_pattern = r'\[(\d+)\]'
        citations = list(set(re.findall(citation_pattern, answer)))
        citations = [int(c) for c in citations]
        citations.sort()
        
        # Build citation details
        citation_details = []
        for cite_num in citations:
            if 0 < cite_num <= len(documents):
                doc = documents[cite_num - 1]
                citation_details.append({
                    'citation_number': cite_num,
                    'doc_type': doc.get('doc_type', 'text'),
                    'page_num': doc.get('page_num', 'N/A'),
                    'text': doc.get('text', '')[:200] + '...' if len(doc.get('text', '')) > 200 else doc.get('text', '')
                })
        
        return {
            'answer': answer,
            'citations': citation_details,
            'num_sources': len(documents),
            'model': model
        }
        
    except Exception as e:
        print(f"[Answer Generation Error] {e}")
        return {
            'answer': f"生成答案时出错：{str(e)}",
            'citations': [],
            'num_sources': len(documents)
        }


def generate_multi_query_answer(query: str, documents_per_query: List[List[Dict[str, Any]]],
                                queries: List[str], model: str = None) -> Dict[str, Any]:
    """
    Generate answer from multiple query results (for RAG Fusion)
    
    Args:
        query: Original query
        documents_per_query: List of document lists for each query variation
        queries: List of query variations
        model: LLM model to use
        
    Returns:
        Dictionary with answer and metadata
    """
    # Combine and deduplicate documents
    seen_ids = set()
    combined_docs = []
    
    for docs in documents_per_query:
        for doc in docs:
            doc_id = doc.get('id')
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                combined_docs.append(doc)
    
    # Re-rank combined documents by their aggregate scores
    combined_docs.sort(key=lambda x: x.get('rrf_score', 0) + x.get('rerank_score', 0), reverse=True)
    
    # Generate answer using combined documents
    return generate_answer(query, combined_docs[:10], model=model)


def generate_decomposed_answer(query: str, sub_answers: List[Dict[str, Any]],
                               sub_queries: List[str], model: str = None) -> Dict[str, Any]:
    """
    Generate final answer from sub-query answers (for Query Decomposition)
    
    Args:
        query: Original complex query
        sub_answers: List of answers for each sub-query
        sub_queries: List of sub-queries
        model: LLM model to use
        
    Returns:
        Dictionary with answer and metadata
    """
    if model is None:
        model = ModelConfig.LLM_MODEL
    
    # Format sub-answers
    sub_answers_text = []
    for i, (sq, sa) in enumerate(zip(sub_queries, sub_answers)):
        sub_answers_text.append(f"子问题 {i+1}：{sq}\n回答：{sa['answer']}")
    
    combined_sub_answers = "\n\n".join(sub_answers_text)
    
    system_prompt = """你是一个专业的知识助手，需要基于多个子问题的答案，综合回答用户的原始问题。

要求：
1. 综合所有子问题的答案，生成一个完整、连贯的回答
2. 保留原有的引用标记
3. 回答要有逻辑性和条理性
4. 如果子答案之间有矛盾，请指出"""
    
    user_prompt = f"""原始问题：{query}

各子问题的答案：
{combined_sub_answers}

请基于上述子问题的答案，综合回答原始问题。"""
    
    try:
        client = OpenAI(
            api_key=ModelConfig.OPENAI_API_KEY,
            base_url=ModelConfig.OPENAI_BASE_URL
        )
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        
        # Collect all citations from sub-answers
        all_citations = []
        for sa in sub_answers:
            all_citations.extend(sa.get('citations', []))
        
        # Deduplicate citations
        seen_cite_ids = set()
        unique_citations = []
        for cite in all_citations:
            cite_id = (cite.get('page_num'), cite.get('text')[:50])
            if cite_id not in seen_cite_ids:
                seen_cite_ids.add(cite_id)
                unique_citations.append(cite)
        
        return {
            'answer': answer,
            'citations': unique_citations,
            'sub_queries': sub_queries,
            'sub_answers': sub_answers,
            'model': model
        }
        
    except Exception as e:
        print(f"[Decomposed Answer Generation Error] {e}")
        # Fallback: concatenate sub-answers
        fallback_answer = f"基于各个方面的分析：\n\n" + "\n\n".join(
            [f"{i+1}. {sa['answer']}" for i, sa in enumerate(sub_answers)]
        )
        return {
            'answer': fallback_answer,
            'citations': all_citations,
            'sub_queries': sub_queries,
            'sub_answers': sub_answers
        }


if __name__ == "__main__":
    # Test answer generation
    test_query = "什么是机器学习？"
    test_docs = [
        {
            'id': '1',
            'text': '机器学习是人工智能的一个分支，它使计算机能够从数据中学习并做出决策，而无需明确编程。',
            'doc_type': 'text',
            'page_num': 1,
            'metadata': {}
        },
        {
            'id': '2',
            'text': '机器学习的主要类型包括监督学习、非监督学习和强化学习。监督学习使用标记的数据进行训练。',
            'doc_type': 'text',
            'page_num': 2,
            'metadata': {}
        }
    ]
    
    print("Testing answer generation...")
    try:
        result = generate_answer(test_query, test_docs)
        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nCitations: {len(result['citations'])}")
        for cite in result['citations']:
            print(f"  [{cite['citation_number']}] Page {cite['page_num']}: {cite['text']}")
    except Exception as e:
        print(f"Answer generation failed: {e}")

