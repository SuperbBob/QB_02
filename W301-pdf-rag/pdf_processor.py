"""
PDF processing module
Extracts text, images, and tables from PDF documents
"""
import os
import fitz  # PyMuPDF
import base64
import mimetypes
import time
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
from openai import OpenAI
from config import ModelConfig, RAGConfig


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract text content from PDF pages
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of dictionaries containing page text
    """
    pdf_document = fitz.open(pdf_path)
    text_content = []
    
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        page_text = page.get_text("text")
        
        if page_text.strip():
            text_content.append({
                "page_num": page_num + 1,
                "text": page_text.strip(),
                "type": "text"
            })
    
    pdf_document.close()
    logger.info(f"Extracted text from {len(text_content)} pages")
    return text_content


def summarize_image(image_path: str, base_url: str = ModelConfig.IMAGE_MODEL_URL) -> str:
    """
    Generate a detailed description of an image using a vision model
    
    Args:
        image_path: Path to the image file
        base_url: Base URL for the vision model API
        
    Returns:
        Image description text
    """
    retry = 0
    max_retries = 3
    
    prompt = """详细地描述这张图片的内容，不要漏掉细节，并提取图片中的文字。注意只需客观说明图片内容，无需进行任何评价。"""
    
    while retry < max_retries:
        try:
            client = OpenAI(api_key='YOUR_API_KEY', base_url=base_url)
            
            # Read local image and convert to Base64 data URL
            with open(image_path, 'rb') as f:
                content_bytes = f.read()
            mime_type = mimetypes.guess_type(image_path)[0] or 'image/png'
            encoded = base64.b64encode(content_bytes).decode('utf-8')
            data_url = f"data:{mime_type};base64,{encoded}"
            
            resp = client.chat.completions.create(
                model='internvl-internlm2',
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt}, 
                        {'type': 'image_url', 'image_url': {'url': data_url}}
                    ]
                }], 
                temperature=0.8, 
                top_p=0.8, 
                max_tokens=2048, 
                stream=False
            )
            
            return resp.choices[0].message.content
        except Exception as e:
            retry += 1
            if retry < max_retries:
                logger.warning(f"Image summarization failed (attempt {retry}/{max_retries}): {e}")
                time.sleep(1)
            else:
                logger.error(f"Failed to summarize image after {max_retries} attempts: {e}")
                return ""


def context_augment_image(page_context: str, image_description: str) -> str:
    """
    Augment image description with page context using LLM
    
    Args:
        page_context: Text context from the page
        image_description: Initial image description
        
    Returns:
        Context-augmented image description
    """
    prompt = f'''目标：通过图片的上下文以及来源文件信息补充图片描述的细节，准确描述出图片在文档中的实际内容和用途含义。

注意事项：
- 上下文中可能会有噪音，请注意甄别。
- 重点关注上下文中的图片caption标注，因为它们通常描述图片的用途和意义。
- 保留图片的意图与重要信息,过滤掉与上下文无关的信息。
- 有时图片描述中会出现重复性的内容，这类内容请视为噪音过滤掉。
- 请直接输出答案，无需解释。
- 如果图片不包含任何内容，或者为背景图片，输出 0

图片描述：
```
{image_description}
```

上下文：
```
{page_context[:2000]}
```
'''
    
    try:
        client = OpenAI(
            api_key=ModelConfig.OPENAI_API_KEY,
            base_url=ModelConfig.OPENAI_BASE_URL
        )
        response = client.chat.completions.create(
            model=ModelConfig.LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一个智能AI助手，根据图片的上下文对图片描述进行补充，补充后的描述要更加准确，更加详细，更加完整。"},
                {"role": "user", "content": prompt}
            ]
        )
        result = response.choices[0].message.content
        
        # Filter out background images
        if result.strip() == "0":
            return ""
        return result
    except Exception as e:
        logger.error(f"Context augmentation failed: {e}")
        return image_description


def extract_images_from_pdf(pdf_path: str, output_dir: str = None) -> List[Dict[str, Any]]:
    """
    Extract images from PDF and generate descriptions
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save extracted images (temporary)
        
    Returns:
        List of dictionaries containing image information
    """
    if output_dir is None:
        output_dir = RAGConfig.IMAGE_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_document = fitz.open(pdf_path)
    logger.info(f"Processing PDF: {pdf_path}")
    
    # Get unique images
    unique_xrefs = set()
    for p in range(pdf_document.page_count):
        page_images = pdf_document.get_page_images(p)
        for item in page_images:
            xref = item[0]
            unique_xrefs.add(xref)
    
    logger.info(f"Found {len(unique_xrefs)} unique images")
    
    if len(unique_xrefs) == 0:
        pdf_document.close()
        return []
    
    results = []
    processed_xrefs = set()
    
    for page_num in range(pdf_document.page_count):
        try:
            page = pdf_document.load_page(page_num)
            page_width = page.rect.width
            
            # Extract page text as context
            page_text = page.get_text("text")
            
            page_images = pdf_document.get_page_images(page_num)
            for img_index, item in enumerate(page_images):
                try:
                    xref = item[0]
                    if xref in processed_xrefs:
                        continue
                    processed_xrefs.add(xref)
                    
                    image_width = item[2]
                    image_height = item[3]
                    
                    # Filter small images
                    if (image_width < page_width / RAGConfig.IMAGE_WIDTH_RATIO or 
                        image_width < RAGConfig.MIN_IMAGE_WIDTH or 
                        image_height < RAGConfig.MIN_IMAGE_HEIGHT):
                        continue
                    
                    # Extract image
                    pix = fitz.Pixmap(pdf_document, xref)
                    if pix.colorspace and pix.colorspace.name == 'DeviceCMYK':
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    image_save_path = f'{output_dir}/img_{page_num + 1}_{img_index + 1}.png'
                    pix.save(image_save_path)
                    del pix
                    
                    # Generate image description
                    summary = summarize_image(image_save_path)
                    if not summary:
                        os.remove(image_save_path)
                        continue
                    
                    # Augment with context
                    augmented_summary = context_augment_image(page_text, summary)
                    if not augmented_summary:
                        os.remove(image_save_path)
                        continue
                    
                    results.append({
                        "page_num": page_num + 1,
                        "image_index": img_index + 1,
                        "summary": summary,
                        "context_augmented_summary": augmented_summary,
                        "image_path": image_save_path,
                        "page_context": page_text.strip(),
                        "type": "image"
                    })
                    
                    logger.info(f"Processed image {len(results)} on page {page_num + 1}")
                    
                    # Clean up temporary image
                    try:
                        os.remove(image_save_path)
                    except:
                        pass
                        
                except Exception as e:
                    logger.error(f"Error processing image on page {page_num + 1}: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing page {page_num + 1}: {e}")
    
    pdf_document.close()
    logger.info(f"Extracted {len(results)} images")
    return results


def table_context_augment(page_context: str, table_md: str) -> str:
    """
    Generate natural language summary of table using context
    
    Args:
        page_context: Text context from the page
        table_md: Table in markdown format
        
    Returns:
        Natural language table summary
    """
    prompt = f"""目标：请根据输入的表格和上下文信息以及来源文件信息，生成针对于该表格的一段简短的语言描述

