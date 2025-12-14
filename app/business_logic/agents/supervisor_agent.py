# src/agents/supervisor_agent.py
import pprint
import traceback
import json
from datetime import datetime
from typing import Dict, Any
from ..services.prompt_loader import PromptLoader
from ..services.logger import logger
from ..services.vector_utils import VectorUtils
from typing import Dict, Any, Optional, List

class SupervisorAgent:
    """指导员智能体"""

    def __init__(self, llm_service):
        """初始化指导员智能体"""
        self.llm_service = llm_service
        self.prompts = PromptLoader.load_prompts("supervisor")
        if not self.prompts:
            logger.warning("找不到指导员提示词配置")

    async def offer_profile_advice(self, state: Dict[str, Any]) -> str:
        """提供侧写师指导"""
        prompt_template = self.prompts.get("offer_profile_advice")

        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            student_basic_info=state["current_student_basic_info"],
            student_scales_results_before_consultation=state['initial_scales_result'],
            dialogue_history = "\n".join(f"{speaker}: {utterance}" for utterance, speaker in state["dialogue_history"]),
            supervisor_working_memory= state.get("supervisor_working_memory", None)
        )

        response_content = await self.llm_service.invoke(full_prompt)
        logger.info("指导员给侧写师的建议已生成")
        return response_content

    async def update_profile_working_memory(self, state: Dict[str, Any]):
        """更新指导员的工作记忆"""
        prompt_template = self.prompts.get("update_profile_working_memory")

        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            student_basic_info=state["current_student_basic_info"],
            dialogue_history = "\n".join(f"{speaker}: {utterance}" for utterance, speaker in state["dialogue_history"]),
            supervisor_working_memory=state.get("supervisor_working_memory", None)
        )

        result = await self.llm_service.invoke_json(full_prompt, default_value={})

        if result:
            state["supervisor_working_memory"] = result

    async def check_profile_complete(self, state: Dict[str, Any]) -> bool:
        """检查侧写是否可以结束"""
        prompt_template = self.prompts.get("check_profile_complete")

        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            student_basic_info=state["current_student_basic_info"],
            dialogue_history = "\n".join(f"{speaker}: {utterance}" for utterance, speaker in state["dialogue_history"]),
            supervisor_working_memory=state["supervisor_working_memory"]
        )

        result = await self.llm_service.invoke_json(full_prompt, default_value={"is_profile_complete": False})

        logger.info(f"指导员判断侧写是否完成: {result.get('is_profile_complete', False)}")
        return result.get("is_profile_complete", False)

    async def assess_portrait(self, state: Dict[str, Any], true_portraits: Dict[str, Any]) -> str:
        """评估侧写师的侧写"""
        prompt_template = self.prompts.get("assess_portrait")

        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            student_basic_info=state["current_student_basic_info"],
            true_portraits=true_portraits,
            portraits=state["psychological_portraits"],
            dialogue_history = "\n".join(f"{speaker}: {utterance}" for utterance, speaker in state["dialogue_history"])
        )

        print("assess_portrait中的psychological_portraits")
        pprint.pprint(state["psychological_portraits"])

        result = await self.llm_service.invoke_json(full_prompt, default_value={})
        return result.get("suggestions", "")

    async def offer_consultation_advice(self, state: Dict[str, Any], therapy_type: str) -> str:
        """提供咨询师指导"""
        prompt_template = self.prompts.get("offer_consultation_advice")

        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            therapy_type=therapy_type,
            student_basic_info=state["current_student_basic_info"],
            dialogue_history = "\n".join(f"{speaker}: {utterance}" for utterance, speaker in state["dialogue_history"]),
            initial_scales = state.get("initial_scales_result", {}),
            final_scales = state.get("scales_result_after_consultation", {})
        )

        response_content = await self.llm_service.invoke(full_prompt)
        logger.info("指导员给咨询师的建议已生成")
        return response_content

    async def offer_cbt_stage_advice(self, state: Dict[str, Any], stage_name: str, stage_config: Dict[str, Any], current_topic: str) -> str:
        """提供CBT阶段指导"""
        newline = "\n"
        dialogue_history = "\n".join(f"{speaker}: {utterance}" for utterance, speaker in state["dialogue_history"][-6:])
        prompt = f"""
        作为经验丰富的CBT督导师，请为咨询师在{stage_config.get('name', stage_name)}阶段提供专业指导。

        当前阶段：{stage_config.get('name', stage_name)}
        阶段描述：{stage_config.get('description', '')}
        阶段目标：{newline.join(stage_config.get('stage_goals', []))}
        主要技术：{', '.join(stage_config.get('techniques', []))}
        
        当前重点话题：{current_topic}
        话题得分情况：{state.get('topic_scores', {})}
        
        来访者基本信息：{state["current_student_basic_info"]}
        心理画像：{state["psychological_portraits"]}
        
        最近对话记录：
        {dialogue_history}

        请基于CBT理论和该阶段的特点，给咨询师提供具体的指导建议，包括：
        1. 如何运用该阶段的核心技术
        2. 如何围绕当前话题进行深入探讨
        3. 需要注意的要点和可能的陷阱
        
        请直接给出建议，不要添加前缀：
        """

        response_content = await self.llm_service.invoke(prompt)
        logger.info(f"指导员给CBT {stage_name} 阶段的建议已生成")
        return response_content

    async def extract_core_topic(self, state: Dict[str, Any]) -> str:
        """提取核心话题"""
        prompt_template = self.prompts.get("extract_core_topic")

        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            student_basic_info=state.get("current_student_basic_info", {}),
            psychological_portraits=state.get("psychological_portraits", {}),
            dialogue_history = "\n".join(f"{speaker}: {utterance}" for utterance, speaker in state["dialogue_history"])
        )

        core_topic = await self.llm_service.invoke(full_prompt)
        return core_topic.strip()

    async def evaluate_topic_relevance(self, current_topic: str, user_response: str) -> Dict[str, Any]:
        """评估话题相关性"""
        prompt_template = self.prompts.get("evaluate_topic_relevance")

        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            current_topic=current_topic,
            user_response=user_response
        )

        result = await self.llm_service.invoke_json(full_prompt, default_value={
            "relevance_score": "slightly_relevant",
            "new_topic": "",
            "explanation": "评估失败"
        })
        
        return result

    async def evaluate_cbt_stage_completion(self, stage_name: str, required_elements: List[str], dialogue_history: List[str]) -> Dict[str, Any]:
        """评估CBT阶段完成情况"""
        prompt_template = self.prompts.get("evaluate_cbt_stage_completion")

        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            stage_name=stage_name,
            required_elements=required_elements,
            dialogue_history = "\n".join(f"{speaker}: {utterance}" for utterance, speaker in dialogue_history[-8:])
        )

        result = await self.llm_service.invoke_json(full_prompt, default_value={
            "completed_elements": [],
            "explanation": "评估失败"
        })
        
        return result
    
    async def check_consultation_complete(self, state: Dict[str, Any]) -> bool:
        """检查咨询是否可以结束"""
        prompt_template = self.prompts.get("check_consultation_complete")

        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            student_basic_info=state["current_student_basic_info"],
            dialogue_history = "\n".join(f"{speaker}: {utterance}" for utterance, speaker in state["dialogue_history"]),
            supervisor_working_memory=state["supervisor_working_memory"]
        )

        result = await self.llm_service.invoke_json(full_prompt, default_value={"is_consultation_complete": False})

        logger.info(f"指导员判断咨询是否完成: {result.get('is_consultation_complete', False)}")
        return result.get("is_consultation_complete", False)

    async def evaluate_therapist(self, state: Dict[str, Any], therapy_type: str) -> str:
        """评估咨询师的咨询"""
        prompt_template = self.prompts.get("evaluate_therapist")

        full_prompt = PromptLoader.format_prompt(
            prompt_template,
            therapy_type=therapy_type,
            student_basic_info=state["current_student_basic_info"],
            psychological_portraits=state["psychological_portraits"],
            dialogue_history = "\n".join(f"{speaker}: {utterance}" for utterance, speaker in state["dialogue_history"]),
            initial_scales=state.get("initial_scales_result", {}),
            final_scales=state.get("scales_result_after_consultation", {})
        )

        result = await self.llm_service.invoke_json(full_prompt, default_value={})
        return result.get("suggestions", "")

    async def create_student_medical_record(self, state: Dict[str, Any], therapy_type: str, memory_manager):
        """创建学生医疗记录"""
        try:
            # 准备医疗记录数据
            student_id = state["current_student_basic_info"].id

            # 这里可以添加生成医疗记录的提示词模板
            # 暂时使用现有的硬编码方式，可以后续改进

            full_prompt = f"""
            你是一位经验丰富的心理咨询督导师，负责生成规范的电子病历。现在需要你为一位学生生成医疗记录。

            学生的基本信息:
            {state["current_student_basic_info"].__dict__}

            心理画像:
            {json.dumps(state.get("psychological_portraits", {}), ensure_ascii=False, indent=2)}

            量表结果:
            - 咨询前: {json.dumps(state.get("initial_scales_result", {}), ensure_ascii=False, indent=2)}
            - 咨询后: {json.dumps(state.get("scales_result_after_consultation", {}), ensure_ascii=False, indent=2)}

            整个对话记录：
            {" ".join(f"{speaker}: {utterance}" for utterance, speaker in state["dialogue_history"])}

            使用的治疗流派: {therapy_type}

            请根据上述信息，生成一份结构化的医疗记录，包含以下内容:
            1. 诊断和主要问题
            2. 治疗计划
            3. 咨询过程记录
            4. 治疗效果评估
            5. 后续建议

            请按照以下JSON格式回答:
            {{
                "diagnoses": ["诊断1", "诊断2"],
                "problems": ["问题1", "问题2"],
                "treatment_plan": {{
                    "approach": "治疗方法",
                    "goals": ["目标1", "目标2"],
                    "estimated_duration": "预计疗程"
                }},
                "process": "咨询过程的概要记录",
                "outcome": {{
                    "improvement_areas": ["改善区域1", "改善区域2"],
                    "remaining_issues": ["剩余问题1", "剩余问题2"],
                    "recommendations": ["建议1", "建议2"]
                }}
            }}

            请只返回JSON内容，不要添加任何额外的解释或说明。"""

            # 获取医疗记录内容
            record_content = await self.llm_service.invoke_json(full_prompt, default_value={})

            init_scale_total_score = 0
            for value in state["initial_scales_result"].values():
                init_scale_total_score += value["final_score"]
            after_scale_total_score = 0
            for value in state["scales_result_after_consultation"].values():
                after_scale_total_score += value["final_score"]

            total_improvement_score = init_scale_total_score - after_scale_total_score  # 正常来说应该是正数，因为量表的分都是越低越好

            # 准备完整的医疗记录数据
            medical_record = {
                "recordId": "",  # 将由memory_manager生成
                "studentId": student_id,
                "basic_info": state["current_student_basic_info"],
                "portrait": state.get("psychological_portraits", {}),
                "symptoms": record_content.get("diagnoses", []),
                "plan": record_content.get("treatment_plan", {}),
                "process": record_content.get("process", ""),
                "result": record_content.get("outcome", {}),
                "status": "active",
                "createdAt": datetime.now().timestamp(),
                "updatedAt": datetime.now().timestamp(),
                "therapyType": therapy_type,
                "initialScaleResults": state.get("initial_scales_result", {}),
                "finalScaleResults": state.get("scales_result_after_consultation", {}),
                "totalImprovementScore": total_improvement_score,
            }

            # 保存到记忆系统
            record_id = await memory_manager.create_medical_record(student_id, medical_record)
            logger.info(f"成功创建学生 {student_id} 的医疗记录: {record_id}")

            # 创建学生特征向量
            vector_data = VectorUtils.create_student_feature_vector(
                state["current_student_basic_info"],
                state.get("psychological_portraits", {})
            )

            # 存储向量并更新索引，关联到病历
            vector_id = await memory_manager.create_student_vector(student_id, vector_data, record_id)

            logger.info(f"成功创建并关联学生 {student_id} 的特征向量: {vector_id}")

            # 更新状态中的记录ID
            if "medical_records" not in state:
                state["medical_records"] = {}
            if student_id not in state["medical_records"]:
                state["medical_records"][student_id] = []
            state["medical_records"][student_id].append(record_id)

            return record_id

        except Exception as e:
            logger.error(f"创建医疗记录时出错: {str(e)}")
            traceback.print_exc()
            return None