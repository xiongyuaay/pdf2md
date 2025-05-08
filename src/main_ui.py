import gradio as gr
import os
import time
import tempfile
import shutil
from pdf_converter_image import PDFConverter
from Knowledge_extractor import KnowledgeExtractor

def process_pdf_tool(pdf_file, api_key, base_url, model_name, extract, local_model, model_url, progress=gr.Progress()):
    logs = []
    knowledge_text = ""
    
    print(f"Debug: process_pdf_tool收到的base_url: {base_url}")
    
    if not pdf_file:
        return "错误：请上传PDF文件", "", None, None
    
    # 检查API设置
    if extract:
        if local_model:
            if not model_url:
                return "错误：使用本地模型需要提供模型URL", "", None, None
        else:
            if not api_key:
                return "错误：使用API提取知识点需要提供API密钥", "", None, None
            if not base_url:
                return "错误：使用API提取知识点需要选择API服务商", "", None, None
            if not model_name:
                return "错误：使用API提取知识点需要选择模型", "", None, None
    
    # 使用临时目录存储处理结果
    temp_dir = tempfile.mkdtemp(prefix="pdf2md_")
    
    base_name = os.path.basename(pdf_file.name)
    file_name = os.path.splitext(base_name)[0]
    
    md_output_path = os.path.join(temp_dir, f"{file_name}.md")
    knowledge_output_path = os.path.join(temp_dir, f"{file_name}_知识点.md")
    
    try:
        # 第一阶段: PDF转Markdown (占总进度的50%)
        logs.append("📄 步骤1：PDF转换为Markdown")
        progress(0.05, desc="初始化转换过程...")
        
        converter = PDFConverter(pdf_file.name)
        progress(0.15, desc="正在处理PDF文件...")
        md_path = converter.process_pdf(md_output_path)
        
        if not md_path:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return "PDF转换失败", "", None, None
        
        logs.append(f"✅ PDF已成功转换为Markdown")
        progress(0.5, desc="PDF转换完成")
        
        # 读取转换后的markdown内容
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        if extract:
            # 第二阶段: 提取知识点 (占总进度的50%)
            logs.append("🔍 步骤2：提取知识点")
            progress(0.55, desc="正在初始化知识点提取...")
            
            # 创建回调函数用于更新进度
            def progress_callback(current, total):
                if total > 0:
                    # 将知识点提取进度映射到55%-95%的总进度范围
                    progress_value = 0.55 + (current / total) * 0.4
                    progress(progress_value, desc=f"正在提取知识点... ({current}/{total})")
            
            extractor = KnowledgeExtractor(
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                use_local_model=local_model,
                local_model_url=model_url
            )
            
            if not md_content:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return "Markdown文件内容为空，无法提取知识点", "", md_path, None
            
            logs.append("⏳ 正在提取知识点，请稍等...")
            # 传递进度回调函数
            knowledge_points = extractor.extract_knowledge_points(md_content, progress_callback=progress_callback)
            
            if not knowledge_points:
                logs.append("⚠️ 未能提取到知识点，仅生成Markdown文件")
                knowledge_output_path = None
            else:
                progress(0.95, desc="正在保存知识点...")
                extractor.save_knowledge_points(knowledge_points, knowledge_output_path)
                logs.append(f"✅ 知识点提取完成")
                knowledge_text = knowledge_points
            
        progress(1.0, desc="处理完成！")
        logs.append("🎉 处理完成！现在可以下载结果文件")
        
    except Exception as e:
        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)
        return f"❌ 发生错误: {e}", "", None, None
    
    return "\n".join(logs), knowledge_text, md_path, knowledge_output_path

