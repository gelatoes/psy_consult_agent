# src/memory/system_initializer.py
"""
记忆系统启动初始化器
负责在应用启动时检查和同步JSON文件与向量数据库
"""
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from app.data_access.memory.initializer import MemoryInitializer
from app.data_access.memory.memory_manager import MemoryManager
from app.business_logic.services.logger import logger


class MemorySystemInitializer:
    """记忆系统启动初始化器

    作为系统入口点组件，检查和初始化记忆子系统
    """

    @staticmethod
    async def initialize_memory_system() -> MemoryManager:
        """
        初始化整个记忆系统

        1. 创建记忆管理器
        2. 检查JSON文件和向量数据库状态
        3. 必要时执行同步

        Returns:
            MemoryManager: 初始化好的记忆管理器实例
        """
        logger.info("开始初始化记忆系统...")

        # 获取动态咨询师配置
        therapist_types = MemorySystemInitializer._get_therapist_types()
        logger.info(f"检测到 {len(therapist_types)} 个心理咨询流派: {', '.join(therapist_types)}")

        # 创建记忆管理器
        memory_manager = MemoryManager()

        # 检查向量数据库目录是否存在
        vector_db_dir = Path(memory_manager.vector_store.persist_directory)
        vector_db_exists = vector_db_dir.exists() and any(
            os.listdir(vector_db_dir)) if vector_db_dir.exists() else False

        # 检查JSON记忆目录是否存在
        json_dir = Path(memory_manager.json_store.base_dir)
        json_exists = json_dir.exists() and any(os.listdir(json_dir)) if json_dir.exists() else False

        logger.info(f"检测到向量数据库: {'是' if vector_db_exists else '否'}")
        logger.info(f"检测到JSON记忆文件: {'是' if json_exists else '否'}")

        # 根据检测结果决定初始化策略
        if vector_db_exists and json_exists:
            logger.info("向量数据库和JSON文件都存在，进行增量同步")
            # 使用初始化器进行增量同步
            initializer = MemoryInitializer(
                json_store=memory_manager.json_store,
                vector_store=memory_manager.vector_store
            )
            await initializer.initialize()

        elif json_exists and not vector_db_exists:
            logger.info("只有JSON文件存在，从JSON重建向量数据库")
            # 使用初始化器从JSON重建向量数据库
            initializer = MemoryInitializer(
                json_store=memory_manager.json_store,
                vector_store=memory_manager.vector_store
            )
            await initializer.rebuild_vector_db_from_json()

        elif vector_db_exists and not json_exists:
            logger.info("只有向量数据库存在，从向量数据库生成JSON文件")
            # 这种情况需要实现从向量数据库重建JSON文件的功能
            await MemorySystemInitializer._rebuild_json_from_vector_db(memory_manager)

        else:
            logger.info("向量数据库和JSON文件都不存在，创建空记忆系统")
            # 初始化空的记忆系统
            await memory_manager.initialize_memories()

        # 确保为所有治疗师流派创建记忆集合
        await MemorySystemInitializer._ensure_therapist_collections(memory_manager, therapist_types)

        logger.info("记忆系统初始化完成")
        return memory_manager

    @staticmethod
    async def _rebuild_json_from_vector_db(memory_manager: MemoryManager) -> None:
        """
        从向量数据库中重建JSON文件

        Args:
            memory_manager: 记忆管理器
        """
        logger.info("从向量数据库重建JSON文件")

        # 首先初始化向量数据库的集合
        await memory_manager.vector_store.init_collections()

        # 获取所有治疗师流派
        therapist_types = MemorySystemInitializer._get_therapist_types()

        # 定义要处理的集合列表
        collections = [
            "profiler_skills",
            "medical_records",
            "student_vectors"  # 添加学生特征向量集合
        ]

        # 添加所有治疗师流派的集合
        for therapy_type in therapist_types:
            collections.append(f"therapist_{therapy_type}_skills")

        # 遍历所有集合
        for collection_name in collections:
            logger.info(f"从向量数据库导出集合: {collection_name}")

            try:
                # 从向量数据库获取所有文档
                documents = await memory_manager.vector_store.search_documents(
                    collection_name,
                    query="",
                    filter_dict=None,
                    limit=1000  # 设置较大的限制以获取所有文档
                )

                if not documents:
                    logger.info(f"集合 {collection_name} 为空，跳过导出")
                    continue

                logger.info(f"为集合 {collection_name} 导出 {len(documents)} 个文档")

                # 将文档写入JSON
                for doc in documents:
                    # 确保文档有ID
                    if "id" not in doc:
                        logger.warning(f"跳过没有ID的文档: {doc}")
                        continue

                    # 将文档添加到JSON
                    success = memory_manager.json_store.add_document(collection_name, doc)
                    if not success:
                        logger.warning(f"将文档 {doc['id']} 写入JSON失败")

                # 如果是学生特征向量集合，还需要重建索引文件
                if collection_name == "student_vectors":
                    await MemorySystemInitializer._rebuild_vector_index(memory_manager, documents)

            except Exception as e:
                logger.error(f"从向量数据库导出集合 {collection_name} 时出错: {str(e)}")

        logger.info("JSON文件重建完成")

    @staticmethod
    async def _rebuild_vector_index(memory_manager: MemoryManager, vector_documents: List[Dict[str, Any]]):
        """重建向量索引文件"""
        try:
            index_path = Path(memory_manager.json_store.base_dir).joinpath("vector_index.json")
            index_data = {}

            for doc in vector_documents:
                vector_id = doc.get("id")
                if not vector_id:
                    continue

                metadata = doc.get("metadata", {})
                student_id = metadata.get("student_id")
                record_id = metadata.get("record_id")

                if not student_id:
                    continue

                index_data[vector_id] = {
                    "student_id": student_id,
                    "record_id": record_id,
                    "updated_at": metadata.get("created_at", datetime.now().timestamp())
                }

            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, ensure_ascii=False, indent=2, fp=f)

            logger.info(f"重建了向量索引文件，包含 {len(index_data)} 个索引项")
        except Exception as e:
            logger.error(f"重建向量索引文件失败: {str(e)}")

    @staticmethod
    def _get_therapist_types() -> List[str]:
        """
        从配置文件获取所有的治疗师流派类型

        Returns:
            List[str]: 治疗师流派类型列表
        """
        # 默认流派
        therapist_types = ["cbt", "psychodynamic"]

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
                therapist_types = [
                    therapist.get("id")
                    for therapist in config_data.get("therapists", [])
                    if therapist.get("id")
                ]

        except Exception as e:
            logger.warning(f"加载治疗师配置失败: {str(e)}，将使用默认流派")

        return therapist_types

    @staticmethod
    async def _ensure_therapist_collections(memory_manager: MemoryManager, therapist_types: List[str]) -> None:
        """
        确保所有治疗师流派的记忆集合都已创建

        Args:
            memory_manager: 记忆管理器
            therapist_types: 治疗师流派类型列表
        """
        # 为每个治疗师流派验证记忆集合
        for therapy_type in therapist_types:
            collection_name = f"therapist_{therapy_type}_skills"

            try:
                # 尝试从集合中获取技能
                skills = await memory_manager.get_skill_memory("therapist", therapy_type=therapy_type)

                # 如果集合为空，添加默认技能
                if not skills:
                    logger.info(f"为治疗师流派 {therapy_type} 添加默认技能记忆")

                    # 创建基础技能
                    skill_memory = {
                        "id": f"{therapy_type}_base_skill_1",
                        "content": f"作为{therapy_type}流派的心理咨询师，能够通过专业技能帮助来访者解决心理问题。",
                        "timestamp": time.time() if 'time' in globals() else 0,
                        "therapy_type": therapy_type
                    }

                    # 存储基础技能
                    await memory_manager.update_skill_memory(
                        "therapist",
                        skill_memory,
                        therapy_type=therapy_type
                    )

                logger.info(f"治疗师流派 {therapy_type} 的记忆集合已验证")

            except Exception as e:
                logger.error(f"验证治疗师流派 {therapy_type} 的记忆集合时出错: {str(e)}")