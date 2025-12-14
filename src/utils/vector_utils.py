# src/utils/vector_utils.py
import json
from typing import Dict, Any, List, Optional
import hashlib
from datetime import datetime
import numpy as np

from src.utils.logger import logger
from src.utils.llm_service import create_llm_service


class VectorUtils:
    """
    向量化工具类，提供将学生信息转换为向量表示的功能
    """

    @staticmethod
    def extract_features_to_text(basic_info: Dict[str, Any], portrait: Dict[str, Any]) -> str:
        """
        从学生基本信息和心理画像中提取关键特征，并拼接成文本

        Args:
            basic_info: 学生基本信息
            portrait: 学生心理画像

        Returns:
            str: 拼接后的特征文本
        """
        features = []

        # 提取基本信息
        if basic_info:
            for key, value in basic_info.items():
                if isinstance(value, (str, int, float, bool)):
                    features.append(f"{key}:{value}")

        # 提取心理画像中的事件信息
        if portrait and "events" in portrait:
            for key, value in portrait["events"].items():
                features.append(f"event_{key}:{value}")

        # 提取心理画像中的情绪信息
        if portrait and "emotions" in portrait:
            for key, value in portrait["emotions"].items():
                features.append(f"emotion_{key}:{value}")

        # 提取心理画像中的行为信息
        if portrait and "behaviors" in portrait:
            for key, value in portrait["behaviors"].items():
                features.append(f"behavior_{key}:{value}")

        # 拼接成文本
        return " ".join(features)

    @staticmethod
    def create_student_feature_vector(basic_info: Dict[str, Any], portrait: Dict[str, Any]) -> Dict[str, Any]:
        """
        将学生基本信息和心理画像合并并创建特征向量

        Args:
            basic_info: 学生基本信息
            portrait: 学生心理画像

        Returns:
            Dict[str, Any]: 包含向量表示、元数据和ID的信息
        """
        try:
            # 提取特征文本
            feature_text = VectorUtils.extract_features_to_text(basic_info, portrait)

            # 生成向量ID（基于特征文本的哈希）
            timestamp = datetime.now().timestamp()
            content_hash = hashlib.md5(feature_text.encode()).hexdigest()[:8]
            vector_id = f"student_vector_{int(timestamp)}_{content_hash}"

            # 使用统一的向量化服务获取向量
            from src.utils.embedding_service import get_text_embedding

            feature_vector = get_text_embedding(feature_text)

            # 创建向量数据对象
            vector_data = {
                "id": vector_id,
                "feature_text": feature_text,
                "feature_vector": feature_vector,  # 可能为None，存储时需要处理
                "metadata": {
                    "student_id": basic_info.get("id", "unknown"),
                    "created_at": timestamp
                }
            }

            return vector_data

        except Exception as e:
            logger.error(f"创建学生特征向量失败: {str(e)}")
            raise