#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试OpenAI API连接
简单脚本，检查OpenAI API是否可用
"""

import os
import sys
import time
import httpx

# OpenAI API设置 - 请替换为您的实际API密钥
API_KEY = "sk-GztT3d3SMnmzPCEB7c79Db0481174220A322A5D7622b6cD3"  # 替换为您的API密钥
BASE_URL = "https://api.tata-api.com/v1"  # 如果使用官方API，改为 "https://api.openai.com/v1"

# 代理设置（如果在中国大陆使用，通常需要代理）
PROXY = "http://127.0.0.1:7890"  # 替换为您的代理地址，如不需要可设为None

def test_openai_connection(verbose=True):
    """测试与OpenAI API的连接"""
    if verbose:
        print("OpenAI API 连接测试")
        print("-" * 40)
        print(f"API密钥: {API_KEY[:8]}...{API_KEY[-4:]}")
        print(f"基础URL: {BASE_URL}")
        print(f"使用代理: {PROXY}")
        print("-" * 40)
    
    # 配置代理
    transport = None
    if PROXY:
        transport = httpx.HTTPTransport(proxy=PROXY)
    
    # 创建客户端
    try:
        from openai import OpenAI
        
        start_time = time.time()
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            http_client=httpx.Client(transport=transport) if transport else None
        )
        
        # 发送简单测试请求
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一个有用的助手。"},
                {"role": "user", "content": "请回复'OpenAI API连接测试成功'"}
            ],
            max_tokens=20,
            temperature=0
        )
        
        # 计算响应时间
        elapsed_time = time.time() - start_time
        
        # 提取回复
        reply = response.choices[0].message.content.strip()
        
        if verbose:
            print(f"✅ 连接成功！")
            print(f"📝 API回复: {reply}")
            print(f"⏱️ 响应时间: {elapsed_time:.2f}秒")
        
        return True, reply, elapsed_time
    
    except ImportError:
        if verbose:
            print("❌ 错误: 未安装OpenAI包。请运行: pip install openai")
        return False, "未安装OpenAI包", 0
    
    except Exception as e:
        if verbose:
            print(f"❌ 连接失败: {e}")
            if "auth" in str(e).lower() or "authentication" in str(e).lower():
                print("  可能是API密钥错误")
            elif "timeout" in str(e).lower():
                print("  连接超时，可能需要检查网络或代理设置")
            elif "proxy" in str(e).lower():
                print("  代理设置可能有误")
            else:
                print(f"  错误类型: {type(e).__name__}")
        
        return False, str(e), 0

def print_solutions():
    """打印可能的解决方案"""
    print("\n可能的解决方案:")
    print("-" * 40)
    print("1. 确认API密钥正确")
    print("2. 检查网络连接")
    print("3. 配置正确的代理 (中国大陆使用OpenAI通常需要代理)")
    print("4. 尝试使用其他API服务商")
    print("5. 检查API账户余额")
    print("6. 尝试使用本地模型替代")

if __name__ == "__main__":
    success, message, time_taken = test_openai_connection()
    
    if not success:
        print_solutions()
        sys.exit(1)
    else:
        print("\n✨ API测试完全成功！可以在您的应用中使用OpenAI API。")
        sys.exit(0) 