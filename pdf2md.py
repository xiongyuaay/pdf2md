#!/usr/bin/env python
# python pdf2md.py --pdf ./data/数学问题v1.0-.pdf --extract --local_model --model_url http://127.0.0.1:8000/v1/chat/completions
"""
PDF教材转Markdown并提取知识点工具
使用方法：
    python pdf2md.py --pdf 文件路径 [选项]
"""

import os
import sys

# 将src目录添加到系统路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.append(src_dir)

from main import main
if __name__ == "__main__":
    main() 