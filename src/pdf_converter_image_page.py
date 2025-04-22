import os
import fitz 
from tqdm import tqdm


class PDFConverter:
    def __init__(self, input_path=None):
        self.input_path = input_path
        self.text_content = ""
        self.image_output_dir = None

    def set_pdf(self, input_path):
        self.input_path = input_path
        return self

    def extract_text_and_images_by_page(self):
        """
        提取每一页的文本和图片（按图片 y 坐标排序），组合为 markdown 格式
        """
        if not self.input_path:
            print("未设置PDF文件路径")
            return []

        doc = fitz.open(self.input_path)
        output = []

        base_name = os.path.splitext(self.input_path)[0]
        image_output_dir = f"{base_name}_images"
        os.makedirs(image_output_dir, exist_ok=True)
        self.image_output_dir = image_output_dir

        for page_num in tqdm(range(len(doc)), desc="提取文本和图片"):
            page = doc[page_num]
            text = page.get_text("text")

            images = []
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                image_filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                image_path = os.path.join(image_output_dir, image_filename)

                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)

                image_rects = page.get_image_rects(xref)
                y_pos = image_rects[0].y0 if image_rects else float('inf')

                images.append((y_pos, image_path))

            images.sort(key=lambda x: x[0])

            page_markdown = f"\n\n## 第 {page_num + 1} 页\n\n{text.strip()}\n"
            for _, image_path in images:
                rel_path = os.path.relpath(image_path, os.path.dirname(self.input_path))
                page_markdown += f"\n\n![图像]({rel_path})\n"

            output.append(page_markdown)

        self.text_content = "\n\n".join(output)
        return self.text_content

    def convert_to_markdown(self, output_path=None):
        if not self.text_content:
            print("没有提取到文本内容，请先调用 extract_text_and_images_by_page 方法")
            return None

        if not output_path:
            base_name = os.path.basename(self.input_path)
            file_name = os.path.splitext(base_name)[0]
            output_path = os.path.join(os.path.dirname(self.input_path), f"{file_name}.md")

        try:
            with open(output_path, 'w', encoding='utf-8') as md_file:
                md_file.write(self.text_content)
            print(f"✅ 已保存Markdown文件: {output_path}")
            return output_path
        except Exception as e:
            print(f"保存Markdown文件时出错: {e}")
            return None

    def process_pdf(self, output_path=None, extraction_method='pdfminer'):
        if not self.input_path:
            print("未设置PDF文件路径")
            return None

        if not os.path.exists(self.input_path):
            print(f"文件不存在: {self.input_path}")
            return None

        print(f"📄 正在处理PDF文件: {self.input_path}")
        self.extract_text_and_images_by_page()
        return self.convert_to_markdown(output_path)
