import argparse
import os
import json
from src.knowledge_extractor import KnowledgeExtractor

def refine_existing_knowledge(input_json_path, output_json_path, api_key, base_url, model_name, use_local_model, local_model_url, batch_size=5):
    if not os.path.exists(input_json_path):
        print(f"错误: 输入文件不存在: {input_json_path}")
        return

    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            knowledge_json_str = f.read()
            try:
                data = json.loads(knowledge_json_str)
                if "knowledge_points" not in data:
                    print(f"错误: 输入的JSON文件 {input_json_path} 缺少 'knowledge_points' 键。")
                    return
            except json.JSONDecodeError as e:
                print(f"错误: 输入文件 {input_json_path} 不是有效的JSON: {e}")
                return

    except Exception as e:
        print(f"读取输入文件 {input_json_path} 时出错: {e}")
        return

    print(f"加载文件 {input_json_path} 进行精炼...")

    extractor = KnowledgeExtractor(
        api_key=api_key,
        use_local_model=use_local_model,
        local_model_url=local_model_url,
        base_url=base_url,
        model_name=model_name
    )

    if not knowledge_json_str or knowledge_json_str == json.dumps({"knowledge_points": []}):
        print("输入的知识点JSON为空或仅包含空列表，无需精炼。")
        if output_json_path:
            try:
                with open(output_json_path, 'w', encoding='utf-8') as f:
                    f.write(json.dumps({"knowledge_points": []}, ensure_ascii=False, indent=2))
                print(f"空的知识点列表已保存到: {output_json_path}")
            except Exception as e:
                print(f"保存空的知识点列表到 {output_json_path} 失败: {e}")
        return
        
    print("\n" + "=" * 50)
    print("开始精炼知识点...")
    print("=" * 50)
    
    all_knowledge_points = data["knowledge_points"]
    total_points = len(all_knowledge_points)
    total_batches = (total_points + batch_size - 1) // batch_size
    all_refined_points = []
    
    print(f"知识点总数: {total_points}, 将分 {total_batches} 批进行精炼，每批 {batch_size} 个知识点")
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, total_points)
        batch_points = all_knowledge_points[start_idx:end_idx]
        
        print(f"正在精炼第 {batch_idx + 1}/{total_batches} 批知识点 (点 {start_idx + 1} 至 {end_idx})")
        
        batch_json = {"knowledge_points": batch_points}
        batch_json_str = json.dumps(batch_json, ensure_ascii=False)
        
        try:
            refined_batch_json_str = extractor.refine_knowledge_points(batch_json_str)
            refined_batch_data = json.loads(refined_batch_json_str)
            
            if "knowledge_points" in refined_batch_data and isinstance(refined_batch_data["knowledge_points"], list):
                all_refined_points.extend(refined_batch_data["knowledge_points"])
                print(f"第 {batch_idx + 1} 批精炼完成，获得 {len(refined_batch_data['knowledge_points'])} 个精炼后的知识点")
            else:
                print(f"第 {batch_idx + 1} 批精炼结果格式不正确，将使用原始知识点")
                all_refined_points.extend(batch_points)
        except Exception as e:
            print(f"精炼第 {batch_idx + 1} 批知识点时出错: {e}，将使用原始知识点")
            all_refined_points.extend(batch_points)
    
    final_points = []
    id_mapping = {}
    
    for i, point in enumerate(all_refined_points):
        original_id = point.get("id", "")
        new_id = f"kp{i+1}"
        point["id"] = new_id
        if original_id:
            id_mapping[original_id] = new_id
        final_points.append(point)
    
    for point in final_points:
        if "related_points" in point and isinstance(point["related_points"], list):
            updated_related = []
            for rel_id in point["related_points"]:
                if rel_id in id_mapping:
                    updated_related.append(id_mapping[rel_id])
                elif rel_id in [p["id"] for p in final_points]:
                    updated_related.append(rel_id)
            point["related_points"] = list(set(updated_related))[:3]  
        else:
            point["related_points"] = []
    
    final_result = {"knowledge_points": final_points}
    refined_knowledge_json_str = json.dumps(final_result, ensure_ascii=False, indent=2)

    if not final_points:
        print("精炼后没有有效的知识点，或精炼过程未能返回有效结果。")
    else:
        print(f"知识点精炼完成，共 {len(final_points)} 个精炼后的知识点。")

    output_dir = os.path.dirname(output_json_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"已创建输出目录: {output_dir}")
    
    with open(output_json_path, 'w', encoding='utf-8') as f:
        f.write(refined_knowledge_json_str)
    print(f"精炼后的知识点已成功保存到: {output_json_path}")


def main():
    parser = argparse.ArgumentParser(description='对已提取的知识点JSON文件进行精炼')
    # parser.add_argument('--input', '-i', type=str, required=True, help='输入的知识点JSON文件路径')
    # parser.add_argument('--output', '-o', type=str, help='精炼后知识点JSON文件的输出路径。如果未提供，将尝试在输入文件名后追加 "_refined".')
    # parser.add_argument('--api_key', '-k', type=str, help='API密钥 (可选, 会尝试从环境变量 OPENAI_API_KEY 读取)')
    # parser.add_argument('--base_url', '-b', type=str, help='API基础URL (可选, 会尝试从环境变量 OPENAI_BASE_URL 读取)')
    # parser.add_argument('--model_name', '-n', type=str, default='gpt-3.5-turbo', help='模型名称 (例如 gpt-3.5-turbo, deepseek-chat)')
    # parser.add_argument('--local_model', '-l', action='store_true', help='是否使用本地部署的大模型')
    # parser.add_argument('--model_url', '-u', type=str, help='本地模型API地址 (如果使用本地模型)')
    # parser.add_argument('--batch_size', '-bs', type=int, default=5, help='每批处理的知识点数量')
    
    args = parser.parse_args()
    args.input = r"E:/pdf教材知识整理/pdf2md/output/数学问题v1.0-_knowledge_points.json"
    args.output = r"E:/pdf教材知识整理/pdf2md/output/数学问题v1.0-_refined_knowledge_points.json"
    args.api_key = "sk-c4db4d3fce94444e95ef3a235a12cc3a"
    args.base_url = "https://api.deepseek.com"
    args.model_name = "deepseek-chat"
    args.local_model = False
    args.model_url = None
    args.batch_size = 5

    output_json_path = args.output
    if not output_json_path:
        input_dir = os.path.dirname(args.input)
        input_filename = os.path.basename(args.input)
        name, ext = os.path.splitext(input_filename)
        output_json_path = os.path.join(input_dir, f"{name}_refined{ext}")
        print(f"未提供输出路径，将使用默认输出路径: {output_json_path}")

    refine_existing_knowledge(
        args.input,
        output_json_path,
        args.api_key,
        args.base_url,
        args.model_name,
        args.local_model,
        args.model_url,
        args.batch_size
    )

if __name__ == "__main__":
    main() 