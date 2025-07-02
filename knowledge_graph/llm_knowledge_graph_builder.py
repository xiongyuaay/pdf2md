import os
import json
import time
from typing import List, Dict, Any

from openai import OpenAI
OPENAI_AVAILABLE = True


class LLMKnowledgeGraphBuilder:
    def __init__(self, api_key: str, base_url: str = None, model_name: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model_name = model_name
        
        if not self.base_url.endswith('/v1'):
            if not self.base_url.endswith('/'):
                self.base_url += '/'
            self.base_url += 'v1'
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
    
    def _call_llm(self, messages: List[Dict], max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=4000,
                    timeout=60  # 单次请求超时时间2分钟
                )
                
                return response.choices[0].message.content
                
            except Exception:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    time.sleep(wait_time)
        
        raise Exception("API调用失败")
    
    def build_knowledge_graph(self, knowledge_points: List[Dict]) -> List[Dict]:
        if not knowledge_points:
            return knowledge_points
        
        titles_info = []
        for point in knowledge_points:
            titles_info.append({
                "id": point.get("id", ""),
                "title": point.get("title", ""),
                "type": point.get("type", "unknown")
            })
        
        batch_size = 20
        all_relations = {}
        
        for i in range(0, len(titles_info), batch_size):
            batch = titles_info[i:i + batch_size]
            
            titles_text = "\n".join([f"{info['id']}: {info['title']} (类型: {info['type']})" 
                                   for info in batch])
            
            prompt = f"""请分析以下知识点标题之间的语义关系，并为每个知识点找出与其他知识点的关系。

知识点列表：
{titles_text}

请分析这些知识点之间可能存在的关系类型：
1. "前提条件" - A是学习B的前提
2. "后续知识" - B是A的进阶或应用
3. "相似概念" - 概念相似或平行
4. "部分-整体" - 一个是另一个的组成部分
5. "互补概念" - 相互补充或对比

请以JSON格式返回结果，格式如下：
{{
  "relations": [
    {{
      "source_id": "知识点ID",
      "target_id": "相关知识点ID", 
      "relation_type": "关系类型",
      "confidence": 0.8
    }}
  ]
}}

注意：
- 只返回确信度较高(>0.6)的关系
- 每个知识点最多关联5个其他知识点
- 只分析当前批次内的知识点关系
- 必须返回有效的JSON格式"""

            try:
                messages = [
                    {"role": "system", "content": "你是一个专业的知识图谱分析专家，擅长分析知识点之间的语义关系。"},
                    {"role": "user", "content": prompt}
                ]
                
                response = self._call_llm(messages)
                
                try:
                    response = response.strip()
                    if "```json" in response:
                        response = response.split("```json")[1].split("```")[0]
                    elif "```" in response:
                        response = response.split("```")[1]
                    
                    relations_data = json.loads(response)
                    
                    if "relations" in relations_data:
                        for relation in relations_data["relations"]:
                            source_id = relation.get("source_id")
                            if source_id not in all_relations:
                                all_relations[source_id] = []
                            all_relations[source_id].append(relation)
                    
                except json.JSONDecodeError:
                    pass
                
            except Exception:
                continue
            
            time.sleep(1)
        
        for point in knowledge_points:
            point_id = point.get("id")
            if point_id in all_relations:
                relations = sorted(all_relations[point_id], 
                                 key=lambda x: x.get("confidence", 0), reverse=True)[:5]
                point["relations"] = relations
                
                point["related_points"] = [r.get("target_id") for r in relations 
                                         if r.get("target_id")]
            else:
                point["relations"] = []
                point["related_points"] = []
        
        return knowledge_points
    
    def process_knowledge_file(self, input_json_path: str, output_json_path: str = None) -> str:
        if not os.path.exists(input_json_path):
            raise FileNotFoundError(f"输入文件不存在: {input_json_path}")
        
        if not output_json_path:
            input_dir = os.path.dirname(input_json_path)
            input_filename = os.path.basename(input_json_path)
            name, ext = os.path.splitext(input_filename)
            output_json_path = os.path.join(input_dir, f"{name}_graph{ext}")
        
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "knowledge_points" not in data:
            raise ValueError("输入文件格式错误，缺少 'knowledge_points' 字段")
        
        knowledge_points = data["knowledge_points"]
        
        enhanced_points = self.build_knowledge_graph(knowledge_points)
        
        result = {"knowledge_points": enhanced_points}
        
        output_dir = os.path.dirname(output_json_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return output_json_path


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='基于LLM构建知识图谱')
    parser.add_argument('--input', '-i', required=True, help='输入的知识点JSON文件')
    parser.add_argument('--output', '-o', help='输出的知识图谱JSON文件')
    parser.add_argument('--api_key', '-k', required=True, help='LLM API Key')
    parser.add_argument('--base_url', '-u', default="https://api.openai.com/v1", help='API Base URL')
    parser.add_argument('--model', '-m', default="deepseek-chat", help='模型名称')
    
    args = parser.parse_args()
    
    builder = LLMKnowledgeGraphBuilder(
        api_key=args.api_key,
        base_url=args.base_url,
        model_name=args.model
    )
    
    try:
        output_path = builder.process_knowledge_file(args.input, args.output)
        print(f"知识图谱构建完成: {output_path}")
    except Exception as e:
        print(f"构建知识图谱时出错: {e}")


if __name__ == "__main__":
    main() 