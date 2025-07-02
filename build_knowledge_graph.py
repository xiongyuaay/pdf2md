import os
import sys
from knowledge_graph.llm_knowledge_graph_builder import LLMKnowledgeGraphBuilder

def main():
    if len(sys.argv) < 2:
        print("使用方法: python build_knowledge_graph.py <知识点JSON文件>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"错误: 文件不存在: {input_file}")
        sys.exit(1)
    
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    if not api_key:
        print("错误: 请设置OPENAI_API_KEY环境变量")
        sys.exit(1)
    
    try:
        builder = LLMKnowledgeGraphBuilder(
            api_key=api_key,
            base_url=base_url,
            model_name=model
        )
        
        output_file = builder.process_knowledge_file(input_file)
        print(f"知识图谱已生成: {output_file}")
        
    except Exception as e:
        print(f"构建知识图谱失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 