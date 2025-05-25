#!/usr/bin/env python

import os
import sys
import socket

def get_local_ip():
    """获取本机IP地址"""
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip
    except:
        return "127.0.0.1"

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)
    sys.path.insert(0, os.path.join(current_dir, "src"))
    
    import gradio as gr
    from ui.main_ui import demo
    
    local_ip = get_local_ip()
    
    demo.launch(
        show_error=True,
        server_name="127.0.0.1",
        share=False,
        inbrowser=True
    )
    
    print(f"\n如自动打开失败，请手动访问: http://127.0.0.1:7860")