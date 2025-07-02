import os
import json
import re
from tqdm import tqdm
import openai
import requests
from dotenv import load_dotenv
from openai import OpenAI
import httpx
import time

class CustomHTTPClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        kwargs.pop("proxies", None) 
        super().__init__(*args, **kwargs)

class KnowledgeExtractor:
    SYSTEM_PROMPT = (
        "你是一个专业的教育内容提取助手，提取教材中的核心知识点。"
        "重点关注：重要概念、定义、原理、公式、定理、方法、步骤、结论、规律。"
        "输出格式：每行用'-'开头的知识点列表，简洁明了，只输出知识点。"
    )

    SYSTEM_PROMPT_JSON = """提取教材核心知识点，输出JSON格式:
{
  "knowledge_points": [
    {
      "id": "kp1",
      "title": "简短标题",
      "content": "详细内容(转义特殊字符)",
      "type": "concept/principle/formula/method/fact",
      "importance": 0.8,
      "related_points": ["kp2"]
    }
  ]
}
只输出有效JSON，无其他内容。"""

    SYSTEM_PROMPT_REFINE_JSON = (
        "优化知识点JSON：删除非核心内容，完善标题和内容，确保字段完整，"
        "修正关联关系，重新生成连续ID。保持相同JSON结构，只输出JSON。"
    )

    def __init__(self, api_key=None, use_local_model=False, local_model_url=None, base_url=None, model_name=None):
        load_dotenv()

        self.use_local_model = use_local_model
        self.local_model_url = local_model_url or os.getenv("LOCAL_MODEL_URL")
        self.client = None
        self.model_name = model_name or "gpt-3.5-turbo"

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
            return json.dumps({"knowledge_points": []}, ensure_ascii=False, indent=2)
        
        if self.use_local_model and not self.local_model_url:
            return json.dumps({"knowledge_points": []}, ensure_ascii=False, indent=2)
            
        if not self.use_local_model and not self.client:
            return json.dumps({"knowledge_points": []}, ensure_ascii=False, indent=2)

        system_prompt = self.SYSTEM_PROMPT_JSON
        text_chunks = self._split_text(text, max_tokens)
        all_json_results = []
        total_chunks = len(text_chunks)
        
        if progress_callback: progress_callback(0, total_chunks)
            
        for i, chunk in enumerate(text_chunks):
            raw_model_output = None
            string_to_be_parsed = None

            try:
                raw_model_output = self._call_model_api(chunk, system_prompt)
                
                string_to_be_parsed = self._extract_json(raw_model_output)
                parsed_json = json.loads(string_to_be_parsed)

                if "knowledge_points" in parsed_json and isinstance(parsed_json["knowledge_points"], list):
                    all_json_results.extend(parsed_json["knowledge_points"])

            except json.JSONDecodeError as e:
                print(f"解析初步提取的JSON失败: {e}")

            except Exception as e:
                print(f"调用API提取知识点或处理时出错 (块 {i+1}/{total_chunks}): {e}")
            
            if progress_callback: progress_callback(i+1, total_chunks)
            elif total_chunks > 1: tqdm.write(f"已处理 {i+1}/{total_chunks} 个文本块进行初步提取")
        
        return self._post_process_knowledge_points(all_json_results)

    def refine_knowledge_points(self, knowledge_json_str, progress_callback=None):
        if not knowledge_json_str:
            return json.dumps({"knowledge_points": []}, ensure_ascii=False, indent=2)

        try:
            parsed_input_json = json.loads(knowledge_json_str)
            if "knowledge_points" not in parsed_input_json or not isinstance(parsed_input_json["knowledge_points"], list):
                return knowledge_json_str 
        except json.JSONDecodeError:
            return knowledge_json_str

        if not parsed_input_json["knowledge_points"]:
            return knowledge_json_str

        user_input_for_refinement = knowledge_json_str

        try:
            refined_json_result_str = self._call_model_api(user_input_for_refinement, self.SYSTEM_PROMPT_REFINE_JSON)
            clean_refined_json_str = self._extract_json(refined_json_result_str)
            
            parsed_refined_json = json.loads(clean_refined_json_str)
            refined_points = []
            if "knowledge_points" in parsed_refined_json and isinstance(parsed_refined_json["knowledge_points"], list):
                refined_points = parsed_refined_json["knowledge_points"]
            else:
                print(f"模型精炼结果的JSON结构不符合预期（缺少knowledge_points列表）。原始输出：{refined_json_result_str[:500]}...")
                if isinstance(parsed_refined_json, list):
                    refined_points = parsed_refined_json
                else:
                    print("由于精炼结果解析失败，将返回原始知识点。")
                    return knowledge_json_str

            return self._post_process_knowledge_points(refined_points, is_refinement=True)

        except json.JSONDecodeError as e:
            print(f"解析精炼后的JSON失败: {e}。数据: {refined_json_result_str[:200]}...")
            return knowledge_json_str
        except Exception as e:
            print(f"调用API精炼知识点时出错: {e}")
            return knowledge_json_str

    def _post_process_knowledge_points(self, points_list, is_refinement=False):
        processed_results = []
        for item in points_list:
            if isinstance(item, dict):
                processed_results.append(item)
            else:
                step_name = "精炼后" if is_refinement else "初步提取"
                print(f"警告: {step_name}发现非字典类型的知识点: {item}，已忽略。")

        temp_id_to_final_id_map = {}
        final_processed_points = []
        for i, point in enumerate(processed_results):
            original_id = point.get("id")
            new_id = f"kp{i+1}"
            point["id"] = new_id
            if original_id:
                temp_id_to_final_id_map[original_id] = new_id
            final_processed_points.append(point)
        
        for point in final_processed_points:
            if "related_points" in point and isinstance(point["related_points"], list):
                valid_related_points = []
                for rel_id in point["related_points"]:
                    if rel_id in temp_id_to_final_id_map:
                        valid_related_points.append(temp_id_to_final_id_map[rel_id])
                    elif rel_id in [p["id"] for p in final_processed_points]:
                        valid_related_points.append(rel_id)
                point["related_points"] = list(set(valid_related_points))[:3]
            elif "related_points" in point: 
                point["related_points"] = []

        final_json_obj = {"knowledge_points": final_processed_points}
        return json.dumps(final_json_obj, ensure_ascii=False, indent=2)

    def _call_model_api(self, user_content, system_prompt):
        if self.use_local_model:
            return self._call_local_model(user_content, system_prompt)
        else:
            return self._call_openai_api(user_content, system_prompt)

    def _extract_json(self, text):
        text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
        return text

    def _call_openai_api(self, user_text_content, system_prompt):
        if not self.client:
            raise RuntimeError("OpenAI 客户端未初始化")

        max_retries = 3; retry_count = 0
        while retry_count < max_retries:
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_text_content}
                    ],
                    temperature=0.0, max_tokens=4000, timeout=120
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries: raise e
                print(f"OpenAI API调用失败 (尝试 {retry_count}/{max_retries}): {e}. 重试中...")
                time.sleep(2 ** retry_count)

    def _call_local_model(self, user_text_content, system_prompt):
        if not self.local_model_url:
            raise RuntimeError("本地模型URL未设置")

        payload = {
            "model": self.model_name, 
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text_content}
            ],
            "stream": False 
        }
        max_retries = 3; retry_count = 0
        while retry_count < max_retries:
            try:
                response = requests.post(self.local_model_url, json=payload, timeout=240)
                response.raise_for_status()
                data = response.json()
                if "choices" in data and data["choices"] and "message" in data["choices"][0] and "content" in data["choices"][0]["message"]:
                    return data["choices"][0]["message"]["content"].strip()
                elif "message" in data and "content" in data["message"]:
                    return data["message"]["content"].strip()
                elif "response" in data:
                    return data["response"].strip()
                else:
                    raise ValueError("本地模型响应格式不兼容")
            except requests.exceptions.RequestException as e:
                retry_count += 1
                if retry_count >= max_retries: raise e
                print(f"本地模型API调用失败 (尝试 {retry_count}/{max_retries}): {e}. 重试中...")
                time.sleep(2 ** retry_count)
            except Exception as e: raise e
            
    def _split_text(self, text, max_tokens, overlap=200):
        length_function = len 
        chunks = []
        current_pos = 0
        text_len = length_function(text)
        if text_len == 0: return chunks
        while current_pos < text_len:
            end_pos = current_pos + max_tokens 
            if end_pos >= text_len:
                chunks.append(text[current_pos:])
                break
            chunk_candidate = text[current_pos:end_pos]
            sentence_end_pos = -1
            for p in ['.', '!', '?', '。', '！', '？', '\n']:
                found_p = chunk_candidate.rfind(p)
                if found_p > sentence_end_pos: sentence_end_pos = found_p
            if sentence_end_pos != -1: actual_end_pos = current_pos + sentence_end_pos + 1
            else: 
                space_pos = chunk_candidate.rfind(' ')
                if space_pos != -1: actual_end_pos = current_pos + space_pos + 1
                else: actual_end_pos = end_pos
            chunks.append(text[current_pos:actual_end_pos])
            current_pos = actual_end_pos - overlap 
            if current_pos < 0 : current_pos = 0 
        return chunks

    def save_knowledge_points(self, knowledge_json_str, output_path_base):
        """
        保存知识点。JSON是主要格式。
        
        Args:
            knowledge_json_str: 包含知识点的JSON字符串
            output_path_base: 输出文件路径的基础名 (不含扩展名)
            
        Returns:
            保存的JSON文件路径，如果失败则返回None
        """
        json_output_path = f"{output_path_base}.json"
        try:
            parsed_json = json.loads(knowledge_json_str)
            with open(json_output_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_json, f, ensure_ascii=False, indent=2)
            print(f"知识点已成功保存到JSON文件: {json_output_path}")
            return json_output_path
        except json.JSONDecodeError as e:
            print(f"保存知识点到JSON时发生错误（JSON无效）: {e}")
            error_path = f"{output_path_base}_error.json"
            with open(error_path, 'w', encoding='utf-8') as f:
                f.write(knowledge_json_str)
            print(f"原始JSON字符串已保存到: {error_path}")
            return None
        except Exception as e:
            print(f"保存知识点到JSON时发生未知错误: {e}")
            return None

    def convert_json_to_md(self, knowledge_json_str):
        try:
            data = json.loads(knowledge_json_str)
            if "knowledge_points" not in data or not isinstance(data["knowledge_points"], list):
                print("JSON数据格式不正确，缺少'knowledge_points'列表")
                return ""
            
            md_lines = []
            for point in data["knowledge_points"]:
                title = point.get("title", "")
                content = point.get("content", "无内容")
                type_info = point.get("type", "未知类型")
                importance = point.get("importance", "未知重要性")
                
                if title:
                    md_lines.append(f"- **{title}**")
                    md_lines.append(f"  - {content}")
                else:
                    md_lines.append(f"- **{content}**")
                
                md_lines.append(f"  - 类型: {type_info}")
                md_lines.append(f"  - 重要性: {importance}")
                
                related = point.get("related_points", [])
                if related and isinstance(related, list):
                    related_str = ", ".join(related)
                    md_lines.append(f"  - 相关知识点: {related_str}")
                md_lines.append("") # 添加空行分隔
                
            return "\n".join(md_lines)
        except json.JSONDecodeError:
            print("JSON解析失败，无法转换为Markdown")
            return ""
        except Exception as e:
            print(f"转换为Markdown时发生错误: {e}")
            return ""

    def save_markdown_from_json(self, knowledge_json_str, output_path_base):
        md_content = self.convert_json_to_md(knowledge_json_str)
        if not md_content:
            print("Markdown内容为空，不保存文件。")
            return None

        md_output_path = f"{output_path_base}.md"
        try:
            with open(md_output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            print(f"知识点已成功转换为Markdown并保存: {md_output_path}")
            return md_output_path
        except Exception as e:
            print(f"保存Markdown文件时发生错误: {e}")
            return None


    
    
