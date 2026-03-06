import PyPDF2
import openai
import os
import re
from config import API_KEY, BASE_URL
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

# 设置OpenAI客户端
client = openai.OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

# 设置tesseract路径（Windows用户需要设置）
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_pdf(pdf_path):
    """
    从PDF文件中提取文本（支持图片PDF）
    """
    text = ""
    try:
        # 尝试使用PyPDF2提取文本
        #with open(pdf_path, 'rb') as file:
        #    reader = PyPDF2.PdfReader(file)
        #    for page_num in range(len(reader.pages)):
        #        page = reader.pages[page_num]
        #        page_text = page.extract_text()
        #        if page_text:
        #            text += page_text

        # 如果PyPDF2提取失败或提取的文本太少，使用OCR
        #if not text or len(text.strip()) < 100:
        #    print("使用OCR提取图片中的文字...")
            # 将PDF转换为图像
        images = convert_from_path(pdf_path)
        for img in images:
            # 使用OCR识别图像中的文字（支持中文）
            img_text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            text += img_text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    return text

def analyze_document_structure(text):
    """
    调用大模型分析文档结构
    """
    prompt = f"""请分析以下文档的结构，识别出所有章节（保留至二级标题），并为每个章节提供详细的编写要求。

输出格式要求：
1. 先概述文档的整体结构和主要内容
2. 然后按层级列出所有章节（保留至二级标题）
3. 为每个章节提供详细的编写要求，包括：
   - 章节的目的和作用
   - 章节应包含的内容要点
   - 编写风格和注意事项
   - 可能需要的专业知识或参考资料
4. 最后提供一份完整的文档编写流程建议

文档内容：
{text}

请以Markdown格式输出，确保结构清晰，内容详细。必须输出整份文档的分析结果。"""

    try:
        response = client.chat.completions.create(
            model="qwen-long",
            messages=[
                {"role": "system", "content": "你是一位专业的文档分析专家，擅长分析各类文档的结构和编写要求。"},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error analyzing document structure: {e}")
        return ""

def save_analysis_to_md(analysis, output_path):
    """
    将分析结果保存为Markdown文件
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(analysis)
        print(f"Analysis saved to {output_path}")
    except Exception as e:
        print(f"Error saving analysis to Markdown: {e}")

def analyze_common_structure(texts):
    """
    分析多篇文档的共性结构
    """
    combined_text = "\n\n==========\n\n".join(texts)
    
    prompt = f"""请分析以下多篇文档的内容，提取它们的共性结构，形成一个统一的目录大纲。

文档内容：
{combined_text}

输出要求：
1. 识别所有文档的共同章节结构
2. 按层级列出完整的目录大纲（至少包含二级标题）
3. 确保大纲覆盖所有文档的核心内容
4. 输出格式为Markdown，使用标题层级表示结构

请只输出目录大纲，不要包含其他内容。"""

    try:
        response = client.chat.completions.create(
            model="qwen-long",
            messages=[
                {"role": "system", "content": "你是一位专业的文档分析专家，擅长分析和提取多个文档的共性结构。"},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error analyzing common structure: {e}")
        return ""

def generate_chapter_description(chapter_title, texts):
    """
    根据章节标题和文档内容生成详细描述
    """
    combined_text = "\n\n==========\n\n".join(texts)
    
    prompt = f"""请根据以下文档内容，为章节 '{chapter_title}' 生成详细的编写要求和描述。

文档内容：
{combined_text}...  # 限制输入长度

输出要求：
1. 详细说明该章节的目的和作用
2. 列出该章节应包含的具体内容要点
3. 提供编写风格和注意事项
4. 说明可能需要的专业知识或参考资料
5. 提供该章节的示例结构

请以Markdown格式输出，确保内容详细、结构清晰。"""

    try:
        response = client.chat.completions.create(
            model="qwen-long",
            messages=[
                {"role": "system", "content": "你是一位专业的文档编写专家，擅长为各个章节生成详细的编写要求。"},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating chapter description: {e}")
        return ""

def extract_chapters_from_outline(outline):
    """
    从目录大纲中提取章节标题（最多二级标题），并保持层级关系
    """
    chapters = []
    current_level1 = None
    lines = outline.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('## '):  # 一级标题
            # 提取标题文本，去除Markdown标记
            chapter_title = line.lstrip('## ').strip()
            current_level1 = chapter_title
            chapters.append((1, chapter_title))
        elif line.startswith('### '):  # 二级标题
            # 提取标题文本，去除Markdown标记
            chapter_title = line.lstrip('### ').strip()
            if current_level1:  # 确保二级标题有对应的一级标题
                chapters.append((2, chapter_title, current_level1))
    return chapters

def main():
    """
    主函数
    """
    # 获取PDF文件路径列表
    # pdf_paths_input = input("请输入PDF文件路径（多个文件用逗号分隔）: ")
    # pdf_paths = [path.strip() for path in pdf_paths_input.split(',')]
    pdf_paths = ["技术标.pdf"]  # 示例路径
    
    # 验证文件存在
    for pdf_path in pdf_paths:
        if not os.path.exists(pdf_path):
            print(f"文件不存在: {pdf_path}")
            return
    
    # 提取所有文档的文本
    print("正在提取PDF文本...")
    texts = []
    for pdf_path in pdf_paths:
        text = extract_text_from_pdf(pdf_path)
        if not text:
            print(f"无法从PDF中提取文本: {pdf_path}")
            return
        texts.append(text)

    #with open("output.txt", 'r', encoding='utf-8') as file:
    #    texts.append(file.read())
    
    # 保存提取的文本（可选）
    #with open("output.txt", "w", encoding="utf-8") as file:
    #    file.write("\n\n".join(texts))
    
    # 分析共性结构
    print("正在分析共性结构...")
    common_structure = analyze_common_structure(texts)
    
    if not common_structure:
        print("分析共性结构失败")
        return
    
    # 创建输出文件夹
    output_dir = "文档分析结果"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 保存目录大纲
    outline_path = os.path.join(output_dir, "目录大纲.md")
    save_analysis_to_md(common_structure, outline_path)
    
    # 提取章节标题
    chapters = extract_chapters_from_outline(common_structure)

    print(chapters)
    
    # 为每个章节生成详细描述
    print("正在为每个章节生成详细描述...")
    for chapter_info in chapters:
        if len(chapter_info) == 2:  # 一级标题
            level, chapter_title = chapter_info
            print(f"处理一级章节: {chapter_title}")
            chapter_description = generate_chapter_description(chapter_title, texts)
            if chapter_description:
                # 生成章节文件名（去除特殊字符）
                chapter_filename = re.sub(r'[\\/:*?"<>|]', '_', chapter_title) + ".md"
                chapter_path = os.path.join(output_dir, chapter_filename)
                save_analysis_to_md(chapter_description, chapter_path)
        #elif len(chapter_info) == 3:  # 二级标题
        #    level, chapter_title, parent_title = chapter_info
        #    print(f"处理二级章节: {parent_title} - {chapter_title}")
        #    # 为二级标题生成描述时，包含父章节信息
        #    full_title = f"{parent_title} - {chapter_title}"
        #    chapter_description = generate_chapter_description(full_title, texts)
        #    if chapter_description:
        #        # 生成章节文件名（去除特殊字符）
        #        chapter_filename = re.sub(r'[\\/:*?"<>|]', '_', full_title) + ".md"
        #        chapter_path = os.path.join(output_dir, chapter_filename)
        #        save_analysis_to_md(chapter_description, chapter_path)
    
    print("分析完成！所有结果已保存到 '文档分析结果' 文件夹中。")

if __name__ == "__main__":
    main()