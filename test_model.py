#!/usr/bin/env python
print("开始执行测试脚本")

import sys
import os

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
except ImportError:
    print("缺少必要的依赖库。正在安装...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                           "torch", "transformers"])
    print("依赖安装完成，正在重新导入...")
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

print("已导入必要的库")

def test_model():
    """测试模型加载功能"""
    print("开始测试模型加载函数")
    
    model_name = "Qwen/Qwen-1.8B-Chat"
    device = "cpu"
    
    print(f"准备加载模型: {model_name} 在设备 {device} 上")
    
    try:
        # 尝试加载模型和分词器
        print("加载分词器...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, 
            trust_remote_code=True
        )
        
        print("分词器加载成功，正在加载模型...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name, 
            device_map=device,
            trust_remote_code=True
        )
        
        print(f"模型加载成功: {model.__class__.__name__}")
        
        # 尝试简单的生成任务
        print("尝试生成回复...")
        inputs = tokenizer("你好，请介绍一下你自己", return_tensors="pt").to(device)
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=50)
        
        response = tokenizer.decode(output[0], skip_special_tokens=True)
        print(f"生成的回复: {response}")
        
        print("测试完成")
        
    except Exception as e:
        print(f"测试失败，错误信息: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("开始执行主函数")
    test_model()
    print("测试结束") 