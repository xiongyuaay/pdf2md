#!/usr/bin/env python
# python pdf2md.py --pdf ./data/数学问题v1.0-.pdf --extract --local_model --model_url http://127.0.0.1:8000/v1/chat/completions
# python pdf2md.py --pdf ./data/简历4.pdf --extract --local_model --model_url http://127.0.0.1:8000/v1/chat/completions
"""
PDF转Markdown + 知识点提取工具
直接运行此文件即可启动图形界面
"""

import os
import sys
import importlib.util
import subprocess
import socket

def check_module_installed(module_name):
    """检查模块是否已安装"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def install_dependencies():
    """安装必要的依赖包"""
    dependencies = ["gradio", "pdfminer.six", "pypdf2", "openai"]
    for dep in dependencies:
        if not check_module_installed(dep.split('.')[0]):
            print(f"正在安装 {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
    print("所有依赖已安装完成！")

def get_local_ip():
    """获取本机IP地址"""
    try:
        # 获取主机名
        hostname = socket.gethostname()
        # 获取本机IP
        ip = socket.gethostbyname(hostname)
        return ip
    except:
        return "127.0.0.1"

if __name__ == "__main__":
    # 安装依赖
    if not check_module_installed("gradio"):
        print("首次运行需要安装依赖...")
        install_dependencies()
    
    # 确保能找到源代码目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)
    
    try:
        # 直接从源代码目录导入
        sys.path.insert(0, os.path.join(current_dir, "src"))
        
        import gradio as gr
        from src.main_ui import demo
        
        # 获取本机IP
        local_ip = get_local_ip()
        
        print("正在启动PDF转Markdown + 知识点提取工具...")
        print("请稍等片刻，程序将自动在浏览器中打开...")
        
        # 启动界面，使用localhost而不是0.0.0.0
        demo.launch(
            show_error=True,
            server_name="127.0.0.1",  # 使用本地回环地址
            share=False,
            inbrowser=True  # 自动在浏览器中打开
        )
        
        print(f"\n如自动打开失败，请手动访问: http://127.0.0.1:7860")
        print(f"如需在局域网内访问，请使用: http://{local_ip}:7860")
        
    except ModuleNotFoundError as e:
        missing_module = str(e).split("'")[1]
        if missing_module.startswith('src.'):
            module_path = missing_module.replace('.', os.path.sep) + '.py'
            print(f"错误：找不到模块文件 {module_path}")
            print("请确保项目文件结构完整。")
        else:
            print(f"错误：缺少模块 {missing_module}")
            print("尝试安装依赖...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", missing_module])
                print(f"已安装 {missing_module}，请重新运行程序")
            except:
                print(f"无法自动安装 {missing_module}，请手动安装：pip install {missing_module}")
        input("按任意键退出...")
        
    except Exception as e:
        print(f"发生错误：{e}")
        print(f"错误类型: {type(e).__name__}")
        input("按任意键退出...") 