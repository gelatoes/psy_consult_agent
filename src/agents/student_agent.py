# src/agents/student_agent.py
from pathlib import Path
from typing import Dict, Any, List, Optional
import os
import json
import re

from src.utils.llm_service import LLMService, create_llm_service
from src.utils.prompt_loader import PromptLoader
from src.utils.logger import logger


class StudentAgent:
    """学生智能体"""

    def __init__(self, config: Dict[str, Any], llm_service: Optional[LLMService] = None):
        """初始化学生智能体"""
        # 保存学生配置
        self.basic_info = config.get("basic_info", {})
        self.real_questionnaire_results = config.get("realQuestionnaireResults", {})
        self.psychological_portrait = config.get("psychologicalPortrait")
        self.additional_info = config.get("additional_info", {})

        self.student_id = self.basic_info.get("id", "unknown")
        self.mental_health = self.real_questionnaire_results.get("ghq", {})
        self.influencing_factors = self.psychological_portrait.get("influencing_factors", {})


        # 如果没有提供llm_service，则使用默认的服务
        if llm_service is None:
            self.llm_service = create_llm_service(
                service_type="siliconflow",
                model_name="Tongyi-Zhiwen/QwenLong-L1-32B",
                default_temperature=0.7,
                api_base="https://api.siliconflow.cn/v1"
            )
        else:
            self.llm_service = llm_service

        # 加载提示词模板
        self.prompts = PromptLoader.load_prompts("student")
        if not self.prompts:
            logger.warning("找不到学生提示词配置")

        # 初始化学生的当前状态
        self.current_state = "normal"  # 学生的当前情绪/状态

    @property
    def name(self) -> str:
        """获取学生姓名"""
        # 新格式没有姓名字段，使用ID作为标识
        return f"学生{self.student_id}"

    def get_info_prompt(self):
        """获取学生的基本信息的prompt"""
        info_prompt = f"""
你是 {self.name}，一名{self.basic_info.get('grade', '未知')}的{self.basic_info.get('gender', '未知')}学生。

基本信息:
- 院校类型: {self.basic_info.get('university_type', '未说明')}
- 专业方向: {self.basic_info.get('major_type', '未说明')}
- 独生子女: {'是' if self.additional_info.get('only_child') == '是' else '否'}
- 家庭背景: 父母居住于{self.additional_info.get('parents_residence', '未知')}，母亲文化程度为{self.additional_info.get('mother_education', '未知')}
- 月生活费: {self.additional_info.get('monthly_allowance', '未知')}
- 学业表现: {self.additional_info.get('academic_performance', '未评估')}

心理健康状况:
- 一般健康问卷(GHQ): {self.mental_health}, 这个数值>=1为坏，数值越大，代表心理健康状态越差

影响因素:
- 运动时长: {self.influencing_factors.get('exercise_duration', '未记录')}
- 睡眠质量: {self.influencing_factors.get('sleep_quality', '未评估')}
- 社会支持: {self.influencing_factors.get('social_support', '未评估')}
- 求助意愿: {self.influencing_factors.get('help_seeking_willingness', '未记录')}
- 感知学业内卷: {self.influencing_factors.get('perceived_academic_involution', '未评估')}
- 向上社会比较: {self.influencing_factors.get('upward_social_comparison', '未评估')}
- 心理韧性: {self.influencing_factors.get('psychological_resilience', '未评估')}
- 压力源数量: {self.influencing_factors.get('stressor_count', '未评估')}

日常行为表现:
- 作息情况: 通常{self.additional_info.get('bedtime', '未知')}点入睡
- 自评健康状况: {self.additional_info.get('self_rated_health', '未评估')}
- 社交媒体成瘾程度: {self.additional_info.get('social_media_addiction', '未评估')}
- 学业内卷水平: {self.additional_info.get('academic_involution_level', '未评估')}
- 幸福指数: {self.real_questionnaire_results.get('Campbell', '未评估')}
- 感知压力: {self.real_questionnaire_results.get('CPSS', '未评估')}
"""
        return info_prompt

    async def fill_scale(self, mode: str, scale_names: List[str], state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """模拟学生填写心理量表"""
        # 验证模式是否有效
        if mode not in ["before_consultation", "after_consultation"]:
            raise ValueError("模式必须是 'before_consultation' 或 'after_consultation'")

        results = {}

        # 前测直接使用真实数据
        if mode == "before_consultation":
            for scale_name in scale_names:
                if scale_name == "GHQ-20":
                    # 解析GHQ分数
                    ghq_score = self.real_questionnaire_results.get("ghq", 0)
                    results[scale_name] = {
                        "each_score": [],
                        "final_score": ghq_score,
                        "thoughts": "使用真实数据填充"
                    }
                elif scale_name == "Campbell":
                    results[scale_name] = {
                        "each_score": [],
                        "final_score": self.real_questionnaire_results.get("Campbell", 0),
                        "thoughts": "使用真实数据填充"
                    }
                elif scale_name == "CPSS":
                    results[scale_name] = {
                        "each_score": [],
                        "final_score": self.real_questionnaire_results.get("CPSS", 0),
                        "thoughts": "使用真实数据填充"
                    }
                else:
                    logger.warning(f"量表 '{scale_name}' 没有预定义的真实数据映射，将跳过")
                    continue

            # 存储结果到state
            state["initial_scales_result"] = results
            logger.info("咨询前量表结果已使用真实数据填充")
            return results

        # 后测使用LLM模拟填写
        else:
            # 加载量表定义
            scales_path = Path(os.path.dirname(__file__)) / ".." / "scales.json"
            try:
                with open(scales_path, 'r', encoding='utf-8') as f:
                    scales_data = json.load(f)
            except FileNotFoundError:
                raise FileNotFoundError(f"找不到量表定义文件: {scales_path}")

            # 针对每个量表进行填写
            for scale_name in scale_names:
                if scale_name not in scales_data:
                    logger.warning(f"找不到量表 '{scale_name}' 的定义，将跳过")
                    continue

                scale_info = scales_data[scale_name]
                scale_prompt = scale_info.get("prompt", "")

                # 获取提示词模板
                prompt_template = self.prompts.get("fill_scale")

                # 格式化提示词
                full_prompt = PromptLoader.format_prompt(
                    prompt_template,
                    student_name=self.name,
                    student_grade=self.basic_info.get('grade', '未知'),
                    student_gender=self.basic_info.get('gender', '未知'),
                    student_info=self.get_info_prompt(),
                    current_state=self.current_state,
                    dialogue_history="\n".join(state["dialogue_history"]),
                    initial_scales=json.dumps(state["initial_scales_result"], ensure_ascii=False, indent=2),
                    scale_prompt=scale_prompt
                )

                # 获取结果
                result = await self.llm_service.invoke_json(full_prompt, default_value={
                    "each_score": [],
                    "final_score": 0,
                    "thoughts": "无法生成量表结果"
                })

                results[scale_name] = result

            # 存储后测结果
            state["scales_result_after_consultation"] = results
            return results

    async def speak(self, state: Dict[str, Any]) -> str:
        """学生回复"""
        # 获取提示词模板
        prompt_template = self.prompts.get("speak")

        # 格式化提示词
        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            student_name=self.name,
            student_grade=self.basic_info.get('grade', '未知'),
            student_gender=self.basic_info.get('gender', '未知'),
            student_info=self.get_info_prompt(),
            current_state=self.current_state,
            dialogue_history="\n".join(state["dialogue_history"])
        )

        # 获取结果
        result = await self.llm_service.invoke_json(full_prompt, default_value={
            "student_response": f"学生：对不起，我现在有点混乱。",
            "mood": self.current_state,
            "thoughts": "无法生成有效回复"
        })

        # 确保学生的回答以"学生："开头
        if not result["student_response"].startswith("学生："):
            result["student_response"] = "学生：" + result["student_response"]

        # 更新对话历史
        state["dialogue_history"].append(result["student_response"])

        # 更新学生情绪状态
        if "mood" in result and result["mood"] != self.current_state:
            logger.info(f"学生情绪变化: {self.current_state} -> {result['mood']}")
            self.current_state = result["mood"]

        # 记录内心想法
        if "thoughts" in result:
            logger.info(f"学生内心想法: {result['thoughts']}")

        return result["student_response"]

    def _parse_score(self, score_str):
        """解析带有评估标准的分数字符串，如 '6 (≥1为坏)' -> 6"""
        if isinstance(score_str, (int, float)):
            return score_str
        if isinstance(score_str, str) and " (" in score_str:
            try:
                return int(score_str.split(" (")[0])
            except ValueError:
                return 0
        try:
            return int(score_str)
        except (ValueError, TypeError):
            return 0