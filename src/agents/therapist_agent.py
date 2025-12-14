# src/agents/therapist_agent.py
import hashlib
import time
import os
import json
import traceback
from typing import Dict, Any, List, Optional

from src.utils.llm_service import LLMService, create_llm_service
from src.utils.prompt_loader import PromptLoader
from src.utils.logger import logger

class TherapistAgent:
    def __init__(
            self,
            therapy_type: str,
            config: Optional[Dict[str, Any]] = None,
            llm_service: Optional[LLMService] = None
    ):
        """生成咨询师智能体"""
        self.therapy_type = therapy_type

        # 如果提供了配置，使用提供的配置；否则尝试从配置文件加载
        if config:
            self.config = config
        else:
            self.config = self._load_config(therapy_type)

        # 如果没有提供llm_service，则使用默认的服务
        if llm_service is None:
            self.llm_service = create_llm_service(
                service_type="siliconflow",
                model_name="Tongyi-Zhiwen/QwenLong-L1-32B",
                default_temperature=0.3,
                api_base="https://api.siliconflow.cn/v1"
            )
        else:
            self.llm_service = llm_service

        # 加载提示词模板
        self.prompts = PromptLoader.load_prompts("therapist")
        if not self.prompts:
            logger.warning("找不到咨询师提示词配置")

    def _load_config(self, therapy_type: str) -> Dict[str, Any]:
        """从配置文件加载特定流派的配置"""
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "therapists_config.json"
            )

            if not os.path.exists(config_path):
                logger.warning(f"未找到咨询师配置文件: {config_path}")
                return self._create_default_config(therapy_type)

            with open(config_path, 'r', encoding='utf-8') as f:
                full_config = json.load(f)

            for therapist_config in full_config.get("therapists", []):
                if therapist_config.get("id") == therapy_type:
                    return therapist_config

            logger.warning(f"在配置文件中未找到流派 '{therapy_type}' 的配置，使用默认配置")
            return self._create_default_config(therapy_type)

        except Exception as e:
            logger.error(f"加载咨询师配置失败: {str(e)}")
            traceback.print_exc()
            return self._create_default_config(therapy_type)

    def _create_default_config(self, therapy_type: str) -> Dict[str, Any]:
        """创建默认配置"""
        # 根据流派提供基本默认配置
        if therapy_type == "cbt":
            return {
                "id": "cbt",
                "name": "认知行为疗法",
                "english_name": "Cognitive Behavioral Therapy",
                "description": "认知行为疗法专注于识别和改变不健康的思维模式和行为。",
                "expertise": ["抑郁症", "焦虑障碍"],
                "core_techniques": ["认知重构", "行为激活"],
                "theoretical_basis": "CBT认为我们的想法、感受和行为是相互关联的。",
                "session_structure": {"typical_sessions": "12-20次"},
                "tone_config": "作为认知行为疗法咨询师，你的语言风格应当清晰、直接且有教育性。",
                "guideline": "遵循CBT基本流程，识别并挑战非理性信念。"
            }
        elif therapy_type == "psychodynamic":
            return {
                "id": "psychodynamic",
                "name": "精神动力学疗法",
                "english_name": "Psychodynamic Therapy",
                "description": "精神动力学疗法关注无意识过程，探索个人早期经历如何影响当前行为和关系。",
                "expertise": ["抑郁症", "人格障碍"],
                "core_techniques": ["自由联想", "移情分析"],
                "theoretical_basis": "精神动力学治疗基于无意识冲突和童年经历塑造成人行为和思维的观念。",
                "session_structure": {"typical_sessions": "数月至数年"},
                "tone_config": "作为精神动力学疗法咨询师，你的语言风格应当探索性强且富有深度。",
                "guideline": "鼓励自由联想，探索潜意识内容和早期经历。"
            }
        else:
            return {
                "id": therapy_type,
                "name": f"{therapy_type}疗法",
                "english_name": f"{therapy_type.capitalize()} Therapy",
                "description": f"{therapy_type}疗法的基本描述。",
                "expertise": ["一般心理问题"],
                "core_techniques": ["倾听", "反馈"],
                "theoretical_basis": "基本理论。",
                "session_structure": {},
                "tone_config": f"作为{therapy_type}疗法咨询师，你应保持专业和支持性的语言风格。",
                "guideline": "提供支持性的对话环境。"
            }

    @property
    def name(self) -> str:
        """获取咨询师流派名称"""
        return self.config.get("name", f"{self.therapy_type}疗法")

    def _format_session_structure(self, structure: Dict[str, Any]) -> str:
        """将会话结构字典格式化为可读字符串"""
        if not structure or not isinstance(structure, dict):
            return "灵活"
        
        mapping = {
            "short_term": "短期治疗",
            "goal_oriented": "目标导向",
            "typical_sessions": "典型会话次数",
            "homework_emphasis": "作业重要性",
            "structure_level": "结构化程度"
        }
        
        parts = []
        for key, readable_key in mapping.items():
            value = structure.get(key)
            if value is not None:
                if isinstance(value, bool):
                    parts.append(f"{readable_key}: {'是' if value else '否'}")
                else:
                    parts.append(f"{readable_key}: {value}")
        return ", ".join(parts) if parts else "灵活"

    def _prepare_system_prompt(self) -> str:
        """准备并格式化系统提示词"""
        prompt_template = self.prompts.get("system_prompt")
        if not prompt_template:
            return "你是一名专业的心理咨询师。"

        # # 格式化列表和字典以便在提示词中清晰展示
        # expertise_str = ", ".join(self.config.get("expertise", []))
        # core_techniques_str = ", ".join(self.config.get("core_techniques", []))
        # session_structure_str = self._format_session_structure(self.config.get("session_structure", {}))

        return PromptLoader.format_prompt(
            prompt_template,
            name=self.config.get("name", "未知疗法"),
            english_name=self.config.get("english_name", "Unknown Therapy"),
            description=self.config.get("description", ""),
            # theoretical_basis=self.config.get("theoretical_basis", ""),
            # expertise=expertise_str,
            # core_techniques=core_techniques_str,
            # session_structure=session_structure_str,
            # tone_config=self.config.get("tone_config", "")
        )

    async def speak(self, state: Dict[str, Any], supervisor_agent, memory_manager, ablation_str: str = 'none'):
        """咨询师说话"""
        # 获取指导员的建议
        advice = await supervisor_agent.offer_consultation_advice(state, self.therapy_type)

        # 获取学生最后一句话作为查询文本
        query_text = ""
        if state["dialogue_history"]:
            # 获取最后一句学生的话
            for line in reversed(state["dialogue_history"]):
                if line.startswith("学生：") or line.startswith("用户："):
                    query_text = line.replace("学生：", "").replace("用户：", "").strip()
                    break

        # 获取咨询师相关的技能记忆
        skills_memory_text = ""
        if ablation_str != 'wo-memory':  # 如果没有消融memory
            if memory_manager:
                try:
                    # 使用向量相似度检索相关技能记忆
                    relevant_skills = await memory_manager.get_skill_memory(
                        'therapist',
                        therapy_type=self.therapy_type,
                        query_text=query_text if query_text else None,
                        limit=5
                    )

                    if relevant_skills and len(relevant_skills) > 0:
                        skills_memory_text = "咨询师技能记忆：\n"
                        for idx, skill in enumerate(relevant_skills, 1):
                            if "content" in skill:
                                # 如果有相似度分数，也显示出来
                                similarity_info = ""
                                if "similarity" in skill:
                                    similarity_info = f" (相似度: {skill['similarity']:.3f})"
                                skills_memory_text += f"{idx}. {skill['content']}{similarity_info}\n"
                    else:
                        skills_memory_text = "咨询师技能记忆：暂无相关记忆\n"
                except Exception as e:
                    logger.error(f"获取咨询师技能记忆时出错: {e}")
                    skills_memory_text = "获取技能记忆失败"

        # 准备系统提示词和用户提示词
        system_prompt = self._prepare_system_prompt()
        user_prompt_template = self.prompts.get("speak")

        # 获取当前对话轮次信息
        current_round = state.get("current_consultation_dialogue_index", 0)
        total_rounds = 8  # 从控制器中看到的最大轮次

        # 格式化用户提示词，添加轮次信息
        user_prompt = PromptLoader.format_prompt(
            user_prompt_template,
            therapy_type=self.therapy_type,
            guideline=self.config.get("guideline", "暂无可用指南，请根据你的专业知识进行回应。"),
            student_basic_info=state["current_student_basic_info"],
            dialogue_history="\n".join(state["dialogue_history"]),
            supervisor_advice=advice,
            psychological_portraits=state["psychological_portraits"],
            shared_memory=state["shared_memory"],
            skills_memory=skills_memory_text,
            current_round=current_round,
            total_rounds=total_rounds
        )

        # 发送到LLM获取结果，同时传递系统和用户提示词
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response_content = await self.llm_service.invoke(full_prompt)

        logger.info("咨询师响应生成完成")

        # 获取最后一句用户话用于去重处理
        last_user_utterance = ""
        for line in reversed(state.get("dialogue_history", [])):
            if line.startswith("学生：") or line.startswith("用户："):
                last_user_utterance = line.replace("学生：", "").replace("用户：", "").strip()
                break

    async def update_working_memory(self, state: Dict[str, Any]):
        """更新咨询师的工作记忆"""
        prompt_template = self.prompts.get("update_working_memory")

        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            therapy_type=self.therapy_type,
            student_basic_info=state["current_student_basic_info"],
            dialogue_history="\n".join(state["dialogue_history"]),
            psychological_portraits=state["psychological_portraits"],
            shared_memory=state["shared_memory"]
        )

        result = await self.llm_service.invoke_json(full_prompt, default_value={})

        if result:
            state["shared_memory"] = result

    async def strengthen_skill(self, state: Dict[str, Any], supervisor_advice: str, memory_manager=None):
        """理解消化指导员的建议，转换为技能记忆"""
        prompt_template = self.prompts.get("strengthen_skill")

        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            therapy_type=self.therapy_type,
            dialogue_history="\n".join(state["dialogue_history"]),
            supervisor_advice=supervisor_advice
        )

        skill_content = await self.llm_service.invoke(full_prompt)
        skill_content = skill_content.strip()

        if memory_manager:
            try:
                current_timestamp = time.time()
                content_hash = hashlib.md5(skill_content.encode()).hexdigest()[:8]
                skill_id = f"therapist_skill_{self.therapy_type}_{int(current_timestamp)}_{content_hash}"

                skill_memory = {
                    "id": skill_id,
                    "content": skill_content,
                    "timestamp": current_timestamp,
                    "agent_type": "therapist"
                }

                await memory_manager.update_skill_memory("therapist", skill_memory, self.therapy_type)
                logger.info(f"咨询师技能记忆已存储，ID: {skill_id}")

            except Exception as e:
                logger.error(f"存储技能记忆时出错: {e}")
                traceback.print_exc()

        return skill_content