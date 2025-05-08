import os
import json
from tqdm import tqdm
import openai
import requests
from dotenv import load_dotenv
from openai import OpenAI
import httpx

class CustomHTTPClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        kwargs.pop("proxies", None) 
        super().__init__(*args, **kwargs)

class KnowledgeExtractor:
    # 系统提示词
    SYSTEM_PROMPT = (
        "你是一个专业的教育内容提取助手。你的任务是识别和提取教材中的核心知识点，而不是简单的内容概述。\n\n"
        "请遵循以下原则提取知识点：\n"
        "1. 只提取真正需要学习和掌握的知识点，而不是所有内容的分点概述\n"
        "2. 重点关注：\n"
        "   - 重要的概念、定义和原理\n"
        "   - 关键公式和定理\n"
        "   - 核心方法和步骤\n"
        "   - 重要的结论和规律\n"
        "   - 需要记忆的关键信息\n"
        "3. 忽略：\n"
        "   - 简单的描述性内容\n"
        "   - 过渡性语句\n"
        "   - 重复的内容\n"
        "   - 非核心的辅助信息\n\n"
        "输出格式要求：\n"
        "1. 每条知识点独立成行，使用 `-` 列表符号开头\n"
        "2. 不使用任何标题（不要有#、##、###）\n"
        "3. 知识点要简洁明了，必要时使用 **加粗** 或 LaTeX 格式\n"
        "4. 不要添加总结、解释、免责声明\n"
        "5. 保留原文中的重要术语、公式、定义、图片引用等，但要精炼\n"
        "6. 只输出知识点列表，其他内容一律不输出"
    )

    def __init__(self, api_key=None, use_local_model=False, local_model_url=None, base_url=None, model_name=None):
        load_dotenv()

        self.use_local_model = use_local_model
        self.local_model_url = local_model_url or os.getenv("LOCAL_MODEL_URL")
        self.client = None
        self.model_name = model_name or "gpt-3.5-turbo"  # 默认模型

        if not self.use_local_model:
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            base_url = base_url or os.getenv("OPENAI_BASE_URL")
            if api_key and base_url:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    http_client=CustomHTTPClient()
                )
            else:
                print("警告: 未设置API密钥或base_url，请设置环境变量或通过参数传入")

    def extract_knowledge_points(self, text, max_tokens=1800, progress_callback=None):
        if not text:
            print("输入文本为空")
            return []
        if self.use_local_model and not self.local_model_url:
            print("未设置本地模型URL，无法提取知识点")
            return []
        if not self.use_local_model and not self.client:
            print("未成功创建client")
            return []

        text_chunks = self._split_text(text, max_tokens)
        all_knowledge_points = []
        total_chunks = len(text_chunks)
        
        if progress_callback:
            progress_callback(0, total_chunks)
            
        for i, chunk in enumerate(text_chunks):
            try:
                if self.use_local_model:
                    knowledge_points_text = self._call_local_model(chunk)
                else:
                    knowledge_points_text = self._call_openai_api(chunk)

                knowledge_points_list = [
                    line.strip() for line in knowledge_points_text.splitlines()
                    if line.strip().startswith("-")
                ]
                all_knowledge_points.extend(knowledge_points_list)
                
                if progress_callback:
                    progress_callback(i+1, total_chunks)
                elif total_chunks > 1:
                    tqdm.write(f"已处理 {i+1}/{total_chunks} 个文本块")

            except Exception as e:
                print(f"调用API提取知识点时出错: {e}")
                # 即使出错也更新进度
                if progress_callback:
                    progress_callback(i+1, total_chunks)

        combined_knowledge = "\n".join(all_knowledge_points)
        return combined_knowledge

    def _call_openai_api(self, text):
        if not self.client:
            raise RuntimeError("OpenAI 客户端未初始化")

        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": f"以下是部分教材内容，请提取关键知识点：\n\n{text}"}
                    ],
                    temperature=0.0,
                    max_tokens=4000,
                    timeout=60  # 设置超时时间为60秒
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise e
                print(f"API调用失败 (尝试 {retry_count}/{max_retries}): {e}")
                import time
                time.sleep(3)

    def _call_local_model(self, text):
        try:
            return self._process_local_model_chunk(text)
        except Exception as e:
            print(f"调用本地模型时出错: {e}")
            return ""

    def _process_local_model_chunk(self, text):
        user_prompt = f"以下是部分教材内容，请提取关键知识点：\n\n{text}"

        payload = {
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 4000
        }

        max_retries = 3 
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = requests.post(self.local_model_url, json=payload, timeout=300)
                response.raise_for_status()
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise e
                print(f"本地模型调用失败 (尝试 {retry_count}/{max_retries}): {e}")
                import time
                time.sleep(3)

        response_data = response.json()

        if "choices" in response_data and len(response_data["choices"]) > 0:
            if "message" in response_data["choices"][0]:
                return response_data["choices"][0]["message"]["content"].strip()
            elif "text" in response_data["choices"][0]:
                return response_data["choices"][0]["text"].strip()
        elif "response" in response_data:
            return response_data["response"].strip()
        elif "text" in response_data:
            return response_data["text"].strip()
        elif "content" in response_data:
            return response_data["content"].strip()
        else:
            return str(response_data)

    def _split_text(self, text, max_tokens, overlap=200):
        chars_per_token = 2
        max_chars = max_tokens * chars_per_token
        overlap_chars = overlap * chars_per_token

        if len(text) <= max_chars:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + max_chars
            if end >= len(text):
                chunks.append(text[start:])
                break

            split_point = text.rfind('\n\n', start, end)
            if split_point == -1 or split_point <= start:
                split_point = text.rfind('\n', start, end)

            if split_point == -1 or split_point <= start:
                for sep in ['. ', '! ', '? ', '。', '！', '？']:
                    split_point = text.rfind(sep, start, end)
                    if split_point > start:
                        split_point += len(sep)
                        break

            if split_point <= start:
                split_point = text.rfind(' ', start, end)

            if split_point <= start:
                split_point = min(end, len(text))

            chunks.append(text[start:split_point])
            start = max(start + (split_point - start) - overlap_chars, start + 1)

        return chunks

    def save_knowledge_points(self, knowledge_points, output_path):
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(knowledge_points)
            print(f"已保存知识点到: {output_path}")
            return output_path
        except Exception as e:
            print(f"保存知识点时出错: {e}")
            return None
