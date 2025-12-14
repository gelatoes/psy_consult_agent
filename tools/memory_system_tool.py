#!/usr/bin/env python
# tools/memory_system_tool.py
"""
记忆系统管理工具
用于手动管理、验证记忆系统状态
"""
import os
import sys
import asyncio
import json
import argparse
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import shutil

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from src.memory.memory_manager import MemoryManager
from src.memory.system_initializer import MemorySystemInitializer
from src.utils.logger import logger


class MemorySystemTool:
    """记忆系统管理工具"""

    def __init__(self):
        """初始化工具"""
        self.memory_manager = None
        self.therapy_types = []

    async def initialize(self):
        """初始化记忆管理器"""
        self.memory_manager = await MemorySystemInitializer.initialize_memory_system()
        # 获取所有治疗师流派
        self.therapy_types = self._get_therapist_types()
        logger.info(f"记忆系统初始化完成")
        logger.info(f"检测到 {len(self.therapy_types)} 个治疗师流派: {', '.join(self.therapy_types)}")
        logger.info(f"JSON文件目录: {self.memory_manager.json_store.base_dir}")
        logger.info(f"向量数据库目录: {self.memory_manager.vector_store.persist_directory}")

    def _get_therapist_types(self) -> List[str]:
        """
        获取所有治疗师流派

        Returns:
            List[str]: 治疗师流派列表
        """
        # 默认流派
        therapy_types = ["cbt", "psychodynamic"]

        try:
            # 尝试从配置文件加载治疗师流派
            base_dir = Path(__file__).parent.parent
            config_path = os.path.join(base_dir, "src", "therapists_config.json")

            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 提取所有流派ID
                therapist_types = [
                    therapist.get("id")
                    for therapist in config_data.get("therapists", [])
                    if therapist.get("id")
                ]

                if therapist_types:
                    therapy_types = therapist_types

        except Exception as e:
            logger.info(f"加载治疗师配置失败: {str(e)}，将使用默认流派")

        return therapy_types

    async def import_test(self):
        """测试从JSON导入到向量数据库"""
        if not self.memory_manager:
            await self.initialize()

        logger.info("\n=== 开始测试JSON到向量数据库的导入 ===")

        # 获取JSON文件中的记录数
        json_store = self.memory_manager.json_store

        # 动态构建集合列表
        collections = ["profiler_skills", "medical_records", "student_vectors"]  # 添加学生特征向量集合
        for therapy_type in self.therapy_types:
            collections.append(f"therapist_{therapy_type}_skills")

        for collection_name in collections:
            logger.info(f"\n正在处理集合: {collection_name}")

            # 获取JSON文件中的记录
            json_docs = json_store.get_all_documents(collection_name)
            logger.info(f"JSON中找到 {len(json_docs)} 条记录")

            if json_docs:
                # 尝试导入第一条记录
                try:
                    first_doc = json_docs[0]
                    doc_id = first_doc.get("id", f"test_{int(time.time())}")

                    # 构建元数据
                    metadata = {}
                    if collection_name == "profiler_skills":
                        metadata = {"agent_type": "profiler"}
                    elif collection_name.startswith("therapist_"):
                        therapy_type = collection_name.split("_")[1]
                        metadata = {"agent_type": "therapist", "therapy_type": therapy_type}
                    elif collection_name == "student_vectors":
                        metadata = {
                            "student_id": first_doc.get("metadata", {}).get("student_id", "unknown"),
                            "record_id": first_doc.get("metadata", {}).get("record_id", ""),
                            "type": "student_vector"
                        }

                    # 直接添加到向量数据库
                    logger.info(f"尝试导入文档ID: {doc_id}")
                    logger.info(f"文档内容: {json.dumps(first_doc, ensure_ascii=False)[:100]}...")

                    await self.memory_manager.vector_store.add_document(
                        collection_name=collection_name,
                        doc_id=doc_id,
                        content=first_doc,
                        metadata=metadata
                    )

                    # 验证导入
                    imported_doc = await self.memory_manager.vector_store.get_document(collection_name, doc_id)
                    if imported_doc:
                        logger.info(f"导入成功! 验证返回: {type(imported_doc)}")
                    else:
                        logger.info(f"导入失败! 无法验证文档")
                except Exception as e:
                    logger.info(f"导入过程出错: {str(e)}")

        logger.info("\n=== 导入测试完成 ===")

    async def list_skills(self, agent_type: str, therapy_type: Optional[str] = None):
        """列出技能记忆"""
        if not self.memory_manager:
            await self.initialize()

        # 如果是therapist但没有指定流派，则列出所有流派的技能
        if agent_type == "therapist" and not therapy_type:
            logger.info(f"\n=== 所有治疗师技能记忆 ===")
            for t_type in self.therapy_types:
                await self._list_specific_skills(agent_type, t_type)
        else:
            await self._list_specific_skills(agent_type, therapy_type)

    async def _list_specific_skills(self, agent_type: str, therapy_type: Optional[str] = None):
        """列出特定类型的技能记忆"""
        logger.info(f"\n=== {agent_type}{' ' + therapy_type if therapy_type else ''} 技能记忆 ===")
        skills = await self.memory_manager.get_skill_memory(agent_type, therapy_type)
        if not skills:
            logger.info("未找到技能记忆")
            return

        logger.info(f"共找到 {len(skills)} 条技能记忆:")
        for idx, skill in enumerate(skills, 1):
            logger.info(f"{idx}. ID: {skill.get('id', 'unknown')}")
            logger.info(f"   内容: {skill.get('content', 'N/A')}")
            if 'timestamp' in skill:
                try:
                    ts = skill['timestamp']
                    time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
                except:
                    time_str = str(ts)
                logger.info(f"   时间: {time_str}")
            logger.info("---")

    async def list_records(self, student_id: Optional[str] = None):
        """列出医疗记录"""
        if not self.memory_manager:
            await self.initialize()

        if student_id:
            logger.info(f"\n=== 学生 {student_id} 的医疗记录 ===")
            records = await self.memory_manager.get_student_medical_records(student_id)
        else:
            logger.info("\n=== 所有医疗记录 ===")
            # 这里需要实现获取所有记录的方法
            records = await self.memory_manager.vector_store.search_documents(
                "medical_records", query="", filter_dict=None, limit=100)

        if not records:
            logger.info("未找到医疗记录")
            return

        logger.info(f"共找到 {len(records)} 条医疗记录:")
        for idx, record in enumerate(records, 1):
            logger.info(f"{idx}. ID: {record.get('id', 'unknown')}")
            logger.info(f"   学生: {record.get('student_id', 'unknown')}")
            logger.info(f"   状态: {record.get('status', 'unknown')}")
            if 'basic_info' in record and 'name' in record['basic_info']:
                logger.info(f"   姓名: {record['basic_info']['name']}")
            if 'psychological_portrait' in record and 'main_issues' in record['psychological_portrait']:
                logger.info(f"   主要问题: {', '.join(record['psychological_portrait']['main_issues'])}")
            if 'created_at' in record:
                try:
                    ts = record['created_at']
                    time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
                except:
                    time_str = str(ts)
                logger.info(f"   创建时间: {time_str}")
            logger.info(f"   记录包含会话数: {len(record.get('sessions', []))}")
            logger.info("---")

    async def list_vectors(self, student_id: Optional[str] = None):
        """列出学生特征向量"""
        if not self.memory_manager:
            await self.initialize()

        logger.info("\n=== 学生特征向量 ===")

        # 获取向量索引
        index_path = Path(self.memory_manager.json_store.base_dir).joinpath("vector_index.json")
        if not index_path.exists():
            logger.info("向量索引文件不存在")
            return

        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        except Exception as e:
            logger.info(f"读取向量索引失败: {str(e)}")
            return

        if not index_data:
            logger.info("向量索引为空")
            return

        # 过滤学生ID（如果指定）
        if student_id:
            filtered_index = {k: v for k, v in index_data.items() if v.get("student_id") == student_id}
            logger.info(f"学生 {student_id} 的特征向量:")
        else:
            filtered_index = index_data
            logger.info(f"所有学生特征向量:")

        if not filtered_index:
            logger.info("未找到匹配的特征向量")
            return

        # 显示向量信息
        for vector_id, info in filtered_index.items():
            logger.info(f"向量ID: {vector_id}")
            logger.info(f"  学生ID: {info.get('student_id', 'unknown')}")
            logger.info(f"  病历ID: {info.get('record_id', 'N/A')}")
            if 'updated_at' in info:
                try:
                    ts = info['updated_at']
                    time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
                except:
                    time_str = str(ts)
                logger.info(f"  更新时间: {time_str}")

            # 尝试获取向量内容
            try:
                vector_data = await self.memory_manager.get_vector_by_id(vector_id)
                if vector_data:
                    logger.info(f"  特征文本: {vector_data.get('feature_text', 'N/A')[:100]}...")
            except Exception as e:
                logger.info(f"  获取向量内容失败: {str(e)}")

            logger.info("---")

    async def add_skill(self, agent_type: str, content: str, therapy_type: Optional[str] = None):
        """添加技能记忆"""
        if not self.memory_manager:
            await self.initialize()

        # 验证治疗师流派
        if agent_type == "therapist" and therapy_type not in self.therapy_types:
            logger.info(f"警告: 未找到流派 '{therapy_type}'")
            logger.info(f"可用流派: {', '.join(self.therapy_types)}")
            return

        # 创建技能数据
        skill_id = f"manual_{agent_type}_{int(time.time())}"
        skill_data = {
            "id": skill_id,
            "content": content,
            "timestamp": time.time(),
            "source": "manual_entry"
        }

        # 添加技能
        await self.memory_manager.update_skill_memory(agent_type, skill_data, therapy_type)
        logger.info(f"成功添加技能: {skill_id}")

    async def sync_json_vector(self):
        """同步JSON和向量数据库"""
        if not self.memory_manager:
            await self.initialize()

        logger.info("\n执行完整同步...")

        # 使用初始化器执行完整同步
        initializer = MemorySystemInitializer()
        memory_manager = await initializer.initialize_memory_system()

        logger.info("同步完成")

    async def validate_memory_system(self):
        """验证记忆系统状态"""
        if not self.memory_manager:
            await self.initialize()

        logger.info("\n=== 记忆系统状态验证 ===")

        # 检查JSON文件
        json_store = self.memory_manager.json_store
        json_dir = Path(json_store.base_dir)
        logger.info(f"JSON文件目录: {json_dir}")
        if not json_dir.exists():
            logger.info("警告: JSON目录不存在")
        else:
            json_files = list(json_dir.glob("*.json"))
            logger.info(f"发现 {len(json_files)} 个JSON文件:")
            for file in json_files:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    logger.info(f"  - {file.name}: {len(data) if isinstance(data, list) else '对象'} 条记录")
                except Exception as e:
                    logger.info(f"  - {file.name}: 读取错误 - {str(e)}")

        # 检查向量数据库
        vector_store = self.memory_manager.vector_store
        vector_dir = Path(vector_store.persist_directory)
        logger.info(f"\n向量数据库目录: {vector_dir}")
        if not vector_dir.exists():
            logger.info("警告: 向量数据库目录不存在")
        else:
            if not any(vector_dir.iterdir()):
                logger.info("警告: 向量数据库目录为空")
            else:
                # 动态检查集合状态
                collections = ["profiler_skills", "medical_records", "student_vectors"]  # 添加学生特征向量集合
                for therapy_type in self.therapy_types:
                    collections.append(f"therapist_{therapy_type}_skills")

                logger.info(f"检查 {len(collections)} 个集合:")
                for collection_name in collections:
                    try:
                        # 尝试获取集合并计数
                        if collection_name in vector_store._collections:
                            count = len(vector_store._collections[collection_name].get()["ids"])
                            logger.info(f"  - {collection_name}: {count} 条记录")
                        else:
                            logger.info(f"  - {collection_name}: 集合不存在")
                    except Exception as e:
                        logger.info(f"  - {collection_name}: 访问错误 - {str(e)}")

        # 检查向量索引文件
        index_path = Path(json_store.base_dir).joinpath("vector_index.json")
        logger.info(f"\n向量索引文件: {index_path}")
        if not index_path.exists():
            logger.info("警告: 向量索引文件不存在")
        else:
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                logger.info(f"向量索引包含 {len(index_data)} 条记录")
            except Exception as e:
                logger.info(f"读取向量索引失败: {str(e)}")

        logger.info("\n记忆系统验证完成")

    async def reset_memory_system(self, confirm: bool = False):
        """重置记忆系统（删除向量数据库，保留JSON）"""
        if not confirm:
            logger.info("警告: 此操作将删除向量数据库文件，但保留JSON文件。")
            response = input("确定要继续吗? (y/n): ")
            if response.lower() != 'y':
                logger.info("操作已取消")
                return

        if not self.memory_manager:
            await self.initialize()

        # 获取向量数据库目录
        vector_dir = Path(self.memory_manager.vector_store.persist_directory)

        if not vector_dir.exists():
            logger.info("向量数据库目录不存在，无需重置")
            return

        # 关闭现有连接
        await self.memory_manager.vector_store.cleanup()
        self.memory_manager = None

        try:
            # 释放资源
            import gc
            gc.collect()
            time.sleep(1)  # 等待资源释放

            # 删除向量数据库文件
            logger.info(f"删除向量数据库目录: {vector_dir}")
            shutil.rmtree(vector_dir, ignore_errors=True)

            # 重新创建目录
            os.makedirs(vector_dir, exist_ok=True)

            # 重置向量索引文件
            json_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "json-memories")
            index_path = json_dir / "vector_index.json"
            if index_path.exists():
                logger.info(f"重置向量索引文件: {index_path}")
                with open(index_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)

            logger.info("向量数据库已重置")

            # 重新初始化
            logger.info("正在从JSON重建向量数据库...")
            await self.initialize()
            logger.info("重建完成")

        except Exception as e:
            logger.info(f"重置记忆系统时出错: {str(e)}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="记忆系统管理工具")

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="命令")

    # 列出技能
    list_skills_parser = subparsers.add_parser("list-skills", help="列出技能记忆")
    list_skills_parser.add_argument("agent_type", choices=["profiler", "therapist"], help="智能体类型")
    list_skills_parser.add_argument("--therapy_type", help="疗法类型（仅当agent_type为therapist时使用）")

    # 列出医疗记录
    list_records_parser = subparsers.add_parser("list-records", help="列出医疗记录")
    list_records_parser.add_argument("--student_id", help="学生ID（可选，不提供则列出所有记录）")

    # 列出特征向量
    list_vectors_parser = subparsers.add_parser("list-vectors", help="列出学生特征向量")
    list_vectors_parser.add_argument("--student_id", help="学生ID（可选，不提供则列出所有向量）")

    # 添加技能
    add_skill_parser = subparsers.add_parser("add-skill", help="添加技能记忆")
    add_skill_parser.add_argument("agent_type", choices=["profiler", "therapist"], help="智能体类型")
    add_skill_parser.add_argument("--therapy_type", help="疗法类型（仅当agent_type为therapist时使用）")
    add_skill_parser.add_argument("--content", required=True, help="技能内容")

    # 同步
    subparsers.add_parser("sync", help="同步JSON和向量数据库")

    # 验证
    subparsers.add_parser("validate", help="验证记忆系统状态")

    # 重置
    reset_parser = subparsers.add_parser("reset", help="重置记忆系统（删除向量数据库，保留JSON）")
    reset_parser.add_argument("--force", action="store_true", help="强制重置，不提示确认")

    # 测试导入
    subparsers.add_parser("import-test", help="测试从JSON导入到向量数据库")

    # 启动工具实例
    tool = MemorySystemTool()

    # 解析参数
    args = parser.parse_args()

    # 执行命令
    if args.command == "list-skills":
        await tool.list_skills(args.agent_type, args.therapy_type)
    elif args.command == "list-records":
        await tool.list_records(args.student_id)
    elif args.command == "list-vectors":
        await tool.list_vectors(args.student_id)
    elif args.command == "add-skill":
        await tool.add_skill(args.agent_type, args.content, args.therapy_type)
    elif args.command == "sync":
        await tool.sync_json_vector()
    elif args.command == "validate":
        await tool.validate_memory_system()
    elif args.command == "reset":
        await tool.reset_memory_system(confirm=args.force)
    elif args.command == "import-test":
        await tool.import_test()
    else:
        parser.print_help()


if __name__ == "__main__":
    # 设置OpenAI API密钥（如有必要）
    if "OPENAI_API_KEY" not in os.environ:
        os.environ["OPENAI_API_KEY"] = "your-api-key-here"  # 替换为您的API密钥

    asyncio.run(main())