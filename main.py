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

def main():
    """
    主函数
    """
    # 获取PDF文件路径
    #pdf_path = input("请输入PDF文件路径: ")
    pdf_path="技术标.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"文件不存在: {pdf_path}")
        return
    
    # 提取文本
    print("正在提取PDF文本...")
    text = extract_text_from_pdf(pdf_path)

    with open("output.txt", "w", encoding="utf-8") as file:
        file.write(text)

    if not text:
        print("无法从PDF中提取文本")
        return
    
    # 分析文档结构
    print("正在分析文档结构...")
    analysis = analyze_document_structure(text)
    
    if not analysis:
        print("文档分析失败")
        return
    
    # 生成输出文件名
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = f"{base_name}_分析.md"
    
    # 保存分析结果
    save_analysis_to_md(analysis, output_path)
    
    print("分析完成！")

if __name__ == "__main__":
    main()