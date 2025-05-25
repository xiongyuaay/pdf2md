import os
import argparse
import json
from src.pdf_converter_image import PDFConverter
from src.knowledge_extractor import KnowledgeExtractor

def main():
    parser = argparse.ArgumentParser(description='PDF教材转Markdown并提取知识点工具')
    # parser.add_argument('--pdf', '-p', type=str, required=True, help='PDF文件路径')
    # parser.add_argument('--output', '-o', type=str, help='输出目录路径')
    # parser.add_argument('--api_key', '-k', type=str, help='API密钥')
    # parser.add_argument('--base_url', '-b', type=str, help='API基础URL (例如 OpenAI, DeepSeek等)')
    # parser.add_argument('--local_model', '-l', action='store_true', help='是否使用本地部署的大模型')
    # parser.add_argument('--model_url', '-u', type=str, help='本地模型API地址')
    # parser.add_argument('--model_name', '-n', type=str, help='模型名称 (例如 gpt-3.5-turbo, deepseek-chat)')

    args = parser.parse_args()
    
    args.pdf = r"E:/pdf教材知识整理/pdf2md/data/数学问题v1.0-.pdf"
    args.output = r"./output"
    args.api_key = "sk-c4db4d3fce94444e95ef3a235a12cc3a"
    args.base_url = "https://api.deepseek.com"
    args.model_name = "deepseek-chat"
    args.local_model = False
    args.model_url = None
    
    if not os.path.exists(args.pdf):
        print(f"错误：PDF文件不存在: {args.pdf}")
        return
    
    output_dir = args.output if args.output else os.path.dirname(args.pdf)
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"已创建输出目录: {output_dir}")
        except Exception as e:
            print(f"创建输出目录失败: {e}")
            return
    
    base_name = os.path.basename(args.pdf)
    file_name_without_ext = os.path.splitext(base_name)[0]
    
    md_conversion_output_path = os.path.join(output_dir, f"{file_name_without_ext}_converted.md")
    knowledge_output_base_name = f"{file_name_without_ext}_knowledge_points"
    knowledge_output_base = os.path.join(output_dir, knowledge_output_base_name)

    print("=" * 50)
    print("步骤1: PDF转换为Markdown (图像处理)")
    print("=" * 50)
    
    converter = PDFConverter(args.pdf)
    converted_md_path = converter.process_pdf(md_conversion_output_path)
    
    if not converted_md_path:
        print("PDF内容提取或Markdown转换失败，程序终止")
        return
    
    print(f"PDF已成功转换为Markdown: {converted_md_path}")
    
    print("\n" + "=" * 50)
    print("步骤2: 提取知识点")
    print("=" * 50)
    
    extractor = KnowledgeExtractor(
        api_key=args.api_key,
        use_local_model=args.local_model,
        local_model_url=args.model_url,
        base_url=args.base_url,
        model_name=args.model_name
    )
    
    try:
        with open(converted_md_path, 'r', encoding='utf-8') as f:
            md_content_for_extraction = f.read()
            
        if not md_content_for_extraction:
            print("转换后的Markdown文件内容为空，无法提取知识点")
            return
            
        knowledge_json_str = extractor.extract_knowledge_points(md_content_for_extraction)
        
        if not knowledge_json_str or knowledge_json_str == json.dumps({"knowledge_points": []}):
            print("未能从文档中提取到初步知识点 (返回的JSON为空或仅包含空列表)")
            return
        
        print("初步知识点提取完成。")

        try:
            json.loads(knowledge_json_str)
        except json.JSONDecodeError as e:
            print(f"最终的知识点不是有效的JSON格式: {e}")
            return

        saved_json_path = extractor.save_knowledge_points(knowledge_json_str, knowledge_output_base)
        
        if saved_json_path:
            print(f"\n主要知识点文件 (JSON): {saved_json_path}")
        else:
            print("知识点JSON文件保存失败。")
    except Exception as e:
        print(f"提取或保存知识点时发生错误: {e}")
    
if __name__ == "__main__":
    main() 