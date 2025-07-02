import os
import sys
import fitz  # PyMuPDF
import json
from pathlib import Path

def pdf_to_markdown(pdf_path, output_path=None):
    """将PDF转换为Markdown格式"""
    if not os.path.exists(pdf_path):
        print(f"错误: PDF文件不存在: {pdf_path}")
        return None
    
    if not output_path:
        output_path = os.path.splitext(pdf_path)[0] + ".md"
    
    try:
        doc = fitz.open(pdf_path)
        markdown_content = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text.strip():
                markdown_content.append(f"## 第 {page_num + 1} 页\n\n{text}\n")
        
        doc.close()
        
        full_content = "\n".join(markdown_content)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        print(f"转换完成: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"转换失败: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("使用方法: python pdf2md.py <PDF文件路径> [输出路径]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    pdf_to_markdown(pdf_path, output_path)

if __name__ == "__main__":
    main()