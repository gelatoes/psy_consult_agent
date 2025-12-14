# src/memory/memory_manager.py
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path

from app.data_access.memory.enhanced_memory_manager import EnhancedMemoryManager
from app.models.memory_schemas import SkillMemory, MedicalRecord
from app.business_logic.services.logger import logger
from app.core.exceptions import StateError


class MemoryManager(EnhancedMemoryManager):
    """高层记忆管理器 - 负责业务逻辑和记忆系统协调

    此类现在继承自EnhancedMemoryManager，同时维护JSON和向量数据库
    保持原有接口不变，以确保兼容性
    """

    def __init__(self):
        """初始化记忆管理器"""
        # 调用父类的初始化方法
        super().__init__()

    # 以下方法保留原接口，但实现委托给父类

    async def reset_working_memory(
            self,
            session_id: str,
            reset_point: str = "post_profiler"
    ) -> None:
        """重置工作记忆到指定点

        Args:
            session_id: 会话ID
            reset_point: 重置点标识
        """
        pass

    async def create_memory_snapshot(
            self,
            session_id: str,
            snapshot_name: str
    ) -> None:
        """创建记忆快照

        Args:
            session_id: 会话ID
            snapshot_name: 快照名称
        """
        pass

    async def restore_memory_snapshot(
            self,
            session_id: str,
            snapshot_name: str
    ) -> None:
        """恢复记忆快照

        Args:
            session_id: 会话ID
            snapshot_name: 快照名称
        """
        pass

    async def create_student_vector(self, student_id: str, vector_data: Dict[str, Any],
                                    record_id: Optional[str] = None) -> str:
        """创建学生特征向量并存储到向量数据库

        Args:
            student_id: 学生ID
            vector_data: 向量数据
            record_id: 关联的病历记录ID

        Returns:
            str: 向量ID
        """
        try:
            # 从向量数据中获取ID
            vector_id = vector_data["id"]

            # 准备元数据
            metadata = {
                "student_id": student_id,
                "record_id": record_id,
                "created_at": vector_data.get("metadata", {}).get("created_at", datetime.now().timestamp()),
                "type": "student_vector"
            }

            # 将向量存入向量数据库
            await self.vector_store.add_document(
                collection_name="student_vectors",
                doc_id=vector_id,
                content=vector_data,
                metadata=metadata
            )

            # 确保索引文件存在
            self._ensure_vector_index_exists()

            # 更新索引文件
            self._update_vector_index(vector_id, student_id, record_id)

            # 将向量数据也保存到JSON文件
            self.json_store.add_document("student_vectors", vector_data)

            logger.info(f"创建了学生 {student_id} 的特征向量: {vector_id}")
            return vector_id
        except Exception as e:
            logger.error(f"创建学生特征向量失败: {str(e)}")
            traceback.print_exc()
            raise StateError("学生特征向量创建失败") from e

    def _ensure_vector_index_exists(self):
        """确保向量索引文件存在"""
        index_path = Path(self.json_store.base_dir).joinpath("vector_index.json")
        if not index_path.exists():
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def _update_vector_index(self, vector_id: str, student_id: str, record_id: Optional[str] = None):
        """更新向量索引文件

        Args:
            vector_id: 向量ID
            student_id: 学生ID
            record_id: 可选的病历记录ID
        """
        index_path = Path(self.json_store.base_dir).joinpath("vector_index.json")
        try:
            # 读取现有索引
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            # 更新索引
            index_data[vector_id] = {
                "student_id": student_id,
                "record_id": record_id,
                "updated_at": datetime.now().timestamp()
            }

            # 写回索引文件
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, ensure_ascii=False, indent=2, fp=f)

        except Exception as e:
            logger.error(f"更新向量索引失败: {str(e)}")
            traceback.print_exc()

    async def get_vector_by_id(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """根据向量ID获取向量数据

        Args:
            vector_id: 向量ID

        Returns:
            Optional[Dict[str, Any]]: 向量数据，如果不存在则返回None
        """
        try:
            return await self.vector_store.get_document("student_vectors", vector_id)
        except Exception as e:
            logger.error(f"获取向量数据失败: {str(e)}")
            # 尝试从JSON获取
            return self.json_store.get_document("student_vectors", vector_id)

    async def find_similar_vectors(self, feature_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """查找与给定特征文本相似的向量

        Args:
            feature_text: 特征文本
            limit: 返回结果的最大数量

        Returns:
            List[Dict[str, Any]]: 相似向量列表
        """
        try:
            results = await self.vector_store.search_documents(
                collection_name="student_vectors",
                query=feature_text,
                filter_dict=None,
                limit=limit
            )
            return results
        except Exception as e:
            logger.error(f"查找相似向量失败: {str(e)}")
            return []

    async def get_vector_index(self) -> Dict[str, Dict[str, Any]]:
        """获取向量索引

        Returns:
            Dict[str, Dict[str, Any]]: 向量索引数据
        """
        index_path = Path(self.json_store.base_dir).joinpath("vector_index.json")
        try:
            if not index_path.exists():
                self._ensure_vector_index_exists()
                return {}

            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"获取向量索引失败: {str(e)}")
            return {}