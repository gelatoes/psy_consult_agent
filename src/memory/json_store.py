# src/memory/json_store.py
"""
JSON记忆存储功能
提供JSON文件与向量数据库之间的中间表示
"""
import os
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.utils.logger import logger


class JSONMemoryStore:
    """JSON记忆存储管理器

    负责读写JSON文件作为向量数据库的中间表示
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        初始化JSON记忆存储

        Args:
            base_dir: JSON文件基础目录，默认为src/json-memories
        """
        # 如果没有指定基础目录，使用默认路径
        if base_dir is None:
            # 在src目录下创建json-memories文件夹
            self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).joinpath("json-memories")
        else:
            self.base_dir = Path(base_dir)

        # 确保基础目录存在
        os.makedirs(self.base_dir, exist_ok=True)

        # 获取可用的治疗流派
        self.therapy_types = self._get_available_therapy_types()

        # 各类记忆的文件路径
        self.memory_files = self._initialize_memory_files()

        # 初始化文件
        self._init_files()

        logger.info(f"JSON记忆存储初始化完成，基础目录: {self.base_dir}")

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
            logger.info(f"加载治疗流派配置失败: {str(e)}，将使用默认流派")

        return therapy_types

    def _initialize_memory_files(self) -> Dict[str, Path]:
        """
        初始化记忆文件路径，包括动态加载的治疗流派

        Returns:
            Dict[str, Path]: 记忆文件路径字典
        """
        memory_files = {
            "profiler_skills": self.base_dir.joinpath("profiler_skills.json"),
            "medical_records": self.base_dir.joinpath("medical_records.json"),
            "student_vectors": self.base_dir.joinpath("student_vectors.json"),  # 添加学生特征向量文件
        }

        # 为每个治疗流派添加文件路径
        for therapy_type in self.therapy_types:
            collection_name = f"therapist_{therapy_type}_skills"
            memory_files[collection_name] = self.base_dir.joinpath(f"{collection_name}.json")

        return memory_files

    def _init_files(self):
        """初始化所有JSON文件"""
        for file_path in self.memory_files.values():
            if not file_path.exists():
                # 如果文件不存在，创建带有空列表的初始文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                logger.info(f"创建初始JSON文件: {file_path}")
            else:
                logger.info(f"已存在JSON文件: {file_path}")

    def get_all_documents(self, collection_name: str) -> List[Dict[str, Any]]:
        """
        获取特定集合所有文档

        Args:
            collection_name: 集合名称 (例如 "profiler_skills")

        Returns:
            List[Dict[str, Any]]: 文档列表
        """
        # 如果请求的集合不存在但是是治疗师技能集合，则动态创建
        if collection_name not in self.memory_files and collection_name.startswith("therapist_"):
            # 提取治疗流派
            therapy_type = collection_name.split("_")[1]
            if therapy_type not in self.therapy_types:
                self.therapy_types.append(therapy_type)
                logger.info(f"添加新的治疗流派: {therapy_type}")

            # 添加新的文件路径
            self.memory_files[collection_name] = self.base_dir.joinpath(f"{collection_name}.json")

            # 初始化文件
            if not self.memory_files[collection_name].exists():
                with open(self.memory_files[collection_name], 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                logger.info(f"创建新的治疗流派JSON文件: {self.memory_files[collection_name]}")

        if collection_name not in self.memory_files:
            logger.info(f"警告: 未找到集合 {collection_name} 的JSON文件")
            return []

        try:
            with open(self.memory_files[collection_name], 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.info(f"读取JSON文件 {self.memory_files[collection_name]} 时出错: {str(e)}")
            return []

    def get_document(self, collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        获取特定文档

        Args:
            collection_name: 集合名称
            doc_id: 文档ID

        Returns:
            Optional[Dict[str, Any]]: 找到的文档，未找到返回None
        """
        documents = self.get_all_documents(collection_name)

        for doc in documents:
            if doc.get("id") == doc_id:
                return doc

        return None

    def add_document(self, collection_name: str, document: Dict[str, Any]) -> bool:
        """
        添加文档到集合

        Args:
            collection_name: 集合名称
            document: 要添加的文档

        Returns:
            bool: 添加是否成功
        """
        # 如果集合不存在但是是治疗师技能集合，则动态创建
        if collection_name not in self.memory_files and collection_name.startswith("therapist_"):
            # 提取治疗流派
            therapy_type = collection_name.split("_")[1]
            if therapy_type not in self.therapy_types:
                self.therapy_types.append(therapy_type)
                logger.info(f"添加新的治疗流派: {therapy_type}")

            # 添加新的文件路径
            self.memory_files[collection_name] = self.base_dir.joinpath(f"{collection_name}.json")

            # 初始化文件
            if not self.memory_files[collection_name].exists():
                with open(self.memory_files[collection_name], 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                logger.info(f"创建新的治疗流派JSON文件: {self.memory_files[collection_name]}")

        if collection_name not in self.memory_files:
            logger.info(f"警告: 未找到集合 {collection_name} 的JSON文件")
            return False

        try:
            # 读取现有文档
            documents = self.get_all_documents(collection_name)

            # 检查是否已存在相同ID的文档
            for i, doc in enumerate(documents):
                if doc.get("id") == document.get("id"):
                    logger.info(f"文档ID {document.get('id')} 已存在，将更新而非添加")
                    documents[i] = document
                    break
            else:
                # 如果循环完成没有找到匹配的ID，添加新文档
                documents.append(document)

            # 写回文件
            with open(self.memory_files[collection_name], 'w', encoding='utf-8') as f:
                json.dump(documents, ensure_ascii=False, indent=2, fp=f)

            logger.info(f"已添加/更新文档到 {collection_name}, ID: {document.get('id')}")
            return True

        except Exception as e:
            logger.info(f"添加文档到 {collection_name} 时出错: {str(e)}")
            return False

    def update_document(self, collection_name: str, doc_id: str, document: Dict[str, Any]) -> bool:
        """
        更新特定文档

        Args:
            collection_name: 集合名称
            doc_id: 要更新的文档ID
            document: 新的文档内容

        Returns:
            bool: 更新是否成功
        """
        if collection_name not in self.memory_files:
            logger.info(f"警告: 未找到集合 {collection_name} 的JSON文件")
            return False

        try:
            # 读取现有文档
            documents = self.get_all_documents(collection_name)
            updated = False

            # 查找并更新文档
            for i, doc in enumerate(documents):
                if doc.get("id") == doc_id:
                    # 确保ID保持一致
                    document["id"] = doc_id
                    documents[i] = document
                    updated = True
                    break

            if not updated:
                logger.info(f"文档ID {doc_id} 不存在，无法更新")
                return False

            # 写回文件
            with open(self.memory_files[collection_name], 'w', encoding='utf-8') as f:
                json.dump(documents, ensure_ascii=False, indent=2, fp=f)

            logger.info(f"已更新文档 {doc_id} 在 {collection_name}")
            return True

        except Exception as e:
            logger.info(f"更新文档 {doc_id} 时出错: {str(e)}")
            return False

    def remove_document(self, collection_name: str, doc_id: str) -> bool:
        """
        从集合中移除文档

        Args:
            collection_name: 集合名称
            doc_id: 要移除的文档ID

        Returns:
            bool: 移除是否成功
        """
        if collection_name not in self.memory_files:
            logger.info(f"警告: 未找到集合 {collection_name} 的JSON文件")
            return False

        try:
            # 读取现有文档
            documents = self.get_all_documents(collection_name)
            original_length = len(documents)

            # 过滤掉要删除的文档
            documents = [doc for doc in documents if doc.get("id") != doc_id]

            if len(documents) == original_length:
                logger.info(f"文档ID {doc_id} 不存在，无需删除")
                return False

            # 写回文件
            with open(self.memory_files[collection_name], 'w', encoding='utf-8') as f:
                json.dump(documents, ensure_ascii=False, indent=2, fp=f)

            logger.info(f"已从 {collection_name} 中删除文档 {doc_id}")
            return True

        except Exception as e:
            logger.info(f"删除文档 {doc_id} 时出错: {str(e)}")
            return False

    def json_to_vector_db_format(self, collection_name: str) -> List[Dict[str, Any]]:
        """
        将JSON格式转换为向量数据库可接受的格式

        Args:
            collection_name: 集合名称

        Returns:
            List[Dict[str, Any]]: 格式化后的文档列表
        """
        documents = self.get_all_documents(collection_name)
        formatted_docs = []

        for doc in documents:
            # 拷贝文档以避免修改原始数据
            formatted_doc = doc.copy()

            # 特定处理逻辑可以根据集合类型添加
            if collection_name == "profiler_skills":
                # 确保必要的元数据字段存在
                if "timestamp" not in formatted_doc:
                    formatted_doc["timestamp"] = time.time()
                if "agent_type" not in formatted_doc:
                    formatted_doc["agent_type"] = "profiler"

            elif collection_name.startswith("therapist_"):
                # 处理咨询师技能特定格式
                therapy_type = collection_name.split("_")[1]  # 提取流派
                if "timestamp" not in formatted_doc:
                    formatted_doc["timestamp"] = time.time()
                if "agent_type" not in formatted_doc:
                    formatted_doc["agent_type"] = "therapist"
                if "therapy_type" not in formatted_doc:
                    formatted_doc["therapy_type"] = therapy_type

            formatted_docs.append(formatted_doc)

        return formatted_docs


# 示例使用
if __name__ == "__main__":
    json_store = JSONMemoryStore()

    # 添加示例技能记忆
    example_skill = {
        "id": "profiler_skill_example",
        "content": "在侧写过程中，应该先关注来访者的情绪状态，再探索认知模式。",
        "timestamp": time.time()
    }

    json_store.add_document("profiler_skills", example_skill)

    # 读取技能记忆
    skills = json_store.get_all_documents("profiler_skills")
    logger.info(f"读取到 {len(skills)} 条侧写师技能记忆")