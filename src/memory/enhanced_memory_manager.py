# src/memory/enhanced_memory_manager.py
import traceback
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import time
from pathlib import Path

from src.memory.json_store import JSONMemoryStore
from src.memory.long_term_store import LongTermMemoryStore
from src.memory.initializer import MemoryInitializer
from src.schemas.memory_schemas import SkillMemory, MedicalRecord
from src.utils.logger import logger
from src.utils.exceptions import StateError


def _get_skill_collection_name(agent_type: str, therapy_type: Optional[str] = None) -> str:
    """获取技能集合名称"""
    if agent_type == "profiler":
        return "profiler_skills"
    elif agent_type == "therapist":
        return f"therapist_{therapy_type}_skills"
    raise ValueError(f"Invalid agent_type or therapy_type: {agent_type}, {therapy_type}")


def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    清洗元数据，确保所有值都是ChromaDB支持的类型(字符串、整数、浮点数或布尔值)
    """
    result = {}
    for key, value in metadata.items():
        if value is None:
            result[key] = "none"  # 将None转换为字符串none
        elif isinstance(value, (str, int, float, bool)):
            result[key] = value
        else:
            result[key] = str(value)  # 将其他类型转换为字符串
    return result


class EnhancedMemoryManager:
    """增强型记忆管理器 - 同时管理JSON文件和向量数据库"""

    def __init__(self):
        """初始化增强型记忆管理器"""
        # 创建JSON存储和向量存储
        self.json_store = JSONMemoryStore()
        self.vector_store = LongTermMemoryStore()

        # 创建记忆初始化器
        self.initializer = MemoryInitializer(
            json_store=self.json_store,
            vector_store=self.vector_store
        )

        # 获取配置的治疗师流派
        self.therapy_types = self._get_therapist_types()

        # 更新集合映射，包含所有治疗师流派
        self._collection_mapping = self._create_collection_mapping()

    def _get_therapist_types(self) -> List[str]:
        """
        从配置文件获取所有的治疗师流派类型

        Returns:
            List[str]: 治疗师流派类型列表
        """
        # 默认流派
        therapy_types = ["cbt", "psychodynamic"]

        try:
            # 尝试加载治疗师配置文件
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "therapists_config.json"
            )

            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 提取所有流派ID
                therapy_types = [
                    therapist.get("id")
                    for therapist in config_data.get("therapists", [])
                    if therapist.get("id")
                ]

                logger.info(f"记忆管理器: 从配置文件加载了 {len(therapy_types)} 个治疗流派")

        except Exception as e:
            logger.warning(f"记忆管理器: 加载治疗师配置失败: {str(e)}，将使用默认流派")

        return therapy_types

    def _create_collection_mapping(self) -> Dict[str, str]:
        """
        创建集合映射，动态包含所有治疗师流派

        Returns:
            Dict[str, str]: 集合映射
        """
        # 基础映射
        mapping = {
            "profiler": "profiler_skills",
            "medical_records": "medical_records"
        }

        # 添加所有治疗师流派的映射
        for therapy_type in self.therapy_types:
            mapping[f"therapist_{therapy_type}"] = f"therapist_{therapy_type}_skills"

        return mapping

    async def initialize_memories(self):
        """初始化记忆系统"""
        try:
            # 使用初始化器同步JSON和向量数据库
            await self.initializer.initialize()
            logger.info("记忆系统初始化成功，JSON和向量数据库已同步")
        except Exception as e:
            logger.error(f"记忆系统初始化失败: {str(e)}")
            traceback.print_exc()
            raise StateError("记忆初始化失败") from e

    # === 技能记忆管理 ===
    async def get_skill_memory(self, agent_type: str, therapy_type: Optional[str] = None,
                               query_text: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """获取技能记忆 (支持向量相似度检索)"""
        try:
            collection_name = _get_skill_collection_name(agent_type, therapy_type)
            logger.info(f"从集合 {collection_name} 获取技能记忆")

            # 如果提供了查询文本，进行向量相似度检索
            if query_text:
                from src.utils.embedding_service import get_text_embedding

                query_vector = get_text_embedding(query_text)

                if query_vector is not None:
                    # 使用向量相似度检索
                    skills = await self.vector_store.search_documents(
                        collection_name,
                        query_vector=query_vector,
                        filter_dict=None,
                        limit=limit
                    )
                    logger.info(f"通过向量检索获取到 {len(skills)} 条相关技能记忆")
                    return skills
                else:
                    logger.warning("查询文本向量化失败，使用全量检索")

            # 从向量数据库获取所有文档（或在向量化失败时的后备方案）
            skills = await self.vector_store.search_documents(
                collection_name,
                query_vector=None,
                filter_dict=None,
                limit=100  # 获取所有技能记忆
            )

            logger.info(f"获取到 {len(skills)} 条技能记忆")
            return skills

        except Exception as e:
            logger.error(f"获取技能记忆失败: {str(e)}")
            traceback.print_exc()

            # 如果向量数据库读取失败，尝试从JSON文件读取
            try:
                logger.info(f"尝试从JSON文件读取技能记忆: {collection_name}")
                skills = self.json_store.get_all_documents(collection_name)
                return skills
            except Exception as json_error:
                logger.error(f"从JSON文件读取技能记忆也失败: {str(json_error)}")
                return []

    async def update_skill_memory(self, agent_type: str, skill_data: Dict[str, Any],
                                  therapy_type: Optional[str] = None) -> None:
        """更新技能记忆 (先更新JSON文件，然后更新向量数据库)"""
        try:
            collection_name = _get_skill_collection_name(agent_type, therapy_type)
            logger.info(f"准备更新集合 {collection_name} 中的技能记忆，ID: {skill_data['id']}")

            # 准备完整的技能数据
            full_skill_data = skill_data.copy()

            # 添加必要的元数据
            full_skill_data["agent_type"] = agent_type
            if therapy_type:
                full_skill_data["therapy_type"] = therapy_type

            # 如果没有时间戳，添加当前时间戳
            if "timestamp" not in full_skill_data:
                full_skill_data["timestamp"] = datetime.now().timestamp()

            # 对技能内容进行向量化
            from src.utils.embedding_service import get_text_embedding
            skill_content = full_skill_data.get("content", "")
            skill_vector = get_text_embedding(skill_content)

            if skill_vector is not None:
                full_skill_data["skill_vector"] = skill_vector
                logger.info(f"成功为技能记忆生成向量，维度: {len(skill_vector)}")
            else:
                logger.warning(f"技能记忆向量化失败: {skill_data['id']}")

            # 1. 首先更新JSON文件
            success = self.json_store.add_document(collection_name, full_skill_data)
            if not success:
                raise StateError(f"更新JSON文件失败: {collection_name}/{skill_data['id']}")

            # 2. 然后更新向量数据库
            metadata = {
                "agent_type": agent_type,
                "therapy_type": therapy_type if therapy_type else "none",
                "updated_at": datetime.now().isoformat()
            }

            # 清洗元数据
            metadata = _sanitize_metadata(metadata)
            logger.debug(f"元数据: {metadata}")

            # 检查文档是否已存在
            existing_doc = await self.vector_store.get_document(collection_name, skill_data["id"])

            if existing_doc:
                logger.debug(f"文档 {skill_data['id']} 已存在，进行更新")
                await self.vector_store.update_document(
                    collection_name,
                    skill_data["id"],
                    full_skill_data,
                    metadata
                )
                logger.info(f"向量数据库中的技能记忆已更新: {agent_type}")
            else:
                logger.debug(f"文档 {skill_data['id']} 不存在，进行添加")
                await self.vector_store.add_document(
                    collection_name,
                    skill_data["id"],
                    full_skill_data,
                    metadata
                )
                logger.info(f"向量数据库中添加了新的技能记忆: {agent_type}")

            # 验证操作是否成功
            verification = await self.vector_store.get_document(collection_name, skill_data["id"])
            if verification:
                logger.debug(f"验证成功: 文档 {skill_data['id']} 已正确存储到向量数据库")
            else:
                logger.warning(f"警告: 无法验证文档 {skill_data['id']} 是否正确存储到向量数据库")

        except Exception as e:
            logger.error(f"更新技能记忆失败: {str(e)}")
            traceback.print_exc()
            raise StateError("技能记忆更新失败") from e

    # === 电子病历管理 ===
    async def create_medical_record(self, student_id: str, record_data) -> str:
        """创建电子病历 (先存入JSON，然后存入向量数据库)"""
        try:
            # 生成唯一ID
            record_id = f"record_{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            record_data["recordId"] = record_id

            # 准备完整记录数据
            full_record = record_data.copy()
            full_record["id"] = record_id
            full_record["student_id"] = student_id
            full_record["created_at"] = datetime.now().timestamp()
            full_record["updated_at"] = full_record["created_at"]

            # 1. 首先存入JSON文件
            collection_name = "medical_records"
            success = self.json_store.add_document(collection_name, full_record)
            if not success:
                raise StateError(f"保存医疗记录到JSON文件失败: {record_id}")

            # 2. 然后存入向量数据库
            metadata = {
                "student_id": student_id,
                "created_at": datetime.now().isoformat(),
                "type": "medical_record"
            }

            # 清洗元数据
            metadata = _sanitize_metadata(metadata)

            await self.vector_store.add_document(
                "medical_records",
                record_id,
                full_record,
                metadata
            )
            logger.info(f"创建了学生 {student_id} 的医疗记录: {record_id}")
            return record_id
        except Exception as e:
            logger.error(f"创建医疗记录失败: {str(e)}")
            traceback.print_exc()
            raise StateError("医疗记录创建失败") from e

    async def get_medical_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取单个医疗记录 (直接从向量数据库读取)"""
        try:
            return await self.vector_store.get_document("medical_records", record_id)
        except Exception as e:
            logger.error(f"获取医疗记录失败: {str(e)}")

            # 尝试从JSON读取
            try:
                return self.json_store.get_document("medical_records", record_id)
            except:
                return None

    async def update_medical_record(self, record_id: str, record_data: Dict[str, Any]) -> bool:
        """更新电子病历 (先更新JSON，然后更新向量数据库)"""
        try:
            # 确保更新时间
            full_record = record_data.copy()
            full_record["updated_at"] = datetime.now().timestamp()

            # 确保ID一致
            full_record["id"] = record_id

            # 1. 首先更新JSON文件
            collection_name = "medical_records"
            success = self.json_store.update_document(collection_name, record_id, full_record)
            if not success:
                raise StateError(f"更新医疗记录JSON文件失败: {record_id}")

            # 2. 然后更新向量数据库
            metadata = {
                "student_id": full_record.get("student_id", "unknown"),
                "updated_at": datetime.now().isoformat(),
                "type": "medical_record"
            }

            # 清洗元数据
            metadata = _sanitize_metadata(metadata)

            await self.vector_store.update_document(
                "medical_records",
                record_id,
                full_record,
                metadata
            )
            logger.info(f"更新了医疗记录: {record_id}")
            return True
        except Exception as e:
            logger.error(f"更新医疗记录失败: {str(e)}")
            traceback.print_exc()
            return False

    async def get_student_medical_records(self, student_id: str) -> List[Dict[str, Any]]:
        """获取学生的所有医疗记录 (从向量数据库查询)"""
        try:
            # 构建过滤条件
            filter_dict = {"student_id": student_id}

            # 从向量数据库查询
            records = await self.vector_store.search_documents(
                "medical_records",
                query="",
                filter_dict=filter_dict,
                limit=100
            )

            return records
        except Exception as e:
            logger.error(f"查询学生医疗记录失败: {str(e)}")

            # 尝试从JSON读取并过滤
            try:
                all_records = self.json_store.get_all_documents("medical_records")
                return [r for r in all_records if r.get("student_id") == student_id]
            except:
                return []

    async def persist_memories(self):
        """确保记忆数据被持久化"""
        try:
            # 在ChromaDB 0.6.3中，数据会自动持久化
            # 此方法保留为兼容接口
            await self.vector_store.cleanup()
            logger.info("记忆系统已配置为自动持久化")
        except Exception as e:
            logger.error(f"记忆持久化提示: {str(e)}")

    async def cleanup(self):
        """清理记忆系统资源"""
        try:
            # 确保清理前进行持久化
            await self.persist_memories()
            logger.info("记忆系统清理完成")
        except Exception as e:
            logger.error(f"记忆系统清理失败: {str(e)}")
            raise StateError("记忆清理失败") from e