# src/memory/long_term_store.py
from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime
import chromadb
from chromadb import Collection

from src.utils.logger import logger


class LongTermMemoryStore:
    """底层存储实现 - 直接负责与数据库的交互"""

    def __init__(self, persist_directory=None):
        """
        初始化长期记忆存储

        Args:
            persist_directory: 持久化目录，如果为None则使用内存模式
        """
        # 如果没有指定持久化目录，使用默认路径
        if persist_directory is None:
            # 在src目录下创建long-term-memories文件夹
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.persist_directory = os.path.join(base_dir, "long-term-memories")
        else:
            self.persist_directory = persist_directory

        # 确保持久化目录存在
        os.makedirs(self.persist_directory, exist_ok=True)

        logger.info(f"向量数据库持久化目录: {self.persist_directory}")

        # 使用最新的ChromaDB客户端创建方式
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self._collections: Dict[str, Collection] = {}

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

                logger.info(f"向量数据库: 从配置文件加载了 {len(therapy_types)} 个治疗流派")

        except Exception as e:
            logger.info(f"向量数据库: 加载治疗流派配置失败: {str(e)}，将使用默认流派")

        return therapy_types

    async def init_collections(self):
        """初始化所有集合"""
        # 构建集合配置
        skills_collections = ["profiler_skills"]

        # 为每个治疗流派添加集合
        for therapy_type in self.therapy_types:
            skills_collections.append(f"therapist_{therapy_type}_skills")

        collections_config = {
            "skills": skills_collections,
            "records": ["medical_records"],
            "vectors": ["student_vectors"]  # 新增向量集合
        }

        # 导入embedding函数
        import chromadb.utils.embedding_functions as embedding_functions

        for category, names in collections_config.items():
            for name in names:
                # 获取或创建集合
                try:
                    self._collections[name] = self.client.get_collection(name=name)
                    logger.info(f"成功加载现有集合: {name}")
                except Exception:
                    # 如果集合不存在，创建新集合
                    # 对于需要向量支持的集合，指定embedding函数
                    if name == "student_vectors" or name.endswith("_skills"):
                        # 创建支持1024维向量的集合
                        # 使用默认的embedding函数，但不进行额外的embedding处理
                        ef = embedding_functions.DefaultEmbeddingFunction()
                        self._collections[name] = self.client.create_collection(
                            name=name,
                            embedding_function=ef
                        )
                        logger.info(f"创建新的向量集合: {name} (支持1024维)")
                    else:
                        self._collections[name] = self.client.create_collection(name=name)
                        logger.info(f"创建新集合: {name}")

    async def add_document(self, collection_name: str, doc_id: str, content: Dict[str, Any],
                           metadata: Dict[str, Any]) -> None:
        """添加文档到指定集合"""
        # 如果集合不存在，首先确保所有集合已初始化
        if collection_name not in self._collections:
            logger.info(f"集合 {collection_name} 不存在，正在初始化所有集合")
            await self.init_collections()

            # 如果仍不存在，则是一个新的治疗流派集合，需要创建
            if collection_name not in self._collections and collection_name.startswith("therapist_"):
                therapy_type = collection_name.split("_")[1]
                if therapy_type not in self.therapy_types:
                    self.therapy_types.append(therapy_type)
                    logger.info(f"添加新的治疗流派集合: {therapy_type}")

                # 创建新集合
                self._collections[collection_name] = self.client.create_collection(name=collection_name)
                logger.info(f"创建新的治疗流派集合: {collection_name}")

        collection = self._collections[collection_name]

        # 检查是否需要提供embedding向量
        embedding_vector = None
        if collection_name == "student_vectors" and "feature_vector" in content:
            embedding_vector = content.get("feature_vector")
        elif collection_name.endswith("_skills") and "skill_vector" in content:
            # 技能记忆集合使用skill_vector
            embedding_vector = content.get("skill_vector")

        if embedding_vector is not None:
            collection.add(
                documents=[json.dumps(content)],
                metadatas=[metadata],
                ids=[doc_id],
                embeddings=[embedding_vector]  # 直接提供embedding向量
            )
        else:
            collection.add(
                documents=[json.dumps(content)],
                metadatas=[metadata],
                ids=[doc_id]
            )
        logger.info(f"已添加文档到 {collection_name}")

    async def get_document(self, collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取指定文档"""
        # 如果集合不存在，首先确保所有集合已初始化
        if collection_name not in self._collections:
            logger.info(f"集合 {collection_name} 不存在，正在初始化所有集合")
            await self.init_collections()

            # 如果仍不存在，则可能是新的治疗流派或者其他未知集合
            if collection_name not in self._collections:
                logger.info(f"集合 {collection_name} 不存在且无法创建")
                return None

        collection = self._collections[collection_name]
        results = collection.get(ids=[doc_id])
        if results["documents"] and results["documents"][0]:
            logger.info(f"从 {collection_name} 成功获取文档 {doc_id}")
            return json.loads(results["documents"][0])
        logger.info(f"在 {collection_name} 中未找到文档 {doc_id}")
        return None

    async def update_document(self, collection_name: str, doc_id: str, content: Dict[str, Any],
                              metadata: Dict[str, Any]) -> None:
        """更新指定文档"""
        # 如果集合不存在，首先确保所有集合已初始化
        if collection_name not in self._collections:
            logger.info(f"集合 {collection_name} 不存在，正在初始化所有集合")
            await self.init_collections()

            # 如果仍不存在，则可能是新的治疗流派或者其他未知集合
            if collection_name not in self._collections:
                logger.info(f"集合 {collection_name} 不存在且无法创建，无法更新文档")
                return

        collection = self._collections[collection_name]

        # 检查是否需要提供embedding向量
        embedding_vector = None
        if collection_name == "student_vectors" and "feature_vector" in content:
            embedding_vector = content.get("feature_vector")
        elif collection_name.endswith("_skills") and "skill_vector" in content:
            # 技能记忆集合使用skill_vector
            embedding_vector = content.get("skill_vector")

        if embedding_vector is not None:
            collection.update(
                ids=[doc_id],
                documents=[json.dumps(content)],
                metadatas=[metadata],
                embeddings=[embedding_vector]  # 直接提供embedding向量
            )
        else:
            collection.update(
                ids=[doc_id],
                documents=[json.dumps(content)],
                metadatas=[metadata]
            )
        logger.info(f"已更新文档 {doc_id}")

    async def search_documents(self, collection_name: str, query_vector: Optional[List[float]] = None,
                               filter_dict: Dict[str, Any] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索文档，支持向量相似度检索"""
        # 如果集合不存在，首先确保所有集合已初始化
        if collection_name not in self._collections:
            logger.info(f"集合 {collection_name} 不存在，正在初始化所有集合")
            await self.init_collections()

            # 如果仍不存在，则返回空列表
            if collection_name not in self._collections:
                logger.info(f"集合 {collection_name} 不存在且无法创建，无法搜索文档")
                return []

        collection = self._collections[collection_name]

        try:
            # 如果没有提供查询向量，则返回前limit个文档
            if query_vector is None:
                results = collection.get(limit=limit, where=filter_dict)
                if results["documents"]:
                    logger.info(f"从 {collection_name} 获取了 {len(results['documents'])} 个文档")
                    documents = []
                    for i, doc in enumerate(results["documents"]):
                        if not doc:
                            continue
                        try:
                            parsed_doc = json.loads(doc)
                            if "metadatas" in results and i < len(results["metadatas"]) and results["metadatas"][i]:
                                parsed_doc.update(results["metadatas"][i])
                            documents.append(parsed_doc)
                        except json.JSONDecodeError:
                            logger.info(f"无法解析文档: {doc}")
                    return documents
            else:
                # 使用向量相似度搜索
                results = collection.query(
                    query_embeddings=[query_vector],
                    n_results=limit,
                    where=filter_dict
                )

                if results["documents"] and results["documents"][0]:
                    logger.info(f"从 {collection_name} 通过向量检索获取了 {len(results['documents'][0])} 个文档")
                    documents = []
                    for i, doc in enumerate(results["documents"][0]):
                        if not doc:
                            continue
                        try:
                            parsed_doc = json.loads(doc)
                            # 添加相似度分数（ChromaDB返回距离，需转换为相似度）
                            if "distances" in results and i < len(results["distances"][0]):
                                distance = results["distances"][0][i]
                                similarity = 1.0 / (1.0 + distance)  # 距离转相似度
                                parsed_doc["similarity"] = similarity

                            if "metadatas" in results and i < len(results["metadatas"][0]) and results["metadatas"][0][
                                i]:
                                parsed_doc.update(results["metadatas"][0][i])

                            documents.append(parsed_doc)
                        except json.JSONDecodeError:
                            logger.info(f"无法解析文档: {doc}")
                    return documents
        except Exception as e:
            logger.info(f"搜索文档时出错: {str(e)}")

        return []

    async def cleanup(self):
        """清理资源"""
        # PersistentClient 会自动管理数据持久化，不需要特别的清理操作
        logger.info("清理资源")