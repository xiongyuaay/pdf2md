# 保留原有 import
import os
import re
import json
from tqdm import tqdm
import openai
import requests
from dotenv import load_dotenv

class KnowledgeExtractor:
    def __init__(self, api_key=None, use_local_model=False, local_model_url=None):
        load_dotenv()
        self.use_local_model = use_local_model
        self.local_model_url = local_model_url or os.getenv("LOCAL_MODEL_URL")

        if self.use_local_model:
            if not self.local_model_url:
                print("警告: 未设置本地模型URL，请设置环境变量LOCAL_MODEL_URL或通过参数传入")
        else:
            openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not openai.api_key:
                print("警告: 未设置OpenAI API密钥，请设置环境变量OPENAI_API_KEY或通过参数传入")

    def extract_knowledge_points(self, text, max_tokens=4000, items_per_page=20):
        if not text:
            print("输入文本为空")
            return ""

        if self.use_local_model and not self.local_model_url:
            print("未设置本地模型URL，无法提取知识点")
            return ""

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
        return self._clean_and_paginate_output(combined_knowledge, items_per_page=items_per_page)

    def _call_openai_api(self, text):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个专业的教育内容分析助手，负责从教材中提炼出结构清晰、重点突出的知识点。\n\n"
                        "**输出要求：**\n"
                        "1. 使用 Markdown 格式；\n"
                        "2. 合理使用标题层级（#、##、###）来表示章节结构；\n"
                        "3. 使用 **加粗** 标记核心术语与概念；\n"
                        "4. 公式使用 LaTeX 格式，包裹于`$$`中；\n"
                        "5. 内容应忠实于原文，不得凭空添加；\n"
                        "6. 同类条目避免重复，语言简洁明确。\n\n"
                        "请确保输出清晰、可读，并适合教学辅助使用。"
                    )
                },
                {"role": "user", "content": f"请从以下教材文本中提取关键知识点：\n\n{text}"}
            ],
            temperature=0.0,
            max_tokens=4000
        )
        return response.choices[0].message['content'].strip()

    def _call_local_model(self, text):
        try:
            result = self._process_local_model_chunk(text)
            return result if result else ""
        except Exception as e:
            print(f"调用本地模型时出错: {e}")
            return ""

    def _process_local_model_chunk(self, text):
        system_prompt = (
            "你是一个专业的教育内容分析助手，负责从教材中提炼出结构清晰、重点突出的知识点。\n\n"
            "**输出要求：**\n"
            "1. 使用 Markdown 格式；\n"
            "2. 合理使用标题层级（#、##、###）来表示章节结构；\n"
            "3. 使用 **加粗** 标记核心术语与概念；\n"
            "4. 公式使用 LaTeX 格式，包裹于`$$`中；\n"
            "5. 内容应忠实于原文，不得凭空添加；\n"
            "6. 同类条目避免重复，语言简洁明确。\n\n"
            "请确保输出清晰、可读，并适合教学辅助使用。"
        )
        user_prompt = f"请从以下教材文本中提取关键知识点：\n\n{text}"
        try:
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.0,
                "max_tokens": 4000
            }
            response = requests.post(self.local_model_url, json=payload, timeout=300)
            response.raise_for_status()
            response_data = response.json()

            if "choices" in response_data and len(response_data["choices"]) > 0:
                choice = response_data["choices"][0]
                return choice.get("message", {}).get("content", choice.get("text", "")).strip()
            return response_data.get("response") or response_data.get("text") or response_data.get("content") or str(response_data)
        except Exception as e:
            print(f"调用本地模型API时出错: {e}")
            return ""

    def _clean_and_paginate_output(self, text, list_style="numbered", items_per_page=20):
        text = re.sub(r'以下是.*?[:：]\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^\s*(?:[-*+]|[0-9]+[.)])\s+', 'TEMP_MARKER ', text, flags=re.MULTILINE)

        lines = text.splitlines()
        items, buffer = [], []

        for line in lines:
            if line.startswith('TEMP_MARKER '):
                if buffer:
                    items.append('\n'.join(buffer).strip())
                    buffer = []
                buffer.append(line.replace('TEMP_MARKER ', '', 1))
            else:
                buffer.append(line)
        if buffer:
            items.append('\n'.join(buffer).strip())

        pages = []
        for i in range(0, len(items), items_per_page):
            page_items = items[i:i+items_per_page]
            page_lines = [
                f"{idx + 1 + i}. {item}" if list_style == "numbered" else f"- {item}"
                for idx, item in enumerate(page_items)
            ]
            page_md = f"## 第 {(i // items_per_page) + 1} 页\n\n" + '\n\n'.join(page_lines)
            pages.append(page_md)

        return '\n\n'.join(pages)

    def save_knowledge_points(self, knowledge_points, output_path):
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(knowledge_points)
            print(f"已保存知识点到: {output_path}")
            return output_path
        except Exception as e:
            print(f"保存知识点时出错: {e}")
            return None

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
