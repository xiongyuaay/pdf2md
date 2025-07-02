import os
import json
import random
import numpy as np
from typing import Dict, List, Tuple, Optional

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from matplotlib.patches import FancyBboxPatch
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import plotly.graph_objects as go
    import plotly.offline as pyo
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False


class EnhancedKnowledgeGraphVisualizer:
    def __init__(self):
        self.color_map = {
            "concept": "#3498db",
            "principle": "#e74c3c",
            "formula": "#9b59b6",
            "method": "#2ecc71",
            "fact": "#f39c12",
            "unknown": "#95a5a6"
        }
        
        self.relation_colors = {
            "前提条件": "#e74c3c",
            "后续知识": "#2ecc71",
            "部分-整体": "#3498db",
            "相似概念": "#9b59b6",
            "互补概念": "#f39c12",
            None: "#95a5a6"
        }
    
    def _setup_chinese_font(self):
        if not MATPLOTLIB_AVAILABLE:
            return
            
        try:
            import platform
            system = platform.system()
            
            if system == "Windows":
                fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'KaiTi']
            elif system == "Darwin":
                fonts = ['Heiti TC', 'PingFang SC', 'STSong', 'Songti SC', 'Arial Unicode MS']
            else:
                fonts = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'Noto Sans CJK SC', 'DejaVu Sans']
            
            font_set = False
            for font in fonts:
                try:
                    plt.rcParams['font.sans-serif'] = [font] + plt.rcParams['font.sans-serif']
                    plt.rcParams['axes.unicode_minus'] = False
                    
                    test_fig, test_ax = plt.subplots(figsize=(1, 1))
                    test_ax.text(0.5, 0.5, '测试中文', fontsize=12)
                    plt.close(test_fig)
                    
                    font_set = True
                    break
                except Exception:
                    continue
            
            if not font_set:
                plt.rcParams['axes.unicode_minus'] = False
                
        except Exception:
            plt.rcParams['axes.unicode_minus'] = False
    
    def load_knowledge_data(self, json_path: str) -> Tuple[List[Dict], List[Dict]]:
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"文件不存在: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "knowledge_points" not in data:
            raise ValueError("数据格式错误，缺少 'knowledge_points' 字段")
        
        knowledge_points = data["knowledge_points"]
        
        nodes = []
        for point in knowledge_points:
            nodes.append({
                "id": point.get("id", ""),
                "title": point.get("title", ""),
                "content": point.get("content", ""),
                "type": point.get("type", "unknown"),
                "importance": point.get("importance", 0.5),
                "color": self.color_map.get(point.get("type", "unknown"), self.color_map["unknown"])
            })
        
        edges = []
        edge_set = set()
        
        for point in knowledge_points:
            source_id = point.get("id")
            
            if "relations" in point and isinstance(point["relations"], list):
                for relation in point["relations"]:
                    target_id = relation.get("target_id")
                    relation_type = relation.get("relation_type")
                    confidence = relation.get("confidence", 0.5)
                    
                    if target_id and (source_id, target_id) not in edge_set:
                        edges.append({
                            "source": source_id,
                            "target": target_id,
                            "relation_type": relation_type,
                            "confidence": confidence,
                            "color": self.relation_colors.get(relation_type, self.relation_colors[None])
                        })
                        edge_set.add((source_id, target_id))
                        edge_set.add((target_id, source_id))
            
            elif "related_points" in point and isinstance(point["related_points"], list):
                for target_id in point["related_points"]:
                    if target_id and (source_id, target_id) not in edge_set:
                        edges.append({
                            "source": source_id,
                            "target": target_id,
                            "relation_type": "相关",
                            "confidence": 0.5,
                            "color": self.relation_colors[None]
                        })
                        edge_set.add((source_id, target_id))
                        edge_set.add((target_id, source_id))
        
        return nodes, edges
    
    def create_simple_html_visualization(self, json_path: str, output_path: str = None, title: str = "知识图谱") -> str:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        knowledge_points = data.get("knowledge_points", [])
        
        if not output_path:
            input_dir = os.path.dirname(json_path)
            input_filename = os.path.basename(json_path)
            name, _ = os.path.splitext(input_filename)
            output_path = os.path.join(input_dir, f"{name}_simple.html")
        total_points = len(knowledge_points)
        total_relations = sum(len(point.get("relations", [])) for point in knowledge_points)
        
        type_counts = {}
        for point in knowledge_points:
            point_type = point.get("type", "unknown")
            type_counts[point_type] = type_counts.get(point_type, 0) + 1
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
        }}
        
        .stats {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        
        .stat-item {{
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            display: block;
        }}
        
        .node-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .node-card {{
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
            background: white;
        }}
        
        .node-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .node-header {{
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .node-type-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            color: white;
            font-size: 0.8em;
            font-weight: bold;
            margin-right: 10px;
        }}
        
        .node-title {{
            font-size: 1.2em;
            font-weight: bold;
            color: #2c3e50;
            flex-grow: 1;
        }}
        
        .importance-bar {{
            width: 100%;
            height: 6px;
            background-color: #ecf0f1;
            border-radius: 3px;
            margin: 10px 0;
            overflow: hidden;
        }}
        
        .importance-fill {{
            height: 100%;
            background: linear-gradient(90deg, #f39c12, #e74c3c);
            border-radius: 3px;
            transition: width 0.3s ease;
        }}
        
        .node-content {{
            color: #7f8c8d;
            font-size: 0.9em;
            line-height: 1.5;
            max-height: 100px;
            overflow: hidden;
            position: relative;
        }}
        
        .relations-section {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #ecf0f1;
        }}
        
        .relation-item {{
            background: #f8f9fa;
            padding: 8px 12px;
            border-radius: 5px;
            margin: 5px 0;
            border-left: 4px solid #3498db;
            font-size: 0.9em;
        }}
        
        .relation-type {{
            font-weight: bold;
            color: #2980b9;
        }}
        
        .confidence {{
            float: right;
            color: #7f8c8d;
            font-size: 0.8em;
        }}
        
        .no-relations {{
            color: #bdc3c7;
            font-style: italic;
            text-align: center;
            padding: 10px;
        }}
        
        .section-title {{
            color: #2c3e50;
            font-size: 1.5em;
            margin: 30px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #ecf0f1;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        
        <div class="stats">
            <div class="stat-item">
                <span class="stat-number">{total_points}</span>
                <span>知识点总数</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">{total_relations}</span>
                <span>关系总数</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">{len(type_counts)}</span>
                <span>知识点类型</span>
            </div>
        </div>
        
        <h2 class="section-title">知识点详情</h2>
        <div class="node-grid">"""
        
        # 添加每个知识点
        for point in knowledge_points:
            point_type = point.get("type", "unknown")
            color = self.color_map.get(point_type, self.color_map["unknown"])
            importance = point.get("importance", 0.5)
            content = point.get("content", "无内容")
            title = point.get('title', '无标题')
            
            if len(content) > 200:
                content = content[:200] + "..."
            
            def html_escape(text):
                if not isinstance(text, str):
                    text = str(text)
                return (text.replace('&', '&amp;')
                           .replace('<', '&lt;')
                           .replace('>', '&gt;')
                           .replace('"', '&quot;')
                           .replace("'", '&#x27;'))
            escaped_title = html_escape(title)
            escaped_content = html_escape(content)
            escaped_point_type = html_escape(point_type)
            
            html_content += f"""
                <div class="node-card">
                    <div class="node-header">
                        <span class="node-type-badge" style="background-color: {color};">{escaped_point_type}</span>
                        <span class="node-title">{escaped_title}</span>
                    </div>
                    
                    <div class="importance-bar">
                        <div class="importance-fill" style="width: {importance * 100}%;"></div>
                    </div>
                    <div style="font-size: 0.8em; color: #7f8c8d; margin-bottom: 10px;">
                        重要性: {importance:.2f}
                    </div>
                    
                    <div class="node-content">
                        {escaped_content}
                    </div>
                    
                    <div class="relations-section">
                        <strong>关系:</strong>"""
            
            relations = point.get("relations", [])
            if relations:
                for relation in relations:
                    target_id = relation.get("target_id", "")
                    relation_type = relation.get("relation_type", "未知关系")
                    confidence = relation.get("confidence", 0.0)
                    
                    target_title = target_id
                    for target_point in knowledge_points:
                        if target_point.get("id") == target_id:
                            target_title = target_point.get("title", target_id)
                            break
                    escaped_relation_type = html_escape(relation_type)
                    escaped_target_title = html_escape(target_title)
                    
                    html_content += f"""
                        <div class="relation-item">
                            <span class="relation-type">{escaped_relation_type}</span> → {escaped_target_title}
                            <span class="confidence">置信度: {confidence:.2f}</span>
                        </div>"""
            else:
                html_content += """
                        <div class="no-relations">暂无关系</div>"""
            
            html_content += """
                    </div>
                </div>"""
        
        html_content += """
        </div>
    </div>
</body>
</html>"""
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path
    
    def visualize_with_pyvis(self, json_path: str, output_path: str = None, title: str = "知识图谱") -> Optional[str]:
        if not PYVIS_AVAILABLE:
            return None
        
        try:
            nodes, edges = self.load_knowledge_data(json_path)
            
            if not nodes:
                return None
            
            if not output_path:
                input_dir = os.path.dirname(json_path)
                input_filename = os.path.basename(json_path)
                name, _ = os.path.splitext(input_filename)
                output_path = os.path.join(input_dir, f"{name}_pyvis.html")
            net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="#333333")
            
            for node in nodes:
                size = max(15, int(node["importance"] * 30))
                hover_title = f"<b>{node['title']}</b><br>"
                hover_title += f"类型: {node['type']}<br>"
                hover_title += f"重要性: {node['importance']:.2f}<br>"
                content_preview = node['content'][:200] + "..." if len(node['content']) > 200 else node['content']
                hover_title += f"内容: {content_preview}"
                
                net.add_node(
                    node["id"], 
                    label=node["title"], 
                    title=hover_title,
                    color=node["color"],
                    size=size
                )
            
            for edge in edges:
                net.add_edge(
                    edge["source"], 
                    edge["target"],
                    title=f"{edge['relation_type']} (置信度: {edge['confidence']:.2f})",
                    color=edge["color"],
                    width=max(1, int(edge["confidence"] * 3))
                )
            net.show_buttons(filter_=['physics'])
            net.set_options("""
            var options = {
                "nodes": {
                    "shape": "dot",
                    "font": {"size": 12, "face": "Arial, sans-serif, 'Microsoft YaHei', 'PingFang SC', 'Heiti TC'"},
                    "borderWidth": 2,
                    "shadow": true
                },
                "edges": {
                    "smooth": {"type": "continuous"},
                    "arrows": {"to": {"enabled": true, "scaleFactor": 0.5}},
                    "shadow": true
                },
                "physics": {
                    "stabilization": {"iterations": 200},
                    "barnesHut": {
                        "gravitationalConstant": -15000,
                        "springLength": 200,
                        "springConstant": 0.05
                    }
                },
                "configure": {
                    "enabled": false
                }
            }
            """)
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            net.save_graph(output_path)
            
            self._fix_pyvis_html_paths(output_path)
            
            return output_path
            
        except Exception:
            return None
    
    def _fix_pyvis_html_paths(self, html_path: str):
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            html_dir = os.path.dirname(html_path)
            project_root = os.path.abspath(".")
            rel_path = os.path.relpath(project_root, html_dir)
            if rel_path == ".":
                lib_path = "lib/bindings/utils.js"
            else:
                lib_path = os.path.join(rel_path, "lib", "bindings", "utils.js").replace("\\", "/")
            
            content = content.replace('src="lib/bindings/utils.js"', f'src="{lib_path}"')
            title_pattern = r'<center>\s*<h1>(.*?)</h1>\s*</center>'
            import re
            title_matches = re.findall(title_pattern, content, re.IGNORECASE | re.DOTALL)
            title_elements = re.findall(r'<center>\s*<h1>.*?</h1>\s*</center>', content, re.IGNORECASE | re.DOTALL)
            
            for title_element in title_elements:
                content = content.replace(title_element, '', 1)
            main_title = '<center><h1>知识图谱可视化</h1></center>\n'
            content = content.replace('<body>', f'<body>\n{main_title}')
            
            legend_css = """
            <style type="text/css">
            #legend {
                position: fixed;
                top: 20px;
                right: 20px;
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid #d0d7de;
                border-radius: 8px;
                padding: 16px;
                font-family: Arial, sans-serif, 'Microsoft YaHei', 'PingFang SC', 'Heiti TC';
                font-size: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                z-index: 1000;
                max-width: 250px;
            }
            
            #legend h3 {
                margin: 0 0 12px 0;
                font-size: 14px;
                font-weight: 600;
                color: #374151;
                border-bottom: 1px solid #e5e7eb;
                padding-bottom: 8px;
            }
            
            .legend-section {
                margin-bottom: 16px;
            }
            
            .legend-section:last-child {
                margin-bottom: 0;
            }
            
            .legend-item {
                display: flex;
                align-items: center;
                margin-bottom: 6px;
                font-size: 11px;
            }
            
            .legend-item:last-child {
                margin-bottom: 0;
            }
            
            .node-indicator {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
                border: 1px solid #ccc;
                flex-shrink: 0;
            }
            
            .edge-indicator {
                width: 20px;
                height: 2px;
                margin-right: 8px;
                flex-shrink: 0;
            }
            
            .legend-label {
                color: #374151;
                line-height: 1.2;
            }
            
            .legend-subtitle {
                font-weight: 600;
                color: #6b7280;
                margin-bottom: 8px;
                font-size: 11px;
            }
            </style>
            """
            
            content = content.replace('</head>', legend_css + '\n</head>')
            legend_html = """
            <div id="legend">
                <h3>图例</h3>
                
                <div class="legend-section">
                    <div class="legend-subtitle">节点类型</div>
                    <div class="legend-item">
                        <div class="node-indicator" style="background-color: #3498db;"></div>
                        <span class="legend-label">概念 (concept)</span>
                    </div>
                    <div class="legend-item">
                        <div class="node-indicator" style="background-color: #e74c3c;"></div>
                        <span class="legend-label">原理 (principle)</span>
                    </div>
                    <div class="legend-item">
                        <div class="node-indicator" style="background-color: #2ecc71;"></div>
                        <span class="legend-label">方法 (method)</span>
                    </div>
                    <div class="legend-item">
                        <div class="node-indicator" style="background-color: #f39c12;"></div>
                        <span class="legend-label">事实 (fact)</span>
                    </div>
                    <div class="legend-item">
                        <div class="node-indicator" style="background-color: #e67e22;"></div>
                        <span class="legend-label">公式 (formula)</span>
                    </div>
                </div>
                
                <div class="legend-section">
                    <div class="legend-subtitle">关系类型</div>
                    <div class="legend-item">
                        <div class="edge-indicator" style="background-color: #e74c3c;"></div>
                        <span class="legend-label">前提条件</span>
                    </div>
                    <div class="legend-item">
                        <div class="edge-indicator" style="background-color: #2ecc71;"></div>
                        <span class="legend-label">后续知识</span>
                    </div>
                    <div class="legend-item">
                        <div class="edge-indicator" style="background-color: #3498db;"></div>
                        <span class="legend-label">部分-整体</span>
                    </div>
                    <div class="legend-item">
                        <div class="edge-indicator" style="background-color: #9b59b6;"></div>
                        <span class="legend-label">相似概念</span>
                    </div>
                    <div class="legend-item">
                        <div class="edge-indicator" style="background-color: #f39c12;"></div>
                        <span class="legend-label">互补概念</span>
                    </div>
                    <div class="legend-item">
                        <div class="edge-indicator" style="background-color: #95a5a6;"></div>
                        <span class="legend-label">一般相关</span>
                    </div>
                </div>
                
                <div class="legend-section">
                    <div class="legend-subtitle">图例说明</div>
                    <div style="font-size: 10px; color: #6b7280; line-height: 1.3;">
                        • 节点大小表示重要性<br>
                        • 箭头粗细表示置信度<br>
                        • 可拖拽节点调整布局
                    </div>
                </div>
            </div>
            """
            
            content = content.replace('<body>', '<body>\n' + legend_html)
            lines = content.split('\n')
            fixed_lines = []
            for line in lines:
                if 'options.configure["container"]' not in line:
                    fixed_lines.append(line)
                else:
                    fixed_lines.append('                  // Configure options disabled')
            
            content = '\n'.join(fixed_lines)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
        except Exception:
            pass
    
    def visualize_with_matplotlib(self, json_path: str, output_path: str = None, title: str = "知识图谱") -> Optional[str]:
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        try:
            self._setup_chinese_font()
            
            nodes, edges = self.load_knowledge_data(json_path)
            
            if not nodes:
                return None
            
            if not output_path:
                input_dir = os.path.dirname(json_path)
                input_filename = os.path.basename(json_path)
                name, _ = os.path.splitext(input_filename)
                output_path = os.path.join(input_dir, f"{name}_matplotlib.png")
            fig, ax = plt.subplots(figsize=(16, 12))
            
            # 如果有networkx，使用更好的布局
            if NETWORKX_AVAILABLE and edges:
                G = nx.Graph()
                for node in nodes:
                    G.add_node(node["id"], **node)
                for edge in edges:
                    G.add_edge(edge["source"], edge["target"], **edge)
                
                # 使用spring布局
                pos = nx.spring_layout(G, k=3, iterations=50)
            else:
                # 简单的圆形布局
                n_nodes = len(nodes)
                pos = {}
                for i, node in enumerate(nodes):
                    angle = 2 * np.pi * i / n_nodes
                    pos[node["id"]] = (np.cos(angle), np.sin(angle))
            
            # 绘制边
            for edge in edges:
                if edge["source"] in pos and edge["target"] in pos:
                    x1, y1 = pos[edge["source"]]
                    x2, y2 = pos[edge["target"]]
                    
                    ax.plot([x1, x2], [y1, y2], 
                           color=edge["color"], 
                           alpha=0.6, 
                           linewidth=edge["confidence"] * 2,
                           zorder=1)
            
            # 绘制节点
            for node in nodes:
                if node["id"] in pos:
                    x, y = pos[node["id"]]
                    size = node["importance"] * 500 + 100
                    
                    # 绘制节点
                    ax.scatter(x, y, s=size, c=node["color"], alpha=0.8, zorder=2, edgecolors='black', linewidth=1)
                    
                    # 添加标签
                    ax.annotate(node["title"], (x, y), xytext=(5, 5), textcoords='offset points',
                               fontsize=8, ha='left', va='bottom', 
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
            
            # 设置图形属性
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_aspect('equal')
            ax.axis('off')
            
            # 添加图例
            legend_elements = []
            for node_type, color in self.color_map.items():
                if any(node["type"] == node_type for node in nodes):
                    legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                                    markerfacecolor=color, markersize=10, label=node_type))
            
            if legend_elements:
                ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1))
            
            plt.tight_layout()
            
            # 保存文件
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"matplotlib可视化已保存到: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"matplotlib可视化失败: {e}")
            return None
    
    def visualize_with_plotly(self, json_path: str, output_path: str = None, title: str = "知识图谱") -> Optional[str]:
        """使用plotly创建交互式图"""
        if not PLOTLY_AVAILABLE:
            print("错误: plotly未安装，无法创建plotly可视化")
            return None
        
        try:
            nodes, edges = self.load_knowledge_data(json_path)
            
            if not nodes:
                print("警告: 没有找到知识点数据")
                return None
            
            # 确定输出路径
            if not output_path:
                input_dir = os.path.dirname(json_path)
                input_filename = os.path.basename(json_path)
                name, _ = os.path.splitext(input_filename)
                output_path = os.path.join(input_dir, f"{name}_plotly.html")
            
            # 创建布局
            if NETWORKX_AVAILABLE and edges:
                G = nx.Graph()
                for node in nodes:
                    G.add_node(node["id"], **node)
                for edge in edges:
                    G.add_edge(edge["source"], edge["target"], **edge)
                pos = nx.spring_layout(G, k=3, iterations=50)
            else:
                # 简单布局
                n_nodes = len(nodes)
                pos = {}
                for i, node in enumerate(nodes):
                    angle = 2 * np.pi * i / n_nodes
                    pos[node["id"]] = (np.cos(angle), np.sin(angle))
            
            # 准备边的坐标
            edge_x = []
            edge_y = []
            edge_info = []
            
            for edge in edges:
                if edge["source"] in pos and edge["target"] in pos:
                    x0, y0 = pos[edge["source"]]
                    x1, y1 = pos[edge["target"]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])
                    edge_info.append(f"{edge['relation_type']} (置信度: {edge['confidence']:.2f})")
            
            # 创建边的轨迹
            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=2, color='#888'),
                hoverinfo='none',
                mode='lines'
            )
            
            # 准备节点数据
            node_x = []
            node_y = []
            node_text = []
            node_color = []
            node_size = []
            node_info = []
            
            for node in nodes:
                if node["id"] in pos:
                    x, y = pos[node["id"]]
                    node_x.append(x)
                    node_y.append(y)
                    node_text.append(node["title"])
                    node_color.append(node["color"])
                    node_size.append(node["importance"] * 30 + 10)
                    
                    # 悬停信息
                    hover_text = f"<b>{node['title']}</b><br>"
                    hover_text += f"类型: {node['type']}<br>"
                    hover_text += f"重要性: {node['importance']:.2f}<br>"
                    content_preview = node['content'][:200] + "..." if len(node['content']) > 200 else node['content']
                    hover_text += f"内容: {content_preview}"
                    node_info.append(hover_text)
            
            # 创建节点轨迹
            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='markers+text',
                hoverinfo='text',
                text=node_text,
                hovertext=node_info,
                textposition="middle center",
                marker=dict(
                    size=node_size,
                    color=node_color,
                    line=dict(width=2, color='black')
                )
            )
            
            # 创建图形
            fig = go.Figure(data=[edge_trace, node_trace],
                           layout=go.Layout(
                               title=dict(
                                   text=title,
                                   font=dict(size=16, family="Arial, sans-serif")
                               ),
                               showlegend=False,
                               hovermode='closest',
                               margin=dict(b=20,l=5,r=5,t=40),
                               annotations=[dict(
                                   text="",
                                   showarrow=False,
                                   xref="paper", yref="paper",
                                   x=0.005, y=-0.002,
                                   xanchor='left', yanchor='bottom',
                                   font=dict(size=12, family="Arial, sans-serif")
                               )],
                               xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                               yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                               plot_bgcolor='white',
                               font=dict(family="Arial, sans-serif")
                           ))
            
            # 保存文件
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            pyo.plot(fig, filename=output_path, auto_open=False)
            
            print(f"plotly可视化已保存到: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"plotly可视化失败: {e}")
            return None
    
    def create_all_visualizations(self, json_path: str, output_dir: str = None, title: str = "知识图谱") -> Dict[str, str]:
        """创建所有可用的可视化"""
        results = {}
        
        if not output_dir:
            output_dir = os.path.dirname(json_path)
        
        input_filename = os.path.basename(json_path)
        name, _ = os.path.splitext(input_filename)
        
        # pyvis可视化
        if PYVIS_AVAILABLE:
            pyvis_path = os.path.join(output_dir, f"{name}_pyvis.html")
            result = self.visualize_with_pyvis(json_path, pyvis_path, title)
            if result:
                results["pyvis"] = result
        
        # matplotlib可视化
        if MATPLOTLIB_AVAILABLE:
            matplotlib_path = os.path.join(output_dir, f"{name}_matplotlib.png")
            result = self.visualize_with_matplotlib(json_path, matplotlib_path, title)
            if result:
                results["matplotlib"] = result
        
        # plotly可视化
        if PLOTLY_AVAILABLE:
            plotly_path = os.path.join(output_dir, f"{name}_plotly.html")
            result = self.visualize_with_plotly(json_path, plotly_path, title)
            if result:
                results["plotly"] = result
        
        return results


# 兼容性函数，替代原来的visualize_knowledge_graph
def visualize_knowledge_graph(input_json_path: str, output_html_path: str = None, title: str = "知识图谱可视化") -> Optional[str]:
    """兼容性函数，优先使用pyvis，失败时使用其他方法"""
    visualizer = EnhancedKnowledgeGraphVisualizer()
    
    # 首先尝试pyvis
    result = visualizer.visualize_with_pyvis(input_json_path, output_html_path, title)
    if result:
        return result
    
    # pyvis失败，尝试plotly
    if output_html_path:
        plotly_path = output_html_path.replace('.html', '_plotly.html')
    else:
        input_dir = os.path.dirname(input_json_path)
        input_filename = os.path.basename(input_json_path)
        name, _ = os.path.splitext(input_filename)
        plotly_path = os.path.join(input_dir, f"{name}_plotly.html")
    
    result = visualizer.visualize_with_plotly(input_json_path, plotly_path, title)
    if result:
        return result
    
    # 都失败了，创建静态图
    if output_html_path:
        matplotlib_path = output_html_path.replace('.html', '_matplotlib.png')
    else:
        input_dir = os.path.dirname(input_json_path)
        input_filename = os.path.basename(input_json_path)
        name, _ = os.path.splitext(input_filename)
        matplotlib_path = os.path.join(input_dir, f"{name}_matplotlib.png")
    
    return visualizer.visualize_with_matplotlib(input_json_path, matplotlib_path, title)


def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='增强的知识图谱可视化工具')
    parser.add_argument('--input', '-i', required=True, help='输入的知识图谱JSON文件')
    parser.add_argument('--output_dir', '-o', help='输出目录，默认为输入文件所在目录')
    parser.add_argument('--title', '-t', default='知识图谱可视化', help='图表标题')
    parser.add_argument('--method', '-m', choices=['pyvis', 'matplotlib', 'plotly', 'all'], 
                       default='all', help='可视化方法')
    
    args = parser.parse_args()
    
    visualizer = EnhancedKnowledgeGraphVisualizer()
    
    if args.method == 'all':
        results = visualizer.create_all_visualizations(args.input, args.output_dir, args.title)
        print(f"创建了 {len(results)} 个可视化文件:")
        for method, path in results.items():
            print(f"  {method}: {path}")
    else:
        if args.method == 'pyvis':
            result = visualizer.visualize_with_pyvis(args.input, None, args.title)
        elif args.method == 'matplotlib':
            result = visualizer.visualize_with_matplotlib(args.input, None, args.title)
        elif args.method == 'plotly':
            result = visualizer.visualize_with_plotly(args.input, None, args.title)
        
        if result:
            print(f"可视化完成: {result}")
        else:
            print("可视化失败")


if __name__ == "__main__":
    main() 