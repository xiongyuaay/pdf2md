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

    SYSTEM_PROMPT_JSON = """你是一个专业的教育内容提取助手。你的任务是识别和提取教材中的核心知识点，并将它们组织为结构化的JSON格式。

请遵循以下原则提取知识点：
1. 只提取真正需要学习和掌握的知识点，而不是所有内容的分点概述
2. 重点关注：
   - 重要的概念、定义和原理
   - 关键公式和定理
   - 核心方法和步骤
   - 重要的结论和规律
   - 需要记忆的关键信息
3. 忽略：
   - 简单的描述性内容
   - 过渡性语句
   - 重复的内容
   - 非核心的辅助信息

输出格式要求：
1. 使用有效的JSON格式，格式如下:
{
  "knowledge_points": [
    {
      "id": "kp1",
      "title": "知识点标题 (简短概括)",
      "content": "知识点详细内容 (确保字符串中的特殊字符如换行符 \\n, 引号 \\\" 等都已正确转义，所有控制字符 U+0000 至 U+001F 都需转义为 \\\\uXXXX 格式)",
      "type": "知识点类型",
      "importance": 0.8,
      "related_points": ["kp2", "kp3"]
    },
    ...
  ]
}

2. 'title' 字段应该是对知识点内容的简短、概括性的标题。
3. 'content' 字段包含知识点的详细描述和解释。确保其内容符合JSON字符串规范，特别是针对特殊字符的转义处理。
4. 类型(type)应从以下几种中选择: "concept"(概念), "principle"(原理), "formula"(公式), "method"(方法), "fact"(事实)
5. 重要性(importance)是0-1之间的小数，表示这个知识点的重要程度
6. 相关知识点(related_points)应包含与当前知识点直接相关的其他知识点ID
7. 确保JSON格式有效且可以被解析
8. 只输出JSON，不要添加任何其他文本、解释或标记
"""

    SYSTEM_PROMPT_REFINE_JSON = (
        "你是一个专业的知识点优化助手。你的任务是基于用户提供的初步提取的JSON知识点列表，进行审查和优化，以提高整体质量。\n\n"
        "请遵循以下优化原则：\n"
        "1. **严格审查**：仔细评估每个知识点，判断其是否为真正的核心知识点。\n"
        "2. **删除非核心内容**：如果一个条目更像是章节标题、简单描述、过渡句或非关键信息，请将其从列表中删除。\n"
        "3. **完善与浓缩**：对于保留的知识点：\n"
        "   - 确保其 'title' (标题) 准确概括核心内容，简洁明了。\n"
        "   - 确保其 'content' (内容) 表达完整、准确，但仍然保持高度浓缩和精炼，避免冗余。\n"
        "   - 必要时，可以合并内容相似但可以整合的知识点，或调整其表述使其更佳。\n"
        "4. **字段一致性**：确保每个知识点都包含 'id', 'title', 'content', 'type', 'importance', 'related_points' 字段。如果原始条目缺少这些字段，请尝试合理补充或赋予默认值（例如 'type': 'unknown', 'importance': 0.5）。\n"
        "5. **ID 和关联**：你可以重新生成 'id' 以确保最终列表中的ID是连续且唯一的（例如 kp1, kp2, ...）。如果删除了某些知识点，请确保 'related_points' 中的引用仍然有效，或者移除无效的引用。\n"
        "6. **保持JSON结构**：输出必须是与输入格式完全相同的JSON结构：\n"
        "{\n"
        "  \"knowledge_points\": [\n"
        "    {\n"
        "      \"id\": \"kp1\",\n"
        "      \"title\": \"优化后的标题\",\n"
        "      \"content\": \"优化后完整且浓缩的内容\",\n"
        "      \"type\": \"概念\",\n"
        "      \"importance\": 0.9,\n"
        "      \"related_points\": [\"kp2\"]\n"
        "    },\n"
        "    ...\n"
        "  ]\n"
        "}\n\n"
        "7. **只输出JSON**：不要添加任何其他文本、解释或标记。你的输出应该是可以直接被程序解析的JSON。\n\n"
        "用户将提供一个包含 'knowledge_points' 列表的JSON对象。请你处理这个列表并返回优化后的版本。"
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
            print("输入文本为空")
            return json.dumps({"knowledge_points": []}, ensure_ascii=False, indent=2)
        
        if self.use_local_model and not self.local_model_url:
            print("未设置本地模型URL，无法提取知识点")
            return json.dumps({"knowledge_points": []}, ensure_ascii=False, indent=2)
            
        if not self.use_local_model and not self.client:
            print("未成功创建client")
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
            print("输入的知识点JSON为空，无法精炼。")
            return json.dumps({"knowledge_points": []}, ensure_ascii=False, indent=2)

        try:
            parsed_input_json = json.loads(knowledge_json_str)
            if "knowledge_points" not in parsed_input_json or not isinstance(parsed_input_json["knowledge_points"], list):
                print("输入的JSON格式不正确，缺少'knowledge_points'列表，无法精炼。")
                return knowledge_json_str 
        except json.JSONDecodeError as e:
            print(f"输入的知识点JSON无效: {e}。无法精炼。")
            return knowledge_json_str

        if not parsed_input_json["knowledge_points"]:
            print("知识点列表为空，无需精炼。")
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


    
    