css = """
.container {
    max-width: 1200px;
    margin: auto;
}
.header {
    text-align: center;
    margin-bottom: 20px;
}
.file-output {
    margin-top: 10px;
    padding: 10px;
    border-radius: 8px;
    background-color: #f9f9f9;
}
.download-section {
    margin-top: 20px;
    padding: 15px;
    border-radius: 10px;
    background-color: #e8f4ff;
    border: 1px solid #c0d8f0;
}
.success-message {
    color: #2e7d32;
    font-weight: 600;
}
.footer {
    text-align: center;
    margin-top: 20px;
    font-size: 0.8em;
    color: #666;
}
"""

# 常用API服务商列表
API_PROVIDERS = {
    "OpenAI官方": "https://api.openai.com/v1",
    "API2D": "https://api.api2d.com/v1",
    "TataAPI": "https://api.tata-api.com/v1",
    "DeepSeek": "https://api.deepseek.com",
    "自定义": "custom"
}

# 常用模型列表
MODEL_CHOICES = {
    "OpenAI官方": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
    "API2D": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
    "TataAPI": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
    "DeepSeek": ["deepseek-chat", "deepseek-coder"],
    "自定义": ["custom"]
}

# 创建Gradio界面
with gr.Blocks(title="PDF转Markdown & 知识点提取器", css=css, theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 📖 PDF转Markdown + 知识点提取工具", elem_classes=["header"])
    gr.Markdown("_将PDF文档转换为Markdown格式，并可选择性地提取重要知识点_")
    
    with gr.Tab("主要功能"):
        with gr.Group():
            with gr.Row():
                pdf_file = gr.File(label="上传PDF文件", file_types=[".pdf"])
            
            with gr.Accordion("高级选项", open=False):
                with gr.Row():
                    with gr.Column():
                        # API设置部分
                        api_key = gr.Textbox(label="API密钥", type="password", placeholder="sk-...")
                        
                        # API服务商选择
                        api_provider = gr.Dropdown(
                            choices=list(API_PROVIDERS.keys()), 
                            value="TataAPI", 
                            label="API服务商",
                            info="选择API服务提供商或自定义基础URL"
                        )
                        
                        # 模型选择
                        model_name = gr.Dropdown(
                            choices=MODEL_CHOICES["TataAPI"],
                            value="gpt-3.5-turbo",
                            label="模型选择",
                            info="选择要使用的模型"
                        )
                        
                        # 自定义模型名称
                        custom_model_name = gr.Textbox(
                            label="自定义模型名称", 
                            placeholder="输入自定义模型名称",
                            visible=False
                        )
                        
                        # 自定义API基础URL
                        custom_base_url = gr.Textbox(
                            label="自定义API基础URL", 
                            placeholder="https://your-api-service.com/v1",
                            visible=False
                        )
                        
                        # 当选择"自定义"时显示输入框
                        def update_custom_fields(provider):
                            is_custom = provider == "自定义"
                            return (
                                gr.update(visible=is_custom),  # custom_base_url
                                gr.update(visible=is_custom),  # custom_model_name
                                gr.update(visible=not is_custom)  # model_name
                            )
                        
                        # 更新模型选择列表
                        def update_model_choices(provider):
                            if provider == "自定义":
                                return gr.update(visible=False)
                            return gr.update(choices=MODEL_CHOICES[provider], value=MODEL_CHOICES[provider][0], visible=True)
                        
                        api_provider.change(
                            fn=update_custom_fields,
                            inputs=api_provider,
                            outputs=[custom_base_url, custom_model_name, model_name]
                        ).then(
                            fn=update_model_choices,
                            inputs=api_provider,
                            outputs=model_name
                        )
                        
                    with gr.Column():
                        extract = gr.Checkbox(label="提取知识点", value=True, info="使用AI提取文档中的关键知识点")
                        local_model = gr.Checkbox(label="使用本地模型", value=False)
                        model_url = gr.Textbox(
                            label="本地模型URL", 
                            placeholder="http://localhost:11434/api/", 
                            visible=False
                        )
                        
                        # 根据选择显示或隐藏模型URL输入框
                        local_model.change(
                            fn=lambda x: gr.update(visible=x),
                            inputs=local_model,
                            outputs=model_url
                        )
            
            run_button = gr.Button("📝 开始处理", variant="primary")
            
            with gr.Row():
                with gr.Column():
                    output_log = gr.Textbox(label="处理日志", lines=12)
                with gr.Column():
                    knowledge_output = gr.Textbox(label="提取的知识点预览", lines=12)
            
            # 添加文件下载区域
            with gr.Group(visible=False, elem_classes=["download-section"]) as download_group:
                # gr.Markdown("## 📥 下载处理结果", elem_classes=["file-output"])
                gr.Markdown("处理已完成，您可以下载以下文件：", elem_classes=["success-message"])
                with gr.Row():
                    with gr.Column():
                        md_download = gr.File(label="下载Markdown文件", interactive=False)
                    with gr.Column():
                        knowledge_download = gr.File(label="下载知识点文件", interactive=False, visible=True)
    
    with gr.Tab("使用帮助"):
        gr.Markdown("""
        ### 🔰 使用说明
        
        1. **上传PDF文件**：点击"上传PDF文件"区域选择您要处理的PDF文档
        2. **高级选项**（可选）：
           - 提供API密钥并选择API服务商
           - 如需使用自定义API地址，选择"自定义"并输入完整的API基础URL
           - 如需使用本地模型，勾选"使用本地模型"并提供URL
        3. **点击"开始处理"**按钮
        4. **下载结果**：处理完成后，可以直接下载生成的文件
        
        ### 💡 提示
        - 大型PDF文件处理可能需要较长时间
        - 知识点提取功能需要API密钥或本地模型支持
        - 如遇到连接问题，建议使用代理或本地模型
        - 不同API服务商可能有不同的请求格式，如遇问题请尝试其他服务商
        """)
    
    gr.Markdown("© 2025 PDF知识提取工具 | [项目主页](https://github.com/yourusername/pdf2md)", elem_classes=["footer"])
    
    def update_download_section(md_path, knowledge_path):
        """更新下载区域的状态和文件"""
        if not md_path:
            return gr.update(visible=False), gr.update(value=None), gr.update(visible=False, value=None)
        
        # 如果有知识点文件，显示知识点下载
        show_knowledge = knowledge_path is not None
        
        return (
            gr.update(visible=True),
            gr.update(value=md_path),
            gr.update(visible=show_knowledge, value=knowledge_path)
        )
    
    # 处理API基础URL
    def get_base_url(provider, custom_url):
        if provider == "自定义":
            return custom_url
        return API_PROVIDERS[provider]
    
    # 处理API设置
    def process_api_settings(provider, custom_url, custom_model, api_key, extract, local_model, model_name):
        if extract and not local_model:
            if not api_key:
                raise gr.Error("请提供API密钥")
            if provider == "自定义":
                if not custom_url:
                    raise gr.Error("请提供自定义API基础URL")
                if not custom_model:
                    raise gr.Error("请提供自定义模型名称")
                return custom_url, custom_model
            if not model_name:
                raise gr.Error("请选择模型")
        base_url = get_base_url(provider, custom_url)
        return base_url, model_name if provider != "自定义" else custom_model
    
    # 创建状态变量
    base_url_state = gr.State()
    model_name_state = gr.State()
    
    run_button.click(
        fn=process_api_settings,
        inputs=[api_provider, custom_base_url, custom_model_name, api_key, extract, local_model, model_name],
        outputs=[base_url_state, model_name_state]
    ).then(
        process_pdf_tool,
        inputs=[pdf_file, api_key, base_url_state, model_name_state, extract, local_model, model_url],
        outputs=[output_log, knowledge_output, md_download, knowledge_download]
    ).then(
        update_download_section,
        inputs=[md_download, knowledge_download],
        outputs=[download_group, md_download, knowledge_download]
    )

if __name__ == "__main__":
    demo.launch(share=False)
