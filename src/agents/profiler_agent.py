# src/agents/profiler_agent.py
import hashlib
import os
import pprint
import time
from typing import Optional, Dict, Any
import json
import traceback

from src.utils.llm_service import LLMService, create_llm_service
from src.utils.prompt_loader import PromptLoader
from src.utils.logger import logger
import sys


class ProfilerAgent:
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        生成侧写师智能体

        Args:
            llm_service: 可选的LLM服务，如果不提供则使用默认的服务
        """
        # 如果没有提供llm_service，则使用默认的服务
        if llm_service is None:
            self.llm_service = create_llm_service(
                service_type="siliconflow",
                model_name="Tongyi-Zhiwen/QwenLong-L1-32B",
                default_temperature=0.5,
                api_base="https://api.siliconflow.cn/v1"
            )
        else:
            self.llm_service = llm_service

        # 加载提示词模板
        self.prompts = PromptLoader.load_prompts("profiler")
        if not self.prompts:
            logger.warning("找不到侧写师提示词配置")

    async def speak(self, state: Dict[str, Any], supervisor_agent, memory_manager, ablation_str: str = "none"):
        # 获取指导员的建议
        # advice = await supervisor_agent.offer_profile_advice(state)

        # 获取学生最后一句话作为查询文本
        query_text = ""
        if state["dialogue_history"]:
            # 获取最后一句学生的话
            for line in reversed(state["dialogue_history"]):
                if line.startswith("学生："):
                    query_text = line.replace("学生：", "").strip()
                    break

        # 获取侧写师相关的技能记忆
        skills_memory_text = ""
        if ablation_str != 'wo-memory':  # 如果没有消融memory
            
            if memory_manager:
                try:
                    # 使用向量相似度检索相关技能记忆
                    relevant_skills = await memory_manager.get_skill_memory(
                        "profiler",
                        query_text=query_text if query_text else None,
                        limit=5
                    )

                    if relevant_skills and len(relevant_skills) > 0:
                        logger.info(f"获取了{len(relevant_skills)}条相关的侧写师技能记忆")
                        skills_memory_text = "侧写师技能记忆：\n"
                        for idx, skill in enumerate(relevant_skills, 1):
                            if "content" in skill:
                                # 如果有相似度分数，也显示出来
                                similarity_info = ""
                                if "similarity" in skill:
                                    similarity_info = f" (相似度: {skill['similarity']:.3f})"
                                skills_memory_text += f"{idx}. {skill['content']}{similarity_info}\n"
                    else:
                        skills_memory_text = "侧写师技能记忆：暂无相关记忆\n"
                except Exception as e:
                    logger.error(f"获取侧写师技能记忆时出错: {e}")
                    skills_memory_text = "侧写师技能记忆：无法获取\n"

            logger.info("最终检索到的侧写师的技能")
            logger.info(skills_memory_text)

        # 获取提示词模板，如果没有配置则使用硬编码的提示词
        prompt_template = self.prompts.get("speak")

        logger.info("侧写师的speak方法中的psychological_portraits是")
        logger.info(state["psychological_portraits"])

        # 格式化提示词
        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            student_basic_info=state["current_student_basic_info"],
            dialogue_history="\n".join(state["dialogue_history"]),
            # supervisor_advice=advice,
            shared_memory=state["shared_memory"],
            skills_memory=skills_memory_text,
            psychological_portraits=state["psychological_portraits"]
        )

        # 发送到LLM获取结果
        response_content = await self.llm_service.invoke(full_prompt)

        logger.info("侧写师响应生成完成")

        # 更新对话历史
        state["dialogue_history"].append("侧写师：" + response_content)

    async def update_working_memory(self, state: Dict[str, Any]):
        # 获取提示词模板
        prompt_template = self.prompts.get("update_working_memory")

        logger.info("侧写师的update_working_memory方法中的psychological_portraits是")
        logger.info(state["psychological_portraits"])

        # 格式化提示词
        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            student_basic_info=state["current_student_basic_info"],
            dialogue_history="\n".join(state["dialogue_history"]),
            psychological_portraits=state["psychological_portraits"],
            shared_memory=state["shared_memory"]
        )

        # 使用invoke_json直接获取解析后的JSON结果
        result = await self.llm_service.invoke_json(full_prompt, default_value={})

        # 更新state中侧写师工作记忆
        if result:
            state["shared_memory"] = result

    async def update_psychological_portraits(self, state: Dict[str, Any]):
        # 获取提示词模板
        prompt_template = self.prompts.get("update_psychological_portraits")

        logger.info("侧写师的update_psychological_portraits方法中的psychological_portraits是")
        logger.info(state["psychological_portraits"])

        # 格式化提示词
        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            student_basic_info=state["current_student_basic_info"],
            dialogue_history="\n".join(state["dialogue_history"]),
            psychological_portraits=state["psychological_portraits"]
        )

        logger.info("update_psychological_portraits中的psychological_portraits")
        logger.info(state["psychological_portraits"])

        # 使用invoke_json直接获取解析后的JSON结果
        result = await self.llm_service.invoke_json(full_prompt, default_value={})

        # 更新state中的心理画像
        if result:
            state["psychological_portraits"] = result

    async def strengthen_skill(self, state: Dict[str, Any], supervisor_overall_advice: str, memory_manager=None):
        # 获取提示词模板
        prompt_template = self.prompts.get("strengthen_skill")

        # 格式化提示词
        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            dialogue_history="\n".join(state["dialogue_history"]),
            supervisor_advice=supervisor_overall_advice
        )

        # 发送到LLM获取结果
        skill_content = await self.llm_service.invoke(full_prompt)
        skill_content = skill_content.strip()

        # 如果提供了记忆管理器，则将技能存储到长期记忆
        if memory_manager:
            try:
                # 创建唯一ID，基于时间戳和内容的哈希
                current_timestamp = time.time()
                content_hash = hashlib.md5(skill_content.encode()).hexdigest()[:8]
                skill_id = f"profiler_skill_{int(current_timestamp)}_{content_hash}"

                # 创建技能记忆对象
                skill_memory = {
                    "id": skill_id,
                    "content": skill_content,
                    "timestamp": current_timestamp,
                    "agent_type": "profiler"
                }

                # 存储技能记忆
                await memory_manager.update_skill_memory("profiler", skill_memory)
                logger.info(f"技能记忆已存储，ID: {skill_id}")

            except Exception as e:
                logger.error(f"存储技能记忆时出错: {e}")
                traceback.print_exc()

        return skill_content