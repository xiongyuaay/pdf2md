#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的OpenAI API测试脚本
使用硬编码方式和requests库测试API连接
"""

import requests
import json
import sys
import time
import traceback

# ===== 配置区域 - 请修改这里的设置 =====
# API密钥 - 替换为您的实际API密钥
API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# API地址 - 根据您使用的服务商修改
API_URL = "https://api.tata-api.com/v1/chat/completions"  # 三方API服务商地址
# API_URL = "https://api.openai.com/v1/chat/completions"  # OpenAI官方地址

# 代理设置 - 如不需要请设置为 None
PROXIES = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890"
}
# PROXIES = None  # 不使用代理

# 超时设置（秒）
TIMEOUT = 30
# ===== 配置结束 =====

def test_api():
    """测试OpenAI API连接"""
    print("=" * 50)
    print("OpenAI API 简易连接测试")
    print("=" * 50)
    print(f"API地址: {API_URL}")
    print(f"使用代理: {PROXIES}")
    print(f"超时设置: {TIMEOUT}秒")
    print("-" * 50)
    
    # 准备API请求
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "你是一个测试助手。"},
            {"role": "user", "content": "请回复'API测试成功'，不要回复其他内容。"}
        ],
        "max_tokens": 50,
        "temperature": 0
    }
    
    try:
        print("🔄 发送API请求...")
        start_time = time.time()
        
        # 发送请求
        response = requests.post(
            API_URL,
            headers=headers,
            json=data,
            proxies=PROXIES,
            timeout=TIMEOUT
        )
        
        elapsed_time = time.time() - start_time
        print(f"⏱️ 请求用时: {elapsed_time:.2f}秒")
        
        # 检查状态码
        print(f"📊 响应状态码: {response.status_code}")
        
        # 处理响应
        if response.status_code == 200:
            result = response.json()
            message = result["choices"][0]["message"]["content"].strip()
            print("\n✅ API连接成功!")
            print(f"📝 API回复: \"{message}\"")
            
            # 输出完整JSON响应
            print("\n📋 完整响应数据:")
            print("-" * 40)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"\n❌ 请求失败! 状态码: {response.status_code}")
            print("\n📋 错误响应:")
            print("-" * 40)
            
            try:
                error_json = response.json()
                print(json.dumps(error_json, indent=2, ensure_ascii=False))
                
                # 分析常见错误
                if "error" in error_json:
                    error_type = error_json.get("error", {}).get("type", "")
                    error_message = error_json.get("error", {}).get("message", "")
                    
                    if "authentication" in error_type or "auth" in error_type:
                        print("\n🔑 认证错误: API密钥可能无效或过期")
                    elif "rate_limit" in error_type:
                        print("\n⏱️ 速率限制: 您的API请求超过了限制")
                    elif "insufficient_quota" in error_type:
                        print("\n💰 余额不足: 您的账户余额不足")
                    
                    print(f"\n📌 错误信息: {error_message}")
            except:
                print(response.text)
            
            return False
    
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时!")
        print("📌 可能原因: 网络连接慢或API服务器响应延迟")
        print("💡 建议: 增加超时设置或检查网络连接")
        
    except requests.exceptions.ProxyError:
        print("\n❌ 代理错误!")
        print("📌 可能原因: 代理服务器配置错误或代理服务不可用")
        print("💡 建议: 检查代理设置或尝试不使用代理")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 连接错误!")
        print("📌 可能原因: 网络连接问题或API地址错误")
        print("💡 建议: 检查网络连接和API地址")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求错误: {e}")
        
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        print("\n堆栈跟踪:")
        traceback.print_exc()
        
    return False

def print_troubleshooting():
    """打印问题排查建议"""
    print("\n" + "=" * 50)
    print("问题排查建议")
    print("=" * 50)
    print("1. 检查API密钥:")
    print("   - 确认API密钥格式正确（以sk-开头）")
    print("   - 验证API密钥没有过期或被吊销")
    
    print("\n2. 检查网络连接:")
    print("   - 确认您的网络可以访问外部服务")
    print("   - 在中国大陆使用OpenAI服务需要代理或VPN")
    
    print("\n3. 检查代理设置:")
    print("   - 确认代理服务正在运行")
    print("   - 验证代理地址和端口正确")
    print("   - 尝试在浏览器中使用相同代理访问https://chat.openai.com")
    
    print("\n4. 检查API地址:")
    print("   - 确认您使用的是正确的API端点")
    print("   - 如果使用第三方API服务，确认服务商地址正确")
    
    print("\n5. 检查账户余额:")
    print("   - 登录OpenAI账户查看余额")
    print("   - 确认没有超出使用限制")

if __name__ == "__main__":
    success = test_api()
    
    if not success:
        print_troubleshooting()
        sys.exit(1)
    
    print("\n✨ 测试完成! API连接正常工作。")
    sys.exit(0) 