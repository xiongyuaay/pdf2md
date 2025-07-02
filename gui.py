import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QFileDialog, QListWidget, QTextEdit, QLabel, QLineEdit, QMessageBox,
    QSplitter, QInputDialog, QProgressDialog, QFrame, QSlider, QSpinBox,
    QGroupBox, QGridLayout, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor

from src.knowledge_extractor import KnowledgeExtractor
from src.pdf_converter_image import PDFConverter
from knowledge_graph.llm_knowledge_graph_builder import LLMKnowledgeGraphBuilder
from knowledge_graph.visualize_knowledge_graph import visualize_knowledge_graph
from knowledge_graph.enhanced_visualizer import EnhancedKnowledgeGraphVisualizer
class PDFExtractionWorker(QThread):
    finished = pyqtSignal(object, str) 
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, pdf_path, output_dir, extractor_config):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.extractor_config = extractor_config

    def run(self):
        if not PDFConverter or not KnowledgeExtractor:
            self.error.emit("PDFConverter或KnowledgeExtractor模块未成功导入，无法执行提取。")
            return

        try:
            base_name = os.path.basename(self.pdf_path)
            file_name_without_ext = os.path.splitext(base_name)[0]
            
            md_conversion_output_path = os.path.join(self.output_dir, f"{file_name_without_ext}_converted.md")
            knowledge_output_base_name = f"{file_name_without_ext}_knowledge_points"
            knowledge_output_base = os.path.join(self.output_dir, knowledge_output_base_name)

            self.progress.emit("步骤1/3: PDF转换为Markdown...")
            converter = PDFConverter(self.pdf_path)
            converted_md_path = converter.process_pdf(md_conversion_output_path)
            
            if not converted_md_path:
                self.error.emit("PDF内容提取或Markdown转换失败。")
                return
            self.progress.emit(f"PDF已成功转换为Markdown")
            
            self.progress.emit("步骤2/3: 从Markdown提取知识点...")
            extractor = KnowledgeExtractor(**self.extractor_config)
            
            with open(converted_md_path, 'r', encoding='utf-8') as f:
                md_content_for_extraction = f.read()
                
            if not md_content_for_extraction.strip():
                self.error.emit("转换后的Markdown文件内容为空，无法提取知识点。")
                return
                
            knowledge_json_str = extractor.extract_knowledge_points(md_content_for_extraction)
            
            if not knowledge_json_str or knowledge_json_str == json.dumps({"knowledge_points": []}):
                self.error.emit("未能从文档中提取到初步知识点。")
                return

            self.progress.emit("步骤3/3: 保存知识点...")
            saved_json_path = extractor.save_knowledge_points(knowledge_json_str, knowledge_output_base)
            
            if saved_json_path:
                with open(saved_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.finished.emit(data.get("knowledge_points", []), saved_json_path)
            else:
                self.error.emit("知识点JSON文件保存失败。")
        except Exception as e:
            self.error.emit(f"提取过程中发生错误: {str(e)}")


class KnowledgeGraphWorker(QThread):
    finished = pyqtSignal(str, object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, json_path, api_key, base_url, model_name, visualization_method="pyvis", relations_data=None):
        super().__init__()
        self.json_path = json_path
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.visualization_method = visualization_method
        self.relations_data = relations_data

    def run(self):
        try:
            self.progress.emit("正在构建知识图谱...")
            
            # 生成知识图谱JSON
            input_dir = os.path.dirname(self.json_path)
            input_filename = os.path.basename(self.json_path)
            name, ext = os.path.splitext(input_filename)
            graph_json_path = os.path.join(input_dir, f"{name}_graph{ext}")
            
            if self.relations_data:
                self.progress.emit("使用预加载的关系数据构建知识图谱...")
                
                # 加载原始知识点数据
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
                
                knowledge_points = original_data.get("knowledge_points", [])
                
                # 为每个知识点添加关系数据
                kp_dict = {kp.get("id"): kp for kp in knowledge_points}
                
                for relation in self.relations_data:
                    source_id = relation.get("source_id")
                    target_id = relation.get("target_id")
                    
                    if source_id in kp_dict:
                        if "related_points" not in kp_dict[source_id]:
                            kp_dict[source_id]["related_points"] = []
                        if target_id not in kp_dict[source_id]["related_points"]:
                            kp_dict[source_id]["related_points"].append(target_id)
                        
                        if "relations" not in kp_dict[source_id]:
                            kp_dict[source_id]["relations"] = []
                        kp_dict[source_id]["relations"].append(relation)
                graph_data = {"knowledge_points": list(kp_dict.values())}
                with open(graph_json_path, 'w', encoding='utf-8') as f:
                    json.dump(graph_data, f, ensure_ascii=False, indent=2)
                    
            else:
                self.progress.emit("正在构建知识图谱...")
                builder = LLMKnowledgeGraphBuilder(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model_name=self.model_name
                )
                
                self.progress.emit("分析知识点关系...")
                graph_json_path = builder.process_knowledge_file(self.json_path, graph_json_path)
            
            self.progress.emit("生成知识图谱可视化...")
            visualizer = EnhancedKnowledgeGraphVisualizer()
            
            if self.visualization_method == "所有方式":
                self.progress.emit("创建所有可视化方式...")
                visualization_results = visualizer.create_all_visualizations(
                    graph_json_path, 
                    title="知识图谱可视化"
                )
                self.finished.emit(graph_json_path, visualization_results)
                
            elif self.visualization_method == "交互式网络图 (pyvis)":
                result_path = visualizer.visualize_with_pyvis(
                    graph_json_path, title="知识图谱可视化"
                )
                self.finished.emit(graph_json_path, result_path)
                
            elif self.visualization_method == "简化HTML表格":
                result_path = visualizer.create_simple_html_visualization(
                    graph_json_path, title="知识图谱可视化"
                )
                self.finished.emit(graph_json_path, result_path)
                
            elif self.visualization_method == "静态网络图 (matplotlib)":
                result_path = visualizer.visualize_with_matplotlib(
                    graph_json_path, title="知识图谱可视化"
                )
                self.finished.emit(graph_json_path, result_path)
                
            elif self.visualization_method == "交互式图表 (plotly)":
                result_path = visualizer.visualize_with_plotly(
                    graph_json_path, title="知识图谱可视化"
                )
                self.finished.emit(graph_json_path, result_path)
            else:
                visualization_html_path = visualize_knowledge_graph(
                    graph_json_path, title="知识图谱可视化"
                )
                self.finished.emit(graph_json_path, visualization_html_path)
            
        except Exception as e:
            self.error.emit(f"构建知识图谱时出错: {str(e)}")



class KnowledgeRefineryApp(QWidget):
    def __init__(self):
        super().__init__()
        self.knowledge_points = []
        self.current_file_path = ""
        self.extractor = None
        self.pdf_extraction_thread = None
        self.knowledge_graph_thread = None
        self.progress_dialog = None
        self.relations_data = []
        self.relations_file_path = ""
        self.init_ui()
        self.init_extractor()

    def init_ui(self):
        self.setWindowTitle('知识点处理工具')
        screen = QApplication.desktop().screenGeometry()
        self.window_width = min(1000, int(screen.width() * 0.8))
        self.window_height = min(700, int(screen.height() * 0.8))
        self.setGeometry(100, 100, self.window_width, self.window_height)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #fafafa;
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 13px;
                color: #333;
            }
            
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                color: #24292f;
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: 500;
                min-height: 18px;
            }
            
            QPushButton:hover {
                background-color: #f3f4f6;
                border-color: #8c959f;
            }
            
            QPushButton:pressed {
                background-color: #e5e5e5;
            }
            
            QPushButton:disabled {
                background-color: #f6f8fa;
                border-color: #d0d7de;
                color: #8c959f;
            }
            
            QPushButton#primaryBtn {
                background-color: #2563eb;
                border-color: #2563eb;
                color: white;
            }
            
            QPushButton#primaryBtn:hover {
                background-color: #1d4ed8;
            }
            
            QPushButton#dangerBtn {
                background-color: #dc2626;
                border-color: #dc2626;
                color: white;
            }
            
            QPushButton#dangerBtn:hover {
                background-color: #b91c1c;
            }
            
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 4px;
                selection-background-color: #dbeafe;
            }
            
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            
            QListWidget::item:selected {
                background-color: #dbeafe;
                color: #1e40af;
            }
            
            QListWidget::item:hover {
                background-color: #f3f4f6;
            }
            
            QTextEdit, QLineEdit {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 8px;
                color: #24292f;
            }
            
            QTextEdit:focus, QLineEdit:focus {
                border-color: #2563eb;
                outline: none;
            }
            
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 8px;
                color: #24292f;
                min-width: 120px;
            }
            
            QComboBox:focus {
                border-color: #2563eb;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #6b7280;
                margin-right: 8px;
            }
            
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
                color: #24292f;
            }
            
            QComboBox QAbstractItemView::item {
                padding: 6px 12px;
                border: none;
            }
            
            QComboBox QAbstractItemView::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
            
            QComboBox QAbstractItemView::item:hover {
                background-color: #dbeafe;
                color: #1d4ed8;
            }
            
            QLabel {
                color: #374151;
                font-weight: 500;
            }
            
            QGroupBox {
                font-weight: 600;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                margin: 4px 0;
                padding-top: 10px;
                background-color: #ffffff;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #374151;
                background-color: #ffffff;
                font-size: 12px;
            }
            
            QSlider::groove:horizontal {
                border: 1px solid #d0d7de;
                height: 4px;
                background: #e5e7eb;
                border-radius: 2px;
            }
            
            QSlider::handle:horizontal {
                background: #2563eb;
                border: 1px solid #1d4ed8;
                width: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            
            QSlider::sub-page:horizontal {
                background: #2563eb;
                border-radius: 2px;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        toolbar_group = QGroupBox("配置与操作")
        toolbar_layout = QGridLayout()
        toolbar_layout.setSpacing(10)
        toolbar_layout.setColumnMinimumWidth(0, 70)
        
        toolbar_layout.addWidget(QLabel("API Key:"), 0, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("输入您的API Key")
        toolbar_layout.addWidget(self.api_key_input, 0, 1, 1, 3)
        
        toolbar_layout.addWidget(QLabel("Base URL:"), 0, 4)
        self.base_url_input = QComboBox()
        self.base_url_input.setEditable(True)
        self.base_url_input.setMinimumWidth(180)
        self.base_url_input.addItems([
            "https://api.openai.com/v1",
            "https://api.deepseek.com",
            "https://api.moonshot.cn/v1",
        ])
        self.base_url_input.setCurrentText("https://api.openai.com/v1")
        toolbar_layout.addWidget(self.base_url_input, 0, 5, 1, 2)
        
        toolbar_layout.addWidget(QLabel("模型:"), 0, 7)
        self.model_input = QComboBox()
        self.model_input.setEditable(True)
        self.model_input.setMinimumWidth(150)
        
        self.model_presets = {
            "https://api.openai.com/v1": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "https://api.deepseek.com": ["deepseek-chat", "deepseek-coder"],
            "https://api.moonshot.cn/v1": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        }
        
        toolbar_layout.addWidget(self.model_input, 0, 8)
        
        self.update_model_options()
        
        toolbar_layout.addWidget(QLabel("操作:"), 1, 0)
        
        self.extract_pdf_btn = QPushButton('从PDF提取')
        self.extract_pdf_btn.setObjectName("primaryBtn")
        self.extract_pdf_btn.clicked.connect(self.start_pdf_extraction)
        toolbar_layout.addWidget(self.extract_pdf_btn, 1, 1)
        
        self.load_json_btn = QPushButton('加载JSON')
        self.load_json_btn.clicked.connect(self.load_knowledge_json)
        self.load_relations_btn = QPushButton('导入关系')
        self.load_relations_btn.clicked.connect(self.load_relations_json)
        self.load_relations_btn.setEnabled(False)  # 需要先加载知识点
        toolbar_layout.addWidget(self.load_json_btn, 1, 2)
        toolbar_layout.addWidget(self.load_relations_btn, 1, 3)
        
        self.save_btn = QPushButton('保存')
        self.save_btn.clicked.connect(self.save_knowledge_json)
        self.save_btn.setEnabled(False)
        toolbar_layout.addWidget(self.save_btn, 1, 4)
        
        toolbar_layout.setColumnStretch(9, 1)
        
        toolbar_group.setLayout(toolbar_layout)
        main_layout.addWidget(toolbar_group)
        
        self.current_file_label = QLabel("当前文件: 未加载")
        self.current_file_label.setStyleSheet("color: #6b7280; font-size: 11px; margin: 2px 0;")
        main_layout.addWidget(self.current_file_label)
        
        self.relations_status_label = QLabel("关系数据: 未导入")
        self.relations_status_label.setStyleSheet("color: #6b7280; font-size: 11px; margin: 2px 0;")
        main_layout.addWidget(self.relations_status_label)

        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setHandleWidth(2)
        content_splitter.setChildrenCollapsible(False)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 8, 0)
        
        list_group = QGroupBox("知识点列表")
        list_group_layout = QVBoxLayout()
        list_group_layout.setContentsMargins(8, 8, 8, 8)
        
        self.knowledge_list_widget = QListWidget()
        self.knowledge_list_widget.itemClicked.connect(self.display_knowledge_point)
        list_group_layout.addWidget(self.knowledge_list_widget)
        
        list_group.setLayout(list_group_layout)
        left_layout.addWidget(list_group)
        
        left_panel.setLayout(left_layout)
        content_splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(8, 0, 0, 0)
        
        detail_title = QLabel("知识点详情")
        detail_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #374151; margin-bottom: 6px;")
        right_layout.addWidget(detail_title)
        
        info_group = QGroupBox("基本信息")
        info_layout = QGridLayout()
        info_layout.setSpacing(8)
        info_layout.setColumnMinimumWidth(0, 50)
        
        info_layout.addWidget(QLabel("ID:"), 0, 0)
        self.kp_id_display = QLineEdit()
        self.kp_id_display.setReadOnly(True)
        info_layout.addWidget(self.kp_id_display, 0, 1, 1, 3)
        
        info_layout.addWidget(QLabel("标题:"), 1, 0)
        self.kp_title_display = QLineEdit()
        self.kp_title_display.setReadOnly(True)
        info_layout.addWidget(self.kp_title_display, 1, 1, 1, 3)
        
        info_layout.addWidget(QLabel("类型:"), 2, 0)
        self.kp_type_display = QLabel("未知")
        self.kp_type_display.setStyleSheet("color: #2563eb; font-weight: 500; padding: 4px 8px; background: #eff6ff; border-radius: 4px; min-width: 80px;")
        self.kp_type_display.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.kp_type_display, 2, 1)
        
        info_layout.addWidget(QLabel("重要性:"), 2, 2)
        self.kp_importance_display = QLabel("未知")
        self.kp_importance_display.setStyleSheet("color: #6b7280; font-weight: 500; padding: 4px 8px; background: #f9fafb; border-radius: 4px; min-width: 100px;")
        self.kp_importance_display.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.kp_importance_display, 2, 3)
        
        info_group.setLayout(info_layout)
        right_layout.addWidget(info_group)

        content_group = QGroupBox("知识点内容")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(8, 8, 8, 8)
        
        self.kp_content_display = QTextEdit()
        self.kp_content_display.setReadOnly(False)
        self.kp_content_display.setMinimumHeight(120)
        content_layout.addWidget(self.kp_content_display)
        
        content_group.setLayout(content_layout)
        right_layout.addWidget(content_group)
        
        # 操作区域
        action_group = QGroupBox("操作")
        action_layout = QVBoxLayout()
        action_layout.setContentsMargins(8, 8, 8, 8)
        
        # 第一行：基本操作按钮
        basic_action_layout = QHBoxLayout()
        
        self.refine_btn = QPushButton('精炼')
        self.refine_btn.setObjectName("primaryBtn")
        self.refine_btn.clicked.connect(self.refine_current_knowledge_point)
        self.refine_btn.setEnabled(False)
        
        self.delete_selected_btn = QPushButton('删除')
        self.delete_selected_btn.setObjectName("dangerBtn")
        self.delete_selected_btn.clicked.connect(self.delete_selected_knowledge_point)
        self.delete_selected_btn.setEnabled(False)
        
        basic_action_layout.addWidget(self.refine_btn)
        basic_action_layout.addWidget(self.delete_selected_btn)
        basic_action_layout.addStretch()
        
        action_layout.addLayout(basic_action_layout)
        
        # 第二行：知识图谱构建和可视化选项
        graph_layout = QHBoxLayout()
        
        self.build_graph_btn = QPushButton('构建知识图谱')
        self.build_graph_btn.setObjectName("primaryBtn")
        self.build_graph_btn.clicked.connect(self.build_knowledge_graph)
        self.build_graph_btn.setEnabled(False)
        
        # 可视化方式选择
        viz_label = QLabel("可视化:")
        viz_label.setStyleSheet("color: #374151; font-weight: 500;")
        
        self.visualization_combo = QComboBox()
        self.visualization_combo.addItems([
            "交互式网络图 (pyvis)",
            "简化HTML表格",
            "静态网络图 (matplotlib)", 
            "交互式图表 (plotly)",
            "所有方式"
        ])
        self.visualization_combo.setCurrentText("交互式网络图 (pyvis)")
        self.visualization_combo.setMinimumWidth(150)
        
        graph_layout.addWidget(self.build_graph_btn)
        graph_layout.addWidget(viz_label)
        graph_layout.addWidget(self.visualization_combo)
        graph_layout.addStretch()
        
        action_layout.addLayout(graph_layout)
        action_group.setLayout(action_layout)
        right_layout.addWidget(action_group)
        right_panel.setLayout(right_layout)
        
        content_splitter.addWidget(right_panel)
        # 根据窗口宽度动态调整分割比例
        left_width = min(320, int(self.window_width * 0.35))
        right_width = self.window_width - left_width - 50  # 减去间距
        content_splitter.setSizes([left_width, right_width])
        
        main_layout.addWidget(content_splitter, 1)
        self.setLayout(main_layout)
        
        # 初始化模型选项
        self.update_model_options()
        
        # 所有控件创建完成后，连接信号
        self.setup_signal_connections()

    def setup_signal_connections(self):
        """设置所有信号连接"""
        # API配置信号
        self.api_key_input.textChanged.connect(self.on_api_config_changed)
        self.base_url_input.currentTextChanged.connect(self.on_api_config_changed)
        self.base_url_input.currentTextChanged.connect(self.update_model_options)
        self.model_input.currentTextChanged.connect(self.on_api_config_changed)
        
        # 初始化extractor
        self.init_extractor()

    def update_model_options(self):
        """根据选择的Base URL更新可用的模型选项"""
        base_url = self.base_url_input.currentText().strip()
        current_model = self.model_input.currentText()
        
        # 使用预设模型映射
        models = self.model_presets.get(base_url, ["gpt-4", "deepseek-chat"])
        
        # 更新下拉框选项
        self.model_input.clear()
        self.model_input.addItems(models)
        
        # 尝试保持之前选择的模型，如果不存在则选择第一个
        if current_model in models:
            self.model_input.setCurrentText(current_model)
        else:
            self.model_input.setCurrentText(models[0])
    
    def on_api_config_changed(self):
        """API配置改变时的处理"""
        self.init_extractor()
        if hasattr(self, 'refine_btn') and hasattr(self, 'knowledge_list_widget'):
            if self.knowledge_list_widget.currentItem() and self.api_key_input.text() and self.extractor:
                self.refine_btn.setEnabled(True)
            else:
                self.refine_btn.setEnabled(False)
        
        if hasattr(self, 'build_graph_btn'):
            self.update_graph_button_state()

    def init_extractor(self):
        """初始化知识提取器"""
        if not KnowledgeExtractor:
            if hasattr(self, 'refine_btn'):
                self.refine_btn.setEnabled(False)
            if hasattr(self, 'extract_pdf_btn'):
                self.extract_pdf_btn.setEnabled(False if not PDFConverter else True)
            return False

        api_key = self.api_key_input.text().strip()
        base_url = self.base_url_input.currentText().strip() or None
        model_name = self.model_input.currentText().strip() or "gpt-4"

        if not api_key:
            self.extractor = None
            if hasattr(self, 'refine_btn'):
                self.refine_btn.setEnabled(False)
            return False

        try:
            current_config = {
                'api_key': api_key,
                'base_url': base_url,
                'model_name': model_name,
                'use_local_model': False,
                'local_model_url': None
            }
            if self.extractor and getattr(self.extractor, '_config', None) == current_config:
                 return True

            self.extractor = KnowledgeExtractor(**current_config)
            self.extractor._config = current_config
            if hasattr(self, 'refine_btn') and hasattr(self, 'knowledge_list_widget') and self.knowledge_list_widget.currentItem():
                self.refine_btn.setEnabled(True)
            return True
        except Exception as e:
            self.extractor = None
            if hasattr(self, 'refine_btn'):
                self.refine_btn.setEnabled(False)
            return False

    def start_pdf_extraction(self):
        if not PDFConverter or not KnowledgeExtractor:
            QMessageBox.critical(self, "模块缺失", "PDFConverter 或 KnowledgeExtractor 模块未导入，无法执行此操作。")
            return

        if not self.init_extractor():
            QMessageBox.warning(self, "API配置问题", "请先正确配置API Key等信息，再进行提取操作。")
            return

        pdf_file_path, _ = QFileDialog.getOpenFileName(self, "选择PDF文件进行提取", "", "PDF Files (*.pdf)")
        if not pdf_file_path:
            return

        output_dir = QFileDialog.getExistingDirectory(self, "选择输出目录 (存放MD和JSON文件)", os.path.dirname(pdf_file_path) or os.getcwd())
        if not output_dir:
            output_dir = os.path.dirname(pdf_file_path) or os.getcwd()
            QMessageBox.information(self, "提示", f"未选择输出目录，将使用: {output_dir}")

        self.progress_dialog = QProgressDialog("正在处理PDF...", "取消", 0, 0, self)
        self.progress_dialog.setWindowTitle("PDF提取进度")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(True)
        self.progress_dialog.show()
        QApplication.processEvents()

        extractor_config = self.extractor._config if self.extractor else self.get_current_extractor_config()
        self.pdf_extraction_thread = PDFExtractionWorker(pdf_file_path, output_dir, extractor_config)
        self.pdf_extraction_thread.finished.connect(self.on_pdf_extraction_finished)
        self.pdf_extraction_thread.error.connect(self.on_pdf_extraction_error)
        self.pdf_extraction_thread.progress.connect(self.update_extraction_progress)
        self.pdf_extraction_thread.start()
        
        self.extract_pdf_btn.setEnabled(False)
        self.load_json_btn.setEnabled(False)
        self.save_btn.setEnabled(False)

    def get_current_extractor_config(self):
        return {
            'api_key': self.api_key_input.text().strip(),
            'base_url': self.base_url_input.currentText().strip() or None,
            'model_name': self.model_input.currentText().strip() or "gpt-4",
            'use_local_model': False,
            'local_model_url': None
        }

    def update_extraction_progress(self, message):
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)
            QApplication.processEvents()

    def on_pdf_extraction_finished(self, extracted_points, saved_json_path):
        if self.progress_dialog:
            self.progress_dialog.close()
        QApplication.restoreOverrideCursor()

        if extracted_points is not None:
            self.knowledge_points = extracted_points
            self.current_file_path = saved_json_path if saved_json_path else ""
            self.current_file_label.setText(f"当前文件: {os.path.basename(self.current_file_path)}" if self.current_file_path else "新提取的知识点 (未保存)")
            self.populate_knowledge_list()
            self.save_btn.setEnabled(bool(self.knowledge_points))
            
            # 启用导入关系按钮
            self.load_relations_btn.setEnabled(True)
            
            # 重置关系数据状态
            self.relations_data = []
            self.relations_file_path = ""
            self.relations_status_label.setText("关系数据: 未导入")
            self.relations_status_label.setStyleSheet("color: #6b7280; font-size: 11px; margin: 2px 0;")
            
            # 清空详情显示
            self.kp_id_display.clear()
            self.kp_title_display.clear()
            self.kp_content_display.clear()
            self.kp_type_display.setText("未知")
            self.kp_type_display.setStyleSheet("color: #6b7280; background: #f9fafb; font-weight: 500; padding: 4px 8px; border-radius: 4px;")
            self.kp_importance_display.setText("未知")
            self.kp_importance_display.setStyleSheet("color: #6b7280; background: #f9fafb; font-weight: 500; padding: 4px 8px; border-radius: 4px;")
            
            # 重置按钮状态
            self.refine_btn.setEnabled(False)
            self.delete_selected_btn.setEnabled(False)
            self.update_graph_button_state()
            
            QMessageBox.information(self, "提取完成", f"成功提取 {len(extracted_points)} 个知识点。")
        else:
             QMessageBox.warning(self, "提取失败", "未能获得有效的知识点数据。")
        
        self.extract_pdf_btn.setEnabled(True)
        self.load_json_btn.setEnabled(True)

    def on_pdf_extraction_error(self, error_message):
        if self.progress_dialog:
            self.progress_dialog.close()
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(self, "提取失败", f"提取过程出错: {error_message}")
        self.extract_pdf_btn.setEnabled(True)
        self.load_json_btn.setEnabled(True)

    def load_knowledge_json(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "加载知识点JSON文件", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if "knowledge_points" in data and isinstance(data["knowledge_points"], list):
                    self.knowledge_points = data["knowledge_points"]
                    self.current_file_path = file_path
                    self.current_file_label.setText(f"当前文件: {os.path.basename(file_path)}")
                    self.populate_knowledge_list()
                    self.save_btn.setEnabled(True)
                    
                    self.load_relations_btn.setEnabled(True)
                    
                    self.relations_data = []
                    self.relations_file_path = ""
                    self.relations_status_label.setText("关系数据: 未导入")
                    self.relations_status_label.setStyleSheet("color: #6b7280; font-size: 11px; margin: 2px 0;")
                    
                    # 清空详情显示
                    self.kp_id_display.clear()
                    self.kp_title_display.clear()
                    self.kp_content_display.clear()
                    self.kp_type_display.setText("未知")
                    self.kp_type_display.setStyleSheet("color: #6b7280; background: #f9fafb; font-weight: 500; padding: 4px 8px; border-radius: 4px;")
                    self.kp_importance_display.setText("未知")
                    self.kp_importance_display.setStyleSheet("color: #6b7280; background: #f9fafb; font-weight: 500; padding: 4px 8px; border-radius: 4px;")
                    
                    # 重置按钮状态
                    self.refine_btn.setEnabled(False) 
                    self.delete_selected_btn.setEnabled(False)
                    self.update_graph_button_state()
                else:
                    QMessageBox.warning(self, "文件格式错误", "JSON文件必须包含一个名为 'knowledge_points' 的列表。")
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"加载文件时出错: {e}")

    def load_relations_json(self):
        """加载关系JSON文件"""
        if not self.knowledge_points:
            QMessageBox.warning(self, "操作无效", "请先加载知识点JSON文件。")
            return
            
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "加载关系JSON文件", 
            "", 
            "JSON Files (*.json);;All Files (*)", 
            options=options
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if "knowledge_points" in data and isinstance(data["knowledge_points"], list):
                    relations_count = 0
                    self.relations_data = []
                    
                    for kp in data["knowledge_points"]:
                        if "relations" in kp and isinstance(kp["relations"], list):
                            for relation in kp["relations"]:
                                if all(key in relation for key in ["source_id", "target_id", "relation_type"]):
                                    self.relations_data.append(relation)
                                    relations_count += 1
                    
                    if relations_count > 0:
                        self.relations_file_path = file_path
                        self.relations_status_label.setText(
                            f"关系数据: 已导入 {relations_count} 个关系 ({os.path.basename(file_path)})"
                        )
                        self.relations_status_label.setStyleSheet("color: #059669; font-size: 11px; margin: 2px 0;")
                        
                        self.update_graph_button_state()
                        
                        QMessageBox.information(
                            self, 
                            "导入成功", 
                            f"成功导入 {relations_count} 个知识点关系。\n构建知识图谱时将使用这些预定义关系。"
                        )
                    else:
                        QMessageBox.warning(self, "没有关系数据", "选择的文件中没有找到有效的关系数据。")
                        
                else:
                    QMessageBox.warning(self, "文件格式错误", "JSON文件必须包含一个名为 'knowledge_points' 的列表。")
                    
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"加载关系文件时出错: {e}")

    def populate_knowledge_list(self):
        self.knowledge_list_widget.clear()
        for i, point in enumerate(self.knowledge_points):
            title = point.get('title', '未命名知识点')
            kp_id = point.get('id', f'temp_id_{i}')
            importance = point.get('importance', 0)
            kp_type = point.get('type', '未知')
            
            if isinstance(importance, (int, float)):
                importance_text = f"({importance:.2f})"
            else:
                importance_text = ""
            
            type_text = kp_type.upper() if kp_type != '未知' else ''
            list_item_text = f"{kp_id} - {title} {importance_text} {type_text}".strip()
            self.knowledge_list_widget.addItem(list_item_text)

    def display_knowledge_point(self, item):
        selected_index = self.knowledge_list_widget.row(item)
        if 0 <= selected_index < len(self.knowledge_points):
            point_data = self.knowledge_points[selected_index]
            self.kp_id_display.setText(point_data.get("id", "N/A"))
            self.kp_title_display.setText(point_data.get("title", ""))
            self.kp_content_display.setText(point_data.get("content", ""))
            
            kp_type = point_data.get("type", "未知")
            type_styles = {
                'concept': "color: #2563eb; background: #eff6ff;",
                'principle': "color: #7c3aed; background: #f3e8ff;",
                'method': "color: #059669; background: #ecfdf5;",
                'fact': "color: #dc2626; background: #fef2f2;",
                'formula': "color: #ea580c; background: #fff7ed;",
                '未知': "color: #6b7280; background: #f9fafb;"
            }
            style = type_styles.get(kp_type, type_styles['未知'])
            self.kp_type_display.setText(kp_type.upper())
            self.kp_type_display.setStyleSheet(f"{style} font-weight: 500; padding: 4px 8px; border-radius: 4px;")
            
            importance = point_data.get("importance", 0)
            if isinstance(importance, (int, float)):
                if importance >= 0.9:
                    level = "极高"
                    color = "#dc2626"
                    bg_color = "#fef2f2"
                elif importance >= 0.8:
                    level = "高"
                    color = "#ea580c"
                    bg_color = "#fff7ed"
                elif importance >= 0.7:
                    level = "中等"
                    color = "#2563eb"
                    bg_color = "#eff6ff"
                elif importance >= 0.5:
                    level = "一般"
                    color = "#059669"
                    bg_color = "#ecfdf5"
                else:
                    level = "低"
                    color = "#6b7280"
                    bg_color = "#f9fafb"
                    
                self.kp_importance_display.setText(f"{level} ({importance:.2f})")
                self.kp_importance_display.setStyleSheet(f"color: {color}; background: {bg_color}; font-weight: 500; padding: 4px 8px; border-radius: 4px;")
            else:
                self.kp_importance_display.setText("未知")
                self.kp_importance_display.setStyleSheet("color: #6b7280; background: #f9fafb; font-weight: 500; padding: 4px 8px; border-radius: 4px;")
            
            self.delete_selected_btn.setEnabled(True)
            
            if self.api_key_input.text().strip() and self.extractor:
                self.refine_btn.setEnabled(True)

    def get_current_selected_point_index_and_data(self):
        selected_item = self.knowledge_list_widget.currentItem()
        if not selected_item:
            return -1, None
        selected_index = self.knowledge_list_widget.row(selected_item)
        if 0 <= selected_index < len(self.knowledge_points):
            return selected_index, self.knowledge_points[selected_index]
        return -1, None

    def refine_current_knowledge_point(self):
        selected_index, point_to_refine = self.get_current_selected_point_index_and_data()
        if point_to_refine is None:
            QMessageBox.warning(self, "操作无效", "请先选择一个知识点。")
            return

        if not self.extractor:
            if not self.init_extractor():
                QMessageBox.critical(self, "精炼失败", "API配置错误，请检查配置。")
                return
        
        temp_input_json_str = json.dumps({"knowledge_points": [point_to_refine]}, ensure_ascii=False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            refined_json_str = self.extractor.refine_knowledge_points(temp_input_json_str)
            refined_data = json.loads(refined_json_str)
            
            if "knowledge_points" in refined_data and refined_data["knowledge_points"]:
                refined_point = refined_data["knowledge_points"][0]
                self.kp_title_display.setText(refined_point.get("title", ""))
                self.kp_content_display.setText(refined_point.get("content", ""))
                self.knowledge_points[selected_index].update({
                    "title": refined_point.get("title", self.knowledge_points[selected_index].get("title")),
                    "content": refined_point.get("content", self.knowledge_points[selected_index].get("content"))
                })
                self.populate_knowledge_list()
                self.knowledge_list_widget.setCurrentRow(selected_index)
                QMessageBox.information(self, "成功", "知识点已精炼完成。")
            else:
                QMessageBox.warning(self, "精炼失败", "未能获得有效的精炼结果。")
        except Exception as e:
            QMessageBox.critical(self, "精炼失败", f"精炼过程出错: {str(e)}")
        finally:
            QApplication.restoreOverrideCursor()

    def delete_selected_knowledge_point(self):
        selected_index, point_to_delete = self.get_current_selected_point_index_and_data()
        if point_to_delete is None:
            QMessageBox.warning(self, "操作无效", "请先选择一个知识点。")
            return

        reply = QMessageBox.question(
            self, 
            '确认删除', 
            f"确定要删除知识点吗？\n\n{point_to_delete.get('title', '未命名知识点')}",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                del self.knowledge_points[selected_index]
                self.populate_knowledge_list()
                
                # 清空详情显示
                self.kp_id_display.clear()
                self.kp_title_display.clear()
                self.kp_content_display.clear()
                self.kp_type_display.setText("未知")
                self.kp_type_display.setStyleSheet("color: #6b7280; background: #f9fafb; font-weight: 500; padding: 4px 8px; border-radius: 4px;")
                self.kp_importance_display.setText("未知")
                self.kp_importance_display.setStyleSheet("color: #6b7280; background: #f9fafb; font-weight: 500; padding: 4px 8px; border-radius: 4px;")
                
                # 更新按钮状态
                self.refine_btn.setEnabled(False)
                self.delete_selected_btn.setEnabled(False)
                self.save_btn.setEnabled(bool(self.knowledge_points))
                
                # 如果没有知识点了，重置关系数据和按钮状态
                if not self.knowledge_points:
                    self.relations_data = []
                    self.relations_file_path = ""
                    self.relations_status_label.setText("关系数据: 未导入")
                    self.relations_status_label.setStyleSheet("color: #6b7280; font-size: 11px; margin: 2px 0;")
                    self.load_relations_btn.setEnabled(False)
                
                self.update_graph_button_state()
                
                QMessageBox.information(self, "删除成功", f"已删除知识点，剩余 {len(self.knowledge_points)} 个。")
                
            except Exception as e:
                QMessageBox.critical(self, "删除失败", f"删除时出错: {str(e)}")

    def save_knowledge_json(self):
        if not self.current_file_path and not self.knowledge_points:
            QMessageBox.information(self, "无数据保存", "没有加载或提取任何知识点数据可供保存。")
            return

        current_selected_idx, _ = self.get_current_selected_point_index_and_data()
        if current_selected_idx != -1:
            self.knowledge_points[current_selected_idx]['content'] = self.kp_content_display.toPlainText()

        default_filename = "knowledge_points_extracted.json"
        if self.current_file_path:
            default_dir = os.path.dirname(self.current_file_path)
            default_filename = os.path.basename(self.current_file_path) 
        else:
            default_dir = os.getcwd()

        options = QFileDialog.Options()
        file_path_to_save, _ = QFileDialog.getSaveFileName(self, "保存知识点JSON文件", 
                                                        os.path.join(default_dir, default_filename),
                                                        "JSON Files (*.json);;All Files (*)", 
                                                        options=options)
        if not file_path_to_save:
            return

        self.current_file_path = file_path_to_save
        try:
            data_to_save = {"knowledge_points": self.knowledge_points}
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "保存成功", f"已保存到: {os.path.basename(self.current_file_path)}")
            self.current_file_label.setText(f"当前文件: {os.path.basename(self.current_file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存时出错: {str(e)}")

    def closeEvent(self, event):
        if self.pdf_extraction_thread and self.pdf_extraction_thread.isRunning():
            reply = QMessageBox.question(self, '确认退出', 
                                       "PDF提取仍在进行中，确定要退出吗？",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.pdf_extraction_thread.terminate()
                self.pdf_extraction_thread.wait()
                event.accept()
            else:
                event.ignore()
        elif self.knowledge_graph_thread and self.knowledge_graph_thread.isRunning():
            reply = QMessageBox.question(self, '确认退出', 
                                       "知识图谱构建仍在进行中，确定要退出吗？",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.knowledge_graph_thread.terminate()
                self.knowledge_graph_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def update_graph_button_state(self):
        """更新构建知识图谱按钮的状态"""
        if hasattr(self, 'build_graph_btn'):
            has_knowledge_points = bool(self.knowledge_points)
            has_api_key = bool(self.api_key_input.text().strip())
            has_relations_data = bool(self.relations_data)
            
            # 如果有关系数据，则不需要API Key；如果没有关系数据，则需要API Key来生成关系
            self.build_graph_btn.setEnabled(has_knowledge_points and (has_api_key or has_relations_data))

    def build_knowledge_graph(self):
        """构建知识图谱"""
        if not self.knowledge_points:
            QMessageBox.warning(self, "无知识点", "请先提取或加载知识点数据。")
            return

        if not self.api_key_input.text().strip():
            QMessageBox.warning(self, "API配置错误", "请先配置API Key。")
            return

        if not self.current_file_path:
            default_dir = os.getcwd()
            options = QFileDialog.Options()
            temp_path, _ = QFileDialog.getSaveFileName(
                self, 
                "选择知识点文件保存位置", 
                os.path.join(default_dir, "knowledge_points.json"),
                "JSON Files (*.json)", 
                options=options
            )
            if not temp_path:
                return
            
            try:
                data_to_save = {"knowledge_points": self.knowledge_points}
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, ensure_ascii=False, indent=2)
                self.current_file_path = temp_path
                self.current_file_label.setText(f"当前文件: {os.path.basename(self.current_file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存知识点文件时出错: {str(e)}")
                return

        api_key = self.api_key_input.text().strip()
        base_url = self.base_url_input.currentText().strip() or "https://api.openai.com/v1"
        model_name = self.model_input.currentText() or "gpt-4"
        visualization_method = self.visualization_combo.currentText()

        self.knowledge_graph_thread = KnowledgeGraphWorker(
            json_path=self.current_file_path,
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            visualization_method=visualization_method,
            relations_data=self.relations_data if self.relations_data else None
        )

        self.knowledge_graph_thread.finished.connect(self.on_knowledge_graph_finished)
        self.knowledge_graph_thread.error.connect(self.on_knowledge_graph_error)
        self.knowledge_graph_thread.progress.connect(self.update_graph_progress)

        self.progress_dialog = QProgressDialog("正在构建知识图谱...", "取消", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.canceled.connect(self.cancel_graph_building)
        self.progress_dialog.show()

        self.build_graph_btn.setEnabled(False)
        self.extract_pdf_btn.setEnabled(False)

        self.knowledge_graph_thread.start()

    def update_graph_progress(self, message):
        """更新知识图谱构建进度"""
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)

    def on_knowledge_graph_finished(self, graph_json_path, visualization_results):
        """知识图谱构建完成"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        self.build_graph_btn.setEnabled(True)
        self.extract_pdf_btn.setEnabled(True)

        try:
            with open(graph_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "knowledge_points" in data:
                self.knowledge_points = data["knowledge_points"]
                self.populate_knowledge_list()
                
                if isinstance(visualization_results, dict):
                    viz_info = "可视化文件:\n"
                    for method, path in visualization_results.items():
                        viz_info += f"  • {method}: {os.path.basename(path)}\n"
                    
                    reply = QMessageBox.question(
                        self, 
                        "知识图谱构建完成",
                        f"知识图谱已成功构建！\n\n"
                        f"增强后的知识点文件: {os.path.basename(graph_json_path)}\n\n"
                        f"{viz_info}\n"
                        f"是否要打开主要可视化文件查看知识图谱？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        # 优先打开pyvis，然后是plotly，最后是其他
                        import webbrowser
                        main_file = None
                        if "pyvis" in visualization_results:
                            main_file = visualization_results["pyvis"]
                        elif "plotly" in visualization_results:
                            main_file = visualization_results["plotly"]
                        elif visualization_results:
                            main_file = list(visualization_results.values())[0]
                        
                        if main_file:
                            webbrowser.open(f"file://{os.path.abspath(main_file)}")
                else:
                    visualization_html_path = visualization_results
                    
                    reply = QMessageBox.question(
                        self, 
                        "知识图谱构建完成",
                        f"知识图谱已成功构建！\n\n"
                        f"增强后的知识点文件: {os.path.basename(graph_json_path)}\n"
                        f"可视化文件: {os.path.basename(visualization_html_path)}\n\n"
                        f"是否要打开可视化文件查看知识图谱？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        # 在默认浏览器中打开HTML文件
                        import webbrowser
                        webbrowser.open(f"file://{os.path.abspath(visualization_html_path)}")
                    
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"加载增强后的知识点数据时出错: {str(e)}")

    def on_knowledge_graph_error(self, error_message):
        """知识图谱构建出错"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        self.build_graph_btn.setEnabled(True)
        self.extract_pdf_btn.setEnabled(True)

        QMessageBox.critical(self, "知识图谱构建失败", error_message)

    def cancel_graph_building(self):
        """取消知识图谱构建"""
        if self.knowledge_graph_thread and self.knowledge_graph_thread.isRunning():
            self.knowledge_graph_thread.terminate()
            self.knowledge_graph_thread.wait()
        
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        self.build_graph_btn.setEnabled(True)
        self.extract_pdf_btn.setEnabled(True)


if __name__ == '__main__':
    modules_ok = True
    if KnowledgeExtractor is None:
        modules_ok = False
    if PDFConverter is None:
        modules_ok = False

    app = QApplication(sys.argv)
    if not modules_ok:
         QMessageBox.warning(None, "模块缺失", "部分核心模块未能导入，相关功能可能无法使用。")

    ex = KnowledgeRefineryApp()
    ex.show()
    sys.exit(app.exec_()) 