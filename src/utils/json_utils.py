# src/utils/json_utils.py
import json
import re
from typing import Dict, Any, Optional, List, Union, TypeVar, Type
import traceback
from src.utils.logger import logger

T = TypeVar('T', bound=Dict[str, Any])


def extract_json_from_text(text: str) -> str:
    """
    从文本中提取JSON部分

    Args:
        text: 可能包含JSON的文本

    Returns:
        str: 提取出的JSON字符串
    """
    json_match = re.search(r'({.*})', text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    return text


def parse_json(text: str, default_value: Optional[T] = None) -> Union[T, Dict[str, Any]]:
    """
    安全地解析JSON字符串

    Args:
        text: 要解析的JSON字符串
        default_value: 解析失败时返回的默认值

    Returns:
        Dict[str, Any]: 解析后的JSON对象或默认值
    """
    try:
        # 提取JSON部分
        json_str = extract_json_from_text(text)
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        error_msg = f"JSON解析失败: {str(e)}"
        logger.error(f"{error_msg}\n原始文本: {text}")
        traceback.print_exc()

        if default_value is not None:
            return default_value
        return {"error": error_msg, "original_text": text}


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    验证JSON对象是否包含所有必需字段

    Args:
        data: 要验证的JSON对象
        required_fields: 必需字段列表

    Returns:
        bool: 是否包含所有必需字段
    """
    return all(field in data for field in required_fields)