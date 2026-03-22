"""PDF 简历解析器：使用 pdfplumber 提取 PDF 文本内容"""

from pathlib import Path
from typing import Optional
from utils.logger import logger


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """
    从 PDF 文件中提取纯文本内容。
    
    Args:
        pdf_path: PDF 文件路径
    
    Returns:
        提取的文本内容
    
    Raises:
        FileNotFoundError: 文件不存在
        ImportError: pdfplumber 未安装
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"不是 PDF 文件: {pdf_path}")

    try:
        import pdfplumber
    except ImportError:
        raise ImportError("请先安装 pdfplumber: pip install pdfplumber")

    logger.info(f"开始解析 PDF: {pdf_path.name}")

    text_parts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        total_pages = len(pdf.pages)
        logger.info(f"PDF 共 {total_pages} 页")

        for i, page in enumerate(pdf.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
                logger.debug(f"  第 {i}/{total_pages} 页: {len(page_text)} 字符")
            else:
                logger.warning(f"  第 {i}/{total_pages} 页: 未提取到文本")

    full_text = "\n\n".join(text_parts)
    logger.info(f"PDF 解析完成: 共提取 {len(full_text)} 字符")

    if not full_text.strip():
        logger.warning("警告：PDF 中未提取到任何文本，可能是扫描件或图片 PDF")

    return full_text


def extract_text_with_layout(pdf_path: str | Path) -> str:
    """
    带布局信息的 PDF 文本提取（保留表格结构）。
    适用于格式化的简历模板。
    """
    pdf_path = Path(pdf_path)

    try:
        import pdfplumber
    except ImportError:
        raise ImportError("请先安装 pdfplumber: pip install pdfplumber")

    text_parts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            # 优先提取表格
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        cells = [cell if cell else "" for cell in row]
                        text_parts.append(" | ".join(cells))
                    text_parts.append("")  # 表格间空行

            # 再提取非表格区域的文本
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return "\n".join(text_parts)
