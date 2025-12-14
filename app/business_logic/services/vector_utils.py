# src/utils/vector_utils.py
from typing import Dict, Any
from datetime import datetime
from app.core.config import settings
import requests
from ..services.logger import logger
from ..services.llm_service import create_llm_service
import hashlib

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
    async def create_student_feature_vector(basic_info: Dict[str, Any], portrait: Dict[str, Any]) -> Dict[str, Any]:
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

            # 生成唯一向量ID
            timestamp = datetime.now().timestamp()
            content_hash = hashlib.md5(feature_text.encode()).hexdigest()[:8]
            vector_id = f"student_vector_{int(timestamp)}_{content_hash}"

            # 简单向量化处理（使用特征文本的哈希值表示）
            # 这里使用简单哈希值模拟向量，实际应用中应使用专业的文本嵌入模型            
            headers = {
                "Authorization": f"Bearer {settings.SILICON_FLOW_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "BAAI/bge-m3",
                "input": feature_text,
                "encoding_format": "float"
            }

            response = requests.post("https://api.siliconflow.cn/v1/embeddings", json=payload, headers=headers)
            response_data = response.json()
            feature_vector = response_data["data"][0]["embedding"]
            
            # 创建最终的向量表示对象
            vector_data = {
                "id": vector_id,
                "feature_text": feature_text,
                "feature_vector": feature_vector,
                "metadata": {
                    "student_id": basic_info.get("id", "unknown"),
                    "created_at": timestamp
                }
            }

            return vector_data

        except Exception as e:
            logger.error(f"创建学生特征向量失败: {str(e)}")
            raise