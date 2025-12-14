# src/memory/initializer.py
"""
记忆系统初始化器
负责检查JSON文件和向量数据库，并在必要时执行同步
"""
import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.data_access.memory.json_store import JSONMemoryStore
from app.data_access.memory.long_term_store import LongTermMemoryStore
from app.business_logic.services.logger import logger
from app.business_logic.services.vector_utils import VectorUtils

class MemoryInitializer:
    """记忆系统初始化器

    检查JSON记忆和向量数据库的状态，并在需要时进行同步
    """

    def __init__(self, json_store: Optional[JSONMemoryStore] = None,
                 vector_store: Optional[LongTermMemoryStore] = None):
        """
        初始化记忆系统初始化器

        Args:
            json_store: 可选的JSON存储对象，如果为None则创建新的
            vector_store: 可选的向量存储对象，如果为None则创建新的
        """
        self.json_store = json_store if json_store else JSONMemoryStore()
        self.vector_store = vector_store if vector_store else LongTermMemoryStore()

        # 获取向量数据库目录路径
        self.vector_db_dir = Path(self.vector_store.persist_directory)

        logger.info(f"记忆初始化器创建完成，JSON路径: {self.json_store.base_dir}, 向量库路径: {self.vector_db_dir}")

        # 获取可用的治疗流派
        self.therapy_types = self._get_available_therapy_types()

    def _get_available_therapy_types(self) -> List[str]:
        """
        从配置文件获取所有可用的治疗流派

        Returns:
            List[str]: 可用的治疗流派列表
        """
        therapy_types = ["cbt", "psychodynamic"]  # 默认支持的流派

        try:
            # 尝试从配置文件加载流派
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "therapists_config.json"
            )

            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 获取所有流派ID
                therapy_types = [
                    therapist.get("id")
                    for therapist in config_data.get("therapists", [])
                    if therapist.get("id")
                ]

                logger.info(f"从配置文件加载了 {len(therapy_types)} 个治疗流派")

        except Exception as e:
            logger.warning(f"加载治疗流派配置失败: {str(e)}，将使用默认流派")

        return therapy_types

    async def initialize(self):
        """
        初始化记忆系统

        检查JSON和向量数据库状态，执行必要的同步
        """
        # 检查向量数据库目录是否存在
        vector_db_exists = self.vector_db_dir.exists() and any(os.listdir(self.vector_db_dir))

        if not vector_db_exists:
            logger.info("向量数据库不存在或为空，将从JSON文件重建")
            await self.rebuild_vector_db_from_json()
        else:
            logger.info("向量数据库已存在，检查是否需要更新")

            # 获取所有集合
            await self.vector_store.init_collections()

            # 执行增量同步确保两种存储保持一致
            await self._sync_json_and_vector_db()

        # 确保所有必要的集合都已创建
        await self._ensure_all_collections()

    async def _sync_json_and_vector_db(self):
        """
        同步JSON文件和向量数据库，确保两者数据一致
        """
        logger.info("开始同步JSON文件和向量数据库")

        # 获取所有需要处理的集合名称
        collections = [
            "profiler_skills",
            "medical_records",
            "student_vectors"  # 添加学生特征向量集合
        ]

        # 添加所有治疗师流派的集合
        for therapy_type in self.therapy_types:
            collections.append(f"therapist_{therapy_type}_skills")

        # 同步每个集合
        for collection_name in collections:
            await self._sync_collection(collection_name)

    async def _sync_collection(self, collection_name: str):
        """
        同步单个集合

        Args:
            collection_name: 集合名称
        """
        try:
            logger.info(f"同步集合: {collection_name}")

            # 从JSON获取所有文档
            json_docs = self.json_store.get_all_documents(collection_name)
            if not json_docs:
                logger.info(f"JSON文件 {collection_name} 为空，无需同步")
                return

            # 获取向量数据库中的所有文档
            vector_docs = await self.vector_store.search_documents(
                collection_name=collection_name,
                query="",
                filter_dict=None,
                limit=10000  # 足够大的限制以获取所有文档
            )

            # 创建向量文档ID集合以便快速查找
            vector_doc_ids = {doc.get("id") for doc in vector_docs if doc.get("id")}

            # 找出需要添加到向量数据库的文档
            for doc in json_docs:
                doc_id = doc.get("id")
                if not doc_id:
                    continue

                if doc_id not in vector_doc_ids:
                    logger.info(f"将文档 {doc_id} 从JSON同步到向量数据库")

                    # 构建元数据
                    metadata = self._build_metadata_for_document(collection_name, doc)

                    # 添加到向量数据库
                    await self.vector_store.add_document(
                        collection_name=collection_name,
                        doc_id=doc_id,
                        content=doc,
                        metadata=metadata
                    )

        except Exception as e:
            logger.error(f"同步集合 {collection_name} 失败: {str(e)}")

    def _build_metadata_for_document(self, collection_name: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        为文档构建元数据

        Args:
            collection_name: 集合名称
            doc: 文档数据

        Returns:
            Dict[str, Any]: 元数据
        """
        metadata = {}

        if collection_name == "profiler_skills":
            metadata = {
                "agent_type": "profiler",
                "updated_at": doc.get("timestamp", ""),
            }
        elif collection_name.startswith("therapist_"):
            therapy_type = collection_name.split("_")[1]
            metadata = {
                "agent_type": "therapist",
                "therapy_type": therapy_type,
                "updated_at": doc.get("timestamp", ""),
            }
        elif collection_name == "medical_records":
            metadata = {
                "student_id": doc.get("studentId", doc.get("student_id", "")),
                "created_at": doc.get("createdAt", doc.get("created_at", "")),
                "type": "medical_record"
            }
        elif collection_name == "student_vectors":
            metadata = {
                "student_id": doc.get("metadata", {}).get("student_id", ""),
                "created_at": doc.get("metadata", {}).get("created_at", ""),
                "record_id": doc.get("metadata", {}).get("record_id", ""),
                "type": "student_vector"
            }

        return metadata

    async def _ensure_all_collections(self):
        """确保所有必要的集合都已创建"""
        collections = [
            "profiler_skills",
            "medical_records",
            "student_vectors"  # 添加学生特征向量集合
        ]

        # 添加所有治疗师流派的集合
        for therapy_type in self.therapy_types:
            collections.append(f"therapist_{therapy_type}_skills")

        # 确保每个集合都存在于向量数据库中
        for collection_name in collections:
            if collection_name not in self.vector_store._collections:
                try:
                    self.vector_store._collections[collection_name] = self.vector_store.client.create_collection(
                        name=collection_name
                    )
                    logger.info(f"创建了缺失的集合: {collection_name}")
                except Exception as e:
                    logger.error(f"创建集合 {collection_name} 失败: {str(e)}")

    async def rebuild_vector_db_from_json(self):
        """
        从JSON文件重建向量数据库
        """
        # 如果向量数据库目录存在但为空，确保它是完全空的
        if self.vector_db_dir.exists():
            shutil.rmtree(self.vector_db_dir)
            os.makedirs(self.vector_db_dir)
            logger.info(f"清空并重新创建向量数据库目录: {self.vector_db_dir}")

        # 初始化向量数据库集合
        await self.vector_store.init_collections()

        # 定义要处理的集合列表，动态包含所有治疗流派
        collections = [
            "profiler_skills",
            "medical_records",
            "student_vectors"  # 添加学生特征向量集合
        ]

        # 添加所有治疗流派的集合
        for therapy_type in self.therapy_types:
            collections.append(f"therapist_{therapy_type}_skills")

        logger.info(f"准备导入以下集合: {collections}")

        # 遍历所有集合，从JSON导入到向量数据库
        for collection_name in collections:
            await self._import_collection(collection_name)

        # 检查特征向量索引文件并重建特征向量
        await self._rebuild_student_vectors_if_needed()

        logger.info("已从JSON文件重建完成向量数据库")

    async def _rebuild_student_vectors_if_needed(self):
        """重建学生特征向量（如果需要）"""
        try:
            # 检查索引文件是否存在
            index_path = Path(self.json_store.base_dir).joinpath("vector_index.json")
            if not index_path.exists():
                logger.info("向量索引文件不存在，将创建空索引文件")
                with open(index_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                return

            # 读取索引文件
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            if not index_data:
                logger.info("向量索引为空，尝试从病历重建特征向量")

                # 获取所有医疗记录
                medical_records = self.json_store.get_all_documents("medical_records")
                if not medical_records:
                    logger.info("没有医疗记录，无法重建特征向量")
                    return

                # 重建每个医疗记录的特征向量
                for record in medical_records:
                    student_id = record.get("studentId", record.get("student_id"))
                    record_id = record.get("id")
                    basic_info = record.get("basic_info", {})
                    portrait = record.get("portrait", {})

                    if not student_id or not record_id or not basic_info:
                        continue

                    # 创建特征向量
                    vector_data = VectorUtils.create_student_feature_vector(basic_info, portrait)
                    vector_id = vector_data["id"]

                    # 添加到向量数据库
                    metadata = {
                        "student_id": student_id,
                        "record_id": record_id,
                        "created_at": vector_data.get("metadata", {}).get("created_at", ""),
                        "type": "student_vector"
                    }

                    await self.vector_store.add_document(
                        collection_name="student_vectors",
                        doc_id=vector_id,
                        content=vector_data,
                        metadata=metadata
                    )

                    # 更新索引
                    index_data[vector_id] = {
                        "student_id": student_id,
                        "record_id": record_id,
                        "updated_at": datetime.now().timestamp()
                    }

                    logger.info(f"从病历 {record_id} 重建特征向量 {vector_id}")

                # 保存更新后的索引
                with open(index_path, 'w', encoding='utf-8') as f:
                    json.dump(index_data, ensure_ascii=False, indent=2, fp=f)

                logger.info(f"重建了 {len(index_data)} 个特征向量")
        except Exception as e:
            logger.error(f"重建特征向量失败: {str(e)}")

    async def _import_collection(self, collection_name: str):
        """
        导入特定集合的JSON数据到向量数据库

        Args:
            collection_name: 集合名称
        """
        # 获取格式化的文档列表
        formatted_docs = self.json_store.json_to_vector_db_format(collection_name)

        if not formatted_docs:
            logger.info(f"集合 {collection_name} 中没有文档，跳过导入")
            return

        logger.info(f"从JSON导入 {len(formatted_docs)} 条文档到向量数据库集合: {collection_name}")

        # 遍历文档并添加到向量数据库
        for doc in formatted_docs:
            doc_id = doc["id"]
            # 构建元数据
            metadata = {}

            # 根据集合类型设置适当的元数据
            if collection_name == "profiler_skills":
                metadata = {
                    "agent_type": "profiler",
                    "updated_at": doc.get("timestamp", ""),
                }
            elif collection_name.startswith("therapist_"):
                therapy_type = collection_name.split("_")[1]
                metadata = {
                    "agent_type": "therapist",
                    "therapy_type": therapy_type,
                    "updated_at": doc.get("timestamp", ""),
                }
            elif collection_name == "medical_records":
                metadata = {
                    "student_id": doc.get("student_id", ""),
                    "created_at": doc.get("created_at", ""),
                    "type": "medical_record"
                }

            # 将文档添加到向量数据库
            try:
                await self.vector_store.add_document(
                    collection_name=collection_name,
                    doc_id=doc_id,
                    content=doc,
                    metadata=metadata
                )
                logger.info(f"已导入文档 {doc_id} 到集合 {collection_name}")
            except Exception as e:
                logger.error(f"导入文档 {doc_id} 到集合 {collection_name} 时出错: {str(e)}")