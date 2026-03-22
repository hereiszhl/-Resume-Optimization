"""通用工具函数：JSON 解析清洗、文件 I/O、时间处理等"""

import re
import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime


def extract_json_from_response(text: str) -> Optional[Dict[str, Any]]:
    """
    从 LLM 响应中提取 JSON 对象。
    支持多种格式：```json 代码块、裸 JSON、花括号/方括号定位。
    包含对 LLM 常见 JSON 格式错误的修复（中文标点、尾逗号等）。
    """
    if not text:
        return None

    def _try_parse(s: str) -> Optional[Dict[str, Any]]:
        """尝试解析 JSON，包含自动修复"""
        s = s.strip()
        if not s:
            return None
        # 第一次：直接解析
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        # 第二次：修复 LLM 常见的 JSON 格式问题后重试
        fixed = _fix_llm_json(s)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    def _fix_llm_json(s: str) -> str:
        """修复 LLM 输出的常见非标准 JSON"""
        # 修复 "key":：value → "key": value （中文冒号紧跟英文冒号）
        s = re.sub(r'"\s*:\s*：\s*', '": ', s)
        # 修复 "key"：value → "key": value （纯中文冒号作为 key-value 分隔）
        s = re.sub(r'"\s*：\s*', '": ', s)
        # 修复中文引号
        s = s.replace('\u201c', '"').replace('\u201d', '"')  # ""
        s = s.replace('\u2018', "'").replace('\u2019', "'")  # ''
        # 修复尾逗号 ,} 和 ,]
        s = re.sub(r',\s*}', '}', s)
        s = re.sub(r',\s*]', ']', s)
        return s

    # 尝试1: 提取 ```json ... ``` 代码块
    pattern = r'```(?:json)?\s*\n?(.*?)\n?\s*```'
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        for match in matches:
            result = _try_parse(match)
            if result is not None:
                return result

    # 尝试2: 直接解析整个文本
    result = _try_parse(text)
    if result is not None:
        return result

    # 尝试3: 定位最外层花括号
    brace_match = re.search(r'\{.*\}', text, re.DOTALL)
    if brace_match:
        result = _try_parse(brace_match.group())
        if result is not None:
            return result

    # 尝试4: 定位最外层方括号（数组）
    bracket_match = re.search(r'\[.*\]', text, re.DOTALL)
    if bracket_match:
        result = _try_parse(bracket_match.group())
        if result is not None:
            return result

    return None


def save_json(data: Any, file_path: str | Path, ensure_ascii: bool = False) -> Path:
    """保存数据为 JSON 文件"""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果是 Pydantic 模型，先转为 dict
    if hasattr(data, 'model_dump'):
        data = data.model_dump()

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=2, default=str)

    return file_path


def load_json(file_path: str | Path) -> Any:
    """加载 JSON 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_timestamp() -> str:
    """生成时间戳字符串"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def truncate_text(text: str, max_length: int = 500) -> str:
    """截断文本并添加省略号"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def read_text_file(file_path: str | Path) -> str:
    """读取文本文件，自动检测编码"""
    file_path = Path(file_path)
    for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
        try:
            return file_path.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"无法读取文件 {file_path}，请检查文件编码")


def read_text_files_from_dir(dir_path: str | Path, extensions: list = None) -> list:
    """
    读取目录下所有文本文件。
    
    Returns:
        [{"filename": "xxx.txt", "content": "..."}]
    """
    dir_path = Path(dir_path)
    if not dir_path.exists():
        return []

    if extensions is None:
        extensions = [".txt", ".md", ".json"]

    results = []
    for f in sorted(dir_path.iterdir()):
        if f.is_file() and f.suffix.lower() in extensions:
            try:
                content = read_text_file(f)
                results.append({"filename": f.name, "content": content})
            except Exception as e:
                results.append({"filename": f.name, "content": f"[读取失败: {e}]"})

    return results
