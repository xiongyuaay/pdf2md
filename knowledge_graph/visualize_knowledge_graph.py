import os
import json
import argparse
from pyvis.network import Network
import random

def get_node_color(node_type):
    """根据知识点类型返回节点颜色"""
    color_map = {
        "concept": "#3498db",  # 蓝色
        "principle": "#e74c3c",  # 红色
        "formula": "#9b59b6",  # 紫色
        "method": "#2ecc71",  # 绿色
        "fact": "#f39c12",  # 橙色
        "unknown": "#95a5a6"  # 灰色
    }
    return color_map.get(node_type, color_map["unknown"])

def get_edge_color(relation_type=None):
    """根据关系类型返回边的颜色"""
    color_map = {
        "前提条件": "#e74c3c",  # 红色
        "后续知识": "#2ecc71",  # 绿色
        "部分-整体": "#3498db",  # 蓝色
        "相似概念": "#9b59b6",  # 紫色
        "互补概念": "#f39c12",  # 橙色
        None: "#95a5a6"  # 灰色(默认)
    }
    return color_map.get(relation_type, color_map[None])

def visualize_knowledge_graph(input_json_path, output_html_path=None, title="知识图谱可视化"):
    """将知识图谱JSON文件可视化为交互式HTML网络图"""
    if not os.path.exists(input_json_path):
        print(f"错误: 输入文件不存在: {input_json_path}")
        return None
    
    if not output_html_path:
        input_dir = os.path.dirname(input_json_path)
        input_filename = os.path.basename(input_json_path)
        name, _ = os.path.splitext(input_filename)
        output_html_path = os.path.join(input_dir, f"{name}_visualization.html")
    
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "knowledge_points" not in data or not isinstance(data["knowledge_points"], list):
            print(f"错误: 输入的JSON文件 {input_json_path} 格式不正确，缺少 'knowledge_points' 列表")
            return None
        
        knowledge_points = data["knowledge_points"]
        
        net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="#333333")
        net.heading = title
        
        for point in knowledge_points:
            node_id = point["id"]
            node_label = point["title"]
            node_type = point.get("type", "unknown")
            node_color = get_node_color(node_type)
            
            node_title = f"<b>{point['title']}</b><br>"
            node_title += f"类型: {node_type}<br>"
            node_title += f"重要性: {point.get('importance', 'N/A')}<br>"
            node_title += f"内容: {point.get('content', '无内容')[:150]}..."
            
            net.add_node(node_id, label=node_label, title=node_title, color=node_color)
        
        edges_added = set()
        
        for point in knowledge_points:
            source_id = point["id"]
            
            if "relations" in point and isinstance(point["relations"], list):
                for relation in point["relations"]:
                    target_id = relation.get("id")
                    relation_type = relation.get("relation_type")
                    
                    if target_id and (source_id, target_id) not in edges_added:
                        edge_color = get_edge_color(relation_type)
                        edge_title = relation_type if relation_type else "相关"
                        
                        net.add_edge(source_id, target_id, title=edge_title, color=edge_color)
                        edges_added.add((source_id, target_id))
                        edges_added.add((target_id, source_id))  # 避免反向重复
            
            elif "related_points" in point and isinstance(point["related_points"], list):
                for target_id in point["related_points"]:
                    if (source_id, target_id) not in edges_added:
                        net.add_edge(source_id, target_id, title="相关", color=get_edge_color())
                        edges_added.add((source_id, target_id))
                        edges_added.add((target_id, source_id))  # 避免反向重复
        
        net.show_buttons(filter_=['physics'])
        net.set_options("""
        var options = {
            "nodes": {
                "shape": "dot",
                "size": 20,
                "font": {
                    "size": 14,
                    "face": "Arial, sans-serif, 'Microsoft YaHei', 'PingFang SC', 'Heiti TC', 'SimHei'"
                },
                "borderWidth": 2
            },
            "edges": {
                "width": 2,
                "smooth": {
                    "type": "continuous"
                }
            },
            "physics": {
                "stabilization": false,
                "barnesHut": {
                    "gravitationalConstant": -20000,
                    "springLength": 150,
                    "springConstant": 0.08
                },
                "minVelocity": 0.75
            }
        }
        """)
        
        output_dir = os.path.dirname(output_html_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        net.save_graph(output_html_path)
        print(f"可视化图谱已保存到: {output_html_path}")
        return output_html_path
        
    except Exception as e:
        print(f"可视化知识图谱时出错: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='可视化知识图谱为交互式HTML网络图')
    parser.add_argument('--input', '-i', type=str, help='输入的知识图谱JSON文件路径')
    parser.add_argument('--output', '-o', type=str, help='输出的HTML文件路径，默认为输入文件名加上"_visualization"后缀')
    parser.add_argument('--title', '-t', type=str, default='知识图谱可视化', help='可视化图的标题')
    
    args = parser.parse_args()
    
    if not args.input:
        args.input = r"E:/pdf教材知识整理/pdf2md/output/数学问题v1.0-_refined_knowledge_points_graph.json"
        print(f"未提供输入路径，使用默认路径: {args.input}")
    
    visualize_knowledge_graph(args.input, args.output, args.title)

if __name__ == "__main__":
    main() 