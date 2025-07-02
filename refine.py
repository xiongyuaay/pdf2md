import os
import sys
import json
import argparse
from src.knowledge_extractor import KnowledgeExtractor


def main():
    parser = argparse.ArgumentParser(description='知识点精炼工具 - 优化已提取的知识点')
    parser.add_argument('input_json', help='输入的知识点JSON文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径(可选)')
    parser.add_argument('-k', '--api_key', help='API密钥')
    parser.add_argument('-u', '--base_url', default="https://api.openai.com/v1", help='API基础URL')
    parser.add_argument('-m', '--model', default="gpt-3.5-turbo", help='模型名称')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_json):
        print(f"错误: 输入文件不存在: {args.input_json}")
        sys.exit(1)
    
    try:
        with open(args.input_json, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
    except Exception as e:
        print(f"错误: 无法读取输入文件: {e}")
        sys.exit(1)
    
    if "knowledge_points" not in original_data:
        print("错误: 输入文件格式不正确，缺少 'knowledge_points' 字段")
        sys.exit(1)
    
    original_count = len(original_data["knowledge_points"])
    print(f"原始知识点数量: {original_count}")
    
    # 初始化知识提取器
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("错误: 未提供API密钥")
        sys.exit(1)
    
    extractor = KnowledgeExtractor(
        api_key=api_key,
        base_url=args.base_url,
        model_name=args.model
    )
    
    try:
        print("开始精炼知识点...")
        original_json_str = json.dumps(original_data, ensure_ascii=False, indent=2)
        refined_json_str = extractor.refine_knowledge_points(original_json_str)
        
        refined_data = json.loads(refined_json_str)
        refined_count = len(refined_data.get("knowledge_points", []))
        
        print(f"精炼后知识点数量: {refined_count}")
        print(f"变化: {refined_count - original_count:+d}")
        
        if args.output:
            output_path = args.output
        else:
            input_dir = os.path.dirname(args.input_json)
            input_filename = os.path.basename(args.input_json)
            name, ext = os.path.splitext(input_filename)
            output_path = os.path.join(input_dir, f"{name}_refined{ext}")
        
        # 保存精炼后的结果
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(refined_data, f, ensure_ascii=False, indent=2)
        
        print(f"精炼后的知识点已保存到: {output_path}")
        
        # 生成对比报告
        if refined_count != original_count:
            compare_output = output_path.replace('.json', '_comparison.md')
            generate_comparison_report(original_data, refined_data, compare_output)
            print(f"对比报告已保存到: {compare_output}")
        
    except Exception as e:
        print(f"精炼过程中发生错误: {e}")
        sys.exit(1)


def generate_comparison_report(original_data, refined_data, output_path):
    """生成原始和精炼后知识点的对比报告"""
    original_points = original_data.get("knowledge_points", [])
    refined_points = refined_data.get("knowledge_points", [])
    
    original_map = {point.get("id", ""): point for point in original_points}
    refined_map = {point.get("id", ""): point for point in refined_points}
    
    original_ids = set(original_map.keys())
    refined_ids = set(refined_map.keys())
    
    removed_ids = original_ids - refined_ids
    added_ids = refined_ids - original_ids
    common_ids = original_ids & refined_ids
    
    report = f"""# 知识点精炼对比报告

## 统计信息
- 原始知识点数量: {len(original_points)}
- 精炼后知识点数量: {len(refined_points)}
- 变化: {len(refined_points) - len(original_points):+d}

## 详细变化
- 删除的知识点: {len(removed_ids)}
- 新增的知识点: {len(added_ids)}
- 保留的知识点: {len(common_ids)}

"""
    
    if removed_ids:
        report += "### 被删除的知识点\n\n"
        for point_id in removed_ids:
            point = original_map[point_id]
            title = point.get("title", "无标题")
            report += f"- **{point_id}**: {title}\n"
        report += "\n"
    
    if added_ids:
        report += "### 新增的知识点\n\n"
        for point_id in added_ids:
            point = refined_map[point_id]
            title = point.get("title", "无标题")
            report += f"- **{point_id}**: {title}\n"
        report += "\n"
    
    content_changes = []
    for point_id in common_ids:
        original = original_map[point_id]
        refined = refined_map[point_id]
        
        if original.get("title") != refined.get("title") or original.get("content") != refined.get("content"):
            content_changes.append(point_id)
    
    if content_changes:
        report += f"### 内容有变化的知识点 ({len(content_changes)}个)\n\n"
        for point_id in content_changes[:10]:  # 只显示前10个
            report += f"- **{point_id}**: {refined_map[point_id].get('title', '无标题')}\n"
        if len(content_changes) > 10:
            report += f"- ... 还有 {len(content_changes) - 10} 个知识点有变化\n"
        report += "\n"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)


if __name__ == "__main__":
    main() 