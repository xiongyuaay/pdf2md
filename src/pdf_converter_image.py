import os
import fitz  # PyMuPDF
import PyPDF2
from pdfminer.high_level import extract_text
from tqdm import tqdm


class PDFConverter:
    def __init__(self, input_path=None):
        self.input_path = input_path
        self.text_content = ""
        self.image_output_dir = None

    def set_pdf(self, input_path):
        self.input_path = input_path
        return self

    def extract_text_with_pdfminer(self):
        try:
            self.text_content = extract_text(self.input_path)
            return self.text_content
        except Exception as e:
            print(f"使用pdfminer提取文本时出错: {e}")
            return ""

    def extract_text_with_pypdf2(self):
        try:
            text = ""
            with open(self.input_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)

                for page_num in tqdm(range(num_pages), desc="提取PDF文本"):
                    page = reader.pages[page_num]
                    extracted = page.extract_text()
                    text += (extracted if extracted else "") + "\n\n"

            self.text_content = text
            return text
        except Exception as e:
            print(f"使用PyPDF2提取文本时出错: {e}")
            return ""

    def extract_images_with_pymupdf(self, image_output_dir=None):
        if not self.input_path:
            print("未设置PDF文件路径")
            return []

        if not image_output_dir:
            base_name = os.path.splitext(self.input_path)[0]
            image_output_dir = f"{base_name}_images"
        os.makedirs(image_output_dir, exist_ok=True)
        self.image_output_dir = image_output_dir

        doc = fitz.open(self.input_path)
        image_paths = []
        image_count = 0

        for page_index in range(len(doc)):
            page = doc[page_index]
            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                image_filename = f"page{page_index + 1}_img{img_index + 1}.{image_ext}"
                image_path = os.path.join(image_output_dir, image_filename)

                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)

                image_paths.append(image_path)
                image_count += 1

        print(f"共提取 {image_count} 张图片，保存在: {image_output_dir}")
        return image_paths

    def convert_to_markdown(self, output_path=None):
        if not self.text_content:
            print("没有提取到文本内容，请先调用extract_text方法")
            return None

        if not output_path:
            base_name = os.path.basename(self.input_path)
            file_name = os.path.splitext(base_name)[0]
            output_path = os.path.join(os.path.dirname(self.input_path), f"{file_name}.md")

        markdown_content = self.text_content

        # 插入图片引用
        if self.image_output_dir and os.path.exists(self.image_output_dir):
            image_files = sorted(os.listdir(self.image_output_dir))
            for image in image_files:
                markdown_content += f"\n\n![{image}]({self.image_output_dir}/{image})"

        try:
            with open(output_path, 'w', encoding='utf-8') as md_file:
                md_file.write(markdown_content)
            print(f"已保存Markdown文件: {output_path}")
            return output_path
        except Exception as e:
            print(f"保存Markdown文件时出错: {e}")
            return None

    def process_pdf(self, output_path=None, extraction_method='pdfminer', extract_images=True):
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

        # 提取图片
        if extract_images:
            self.extract_images_with_pymupdf()

        return self.convert_to_markdown(output_path)