注意：
在描述中尽可能包含以下内容：
- 表格名称：根据上下文或表格内容推测表格的名称。
- 表格内容简介：使用自然语言总结表格的内容，包括主要信息、数据点和结构。
- 表格意图：分析表格的用途或目的，例如是否用于展示、比较、统计等。
你生成的描述需要控制在三句话以内。

输入表格：
{table_md}

表格上下文：
{page_context[:1500]}
"""
    
    try:
        client = OpenAI(
            api_key=ModelConfig.OPENAI_API_KEY,
            base_url=ModelConfig.OPENAI_BASE_URL
        )
        response = client.chat.completions.create(
            model=ModelConfig.LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一个智能AI助手，根据表格的上下文对表格内容进行补充，补充后的内容要更加准确，更加详细，更加完整。"},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Table context augmentation failed: {e}")
        return table_md


def extract_tables_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract tables from PDF and generate summaries
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of dictionaries containing table information
    """
    pdf_document = fitz.open(pdf_path)
    results = []
    
    for page_num in range(pdf_document.page_count):
        try:
            page = pdf_document.load_page(page_num)
            page_text = page.get_text("text")
            page_tables = page.find_tables()
            
            for table_index, table in enumerate(page_tables):
                try:
                    md = table.to_markdown()
                    if not md.strip():
                        continue
                    
                    # Generate table summary
                    augmented = table_context_augment(page_text, md)
                    
                    results.append({
                        "page_num": page_num + 1,
                        "table_index": table_index + 1,
                        "table_markdown": md,
                        "page_context": page_text.strip(),
                        "context_augmented_table": augmented,
                        "type": "table"
                    })
                    
                    logger.info(f"Processed table {table_index + 1} on page {page_num + 1}")
                except Exception as e:
                    logger.error(f"Error processing table on page {page_num + 1}: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing page {page_num + 1}: {e}")
    
    pdf_document.close()
    logger.info(f"Extracted {len(results)} tables")
    return results


def process_pdf(pdf_path: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Process a PDF file and extract all content types
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Tuple of (text_content, images, tables)
    """
    logger.info(f"Starting PDF processing: {pdf_path}")
    
    text_content = extract_text_from_pdf(pdf_path)
    images = extract_images_from_pdf(pdf_path)
    tables = extract_tables_from_pdf(pdf_path)
    
    logger.info(f"PDF processing complete: {len(text_content)} text pages, "
                f"{len(images)} images, {len(tables)} tables")
    
    return text_content, images, tables


if __name__ == "__main__":
    # Test PDF processing
    test_pdf = "/Users/peixingao/Documents/RAG Demo/test_pdf/image_extraction_example.pdf"
    
    if os.path.exists(test_pdf):
        text, images, tables = process_pdf(test_pdf)
        print(f"\nProcessed: {len(text)} pages, {len(images)} images, {len(tables)} tables")
    else:
        print("Test PDF not found. Please provide a valid PDF path.")

