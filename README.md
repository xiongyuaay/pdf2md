# PDF教材转换与知识点提取工具

这是一个用于将PDF教材转换为Markdown格式并提取知识点的工具。该工具使用Python开发，可以：

1. 将PDF文件转换为Markdown格式
2. 使用大语言模型（如OpenAI的GPT模型或本地部署的模型）提取教材中的关键知识点
3. 将提取的知识点整理为结构化的Markdown文档

## 功能特点

- 支持多种PDF文本提取方法（pdfminer和PyPDF2）
- 自动处理大型PDF文件，分段提取文本以避免API限制
- 支持使用OpenAI API或本地部署的大模型提取知识点
- 使用AI技术提取和整理知识点，保持原文的准确性
- 生成标准Markdown格式的知识点文档，适合进一步加工或直接学习使用
- 命令行界面，方便批处理或集成到其他工作流中
- 提供一体化Python脚本直接部署本地大模型API服务（无需额外工具）

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/pdf2md.git
cd pdf2md
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 设置API密钥或本地模型URL

在项目根目录创建`.env`文件：

```
# 使用OpenAI API时需要设置
OPENAI_API_KEY=your_api_key_here

# 使用本地模型时需要设置
LOCAL_MODEL_URL=http://localhost:1234/v1/chat/completions
```

或者在运行时通过命令行参数传入API密钥或本地模型URL。

## 使用方法

### 基本用法

1. **仅将PDF转换为Markdown**:

```bash
python pdf2md.py --pdf path/to/your/textbook.pdf
```

2. **使用OpenAI API提取知识点**:

```bash
python pdf2md.py --pdf path/to/your/textbook.pdf --extract
```

3. **使用本地部署的大模型提取知识点**:

```bash
python pdf2md.py --pdf path/to/your/textbook.pdf --extract --local_model --model_url http://localhost:1234/v1/chat/completions
```

### 高级选项

```bash
python pdf2md.py --pdf path/to/your/textbook.pdf --output output_directory --extract --method pypdf2 --api_key your_api_key
```

### 参数说明

- `--pdf`, `-p`: PDF文件路径（必需）
- `--output`, `-o`: 输出目录路径（可选，默认为PDF文件所在目录）
- `--api_key`, `-k`: OpenAI API密钥（可选，默认使用环境变量）
- `--extract`, `-e`: 启用知识点提取功能（可选标志）
- `--method`, `-m`: PDF文本提取方法，可选`pdfminer`或`pypdf2`（默认为`pdfminer`）
- `--local_model`, `-l`: 使用本地部署的大模型（可选标志）
- `--model_url`, `-u`: 本地模型API地址（可选，默认使用环境变量）

## 输出文件

该工具会生成两个文件：

1. `{filename}.md` - 原始PDF转换后的Markdown文件
2. `{filename}_知识点.md` - 提取整理后的知识点文件（如果启用了知识点提取功能）

## 内置一体化大模型部署

本工具提供了一个简单的内置Python脚本（`src/model_server.py`），可以一键部署本地大模型API服务器，无需安装其他工具。
### 使用步骤：

1. **启动模型服务器**:

```bash
# 使用默认小型模型
python src/model_server.py

# 使用指定的中文大模型
python src/model_server.py --model_name "Qwen/Qwen-7B-Chat"

# 对大型模型使用量化以节省显存
python src/model_server.py --model_name "Qwen/Qwen-7B-Chat" --quantization 4bit
```

2. **连接到模型服务进行知识点提取**:

```bash
python pdf2md.py --pdf your_file.pdf --extract --local_model --model_url http://localhost:8000/v1/chat/completions
```

### 模型服务器参数：

- `--model_name`, `-m`: 模型名称或路径，默认使用"Qwen/Qwen-1.8B-Chat"（轻量级模型）
- `--device`, `-d`: 运行设备，可选"cpu"、"cuda"、"auto"（默认）
- `--quantization`, `-q`: 量化方法，可选"4bit"、"8bit"或不设置
- `--port`, `-p`: 服务器端口号，默认8000
- `--host`: 服务器地址，默认"0.0.0.0"（允许任何地址访问）

### 支持的中文模型：

脚本支持自动下载和运行以下模型（可根据您的硬件选择合适的规格）：

| 模型系列 | 轻量版本 | 中等版本 | 完整版本 | 最低显存 |
|--------|---------|---------|---------|---------|
| 通义千问 | Qwen/Qwen-1.8B-Chat | Qwen/Qwen-7B-Chat | Qwen/Qwen-14B-Chat | 2GB/8GB/16GB |
| 百川智能 | baichuan-inc/Baichuan2-7B-Chat | - | baichuan-inc/Baichuan2-13B-Chat | 8GB/16GB |
| ChatGLM | THUDM/chatglm3-6b | - | THUDM/chatglm3-6b-32k | 6GB/6GB |
| Yi模型 | 01-ai/Yi-1.5-6B | - | 01-ai/Yi-1.5-9B | 6GB/12GB |

**注意**：使用模型名称时，脚本会自动从Hugging Face下载模型。


### 自定义本地模型API集成

如果您使用的本地模型API格式与工具不兼容，可以修改`knowledge_extractor.py`中的`_call_local_model`方法：

```python
def _call_local_model(self, text):
    # 这里是原有实现
    # ...
    
    # 添加自定义API格式支持
    elif "your_custom_format" in response_data:
        return response_data["your_custom_format"].strip()
```

## 提示与建议

- 对于文字识别质量较高的PDF，推荐使用`pdfminer`提取方法
- 对于扫描质量较差或包含复杂图形的PDF，需要预先使用OCR软件处理
- 使用本地模型时，需要确保模型有足够的能力理解和分析教材内容
- 对于中文教材，建议使用支持中文的模型，如Qwen、Baichuan、ChatGLM等

## 开发者信息

如果您想修改或扩展此工具：

- `src/pdf_converter.py` - PDF转换模块
- `src/knowledge_extractor.py` - 知识点提取模块
- `src/main.py` - 主程序逻辑
- `src/model_server.py` - 内置大模型API服务器

## 许可证

MIT 
