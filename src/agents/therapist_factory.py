# src/agents/therapist_factory.py
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.utils.llm_service import LLMService
from src.agents.therapist_agent import TherapistAgent
from src.utils.logger import logger
from src.memory.memory_manager import MemoryManager

class TherapistFactory:
    """心理咨询师工厂类"""

    def __init__(self, memory_manager: Optional[MemoryManager] = None, llm_service: Optional[LLMService] = None):
        """初始化心理咨询师工厂"""
        self.memory_manager = memory_manager
        self.llm_service = llm_service
        self.therapists_config = {}

    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """加载心理咨询师配置"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "therapists_config.json"
            )

        try:
            if not os.path.exists(config_path):
                logger.warning(f"未找到心理咨询师配置文件: {config_path}")
                return {}

            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            self.therapists_config = config_data
            logger.info(f"成功加载了 {len(config_data.get('therapists', []))} 个咨询师配置")
            return config_data

        except Exception as e:
            logger.error(f"加载心理咨询师配置失败: {str(e)}")
            return {}

    def create_therapist(self, therapy_type: str) -> Optional[TherapistAgent]:
        """创建特定流派的心理咨询师"""
        if not self.therapists_config:
            self.load_config()

        therapy_config = None
        for therapist in self.therapists_config.get("therapists", []):
            if therapist.get("id") == therapy_type:
                therapy_config = therapist
                break

        if therapy_config is None:
            logger.warning(f"未找到流派 '{therapy_type}' 的配置")
            return None

        try:
            therapist = TherapistAgent(
                therapy_type=therapy_type,
                config=therapy_config,
                llm_service=self.llm_service
            )
            logger.info(f"成功创建 {therapy_type} 流派的咨询师")
            return therapist

        except Exception as e:
            logger.error(f"创建 {therapy_type} 流派的咨询师时出错: {str(e)}")
            return None

    def create_all_therapists(self) -> List[TherapistAgent]:
        """根据配置创建所有流派的心理咨询师"""
        if not self.therapists_config:
            self.load_config()

        therapists = []
        for therapist_config in self.therapists_config.get("therapists", []):
            therapy_type = therapist_config.get("id")

            if not therapy_type:
                logger.warning("配置中的咨询师缺少id字段，将跳过")
                continue

            try:
                therapist = TherapistAgent(
                    therapy_type=therapy_type,
                    config=therapist_config,
                    llm_service=self.llm_service
                )
                therapists.append(therapist)
                logger.info(f"成功创建 {therapy_type} 流派的咨询师")

            except Exception as e:
                logger.error(f"创建 {therapy_type} 流派的咨询师时出错: {str(e)}")

        logger.info(f"总共创建了 {len(therapists)} 个咨询师实例")
        return therapists

    async def ensure_therapist_memories(self) -> None:
        """确保所有配置的咨询师在记忆系统中有对应的记忆集合"""
        if not self.memory_manager:
            logger.warning("记忆管理器未提供，无法初始化咨询师记忆")
            return

        if not self.therapists_config:
            self.load_config()

        for therapist_config in self.therapists_config.get("therapists", []):
            therapy_type = therapist_config.get("id")

            if not therapy_type:
                continue

            try:
                skills = await self.memory_manager.get_skill_memory("therapist", therapy_type=therapy_type)

                if not skills:
                    logger.info(f"咨询师 {therapy_type} 的技能记忆为空，将创建初始技能记忆")
                    core_techniques = therapist_config.get("core_techniques", [])

                    for i, technique in enumerate(core_techniques):
                        skill_content = f"作为{therapist_config.get('name', therapy_type)}咨询师，掌握{technique}技术，能够有效帮助来访者解决心理问题。"

                        skill_memory = {
                            "id": f"{therapy_type}_base_skill_{i}",
                            "content": skill_content,
                            "timestamp": 0,  # 使用0表示系统初始化的基础技能
                            "therapy_type": therapy_type
                        }

                        await self.memory_manager.update_skill_memory(
                            "therapist",
                            skill_memory,
                            therapy_type=therapy_type
                        )

                    logger.info(f"为咨询师 {therapy_type} 创建了 {len(core_techniques)} 条初始技能记忆")

            except Exception as e:
                logger.error(f"初始化咨询师 {therapy_type} 的记忆时出错: {str(e)}")