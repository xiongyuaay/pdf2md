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

# 尝试从项目中导入所需模块
try:
    from src.knowledge_extractor import KnowledgeExtractor
    print("KnowledgeExtractor 导入成功")
except ImportError:
    KnowledgeExtractor = None
    print("错误: 无法导入 KnowledgeExtractor。请确保 src/knowledge_extractor.py 存在且路径正确。")

try:
    from src.pdf_converter_image import PDFConverter
    print("PDFConverter 导入成功")
except ImportError:
    PDFConverter = None
    print("错误: 无法导入 PDFConverter。请确保 src/pdf_converter_image.py 存在且路径正确。")


# --- PDF提取工作线程 ---
class PDFExtractionWorker(QThread):
    finished = pyqtSignal(object, str) # 传递结果 (knowledge_points列表或None) 和 最终保存的json路径
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

            self.progress.emit("步骤1/3: PDF转换为Markdown (图像处理)... 这可能需要一些时间。")
            converter = PDFConverter(self.pdf_path)
            converted_md_path = converter.process_pdf(md_conversion_output_path)
            
            if not converted_md_path:
                self.error.emit("PDF内容提取或Markdown转换失败。")
                return
            self.progress.emit(f"PDF已成功转换为Markdown: {converted_md_path}")
            
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
                # 加载刚保存的json，获取knowledge_points列表
                with open(saved_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.finished.emit(data.get("knowledge_points", []), saved_json_path)
            else:
                self.error.emit("知识点JSON文件保存失败。")
        except Exception as e:
            self.error.emit(f"提取过程中发生错误: {str(e)}")


class KnowledgeRefineryApp(QWidget):
    def __init__(self):
        super().__init__()
        self.knowledge_points = []
        self.current_file_path = ""
        self.extractor = None # 用于 KnowledgeExtractor 实例
        self.pdf_extraction_thread = None
        self.progress_dialog = None
        self.init_ui()
        self.init_extractor() # 初始化 extractor 实例，如果API key已提供

    def init_ui(self):
        self.setWindowTitle('知识点处理工具 - PDF2MD Knowledge Refinery')
        self.setGeometry(100, 100, 1000, 700)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #f7f5f3;
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 9pt;
                color: #5a5a5a;
            }
            
            QPushButton {
                background-color: #a8a5a0;
                border: none;
                color: #2c2c2c;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: normal;
                min-height: 16px;
            }
            
            QPushButton:hover {
                background-color: #9b9691;
                color: #1a1a1a;
            }
            
            QPushButton:pressed {
                background-color: #8e8a85;
                color: #000000;
            }
            
            QPushButton:disabled {
                background-color: #d4d1ce;
                color: #9a9a9a;
            }
            
            QPushButton#deleteBtn {
                background-color: #c4a5a0;
                color: #2c2c2c;
            }
            
            QPushButton#deleteBtn:hover {
                background-color: #b89691;
                color: #1a1a1a;
            }
            
            QPushButton#refineBtn {
                background-color: #a0b4c4;
                color: #2c2c2c;
            }
            
            QPushButton#refineBtn:hover {
                background-color: #91a5b8;
                color: #1a1a1a;
            }
            
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #d4d1ce;
                border-radius: 4px;
                padding: 4px;
                selection-background-color: #e8e5e2;
            }
            
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #f0ede9;
                border-radius: 2px;
                margin: 1px 0;
            }
            
            QListWidget::item:selected {
                background-color: #a8a5a0;
                color: white;
            }
            
            QListWidget::item:hover {
                background-color: #f0ede9;
            }
            
            QTextEdit, QLineEdit {
                background-color: #ffffff;
                border: 1px solid #d4d1ce;
                border-radius: 4px;
                padding: 6px;
                color: #5a5a5a;
            }
            
            QTextEdit:focus, QLineEdit:focus {
                border: 1px solid #a8a5a0;
            }
            
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #d4d1ce;
                border-radius: 4px;
                padding: 6px;
                color: #5a5a5a;
                min-width: 100px;
            }
            
            QComboBox:focus {
                border: 1px solid #a8a5a0;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #7a7a7a;
                margin-right: 5px;
            }
            
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #d4d1ce;
                selection-background-color: #e8e5e2;
                color: #5a5a5a;
            }
            
            QLabel {
                color: #5a5a5a;
                font-weight: normal;
                margin: 2px 0;
            }
            
            QGroupBox {
                font-weight: normal;
                border: 1px solid #d4d1ce;
                border-radius: 4px;
                margin: 5px 0;
                padding-top: 10px;
                background-color: #faf9f7;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #7a7a7a;
                background-color: #faf9f7;
                font-size: 9pt;
            }
            
            QSlider::groove:horizontal {
                border: 1px solid #d4d1ce;
                height: 6px;
                background: #e8e5e2;
                margin: 2px 0;
                border-radius: 3px;
            }
            
            QSlider::handle:horizontal {
                background: #a8a5a0;
                border: 1px solid #8e8a85;
                width: 14px;
                margin: -2px 0;
                border-radius: 7px;
            }
            
            QSlider::handle:horizontal:hover {
                background: #b5b2ad;
            }
            
            QSlider::sub-page:horizontal {
                background: #a8a5a0;
                border-radius: 3px;
            }
        """)
        
        main_layout = QVBoxLayout()

        file_ops_group = QGroupBox("文件操作")
        file_ops_layout = QHBoxLayout()
        self.extract_pdf_btn = QPushButton('📄 从PDF提取知识点')
        self.extract_pdf_btn.clicked.connect(self.start_pdf_extraction)
        self.load_json_btn = QPushButton('📂 加载知识点JSON')
        self.load_json_btn.clicked.connect(self.load_knowledge_json)
        self.save_btn = QPushButton('💾 保存当前知识点')
        self.save_btn.clicked.connect(self.save_knowledge_json)
        self.save_btn.setEnabled(False)
        file_ops_layout.addWidget(self.extract_pdf_btn)
        file_ops_layout.addWidget(self.load_json_btn)
        file_ops_layout.addWidget(self.save_btn)
        file_ops_layout.addStretch()
        file_ops_group.setLayout(file_ops_layout)
        main_layout.addWidget(file_ops_group)
        
        self.current_file_label = QLabel("📋 当前文件: 未加载文件")
        self.current_file_label.setStyleSheet("color: #7a7a7a; font-style: italic; margin: 2px; font-size: 8pt;")
        main_layout.addWidget(self.current_file_label)

        splitter = QSplitter(Qt.Horizontal)
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        list_title = QLabel("📚 知识点列表")
        list_title.setStyleSheet("font-size: 10pt; color: #7a7a7a; font-weight: normal; margin: 5px 0;")
        left_layout.addWidget(list_title)
        
        self.knowledge_list_widget = QListWidget()
        self.knowledge_list_widget.itemClicked.connect(self.display_knowledge_point)
        left_layout.addWidget(self.knowledge_list_widget)
        
        left_buttons_layout = QHBoxLayout()
        self.delete_selected_btn = QPushButton('🗑️ 删除选中知识点')
        self.delete_selected_btn.setObjectName("deleteBtn")
        self.delete_selected_btn.clicked.connect(self.delete_selected_knowledge_point)
        self.delete_selected_btn.setEnabled(False)
        left_buttons_layout.addWidget(self.delete_selected_btn)
        left_layout.addLayout(left_buttons_layout)
        
        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        detail_title = QLabel("📝 知识点详情")
        detail_title.setStyleSheet("font-size: 10pt; color: #7a7a7a; font-weight: normal; margin: 5px 0;")
        right_layout.addWidget(detail_title)
        
        basic_info_group = QGroupBox("基本信息")
        basic_info_layout = QGridLayout()
        
        basic_info_layout.addWidget(QLabel("🆔 知识点ID:"), 0, 0)
        self.kp_id_display = QLineEdit()
        self.kp_id_display.setReadOnly(True)
        basic_info_layout.addWidget(self.kp_id_display, 0, 1)
        
        basic_info_layout.addWidget(QLabel("📌 知识点标题:"), 1, 0)
        self.kp_title_display = QLineEdit()
        self.kp_title_display.setReadOnly(True)
        basic_info_layout.addWidget(self.kp_title_display, 1, 1)
        
        basic_info_layout.addWidget(QLabel("🏷️ 类型:"), 2, 0)
        self.kp_type_display = QLineEdit()
        self.kp_type_display.setReadOnly(True)
        basic_info_layout.addWidget(self.kp_type_display, 2, 1)
        
        basic_info_group.setLayout(basic_info_layout)
        right_layout.addWidget(basic_info_group)
        
        importance_group = QGroupBox("重要性评估")
        importance_layout = QVBoxLayout()
        
        importance_info_layout = QHBoxLayout()
        importance_info_layout.addWidget(QLabel("⭐ 重要性数值:"))
        self.kp_importance_display = QLineEdit()
        self.kp_importance_display.setReadOnly(True)
        self.kp_importance_display.setMaximumWidth(100)
        importance_info_layout.addWidget(self.kp_importance_display)
        
        self.importance_slider = QSlider(Qt.Horizontal)
        self.importance_slider.setRange(0, 100)
        self.importance_slider.setEnabled(False)
        importance_info_layout.addWidget(self.importance_slider)
        importance_layout.addLayout(importance_info_layout)
        
        self.importance_level_label = QLabel("📊 重要性等级: 未知")
        self.importance_level_label.setStyleSheet("font-weight: normal; margin: 2px 0; color: #a8a5a0;")
        importance_layout.addWidget(self.importance_level_label)
        
        importance_group.setLayout(importance_layout)
        right_layout.addWidget(importance_group)

        content_group = QGroupBox("知识点内容")
        content_layout = QVBoxLayout()
        self.kp_content_display = QTextEdit()
        self.kp_content_display.setReadOnly(False)
        self.kp_content_display.setMinimumHeight(150)
        content_layout.addWidget(self.kp_content_display)
        content_group.setLayout(content_layout)
        right_layout.addWidget(content_group)
        
        actions_group = QGroupBox("操作")
        actions_layout = QHBoxLayout()
        
        self.refine_btn = QPushButton('✨ 精炼当前知识点')
        self.refine_btn.setObjectName("refineBtn")
        self.refine_btn.clicked.connect(self.refine_current_knowledge_point)
        self.refine_btn.setEnabled(False)
        actions_layout.addWidget(self.refine_btn)
        
        self.delete_current_btn = QPushButton('🗑️ 删除当前知识点')
        self.delete_current_btn.setObjectName("deleteBtn")
        self.delete_current_btn.clicked.connect(self.delete_current_knowledge_point)
        self.delete_current_btn.setEnabled(False)
        actions_layout.addWidget(self.delete_current_btn)
        
        actions_group.setLayout(actions_layout)
        right_layout.addWidget(actions_group)

        right_panel.setLayout(right_layout)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        splitter.setSizes([300, 700]) 
        main_layout.addWidget(splitter, 1)
        
        api_config_group = QGroupBox("🔧 API配置")
        api_config_layout = QGridLayout()
        
        api_config_layout.addWidget(QLabel("🔑 API Key:"), 0, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("LLM API Key (例如 DeepSeek, OpenAI)")
        self.api_key_input.textChanged.connect(self.on_api_config_changed)
        api_config_layout.addWidget(self.api_key_input, 0, 1)
        
        api_config_layout.addWidget(QLabel("🌐 Base URL:"), 1, 0)
        self.base_url_input = QComboBox()
        self.base_url_input.setEditable(True)
        self.base_url_input.addItems([
            "",
            "https://api.deepseek.com",
            "https://api.openai.com/v1",
            "https://api.anthropic.com",
            "https://api.moonshot.cn/v1",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "https://open.bigmodel.cn/api/paas/v4",
            "https://api.siliconflow.cn/v1",
            "https://api.together.xyz/v1"
        ])
        self.base_url_input.setCurrentText("")
        self.base_url_input.lineEdit().setPlaceholderText("API Base URL (可选)")
        self.base_url_input.currentTextChanged.connect(self.on_api_config_changed)
        api_config_layout.addWidget(self.base_url_input, 1, 1)

        api_config_layout.addWidget(QLabel("🤖 Model Name:"), 2, 0)
        self.model_name_input = QLineEdit("deepseek-chat")
        self.model_name_input.textChanged.connect(self.on_api_config_changed)
        api_config_layout.addWidget(self.model_name_input, 2, 1)
        
        api_config_group.setLayout(api_config_layout)
        main_layout.addWidget(api_config_group)
        
        self.setLayout(main_layout)

    def on_api_config_changed(self):
        self.init_extractor()
        if self.knowledge_list_widget.currentItem() and self.api_key_input.text() and self.extractor:
            self.refine_btn.setEnabled(True)
        else:
            self.refine_btn.setEnabled(False)

    def init_extractor(self):
        if not KnowledgeExtractor:
            self.refine_btn.setEnabled(False)
            self.extract_pdf_btn.setEnabled(False if not PDFConverter else True)
            return False

        api_key = self.api_key_input.text().strip()
        base_url = self.base_url_input.currentText().strip() or None
        model_name = self.model_name_input.text().strip() or "deepseek-chat"
        use_local_model = False
        local_model_url = None

        if not api_key:
            self.extractor = None
            self.refine_btn.setEnabled(False)
            return False

        try:
            current_config = {
                'api_key': api_key,
                'base_url': base_url,
                'model_name': model_name,
                'use_local_model': use_local_model,
                'local_model_url': local_model_url
            }
            if self.extractor and getattr(self.extractor, '_config', None) == current_config:
                 return True

            self.extractor = KnowledgeExtractor(**current_config)
            self.extractor._config = current_config
            print(f"KnowledgeExtractor 初始化/更新成功，模型: {model_name}")
            if self.knowledge_list_widget.currentItem():
                self.refine_btn.setEnabled(True)
            return True
        except Exception as e:
            print(f"KnowledgeExtractor 初始化失败: {e}")
            self.extractor = None
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
            'model_name': self.model_name_input.text().strip() or "deepseek-chat",
            'use_local_model': False,
            'local_model_url': None
        }

    def update_extraction_progress(self, message):
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)
            print(f"[进度]: {message}")
            QApplication.processEvents()

    def on_pdf_extraction_finished(self, extracted_points, saved_json_path):
        if self.progress_dialog:
            self.progress_dialog.close()
        QApplication.restoreOverrideCursor()

        if extracted_points is not None:
            self.knowledge_points = extracted_points
            self.current_file_path = saved_json_path if saved_json_path else ""
            self.current_file_label.setText(f"📋 当前文件: {os.path.basename(self.current_file_path)}" if self.current_file_path else "📋 新提取的知识点 (未保存)")
            self.populate_knowledge_list()
            self.save_btn.setEnabled(True if self.knowledge_points else False)
            self.kp_id_display.clear()
            self.kp_title_display.clear()
            self.kp_content_display.clear()
            self.kp_type_display.clear()
            self.kp_importance_display.clear()
            self.importance_slider.setValue(0)
            self.importance_level_label.setText("📊 重要性等级: 未知")
            self.importance_level_label.setStyleSheet("font-weight: normal; margin: 2px 0; color: #a8a5a0;")
            self.refine_btn.setEnabled(False)
            self.delete_selected_btn.setEnabled(False)
            self.delete_current_btn.setEnabled(False)
            QMessageBox.information(self, "提取完成", f"成功从PDF提取了 {len(extracted_points)} 个知识点。\n已保存到: {saved_json_path if saved_json_path else '提取完成但未指定保存路径或保存失败'}")
            print(f"成功提取 {len(extracted_points)} 个知识点。保存在: {saved_json_path}")
        else:
             QMessageBox.warning(self, "提取结果问题", "PDF提取过程完成，但未能获得有效的知识点数据。")
             print("PDF提取过程完成，但未能获得有效的知识点数据。")
        
        self.extract_pdf_btn.setEnabled(True)
        self.load_json_btn.setEnabled(True)

    def on_pdf_extraction_error(self, error_message):
        if self.progress_dialog:
            self.progress_dialog.close()
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(self, "PDF提取失败", f"从PDF提取知识点时出错: {error_message}")
        print(f"PDF提取错误: {error_message}")
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
                    self.current_file_label.setText(f"📋 当前文件: {os.path.basename(file_path)}")
                    self.populate_knowledge_list()
                    self.save_btn.setEnabled(True)
                    self.kp_id_display.clear()
                    self.kp_title_display.clear()
                    self.kp_content_display.clear()
                    self.kp_type_display.clear()
                    self.kp_importance_display.clear()
                    self.importance_slider.setValue(0)
                    self.importance_level_label.setText("📊 重要性等级: 未知")
                    self.importance_level_label.setStyleSheet("font-weight: normal; margin: 2px 0; color: #a8a5a0;")
                    self.refine_btn.setEnabled(False) 
                    self.delete_selected_btn.setEnabled(False)
                    self.delete_current_btn.setEnabled(False)
                    print(f"成功加载 {len(self.knowledge_points)} 个知识点从 {file_path}")
                else:
                    QMessageBox.warning(self, "文件格式错误", "JSON文件必须包含一个名为 'knowledge_points' 的列表。")
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"加载文件时出错: {e}")

    def populate_knowledge_list(self):
        self.knowledge_list_widget.clear()
        for i, point in enumerate(self.knowledge_points):
            title = point.get('title', '未命名知识点')
            kp_id = point.get('id', f'temp_id_{i}')
            importance = point.get('importance', 0)
            kp_type = point.get('type', '未知')
            
            if isinstance(importance, (int, float)):
                if importance >= 0.9:
                    stars = "🔥🔥🔥"
                elif importance >= 0.8:
                    stars = "⭐⭐⭐"
                elif importance >= 0.7:
                    stars = "⭐⭐"
                elif importance >= 0.5:
                    stars = "⭐"
                else:
                    stars = "📉"
                importance_text = f"({importance:.2f}) {stars}"
            else:
                importance_text = "(未知)"
            
            type_icon = {
                'concept': '💡',
                'principle': '📐',
                'method': '🔧',
                'fact': '📋',
                'formula': '🧮'
            }.get(kp_type, '📄')
            
            list_item_text = f"{type_icon} {kp_id} - {title} {importance_text}"
            self.knowledge_list_widget.addItem(list_item_text)

    def display_knowledge_point(self, item):
        selected_index = self.knowledge_list_widget.row(item)
        if 0 <= selected_index < len(self.knowledge_points):
            point_data = self.knowledge_points[selected_index]
            self.kp_id_display.setText(point_data.get("id", "N/A"))
            self.kp_title_display.setText(point_data.get("title", ""))
            self.kp_content_display.setText(point_data.get("content", ""))
            
            kp_type = point_data.get("type", "未知")
            self.kp_type_display.setText(kp_type)
            
            importance = point_data.get("importance", 0)
            if isinstance(importance, (int, float)):
                self.kp_importance_display.setText(f"{importance:.2f}")
                slider_value = int(importance * 100)
                self.importance_slider.setValue(slider_value)
                
                if importance >= 0.9:
                    level = "极高 🔥"
                    color = "#c4a5a0"
                elif importance >= 0.8:
                    level = "高 ⭐"
                    color = "#c4b5a0"
                elif importance >= 0.7:
                    level = "中等 📊"
                    color = "#a0b4c4"
                elif importance >= 0.5:
                    level = "一般 📈"
                    color = "#a5c4a0"
                else:
                    level = "低 📉"
                    color = "#a8a5a0"
                    
                self.importance_level_label.setText(f"📊 重要性等级: {level}")
                self.importance_level_label.setStyleSheet(f"font-weight: normal; margin: 2px 0; color: {color};")
            else:
                self.kp_importance_display.setText("未知")
                self.importance_slider.setValue(0)
                self.importance_level_label.setText("📊 重要性等级: 未知")
                self.importance_level_label.setStyleSheet("font-weight: normal; margin: 2px 0; color: #a8a5a0;")
            
            self.delete_selected_btn.setEnabled(True)
            self.delete_current_btn.setEnabled(True)
            
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
            QMessageBox.warning(self, "操作无效", "请先在列表中选择一个知识点。")
            return

        if not self.extractor:
            if not self.init_extractor():
                QMessageBox.critical(self, "精炼失败", "KnowledgeExtractor 初始化失败。请检查API配置。")
                return
        
        temp_input_json_str = json.dumps({"knowledge_points": [point_to_refine]}, ensure_ascii=False)
        print(f"准备精炼知识点ID: {point_to_refine.get('id', 'N/A')}")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            refined_json_str = self.extractor.refine_knowledge_points(temp_input_json_str)
            refined_data = json.loads(refined_json_str)
            
            if "knowledge_points" in refined_data and refined_data["knowledge_points"]:
                refined_point = refined_data["knowledge_points"][0]
                self.kp_title_display.setText(refined_point.get("title", ""))
                self.kp_content_display.setText(refined_point.get("content", ""))
                self.knowledge_points[selected_index]["title"] = refined_point.get("title", self.knowledge_points[selected_index].get("title"))
                self.knowledge_points[selected_index]["content"] = refined_point.get("content", self.knowledge_points[selected_index].get("content"))
                list_item_text = f"{self.knowledge_points[selected_index].get('id', 'N/A')} - {refined_point.get('title', '未命名知识点')}"
                self.knowledge_list_widget.currentItem().setText(list_item_text)
                QMessageBox.information(self, "精炼成功", "知识点已精炼并更新显示。")
                print(f"知识点ID: {point_to_refine.get('id', 'N/A')} 精炼成功")
            else:
                QMessageBox.warning(self, "精炼结果问题", "精炼操作未返回有效知识点。原始数据未改变。")
                print(f"知识点ID: {point_to_refine.get('id', 'N/A')} 精炼返回数据格式不正确或为空: {refined_json_str}")
        except Exception as e:
            QMessageBox.critical(self, "精炼失败", f"精炼知识点时出错: {e}")
            print(f"知识点ID: {point_to_refine.get('id', 'N/A')} 精炼时发生异常: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def delete_selected_knowledge_point(self):
        self.delete_current_knowledge_point()

    def delete_current_knowledge_point(self):
        selected_index, point_to_delete = self.get_current_selected_point_index_and_data()
        if point_to_delete is None:
            QMessageBox.warning(self, "操作无效", "请先在列表中选择一个知识点。")
            return

        reply = QMessageBox.question(
            self, 
            '确认删除', 
            f"确定要删除以下知识点吗？\n\nID: {point_to_delete.get('id', 'N/A')}\n标题: {point_to_delete.get('title', '未命名知识点')}",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                del self.knowledge_points[selected_index]
                
                self.populate_knowledge_list()
                
                self.kp_id_display.clear()
                self.kp_title_display.clear()
                self.kp_content_display.clear()
                self.kp_type_display.clear()
                self.kp_importance_display.clear()
                self.importance_slider.setValue(0)
                self.importance_level_label.setText("📊 重要性等级: 未知")
                self.importance_level_label.setStyleSheet("font-weight: normal; margin: 2px 0; color: #a8a5a0;")
                
                self.refine_btn.setEnabled(False)
                self.delete_selected_btn.setEnabled(False)
                self.delete_current_btn.setEnabled(False)
                
                self.save_btn.setEnabled(True if self.knowledge_points else False)
                
                QMessageBox.information(self, "删除成功", f"知识点 '{point_to_delete.get('title', '未命名知识点')}' 已删除。\n剩余 {len(self.knowledge_points)} 个知识点。")
                print(f"已删除知识点: {point_to_delete.get('id', 'N/A')} - {point_to_delete.get('title', '未命名知识点')}")
                
            except Exception as e:
                QMessageBox.critical(self, "删除失败", f"删除知识点时出错: {e}")
                print(f"删除知识点时发生异常: {e}")

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
            QMessageBox.information(self, "保存成功", f"知识点已保存到: {self.current_file_path}")
            self.current_file_label.setText(f"📋 当前文件: {os.path.basename(self.current_file_path)}" if self.current_file_path else "📋 新提取的知识点 (未保存)") 
            print(f"知识点成功保存到: {self.current_file_path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存文件时出错: {e}")
            print(f"保存文件到 {self.current_file_path} 时出错: {e}")

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
        else:
            event.accept()


if __name__ == '__main__':
    modules_ok = True
    if KnowledgeExtractor is None:
        modules_ok = False
        print("KnowledgeExtractor 模块导入失败，部分功能将受限。")
    if PDFConverter is None:
        modules_ok = False
        print("PDFConverter 模块导入失败，PDF提取功能将受限。")

    app = QApplication(sys.argv)
    if not modules_ok:
         QMessageBox.warning(None, "模块缺失", "一个或多个核心模块 (KnowledgeExtractor, PDFConverter) 未能成功导入。\n请确保相关py文件在正确路径下。\nGUI将启动，但相关功能可能无法使用。")

    ex = KnowledgeRefineryApp()
    ex.show()
    sys.exit(app.exec_()) 