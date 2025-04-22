import os
import json
from tqdm import tqdm
import openai
import requests
from dotenv import load_dotenv
from openai import OpenAI
import httpx

class KnowledgeExtractor:
    def __init__(self, api_key=None, use_local_model=False, local_model_url=None, base_url=None):
        load_dotenv()

        self.use_local_model = use_local_model
        self.local_model_url = local_model_url or os.getenv("LOCAL_MODEL_URL")
        self.client = None
        transport = httpx.HTTPTransport(proxy="http://127.0.0.1:7890")

        http_client = httpx.Client(transport=transport)

        if not self.use_local_model:
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            base_url = base_url or os.getenv("OPENAI_BASE_URL") 

            # https://ai-yyds.com
            # https://api.openai.com/v1
            # https://ai-yyds.com/v1
            # https://api.tata-api.com/v1
            if api_key:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=base_url if base_url else "https://api.tata-api.com/v1",
                    http_client=http_client
                )
            else:
                print("警告: 未设置OpenAI API密钥，请设置环境变量OPENAI_API_KEY或通过参数传入")
            
    def extract_knowledge_points(self, text, max_tokens=1800):
        """
        从文本中提取知识点
        
        Args:
            text (str): 输入文本
            max_tokens (int): 每次处理的最大token数
            
        Returns:
            list: 知识点列表
        """
        if not text:
            print("输入文本为空")
            return []
            
        if self.use_local_model:
            if not self.local_model_url:
                print("未设置本地模型URL，无法提取知识点")
                return []
        else:
            if not self.client:
                print("未成功创建client")
                return []
            
        text_chunks = self._split_text(text, max_tokens)
        
        all_knowledge_points = []
        
        for i, chunk in enumerate(tqdm(text_chunks, desc="提取知识点")):
            try:
                if self.use_local_model:
                    knowledge_points = self._call_local_model(chunk)
                else:
                    knowledge_points = self._call_openai_api(chunk)
                
                all_knowledge_points.append(knowledge_points)
                
            except Exception as e:
                print(f"调用API提取知识点时出错: {e}")
                
        combined_knowledge = "\n\n".join(all_knowledge_points)
        return combined_knowledge
        
    def _call_openai_api(self, text):
        """
        调用OpenAI API提取知识点
        """
        if not self.client:
            raise RuntimeError("OpenAI 客户端未初始化")
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一个专业的教育内容分析助手。"
                                              "请从提供的教材文本中提取关键知识点，并严格遵循以下要求：\n"
                                              "1. 使用 Markdown 格式组织内容；\n"
                                              "2. 根据原文结构，使用合适的标题层级（#、##、###）；\n"
                                              "3. 重点概念使用 **加粗** 标记；\n"
                                              "4. 所有公式或特殊符号使用 LaTeX 格式；\n"
                                              "5. 保持原文准确性，不随意添加解释或改写内容；\n"
                                              "6. 保留所有原始文本中的图片引用（如 ![图片说明](图片链接)）；\n"
                                              "7. 不要输出额外的总结、说明、免责声明、或与任务无关的文字。\n"
                },
                {"role": "user", "content": f"以下是部分教材内容，请仅按要求提取关键知识点，不要添加其他内容：\n\n{text}"}
            ],
            temperature=0.0,
            max_tokens=4000
        )

        return response.choices[0].message.content.strip()
    
    def _call_local_model(self, text):
        """
        调用本地模型API提取知识点
        
        Args:
            text (str): 输入文本
            
        Returns:
            str: 提取的知识点
        """
        # text_chunks = self._further_split(text, max_tokens=1800)
        # if len(text_chunks) > 1:
        #     print(f"文本过长，已拆分为{len(text_chunks)}个更小的块进行处理")
        #     results = []
        #     for i, chunk in enumerate(text_chunks):
        #         print(f"处理小块 {i+1}/{len(text_chunks)}")
        #         chunk_result = self._process_local_model_chunk(chunk)
        #         if chunk_result:
        #             results.append(chunk_result)
        #     return "\n\n".join(results)
        # else:
        #     return self._process_local_model_chunk(text)
        
        try:
            result = self._process_local_model_chunk(text)
            return result if result else ""
        except Exception as e:
            print(f"调用本地模型时出错: {e}")
            return ""
    
    def _process_local_model_chunk(self, text):
        """处理单个文本块的具体逻辑"""
        system_prompt = (
            "你是一个专业的教育内容分析助手。"
            "请从提供的教材文本中提取关键知识点，并严格遵循以下要求：\n"
            "1. 使用 Markdown 格式组织内容；\n"
            "2. 根据原文结构，使用合适的标题层级（#、##、###）；\n"
            "3. 重点概念使用 **加粗** 标记；\n"
            "4. 所有公式或特殊符号使用 LaTeX 格式；\n"
            "5. 保持原文准确性，不随意添加解释或改写内容；\n"
            "6. 保留所有原始文本中的图片引用（如 ![图片说明](图片链接)）；\n"
            "7. 不要输出额外的总结、说明、免责声明、或与任务无关的文字。\n"
            "你的任务是仅输出格式化后的知识点内容，保持简洁和一致性。"
        )

        user_prompt = f"以下是部分教材内容，请仅按要求提取关键知识点，不要添加其他内容：\n\n{text}"

        
        try:
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.0,
                "max_tokens": 4000
            }
            
            print(f"payload: {payload}")
            response = requests.post(self.local_model_url, json=payload, timeout=300)
            response.raise_for_status()
            
            response_data = response.json()
            print(f"response_data: {response_data}")

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
                
        except Exception as e:
            print(f"调用本地模型API时出错: {e}")
            return ""

    def _further_split(self, text, max_tokens=1800):
        """
        进一步将可能超出模型最大上下文长度的文本分割成更小的块
        
        Args:
            text (str): 输入文本
            max_tokens (int): 每个部分的期望最大token数
            
        Returns:
            list: 文本部分列表
        """
        chars_per_token = 1
        max_chars = max_tokens * chars_per_token
        
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
                for sep in ['. ', '! ', '? ', '。', '！', '？', '；', ';']:
                    split_point = text.rfind(sep, start, end)
                    if split_point > start:
                        split_point += len(sep)  # 包含分隔符
                        break
                        
            if split_point <= start:
                for sep in ['，', ',', ' ']:
                    split_point = text.rfind(sep, start, end)
                    if split_point > start:
                        split_point += len(sep)
                        break
                
            if split_point <= start:
                split_point = min(end, len(text))
                
            chunks.append(text[start:split_point])
            
            start = split_point
            
        return chunks
        
    def _split_text(self, text, max_tokens, overlap=200):
        """
        将文本分割成多个部分，以避免超出token限制
        
        Args:
            text (str): 输入文本
            max_tokens (int): 每个部分的最大token数
            overlap (int): 重叠的token数
            
        Returns:
            list: 文本部分列表
        """
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
                        split_point += len(sep)  # 包含分隔符
                        break
                        
            if split_point <= start:
                split_point = text.rfind(' ', start, end)
                
            if split_point <= start:
                split_point = min(end, len(text))
                
            chunks.append(text[start:split_point])
            
            start = max(start + (split_point - start) - overlap_chars, start + 1)
            
        return chunks
        
    def save_knowledge_points(self, knowledge_points, output_path):
        """
        保存提取的知识点到文件
        
        Args:
            knowledge_points (str): 提取的知识点
            output_path (str): 输出文件路径
            
        Returns:
            str: 保存的文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(knowledge_points)
            print(f"已保存知识点到: {output_path}")
            return output_path
        except Exception as e:
            print(f"保存知识点时出错: {e}")
            return None 