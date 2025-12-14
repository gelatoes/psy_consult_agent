# src/memory/long_term_store.py
from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime
import chromadb
from chromadb import Collection


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

        print(f"向量数据库持久化目录: {self.persist_directory}")

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

                print(f"向量数据库: 从配置文件加载了 {len(therapy_types)} 个治疗流派")

        except Exception as e:
            print(f"向量数据库: 加载治疗流派配置失败: {str(e)}，将使用默认流派")

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

        for category, names in collections_config.items():
            for name in names:
                # 获取或创建集合
                try:
                    self._collections[name] = self.client.get_collection(name=name)
                    print(f"成功加载现有集合: {name}")
                except Exception:
                    # 如果集合不存在，创建新集合
                    self._collections[name] = self.client.create_collection(name=name)
                    print(f"创建新集合: {name}")

    async def add_document(self, collection_name: str, doc_id: str, content: Dict[str, Any],
                           metadata: Dict[str, Any]) -> None:
        """添加文档到指定集合"""
        # 如果集合不存在，首先确保所有集合已初始化
        if collection_name not in self._collections:
            print(f"集合 {collection_name} 不存在，正在初始化所有集合")
            await self.init_collections()

            # 如果仍不存在，则是一个新的治疗流派集合，需要创建
            if collection_name not in self._collections and collection_name.startswith("therapist_"):
                therapy_type = collection_name.split("_")[1]
                if therapy_type not in self.therapy_types:
                    self.therapy_types.append(therapy_type)
                    print(f"添加新的治疗流派集合: {therapy_type}")

                # 创建新集合
                self._collections[collection_name] = self.client.create_collection(name=collection_name)
                print(f"创建新的治疗流派集合: {collection_name}")

        collection = self._collections[collection_name]
        collection.add(
            documents=[json.dumps(content)],
            metadatas=[metadata],
            ids=[doc_id]
        )
        print(f"已添加文档到 {collection_name}")

    async def get_document(self, collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取指定文档"""
        # 如果集合不存在，首先确保所有集合已初始化
        if collection_name not in self._collections:
            print(f"集合 {collection_name} 不存在，正在初始化所有集合")
            await self.init_collections()

            # 如果仍不存在，则可能是新的治疗流派或者其他未知集合
            if collection_name not in self._collections:
                print(f"集合 {collection_name} 不存在且无法创建")
                return None

        collection = self._collections[collection_name]
        results = collection.get(ids=[doc_id])
        if results["documents"] and results["documents"][0]:
            print(f"从 {collection_name} 成功获取文档 {doc_id}")
            return json.loads(results["documents"][0])
        print(f"在 {collection_name} 中未找到文档 {doc_id}")
        return None

    async def update_document(self, collection_name: str, doc_id: str, content: Dict[str, Any],
                              metadata: Dict[str, Any]) -> None:
        """更新指定文档"""
        # 如果集合不存在，首先确保所有集合已初始化
        if collection_name not in self._collections:
            print(f"集合 {collection_name} 不存在，正在初始化所有集合")
            await self.init_collections()

            # 如果仍不存在，则可能是新的治疗流派或者其他未知集合
            if collection_name not in self._collections:
                print(f"集合 {collection_name} 不存在且无法创建，无法更新文档")
                return

        collection = self._collections[collection_name]
        collection.update(
            ids=[doc_id],
            documents=[json.dumps(content)],
            metadatas=[metadata]
        )
        print(f"已更新文档 {doc_id}")

    async def search_documents(self, collection_name: str, query: str,
                               filter_dict: Dict[str, Any] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索文档"""
        # 如果集合不存在，首先确保所有集合已初始化
        if collection_name not in self._collections:
            print(f"集合 {collection_name} 不存在，正在初始化所有集合")
            await self.init_collections()

            # 如果仍不存在，则返回空列表
            if collection_name not in self._collections:
                print(f"集合 {collection_name} 不存在且无法创建，无法搜索文档")
                return []

        collection = self._collections[collection_name]

        try:
            # 获取所有文档
            results = collection.get(limit=limit)
            if results["documents"]:
                print(f"从 {collection_name} 获取了 {len(results['documents'])} 个文档")
                # 解析文档并将元数据合并到文档中
                documents = []
                for i, doc in enumerate(results["documents"]):
                    if not doc:
                        continue
                    try:
                        parsed_doc = json.loads(doc)
                        # 如果存在元数据，将其合并到文档中
                        if "metadatas" in results and i < len(results["metadatas"]) and results["metadatas"][i]:
                            parsed_doc.update(results["metadatas"][i])
                        documents.append(parsed_doc)
                    except json.JSONDecodeError:
                        print(f"无法解析文档: {doc}")
                return documents
        except Exception as e:
            print(f"获取文档时出错: {str(e)}")

        return []

    async def cleanup(self):
        """清理资源"""
        # PersistentClient 会自动管理数据持久化，不需要特别的清理操作
        print("清理资源")