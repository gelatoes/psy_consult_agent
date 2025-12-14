# /src/utils/embedding_service.py
import requests
import json
from typing import List, Optional
from src.utils.logger import logger


class EmbeddingService:
    """硅基流动向量化服务"""

    def __init__(self, api_key: str = "sk-bhmzptjtxnrzivvdtyfxcmtxhiatzggqwfkggntziujxtjbh",
                 model: str = "BAAI/bge-m3"):
        """
        初始化向量化服务

        Args:
            api_key: 硅基流动API密钥
            model: 向量化模型名称
        """
        self.api_key = api_key
        self.model = model
        self.url = "https://api.siliconflow.cn/v1/embeddings"

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        获取文本的向量表示

        Args:
            text: 需要向量化的文本

        Returns:
            Optional[List[float]]: 向量列表，失败时返回None
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "input": text,
                "encoding_format": "float"
            }

            response = requests.post(self.url, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error(f"向量化API调用失败: {response.status_code}, {response.text}")
                return None

            response_data = response.json()

            if "data" not in response_data or len(response_data["data"]) == 0:
                logger.error("向量化响应格式错误")
                return None

            embedding = response_data["data"][0]["embedding"]
            logger.info(f"成功获取向量，维度: {len(embedding)}")
            return embedding

        except Exception as e:
            logger.error(f"向量化服务调用失败: {str(e)}")
            return None


# 全局向量化服务实例
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """获取全局向量化服务实例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def get_text_embedding(text: str) -> Optional[List[float]]:
    """
    获取文本向量的便捷函数

    Args:
        text: 需要向量化的文本

    Returns:
        Optional[List[float]]: 向量列表，失败时返回None
    """
    service = get_embedding_service()
    return service.get_embedding(text)