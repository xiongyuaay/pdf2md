import sys
import os
import json
from src.knowledge_extractor import KnowledgeExtractor
from src.pdf_converter_image import PDFConverter


def main():
    if len(sys.argv) < 2:
        print("使用方法: python main.py <PDF文件路径> [输出目录]")
        print("示例: python main.py data/example.pdf output/")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    
    if not os.path.exists(pdf_path):
        print(f"错误: PDF文件不存在: {pdf_path}")
        sys.exit(1)
    
    if not pdf_path.lower().endswith('.pdf'):
        print(f"错误: 输入文件必须是PDF格式: {pdf_path}")
        sys.exit(1)
    
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        print("步骤1/2: 转换PDF到Markdown...")
        base_name = os.path.basename(pdf_path)
        file_name_without_ext = os.path.splitext(base_name)[0]
        
        converter = PDFConverter(pdf_path)
        md_output_path = os.path.join(output_dir, f"{file_name_without_ext}_converted.md")
        converted_md_path = converter.process_pdf(md_output_path)
        
        if not converted_md_path:
            print("PDF转换失败")
            sys.exit(1)
        
        print(f"PDF已转换为Markdown: {converted_md_path}")
        
        print("步骤2/2: 提取知识点...")
        
        extractor = KnowledgeExtractor(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model_name=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        )
        
        with open(converted_md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        if not md_content.strip():
            print("Markdown文件内容为空")
            sys.exit(1)
        
        knowledge_json_str = extractor.extract_knowledge_points(md_content)
        
        if not knowledge_json_str or knowledge_json_str == json.dumps({"knowledge_points": []}):
            print("未能提取到知识点")
            sys.exit(1)
        
        knowledge_output_base = os.path.join(output_dir, f"{file_name_without_ext}_knowledge_points")
        saved_json_path = extractor.save_knowledge_points(knowledge_json_str, knowledge_output_base)
        
        if saved_json_path:
            print(f"知识点已保存到: {saved_json_path}")
            print("处理完成!")
        else:
            print("知识点保存失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 