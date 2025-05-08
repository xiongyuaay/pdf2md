import os
import argparse
from pdf_converter_image import PDFConverter
from Knowledge_extractor import KnowledgeExtractor

def main():
    parser = argparse.ArgumentParser(description='PDF教材转Markdown并提取知识点工具')
    parser.add_argument('--pdf', '-p', type=str, help='PDF文件路径')
    parser.add_argument('--output', '-o', type=str, help='输出目录路径')
    parser.add_argument('--api_key', '-k', type=str, help='OpenAI API密钥')
    parser.add_argument('--extract', '-e', action='store_true', help='是否提取知识点')
    parser.add_argument('--local_model', '-l', action='store_true', help='是否使用本地部署的大模型')
    parser.add_argument('--model_url', '-u', type=str, help='模型API地址')
    
    args = parser.parse_args()
    
    if not args.pdf:
        print("错误：请指定PDF文件路径")
        parser.print_help()
        return
    
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
    file_name = os.path.splitext(base_name)[0]
    
    md_output_path = os.path.join(output_dir, f"{file_name}.md")
    knowledge_output_path = os.path.join(output_dir, f"{file_name}_知识点.md")
    
    # 1. PDF转换为Markdown
    print("=" * 50)
    print("步骤1: PDF转换为Markdown")
    print("=" * 50)
    
    converter = PDFConverter(args.pdf)
    md_path = converter.process_pdf(md_output_path, args.method)
    
    if not md_path:
        print("PDF转换失败，程序终止")
        return
    
    print(f"PDF已成功转换为Markdown: {md_path}")
    
    # 2. 提取知识点
    if args.extract:
        print("\n" + "=" * 50)
        print("步骤2: 提取知识点")
        print("=" * 50)
        
        # 初始化知识点提取器，支持本地模型
        extractor = KnowledgeExtractor(
            api_key=args.api_key,
            use_local_model=args.local_model,
            local_model_url=args.model_url
        )
        
        # 读取Markdown文件内容
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
                
            if not md_content:
                print("Markdown文件内容为空，无法提取知识点")
                return
                
            # 提取知识点
            if args.local_model:
                print("使用本地部署的大模型提取知识点...")
            else:
                print("使用OpenAI API提取知识点...")
                
            print("这可能需要几分钟时间...")
            knowledge_points = extractor.extract_knowledge_points(md_content)
            
            if not knowledge_points:
                print("未能提取到知识点")
                return
                
            # 保存知识点
            knowledge_path = extractor.save_knowledge_points(knowledge_points, knowledge_output_path)
            
            if knowledge_path:
                print(f"知识点已成功提取并保存: {knowledge_path}")
                
        except Exception as e:
            print(f"提取知识点时发生错误: {e}")
    
    print("\n处理完成!")

if __name__ == "__main__":
    main() 