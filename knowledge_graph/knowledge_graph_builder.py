import os
import json
import numpy as np
from tqdm import tqdm
import time
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


class KnowledgeGraphBuilder:
    def __init__(self, embedding_model_name=None):
        load_dotenv()
        
        self.embedding_model_name = embedding_model_name or "paraphrase-multilingual-MiniLM-L12-v2"
        

        try:
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
        except OSError as e:
            if "Use `from_tf=True`" in str(e):
                print(f"检测到TensorFlow模型，尝试使用from_tf=True参数加载...")
                self.embedding_model = SentenceTransformer(
                    self.embedding_model_name, 
                    from_tf=True
                )
            else:
                print(f"加载模型失败，尝试使用备用模型...")
                self.embedding_model_name = "paraphrase-multilingual-MiniLM-L12-v2"
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                
        print(f"已成功初始化本地嵌入模型: {self.embedding_model_name}")

    
    def get_embedding(self, text):
        """获取文本的嵌入向量"""
        if not self.embedding_model:
            raise RuntimeError("嵌入模型未初始化")
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 使用sentence-transformers生成嵌入向量
                embedding = self.embedding_model.encode(text)
                return embedding
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise e
                print(f"获取嵌入向量失败 (尝试 {retry_count}/{max_retries}): {e}. 重试中...")
                time.sleep(2 ** retry_count)
    
    def cosine_similarity(self, vec1, vec2):
        """计算两个向量的余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm_a = np.linalg.norm(vec1)
        norm_b = np.linalg.norm(vec2)
        
        if norm_a == 0 or norm_b == 0:
            return 0
        
        return dot_product / (norm_a * norm_b)
    
    def build_knowledge_graph(self, knowledge_points, similarity_threshold=0.7, max_relations=5, batch_size=50):
        if not self.embedding_model:
            print("警告: 嵌入模型未初始化，无法构建知识图谱")
            return knowledge_points
        
        if not knowledge_points:
            print("知识点列表为空，无需构建知识图谱")
            return knowledge_points
        
        total_points = len(knowledge_points)
        print(f"开始为{total_points}个知识点构建知识图谱...")
        
        print("正在生成知识点的嵌入向量...")
        embeddings = {}
        
        batches = [knowledge_points[i:i+batch_size] for i in range(0, total_points, batch_size)]
        
        for batch_idx, batch in enumerate(batches):
            print(f"处理第 {batch_idx+1}/{len(batches)} 批知识点的嵌入向量")
            
            for point in tqdm(batch, desc=f"Batch {batch_idx+1}"):
                text = f"{point['title']}: {point['content']}"
                try:
                    embedding = self.get_embedding(text)
                    embeddings[point['id']] = embedding
                except Exception as e:
                    print(f"获取知识点 {point['id']} 的嵌入向量时出错: {e}")
        
        print("计算知识点间的相似度并构建关联...")
        for i, point in tqdm(enumerate(knowledge_points), total=total_points, desc="构建关联"):
            if point['id'] not in embeddings:
                continue
                
            similarities = []
            for other_point in knowledge_points:
                if point['id'] != other_point['id'] and other_point['id'] in embeddings:
                    similarity = self.cosine_similarity(
                        embeddings[point['id']], 
                        embeddings[other_point['id']]
                    )
                    if similarity > similarity_threshold:
                        similarities.append((other_point['id'], similarity))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            related_ids = [item[0] for item in similarities[:max_relations]]
            
            point['related_points'] = related_ids
        
        print("知识图谱构建完成！")
        return knowledge_points
    
    def process_knowledge_file(self, input_json_path, output_json_path=None, similarity_threshold=0.7, max_relations=5, enhance_with_llm=False):
        if enhance_with_llm:
            print("警告: 当前版本不支持使用大语言模型增强关系，已忽略此参数")
            
        if not os.path.exists(input_json_path):
            print(f"错误: 输入文件不存在: {input_json_path}")
            return None
            
        if not output_json_path:
            input_dir = os.path.dirname(input_json_path)
            input_filename = os.path.basename(input_json_path)
            name, ext = os.path.splitext(input_filename)
            output_json_path = os.path.join(input_dir, f"{name}_graph{ext}")
        
        try:
            with open(input_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if "knowledge_points" not in data or not isinstance(data["knowledge_points"], list):
                print(f"错误: 输入的JSON文件 {input_json_path} 格式不正确，缺少 'knowledge_points' 列表")
                return None
                
            knowledge_points = data["knowledge_points"]
            
            knowledge_points = self.build_knowledge_graph(
                knowledge_points, 
                similarity_threshold=similarity_threshold,
                max_relations=max_relations
            )
            
            result = {"knowledge_points": knowledge_points}
            
            output_dir = os.path.dirname(output_json_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
            print(f"知识图谱已保存到: {output_json_path}")
            return output_json_path
            
        except Exception as e:
            print(f"处理知识点文件时出错: {e}")
            return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='构建基于Sentence Transformers的知识图谱')
    parser.add_argument('--input', '-i', type=str, required=True, help='输入的知识点JSON文件路径')
    parser.add_argument('--output', '-o', type=str, help='输出的知识图谱JSON文件路径')
    parser.add_argument('--threshold', '-t', type=float, default=0.7, help='相似度阈值 (默认: 0.7)')
    parser.add_argument('--max_relations', '-m', type=int, default=5, help='每个知识点最多关联数量 (默认: 5)')
    parser.add_argument('--embedding_model', '-e', type=str, default='paraphrase-multilingual-MiniLM-L12-v2', 
                        help='Sentence Transformers嵌入模型名称 (默认: paraphrase-multilingual-MiniLM-L12-v2)')
    
    args = parser.parse_args()
    
    builder = KnowledgeGraphBuilder(
        embedding_model_name=args.embedding_model
    )
    
    builder.process_knowledge_file(
        args.input,
        args.output,
        similarity_threshold=args.threshold,
        max_relations=args.max_relations
    )


if __name__ == "__main__":
    main() 