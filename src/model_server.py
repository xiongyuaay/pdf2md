#!/usr/bin/env python
print("DEBUG: 脚本开始执行")

print("DEBUG: 导入前")
import os
import sys
import argparse
import logging
import json
import time
from typing import List, Dict, Any, Optional, Union

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from transformers import TextIteratorStreamer
    from threading import Thread
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse, JSONResponse
    import uvicorn
    from pydantic import BaseModel, Field
    print("DEBUG: 导入后")
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                           "torch", "transformers", "fastapi", "uvicorn",
                           "pydantic", "sentencepiece", "accelerate"])
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from transformers import TextIteratorStreamer
    from threading import Thread
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse, JSONResponse
    import uvicorn
    from pydantic import BaseModel, Field
    print("DEBUG: 导入后")

print("DEBUG: 导入后")
# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# API请求模型
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "local_model"
    messages: List[Message]
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048
    stream: bool = False

class ModelManager:
    """大模型管理器，负责加载和运行模型"""
    
    def __init__(self, model_name: str, device: str = "auto", quantization: str = None):
        """
        初始化模型管理器
        
        Args:
            model_name: 模型名称或路径
            device: 运行设备，可选 'cpu', 'cuda', 'auto'
            quantization: 量化方法，可选 '4bit', '8bit', None
        """
        self.model_name = model_name
        
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self.quantization = quantization
        self.model = None
        self.tokenizer = None
        
        self.is_chinese_model = any(name in model_name.lower() for name 
                                   in ["qwen", "baichuan", "chatglm", "yi", "moss", "chinese"])
        
        self._load_model()
        
    def _load_model(self):
        """加载并配置模型与分词器"""
        logger.info(f"正在加载模型 {self.model_name}...")
        
        # 配置量化参数
        load_kwargs = {"device_map": self.device, "trust_remote_code": True}
        if self.quantization == "4bit":
            from transformers import BitsAndBytesConfig
            load_kwargs.update({
                "quantization_config": BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
            })
        elif self.quantization == "8bit":
            from transformers import BitsAndBytesConfig
            load_kwargs.update({
                "quantization_config": BitsAndBytesConfig(
                    load_in_8bit=True
                )
            })
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, 
                trust_remote_code=True
            )
                
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, 
                **load_kwargs
            )
            
            if not self.tokenizer.pad_token:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            if "qwen" in self.model_name.lower():
                from transformers import GenerationConfig
                self.model.generation_config = GenerationConfig.from_pretrained(self.model_name)
                
            logger.info(f"模型 {self.model_name} 加载完成，运行在 {self.device} 上")
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise
    
    def _format_prompt(self, messages: List[Message]) -> str:
        """
        根据不同模型格式化对话提示
        
        Args:
            messages: 对话消息列表
            
        Returns:
            格式化后的提示文本
        """
        if "qwen" in self.model_name.lower():
            print("Qwen模型")
            return self._format_qwen_prompt(messages)
        elif "chatglm" in self.model_name.lower():
            print("ChatGLM模型")
            return self._format_chatglm_prompt(messages)
        elif "baichuan" in self.model_name.lower():
            print("Baichuan模型")
            return self._format_baichuan_prompt(messages)
        else:
            print("默认格式")
            return self._format_default_prompt(messages)
    
    def _format_default_prompt(self, messages: List[Message]) -> str:
        """默认ChatML格式提示"""
        prompt = ""
        for msg in messages:
            role = msg.role
            content = msg.content
            if role == "system":
                prompt += f"<|system|>\n{content}\n"
            elif role == "user":
                prompt += f"<|user|>\n{content}\n"
            elif role == "assistant":
                prompt += f"<|assistant|>\n{content}\n"
        prompt += "<|assistant|>\n"
        return prompt
    
    def _format_qwen_prompt(self, messages: List[Message]) -> str:
        """Qwen模型的对话格式"""
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        if not getattr(self.tokenizer, "chat_template", None):
            self.tokenizer.chat_template = (
                "{% for message in messages %}"
                "{{ message['role'] }}: {{ message['content'] }}\n"
                "{% endfor %}assistant: "
            )
        return self.tokenizer.apply_chat_template(
            formatted_messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
    
    def _format_chatglm_prompt(self, messages: List[Message]) -> str:
        """ChatGLM模型的对话格式"""
        history = []
        system = ""
        
        for i, msg in enumerate(messages):
            if msg.role == "system":
                system += msg.content + "\n"
            elif msg.role == "user":
                if i < len(messages) - 1 and messages[i+1].role == "assistant":
                    history.append([msg.content, messages[i+1].content])
                else:
                    query = msg.content
        
        # 处理最后一个用户消息
        if messages[-1].role == "user":
            query = messages[-1].content
        else:
            query = ""
        
        if system:
            query = system + "\n" + query
            
        return query, history
    
    def _format_baichuan_prompt(self, messages: List[Message]) -> str:
        """Baichuan模型的对话格式"""
        prompt = ""
        for msg in messages:
            if msg.role == "system":
                prompt += f"<reserved_102>{msg.content}</reserved_103>\n"
            elif msg.role == "user":
                prompt += f"<reserved_106>{msg.content}</reserved_107>\n"
            elif msg.role == "assistant":
                prompt += f"<reserved_104>{msg.content}</reserved_105>\n"
        prompt += "<reserved_104>"
        return prompt
    
    def generate(self, messages: List[Message], 
                temperature: float = 0, 
                top_p: float = 0.9,
                max_tokens: int = 2048) -> str:
        """
        生成回复文本
        
        Args:
            messages: 对话消息列表
            temperature: 温度参数
            top_p: Top-p采样参数
            max_tokens: 最大生成token数
            
        Returns:
            生成的回复文本
        """
        print(f"generate: {messages}")
        try:
            if "chatglm" in self.model_name.lower():
                query, history = self._format_chatglm_prompt(messages)
                response, _ = self.model.chat(
                    self.tokenizer,
                    query,
                    history=history,
                    temperature=temperature,
                    top_p=top_p,
                    max_length=max_tokens
                )
                return response
            
            prompt = self._format_prompt(messages)
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            gen_kwargs = {
                "temperature": temperature,
                "top_p": top_p,
                "max_new_tokens": max_tokens,
                "do_sample": temperature > 0.1,
                "pad_token_id": self.tokenizer.pad_token_id,
            }
            
            with torch.no_grad():
                output = self.model.generate(**inputs, **gen_kwargs)
                
            generated_text = self.tokenizer.decode(
                output[0][inputs["input_ids"].shape[1]:], 
                skip_special_tokens=True
            )
            print(f"generated_text: {generated_text}")
            return generated_text.strip()
            
        except Exception as e:
            logger.error(f"生成失败: {e}")
            raise
            
    def generate_stream(self, messages: List[Message], 
                       temperature: float = 0.7, 
                       top_p: float = 0.9,
                       max_tokens: int = 2048):
        """
        流式生成回复
        
        Args:
            messages: 对话消息列表
            temperature: 温度参数
            top_p: Top-p采样参数
            max_tokens: 最大生成token数
            
        Returns:
            生成的文本迭代器
        """
        if "chatglm" in self.model_name.lower():
            query, history = self._format_chatglm_prompt(messages)
            for response, _ in self.model.stream_chat(
                self.tokenizer,
                query,
                history=history,
                temperature=temperature,
                top_p=top_p,
                max_length=max_tokens
            ):
                yield response
            return
            
        prompt = self._format_prompt(messages)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        streamer = TextIteratorStreamer(
            self.tokenizer, 
            skip_special_tokens=True,
            skip_prompt=True
        )
        
        gen_kwargs = {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"],
            "temperature": temperature,
            "top_p": top_p,
            "max_new_tokens": max_tokens,
            "do_sample": temperature > 0.1,
            "streamer": streamer,
        }
        
        generation_thread = Thread(target=self.model.generate, kwargs=gen_kwargs)
        generation_thread.start()
        
        generated_text = ""
        for new_text in streamer:
            generated_text += new_text
            yield generated_text

app = FastAPI(title="本地大模型API服务器")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model_manager = None

@app.post("/v1/chat/completions")
async def chat_completion(request: ChatCompletionRequest):
    """
    聊天补全API，兼容OpenAI格式
    """
    global model_manager
    print(f"request: {request}")
    
    try:
        if model_manager is None:
            raise HTTPException(status_code=500, detail="模型尚未加载")
        
        if request.stream:
            print("流式生成")
            async def generate_stream():
                stream_gen = model_manager.generate_stream(
                    request.messages,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=request.max_tokens
                )
                
                for i, content in enumerate(stream_gen):
                    chunk = {
                        "id": f"chatcmpl-{int(time.time())}-{i}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "content": content if i == 0 else content[len(prev_content):],
                            },
                            "finish_reason": None
                        }]
                    }
                    prev_content = content
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                end_chunk = {
                    "id": f"chatcmpl-{int(time.time())}-end",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(end_chunk)}\n\n"
                yield "data: [DONE]\n\n"
                
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream"
            )
        
        print("非流式生成")
        content = model_manager.generate(
            request.messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens
        )
        
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,  # 这里简化了token计数
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
    
    except Exception as e:
        logger.error(f"处理请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
async def list_models():
    """获取可用模型列表"""
    model_list = [{
        "id": "local-model",
        "object": "model",
        "created": int(time.time()),
        "owned_by": "user"
    }]
    return {"object": "list", "data": model_list}

@app.get("/")
async def root():
    """API根路径"""
    return {
        "status": "running",
        "model": model_manager.model_name if model_manager else "未加载",
        "device": model_manager.device if model_manager else "未知",
        "quantization": model_manager.quantization if model_manager else "无"
    }

def main():
    """主函数"""
    print("DEBUG: 主函数开始执行")
    parser = argparse.ArgumentParser(description="本地大模型API服务器")
    parser.add_argument("--model_name", "-m", type=str, default="Qwen/Qwen-1_8B-Chat",
                        help="模型名称或路径，默认使用较小的Qwen-1.8B-Chat")
    parser.add_argument("--device", "-d", type=str, default="cuda",
                        choices=["auto", "cpu", "cuda"],
                        help="运行设备，可选 'cpu', 'cuda', 'auto'")
    parser.add_argument("--quantization", "-q", type=str, default=None,
                        choices=[None, "4bit", "8bit"],
                        help="模型量化方法，可选 '4bit', '8bit', None")
    parser.add_argument("--port", "-p", type=int, default=8000,
                        help="服务器端口")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="服务器地址")
    
    args = parser.parse_args()
    print(f"DEBUG: 参数解析完成, model_name={args.model_name}, device={args.device}")
    
    global model_manager
    try:
        print("DEBUG: 开始初始化ModelManager")
        model_manager = ModelManager(
            model_name=args.model_name,
            device=args.device,
            quantization=args.quantization
        )
        print("DEBUG: ModelManager初始化完成")
        
        logger.info(f"启动服务器在 {args.host}:{args.port}")
        logger.info(f"模型API兼容OpenAI格式，可通过 http://{args.host}:{args.port}/v1/chat/completions 访问")
        logger.info(f"服务与pdf2md工具集成示例: python pdf2md.py --pdf your_file.pdf --extract --local_model --model_url http://127.0.0.1:{args.port}/v1/chat/completions")
        
        print("DEBUG: 准备启动uvicorn服务器")
        uvicorn.run(app, host=args.host, port=args.port)
    
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        print(f"DEBUG: 异常详情: {repr(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("DEBUG: __name__ == __main__")
    main() 
