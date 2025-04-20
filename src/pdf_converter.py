import os
import PyPDF2
from pdfminer.high_level import extract_text
from tqdm import tqdm

class PDFConverter:
    def __init__(self, input_path=None):
        """
        初始化PDF转换器
        
        Args:
            input_path (str): PDF文件路径
        """
        self.input_path = input_path
        self.text_content = ""
        
    def set_pdf(self, input_path):
        """
        设置PDF文件路径
        
        Args:
            input_path (str): PDF文件路径
        """
        self.input_path = input_path
        return self
    
    def extract_text_with_pdfminer(self):
        """
        使用pdfminer提取PDF文本
        
        Returns:
            str: 提取的文本内容
        """
        try:
            self.text_content = extract_text(self.input_path)
            return self.text_content
        except Exception as e:
            print(f"使用pdfminer提取文本时出错: {e}")
            return ""
    
    def extract_text_with_pypdf2(self):
        """
        使用PyPDF2提取PDF文本
        
        Returns:
            str: 提取的文本内容
        """
        try:
            text = ""
            with open(self.input_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)
                
                for page_num in tqdm(range(num_pages), desc="提取PDF文本"):
                    page = reader.pages[page_num]
                    text += page.extract_text() + "\n\n"
                
            self.text_content = text
            return text
        except Exception as e:
            print(f"使用PyPDF2提取文本时出错: {e}")
            return ""
    
    def convert_to_markdown(self, output_path=None):
        """
        将提取的文本转换为Markdown格式并保存
        
        Args:
            output_path (str): 输出Markdown文件路径
            
        Returns:
            str: 保存的文件路径
        """
        if not self.text_content:
            print("没有提取到文本内容，请先调用extract_text方法")
            return None
        
        if not output_path:
            base_name = os.path.basename(self.input_path)
            file_name = os.path.splitext(base_name)[0]
            output_path = os.path.join(os.path.dirname(self.input_path), f"{file_name}.md")
        
        # 文本到Markdown的转换
        markdown_content = self.text_content
        
        try:
            with open(output_path, 'w', encoding='utf-8') as md_file:
                md_file.write(markdown_content)
            print(f"已保存Markdown文件: {output_path}")
            return output_path
        except Exception as e:
            print(f"保存Markdown文件时出错: {e}")
            return None
            
    def process_pdf(self, output_path=None, extraction_method='pdfminer'):
        """
        处理PDF文件：提取文本并转换为Markdown
        
        Args:
            output_path (str): 输出Markdown文件路径
            extraction_method (str): 文本提取方法
            
        Returns:
            str: 保存的文件路径
        """
        if not self.input_path:
            print("未设置PDF文件路径")
            return None
            
        if not os.path.exists(self.input_path):
            print(f"文件不存在: {self.input_path}")
            return None
            
        print(f"正在处理PDF文件: {self.input_path}")
        
        # 提取文本
        if extraction_method.lower() == 'pdfminer':
            self.extract_text_with_pdfminer()
        else:
            self.extract_text_with_pypdf2()
            
        return self.convert_to_markdown(output_path) 