# src/controllers/consultation_controller.py
import os
import json
from typing import Dict, Any, List
from src.controllers.base_controller import BaseController
from src.agents import TherapistAgent, ProfilerAgent, SupervisorAgent
from src.memory.memory_manager import MemoryManager
from src.utils.logger import logger
from src.utils.exceptions import ConsultationError
import sys
import random

class ConsultationController(BaseController):
    """咨询模式控制器"""

    def __init__(
            self,
            profiler_agent: ProfilerAgent,
            therapist_agents: List[TherapistAgent],
            supervisor_agent: SupervisorAgent,
            memory_manager: MemoryManager,
            ablation_str: str = "none"
    ):
        self.profiler_agent = profiler_agent
        self.therapist_agents = therapist_agents
        self.supervisor_agent = supervisor_agent
        self.memory_manager = memory_manager
        self.ablation_str = ablation_str

        # 固定选择CBT咨询师
        self.selected_therapist = None
        for therapist in therapist_agents:
            if therapist and therapist.therapy_type == "cbt":
                self.selected_therapist = therapist
                break
        
        if not self.selected_therapist:
            logger.error("未找到CBT咨询师")
            raise ConsultationError("未找到CBT咨询师")

        # 加载CBT配置
        self.cbt_config = self._load_cbt_config()
        
        # 日志输出咨询师信息
        logger.info(f"咨询控制器初始化，使用CBT咨询师: {self.selected_therapist.therapy_type}")

        super().__init__()

    def _load_cbt_config(self) -> Dict[str, Any]:
        """加载CBT配置"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cbt_config.json")
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载CBT配置失败: {str(e)}")
            return {}

    def _register_nodes(self):
        """注册咨询流程的所有节点"""
        try:
            # 1. 初始化阶段
            self.graph.add_node("initialize", self._initialize_state)
            self.graph.add_node("greet_user", self._handle_greeting)

            # 2. 量表测评阶段
            self.graph.add_node("initial_scale", self._handle_initial_scale)

            # 3. 侧写阶段 
            # 如果没有wo-profiler的消融
            if self.ablation_str != "wo-profiler":
                self.graph.add_node("profiler_dialogue", self._handle_profiler_dialogue)
                self.graph.add_node("check_profiler_complete", self._check_profiler_complete)
                self.graph.add_node("create_portrait", self._handle_create_portrait)

            # 4. 咨询师选择阶段（固定选择CBT）
            self.graph.add_node("select_therapist", self._handle_therapist_selection)
            self.graph.add_node("initialize_cbt_topics", self._initialize_cbt_topics)

            # 5. CBT咨询阶段 - 分为4个大阶段
            self.graph.add_node("cbt_stage_1", self._handle_cbt_stage_1)
            self.graph.add_node("check_stage_1_complete", self._check_cbt_stage_complete)
            
            self.graph.add_node("cbt_stage_2", self._handle_cbt_stage_2)
            self.graph.add_node("check_stage_2_complete", self._check_cbt_stage_complete)
            
            self.graph.add_node("cbt_stage_3", self._handle_cbt_stage_3)
            self.graph.add_node("check_stage_3_complete", self._check_cbt_stage_complete)
            
            self.graph.add_node("cbt_stage_4", self._handle_cbt_stage_4)
            self.graph.add_node("check_stage_4_complete", self._check_cbt_stage_complete)

            # 6. 结束评估阶段
            self.graph.add_node("final_scale", self._handle_final_scale)
            self.graph.add_node("evaluate_consultation", self._handle_evaluation)
            
            # 如果没有wo-memory的消融
            if self.ablation_str != "wo-memory":
                self.graph.add_node("update_agent_skills", self._update_agent_skills)
                
            self.graph.add_node("save_medical_record", self._save_medical_record)
            self.graph.add_node("finalize", self._finalize_consultation)

            logger.info("咨询流程节点注册完成")

        except Exception as e:
            logger.error(f"注册咨询节点时出错: {str(e)}")
            raise ConsultationError("注册咨询节点失败") from e

    def _define_edges(self):
        """定义咨询流程的状态转换规则"""
        try:
            # 设置入口点为initialize节点
            self.graph.set_entry_point("initialize")

            # 1. 初始化和问候
            self.graph.add_edge("initialize", "greet_user")
            self.graph.add_edge("greet_user", "initial_scale")

            if self.ablation_str != "wo-profiler":

                # 2. 量表到侧写
                self.graph.add_edge("initial_scale", "profiler_dialogue")

                # 3. 侧写阶段循环
                self.graph.add_edge("profiler_dialogue", "check_profiler_complete")
                self.graph.add_conditional_edges(
                    "check_profiler_complete",
                    self._should_continue_profiler,
                    {
                        True: "profiler_dialogue",  # 继续侧写对话
                        False: "create_portrait"  # 结束侧写,创建画像
                    }
                )

                # 4. 画像到咨询师选择
                self.graph.add_edge("create_portrait", "select_therapist")
            else:
                # 如果没有侧写阶段，直接从量表到咨询师选择
                self.graph.add_edge("initial_scale", "select_therapist")

            # 5. CBT咨询阶段流程
            self.graph.add_edge("select_therapist", "initialize_cbt_topics")
            self.graph.add_edge("initialize_cbt_topics", "cbt_stage_1")
            
            # CBT阶段1循环
            self.graph.add_edge("cbt_stage_1", "check_stage_1_complete")
            self.graph.add_conditional_edges(
                "check_stage_1_complete",
                self._should_continue_stage_1,
                {
                    True: "cbt_stage_1",
                    False: "cbt_stage_2"
                }
            )
            
            # CBT阶段2循环
            self.graph.add_edge("cbt_stage_2", "check_stage_2_complete")
            self.graph.add_conditional_edges(
                "check_stage_2_complete",
                self._should_continue_stage_2,
                {
                    True: "cbt_stage_2",
                    False: "cbt_stage_3"
                }
            )
            
            # CBT阶段3循环
            self.graph.add_edge("cbt_stage_3", "check_stage_3_complete")
            self.graph.add_conditional_edges(
                "check_stage_3_complete",
                self._should_continue_stage_3,
                {
                    True: "cbt_stage_3",
                    False: "cbt_stage_4"
                }
            )
            
            # CBT阶段4循环
            self.graph.add_edge("cbt_stage_4", "check_stage_4_complete")
            self.graph.add_conditional_edges(
                "check_stage_4_complete",
                self._should_continue_stage_4,
                {
                    True: "cbt_stage_4",
                    False: "final_scale"
                }
            )

            # 6. 结束流程
            self.graph.add_edge("final_scale", "evaluate_consultation")
            
            # 有关memory的消融
            if self.ablation_str != "wo-memory":
                self.graph.add_edge("evaluate_consultation", "update_agent_skills")
                self.graph.add_edge("update_agent_skills", "save_medical_record")
            else:
                self.graph.add_edge("evaluate_consultation", "save_medical_record")
            self.graph.add_edge("save_medical_record", "finalize")

            logger.info("咨询流程边定义完成")

        except Exception as e:
            logger.error(f"定义咨询边时出错: {str(e)}")
            raise ConsultationError("定义咨询边失败") from e

    async def _initialize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """初始化咨询状态

        初始化所有必要的工作记忆和状态信息

        Args:
            state: 初始状态信息

        Returns:
            初始化后的状态,包含:
            - session_id
            - shared_working_memory
            - supervisor_working_memory
            - medical_record
            - psychological_portrait
        """
        try:
            logger.info("初始化咨询状态")

            # 初始化基础状态
            state["shared_memory"] = {}
            state["supervisor_working_memory"] = {}
            state["dialogue_history"] = []
            state["psychological_portraits"] = {}
            state["current_phase"] = 'initial'
            state["scales_result_after_consultation"] = {}
            state["is_profile_complete"] = False
            state["is_consultation_complete"] = False
            state["current_profile_dialogue_index"] = 0
            state["current_consultation_dialogue_index"] = 0

            # CBT相关状态初始化
            state["current_cbt_stage"] = "stage_1"
            state["cbt_stage_dialogues"] = {
                "stage_1": 0,
                "stage_2": 0, 
                "stage_3": 0,
                "stage_4": 0
            }
            state["cbt_stage_completions"] = {
                "stage_1": [],
                "stage_2": [],
                "stage_3": [],
                "stage_4": []
            }
            state["topic_scores"] = {}  # 话题得分记录表
            state["core_topic"] = ""  # 核心话题
            # 标志：CBT话题是否已初始化，防止重复初始化覆盖已有记忆
            state["_cbt_topics_initialized"] = False

            logger.info("咨询状态初始化完成")
            return state
        except Exception as e:
            logger.error(f"初始化咨询状态失败: {str(e)}")
            raise ConsultationError("初始化咨询状态失败") from e

    async def _handle_greeting(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理系统初始问候"""
        try:
            logger.info("系统开始问候")

            # 系统问候语
            # greeting = "您好！欢迎使用心理咨询系统。我是您的心理侧写师，接下来我会和您聊一聊，了解您的情况。请问您最近有什么想和我分享的吗？"
            greeting = "您好！欢迎使用心理咨询系统。接下来我会和您聊一聊，了解您的情况。请问您最近有什么想和我分享的吗？"
            

            # 添加到对话历史
            state["dialogue_history"].append(f"系统：{greeting}")

            # 获取用户回应
            user_response = await self._get_user_input(state)
            state["dialogue_history"].append(f"用户：{user_response}")

            logger.info("用户已回应系统问候")
            return state
        except Exception as e:
            logger.error(f"系统问候失败: {str(e)}")
            raise ConsultationError("系统问候失败") from e

    async def _handle_initial_scale(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始量表填写

        让用户填写心理量表并记录结果

        Args:
            state: 当前状态

        Returns:
            更新后的状态,包含量表结果
        """
        try:
            logger.info("加载用户初始量表数据")

            # 在实际应用中，这里应该从数据库或API获取用户已填写的量表数据
            # 此处使用模拟数据
            state["initial_scales_result"] = {
                "GHQ-20": {
                    "final_score": 6,
                    "assessment": "轻度心理压力"
                },
                "Campbell": {
                    "final_score": 10,
                    "assessment": "中等幸福感"
                },
                "CPSS": {
                    "final_score": 41,
                    "assessment": "中度压力"
                }
            }

            logger.info("初始量表数据加载完成")
            return state
        except Exception as e:
            logger.error(f"加载初始量表数据失败: {str(e)}")
            raise ConsultationError("加载初始量表数据失败") from e

    async def _handle_profiler_dialogue(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理侧写师对话阶段(单轮)"""
        try:
            logger.info(f"侧写对话轮次: {state['current_profile_dialogue_index']}")

            # 如果不是第一轮对话，侧写师需要回应
            if state["current_profile_dialogue_index"] > 0:
                # 侧写师生成回应
                await self.profiler_agent.speak(state, self.supervisor_agent, self.memory_manager, self.ablation_str)

                # 获取用户回应
                user_response = await self._get_user_input(state, "侧写师")
                state["dialogue_history"].append(f"用户：{user_response}")

            if self.ablation_str != "wo-memory": # without memory 直接不更新 使所有的memory都为初始状态
                # 侧写师更新工作记忆
                await self.profiler_agent.update_working_memory(state)

                # 指导员更新工作记忆
                await self.supervisor_agent.update_profile_working_memory(state)

            # 侧写师更新心理画像
            await self.profiler_agent.update_psychological_portraits(state)



            # 更新对话索引
            state["current_profile_dialogue_index"] += 1

            logger.info("侧写对话轮次完成")
            return state
        except Exception as e:
            logger.error(f"侧写对话失败: {str(e)}")
            raise ConsultationError("侧写对话失败") from e

    async def _check_profiler_complete(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """检查侧写阶段是否完成"""
        try:
            logger.info("检查侧写是否完成")

            # 添加轮次限制 (修改此处数字可调整最大对话轮次)
            MAX_PROFILE_TURNS = 1

            if state["current_profile_dialogue_index"] >= MAX_PROFILE_TURNS:
                state["is_profile_complete"] = True
                logger.info(f"侧写对话达到最大轮次({MAX_PROFILE_TURNS})，结束侧写阶段")
                return state

            # 由指导员判断是否完成侧写
            is_profile_complete = await self.supervisor_agent.check_profile_complete(state)
            # 更新状态
            if is_profile_complete:
                state["is_profile_complete"] = True
                await self.supervisor_agent.get_risk_factors(state)
                
                logger.info("指导员判断侧写阶段完成")
            else:   
                logger.info("指导员判断侧写阶段继续")

            return state
        except Exception as e:
            logger.error(f"检查侧写完成状态失败: {str(e)}")
            raise ConsultationError("检查侧写完成状态失败") from e

    def _should_continue_profiler(self, state: Dict[str, Any]) -> bool:
        """判断是否继续侧写对话

        Args:
            state: 当前状态

        Returns:
            True表示继续对话,False表示结束侧写
        """
        return not state.get("is_profile_complete", False)

    async def _handle_create_portrait(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """生成心理画像

        综合对话历史和量表结果生成画像

        Args:
            state: 当前状态

        Returns:
            更新后的状态,包含心理画像
        """
        try:
            logger.info("创建最终心理画像")

            # 侧写师已经在对话过程中不断更新心理画像
            # 这里可以做最后的整合或优化
            logger.info("心理画像已创建完成")

            return state
        except Exception as e:
            logger.error(f"创建心理画像失败: {str(e)}")
            raise ConsultationError("创建心理画像失败") from e

    async def _handle_therapist_selection(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """选择CBT咨询师"""
        try:
            logger.info("开始选择咨询师")

            # 固定选择CBT咨询师
            if not self.selected_therapist:
                raise ConsultationError("CBT咨询师未正确初始化")

            logger.info(f"已选择CBT咨询师: {self.selected_therapist.therapy_type}")

            # 记录所选择的咨询师流派
            state["selected_therapist_type"] = self.selected_therapist.therapy_type

            # 在对话历史中添加咨询师介绍
            introduction = f"您好，我是您的心理咨询师，专注于认知行为疗法(CBT)。接下来，我将基于您的情况，帮助您解决心理问题。我们将通过四个阶段来进行：识别自动思维、确定思想陷阱、挑战自动思维，以及回归现实思维。"
            introduction = self._clean_numbering(introduction)
            state["dialogue_history"].append(f"咨询师：{introduction}")

            return state
        except Exception as e:
            logger.error(f"选择咨询师失败: {str(e)}")
            raise ConsultationError("选择咨询师失败") from e

    async def _initialize_cbt_topics(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """初始化CBT话题记录表"""
        try:
            logger.info("初始化CBT话题记录表")
            
            # 确保CBT状态已初始化
            if "cbt_stage_dialogues" not in state:
                state["cbt_stage_dialogues"] = {
                    "stage_1": 0,
                    "stage_2": 0, 
                    "stage_3": 0,
                    "stage_4": 0
                }
            
            if "cbt_stage_completions" not in state:
                state["cbt_stage_completions"] = {
                    "stage_1": [],
                    "stage_2": [],
                    "stage_3": [],
                    "stage_4": []
                }
            
            # 督导师根据侧写结果提取核心主题
            newline = "\n"
            prompt = f"""
            根据以下侧写分析结果，提取来访者的核心心理问题主题，用一个简洁的短语概括：

            基本信息：{state.get("current_student_basic_info", {})}
            心理画像：{state.get("psychological_portraits", {})}
            对话历史：{newline.join(state.get("dialogue_history", []))}

            请直接回答核心主题，不要解释。例如："学业焦虑"、"社交恐惧"、"自信缺失"等。
            """
            
            core_topic = await self.supervisor_agent.llm_service.invoke(prompt)
            core_topic = core_topic.strip()

            # 如果已经初始化过CBT话题，则不重复覆盖
            if state.get("_cbt_topics_initialized"):
                logger.info("CBT话题已初始化，跳过重复设置 core_topic/topic_scores")
                return state

            # 初始化话题得分表（仅首次）
            initial_score = self.cbt_config.get("reinforcement_learning", {}).get("initial_topic_score", 5)
            if not state.get("core_topic"):
                state["core_topic"] = core_topic
            if not state.get("topic_scores"):
                state["topic_scores"] = {state["core_topic"]: initial_score}

            # 设置初始化完成标志
            state["_cbt_topics_initialized"] = True

            logger.info(f"核心话题已确定: {state.get('core_topic')}，初始分数: {initial_score}")
            return state
            
        except Exception as e:
            logger.error(f"初始化CBT话题记录表失败: {str(e)}")
            raise ConsultationError("初始化CBT话题记录表失败") from e

    async def _handle_cbt_stage_1(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理CBT阶段1：识别自动思维"""
        return await self._handle_cbt_stage(state, "stage_1")

    async def _handle_cbt_stage_2(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理CBT阶段2：确定思想陷阱"""
        return await self._handle_cbt_stage(state, "stage_2")

    async def _handle_cbt_stage_3(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理CBT阶段3：挑战自动思维"""
        return await self._handle_cbt_stage(state, "stage_3")

    async def _handle_cbt_stage_4(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理CBT阶段4：回归现实思维"""
        return await self._handle_cbt_stage(state, "stage_4")

    async def _handle_cbt_stage(self, state: Dict[str, Any], stage_name: str) -> Dict[str, Any]:
        """处理CBT具体阶段的对话"""
        try:
            # 调试：记录 state 对象 id 与当前 keys，便于跟踪是否为同一对象
            logger.debug(f"_handle_cbt_stage state id={id(state)}, keys={list(state.keys())}")
            # 确保CBT状态完整性
            if "cbt_stage_dialogues" not in state:
                # 如果之前已标记为初始化过，说明字段意外丢失，跳过自动重置以免覆盖真实记忆
                if state.get("_cbt_topics_initialized"):
                    logger.error("cbt_stage_dialogues 丢失但已标记为已初始化，跳过重置以防覆盖")
                else:
                    state["cbt_stage_dialogues"] = {
                        "stage_1": 0,
                        "stage_2": 0, 
                        "stage_3": 0,
                        "stage_4": 0
                    }
                    logger.info("重新初始化cbt_stage_dialogues")
            
            if "cbt_stage_completions" not in state:
                if state.get("_cbt_topics_initialized"):
                    logger.error("cbt_stage_completions 丢失但已标记为已初始化，跳过重置以防覆盖")
                else:
                    state["cbt_stage_completions"] = {
                        "stage_1": [],
                        "stage_2": [],
                        "stage_3": [],
                        "stage_4": []
                    }
                    logger.info("重新初始化cbt_stage_completions")
            
            if "topic_scores" not in state:
                if state.get("_cbt_topics_initialized"):
                    logger.error("topic_scores 丢失但已标记为已初始化，跳过重置以防覆盖")
                else:
                    state["topic_scores"] = {"默认话题": 5}
                    logger.info("重新初始化topic_scores")
            
            stage_config = self.cbt_config.get("cbt_stages", {}).get(stage_name, {})
            
            # 详细的阶段开始日志
            logger.info(f"🎯 开始CBT {stage_name}({stage_config.get('name', stage_name)}) 阶段对话")
            logger.info(f"   当前轮次: {state['cbt_stage_dialogues'][stage_name]}")
            logger.info(f"   已完成要素: {state['cbt_stage_completions'][stage_name]}")
            logger.info(f"   当前阶段状态: is_{stage_name}_complete = {state.get(f'is_{stage_name}_complete', False)}")

            # 更新当前阶段
            state["current_cbt_stage"] = stage_name

            # 根据话题得分选择当前最优话题
            current_topic = self._select_best_topic(state)
            
            # 咨询师基于CBT阶段和当前话题生成回应
            await self._cbt_therapist_speak(state, stage_name, current_topic)

            # 获取用户回应
            user_response = await self._get_user_input(state, f"CBT咨询师({stage_config.get('name', stage_name)})")
            state["dialogue_history"].append(f"用户：{user_response}")
            
            # 督导师评估对话内容并更新话题得分
            await self._update_topic_scores(state, user_response, current_topic)

            # 督导师评估阶段完成要素
            await self._evaluate_stage_completion(state, stage_name, user_response)

            if self.ablation_str != "wo-memory":
                # 咨询师更新工作记忆
                await self.selected_therapist.update_working_memory(state)

            # 更新对话计数
            state["cbt_stage_dialogues"][stage_name] += 1

            logger.info(f"CBT {stage_name} 对话轮次完成")
            return state
            
        except Exception as e:
            logger.error(f"CBT {stage_name} 对话失败: {str(e)}")
            raise ConsultationError(f"CBT {stage_name} 对话失败") from e

    def _select_best_topic(self, state: Dict[str, Any]) -> str:
        """根据话题得分选择当前最优话题"""
        topic_scores = state.get("topic_scores", {})
        if not topic_scores:
            return state.get("core_topic", "情绪困扰")
        
        # 选择得分最高的话题
        best_topic = max(topic_scores.items(), key=lambda x: x[1])[0]
        logger.info(f"当前选择话题: {best_topic}，得分: {topic_scores[best_topic]}")
        return best_topic

    async def _cbt_therapist_speak(self, state: Dict[str, Any], stage_name: str, current_topic: str):
        """CBT咨询师基于阶段和话题生成回应"""
        stage_config = self.cbt_config.get("cbt_stages", {}).get(stage_name, {})
        
        # 获取督导师的CBT阶段指导
        advice = await self.supervisor_agent.offer_cbt_stage_advice(state, stage_name, stage_config, current_topic)

        # 加载CBT专门的提示词
        from src.utils.prompt_loader import PromptLoader
        cbt_prompts = PromptLoader.load_prompts("cbt")

        # 优先使用分步子问题（如果stage_config定义了sub_questions或提示词存在cbt_therapist_question）
        sub_questions = stage_config.get("sub_questions", [])

        # 初始化每阶段的子问题索引
        state.setdefault("cbt_sub_question_index", {})
        state["cbt_sub_question_index"].setdefault(stage_name, 0)

        # 如果配置中存在子问题列表，则每轮只生成/取出一个子问题，并包装成自然的多句引导
        if sub_questions:
            idx = state["cbt_sub_question_index"][stage_name]
            if idx < len(sub_questions):
                raw_q = sub_questions[idx]
            else:
                # 超出子问题索引时，循环使用最后一个问题作为延伸问法
                raw_q = sub_questions[-1]

            # 简化问题组合，不再使用固定格式
            # 使用最近一条用户话作为回顾关键词（如果可用），但不要逐字引用，改为一句概括性复述
            last_user = ""
            for item in reversed(state.get("dialogue_history", [])):
                if item.startswith("用户："):
                    last_user = item.replace("用户：", "").strip()
                    break

            recap = ""
            transition = ""
            # 提取用户话语的关键词进行简短回应，而不是全盘概括
            if last_user:
                try:
                    keyword_prompt = f"从这段话中提取1-2个最重要的关键词，用于简短回应：\n\n{last_user}\n\n只需返回关键词，用中文顿号「、」分隔。"
                    keywords = await self.supervisor_agent.llm_service.invoke(keyword_prompt)
                    keywords = keywords.strip().replace('\n', '').replace(',', '、').replace('，', '、')
                    if keywords and len(keywords) < 20:  # 确保是简短的关键词
                        recap = f"关于{keywords}，"
                        
                        # 生成温暖的过渡句
                        transition_prompt = f"""基于用户刚才的话，生成一句温暖、自然的过渡句。要求：
                        1. 体现理解和关心，但不要用固定套话
                        2. 可以是鼓励、安慰或相关的温暖表达
                        3. 15-25字左右
                        4. 口吻亲切自然，像朋友聊天

                        用户刚说：{last_user}

                        请直接返回一句过渡话："""
                        transition_text = await self.supervisor_agent.llm_service.invoke(transition_prompt)
                        transition = transition_text.strip().replace('\n', ' ')  # 移除换行符但不限制长度
                except Exception:
                    recap = ""
                    transition = ""
            empathy = ""  # 删除固定套话
            # 生成带有举例的问题变体，帮助用户理解如何回答
            variants = []
            try:
                variant_prompt = f"""基于以下提示生成一个自然的问题，要求：
1. 保持专业性和亲切口吻
2. 在问题后适当加入"如"开头的简单举例，帮助用户理解回答方向
3. 不要数字编号
4. 让回复自然完整，不要生硬截断，尽量控制在50字以内

提示问题：{raw_q}
用户最近提到：{last_user}

请直接返回一个完整的问题（包含举例）。"""
                enhanced_question = await self.supervisor_agent.llm_service.invoke(variant_prompt)
                enhanced_question = enhanced_question.strip()
                if enhanced_question:
                    variants.append(enhanced_question)  # 移除强制添加问号，让LLM自然处理标点
            except Exception:
                pass
            
            # 如果LLM生成失败，使用简单的后备方案
            if not variants:
                base_q = raw_q  # 移除强制添加问号，保持原始格式
                # 简单添加举例
                if "感受" in base_q or "感觉" in base_q:
                    variants.append(f"{base_q} 如紧张、失落、愤怒等等。")
                elif "想法" in base_q or "念头" in base_q:
                    variants.append(f"{base_q} 如担心、质疑、期待等。")
                else:
                    variants.append(base_q)

            # 随机选择一个变体以增加自然性
            question = random.choice(variants)

            # 组合回复：关键词回顾 + 温暖过渡 + 问题
            if recap and transition:
                composed = f"{recap}{transition} {question}".strip()
            elif recap:
                composed = f"{recap} {question}".strip()
            else:
                composed = question.strip()
                
            # 清理空格并保证首字母大写
            composed = self._clean_numbering(composed.strip())
            if composed and composed[0].islower():
                composed = composed[0].upper() + composed[1:]

            state["dialogue_history"].append(f"咨询师：{composed}")
            # 递增子问题索引
            state["cbt_sub_question_index"][stage_name] += 1
            return

        # 如果没有静态子问题列表，尝试使用提示模板动态生成单条子问题
        if cbt_prompts and "cbt_therapist_question" in cbt_prompts:
            prompt_template = cbt_prompts["cbt_therapist_question"]
            single_q_prompt = PromptLoader.format_prompt(
                prompt_template,
                stage_name=stage_name,
                stage_description=stage_config.get("description", ""),
                stage_goals="\n".join(stage_config.get("stage_goals", [])),
                supervisor_advice=advice,
                current_topic=current_topic,
                dialogue_history="\n".join(state.get("dialogue_history", [])[-6:])
            )
            # 要求 LLM 输出遵循“回顾→共情→单一问题→过渡”的四段式文本，便于自然衔接
            # 要求 LLM 在回顾中不要逐字引用用户原话，而是用概括性复述；确保输出遵循四段式
            format_prompt = single_q_prompt + "\n\n请用自然的语言直接回应学生，就像面对面聊天一样。避免套话和客套话。"
            question_block = await self.supervisor_agent.llm_service.invoke(format_prompt)
            question_block = question_block.strip()

            # 如果 LLM 只返回了一个问题（兼容情况），则用默认包装
            if '\n' not in question_block or len(question_block.splitlines()) < 2:
                last_user = "" 
                for item in reversed(state.get("dialogue_history", [])):
                    if item.startswith("用户："):
                        last_user = item.replace("用户：", "").strip()
                        break

                # 提取关键词而非全盘概括
                recap = ""
                transition = ""
                if last_user:
                    try:
                        keyword_prompt = f"从这段话中提取1-2个最重要的关键词，用于简短回应：\n\n{last_user}\n\n只需返回关键词，用中文顿号「、」分隔。"
                        keywords = await self.supervisor_agent.llm_service.invoke(keyword_prompt)
                        keywords = keywords.strip().replace('\n', '').replace(',', '、').replace('，', '、')
                        if keywords and len(keywords) < 20:  # 确保是简短的关键词
                            recap = f"关于{keywords}，"
                            
                            # 生成温暖的过渡句
                            transition_prompt = f"""基于用户刚才的话，生成一句温暖、自然的过渡句。要求：
                            1. 体现理解和关心，但不要用固定套话
                            2. 可以是鼓励、安慰或相关的温暖表达
                            3. 15-25字左右
                            4. 口吻亲切自然，像朋友聊天

                            用户刚说：{last_user}

                            请直接返回一句过渡话："""
                            transition_text = await self.supervisor_agent.llm_service.invoke(transition_prompt)
                            transition = transition_text.strip().replace('\n', ' ')  # 移除换行符但不限制长度
                    except Exception:
                        recap = ""
                        transition = ""
                single_q = question_block  # 移除强制添加问号，保持LLM生成的原始格式
                
                # 组合回复
                if recap and transition:
                    composed = f"{recap}{transition} {single_q}".strip()
                elif recap:
                    composed = f"{recap} {single_q}".strip()
                else:
                    composed = single_q.strip()
                    
                composed = self._clean_numbering(composed)
                state["dialogue_history"].append(f"咨询师：{composed}")
            else:
                # 直接使用 LLM 输出的多行文本（合并为一句话块以便历史记录）
                compact = ' '.join([line.strip() for line in question_block.splitlines() if line.strip()])
                # 清理可能的编号
                compact = self._clean_numbering(compact)
                state["dialogue_history"].append(f"咨询师：{compact}")

            # 递增子问题索引以用于后续逻辑
            state["cbt_sub_question_index"][stage_name] += 1
            return

        # 后备：如果没有子问题模板，则生成完整的自然回应
        newline = "\n"
        
        # 获取用户最近发言并提取关键词
        last_user = ""
        for item in reversed(state.get("dialogue_history", [])):
            if item.startswith("用户："):
                last_user = item.replace("用户：", "").strip()
                break
        
        full_prompt = f"""
        作为认知行为疗法(CBT)咨询师，请生成一个自然、亲切的回应。

        督导师指导：{advice}
        当前重点话题：{current_topic}
        用户刚才说：{last_user}

        对话历史：
        {newline.join(state.get('dialogue_history', [])[-4:])}

        要求：
        1. 从用户话语中提取关键词进行简短回应
        2. 在关键词回顾和问题之间加入温暖的过渡句（如鼓励、理解等）
        3. 针对话题"{current_topic}"提出一个专业问题
        4. 适当用"如"举例帮助用户理解回答方向
        5. 保持亲切专业的口吻，让回复自然完整
        6. 绝对不要使用数字编号
        7. 格式：关键词回顾 + 温暖过渡 + 问题举例

        直接给出咨询师的话：
        """
        response = await self.supervisor_agent.llm_service.invoke(full_prompt)
        response = self._clean_numbering(response.strip())
        state["dialogue_history"].append(f"咨询师：{response}")

    async def _update_topic_scores(self, state: Dict[str, Any], user_response: str, current_topic: str):
        """督导师评估用户回应并更新话题得分"""
        reward_system = self.cbt_config.get("reinforcement_learning", {}).get("reward_system", {})
        
        try:
            result = await self.supervisor_agent.evaluate_topic_relevance(current_topic, user_response)
            relevance = result.get("relevance_score", "slightly_relevant")
            new_topic = result.get("new_topic", "").strip()
            
            # 更新当前话题得分
            score_change = reward_system.get(relevance, 0)
            state["topic_scores"][current_topic] = state["topic_scores"].get(current_topic, 5) + score_change
            
            # 如果有新话题，添加到记录表
            if new_topic and new_topic not in state["topic_scores"]:
                initial_score = self.cbt_config.get("reinforcement_learning", {}).get("initial_topic_score", 5)
                state["topic_scores"][new_topic] = initial_score
                logger.info(f"发现新话题: {new_topic}，初始分数: {initial_score}")
            
            logger.info(f"话题得分更新 - {current_topic}: {score_change:+d} -> {state['topic_scores'][current_topic]}")
            
        except Exception as e:
            logger.error(f"更新话题得分失败: {str(e)}")

    async def _evaluate_stage_completion(self, state: Dict[str, Any], stage_name: str, user_response: str):
        """督导师评估阶段完成要素"""
        # 调试：记录 state 对象 id 与当前 keys，便于追踪是否为同一对象
        logger.debug(f"_evaluate_stage_completion state id={id(state)}, keys={list(state.keys())}")
        stage_config = self.cbt_config.get("cbt_stages", {}).get(stage_name, {})
        required_elements = stage_config.get("completion_criteria", {}).get("required_elements", [])

        # 构建评估提示词
        newline = "\n"
        prompt = f"""
        作为督导师，评估来访者在CBT{stage_config.get('name', stage_name)}阶段的完成情况：

        阶段要求的完成要素：{required_elements}
        
        最近对话内容：
        {newline.join(state.get('dialogue_history', [])[-8:])}

        请仔细评估来访者在本轮对话中完成了哪些要素。对每个要素进行详细分析：

        请以JSON格式回应：
        {{
            "element_analysis": {{
                "要素1": {{"completed": true/false, "evidence": "支持判断的证据", "explanation": "详细解释"}},
                "要素2": {{"completed": true/false, "evidence": "支持判断的证据", "explanation": "详细解释"}}
            }},
            "completed_elements": ["已完成的要素列表"],
            "overall_assessment": "整体评估说明",
            "completion_progress": "完成进度描述"
        }}
        """
        
        try:
            result = await self.supervisor_agent.llm_service.invoke_json(prompt, default_value={})
            
            # 详细输出督导师的判断
            logger.info(f"=== CBT {stage_name} 阶段完成要素评估 ===")
            
            element_analysis = result.get("element_analysis", {})
            for element, analysis in element_analysis.items():
                status = "✓ 已完成" if analysis.get("completed", False) else "✗ 未完成"
                logger.info(f"要素: {element} - {status}")
                logger.info(f"  证据: {analysis.get('evidence', '无')}")
                logger.info(f"  解释: {analysis.get('explanation', '无')}")
            
            completed = result.get("completed_elements", [])
            current_completed = len(state["cbt_stage_completions"][stage_name])
            total_required = len(required_elements);
            
            logger.info(f"整体评估: {result.get('overall_assessment', '无')}")
            logger.info(f"完成进度: {result.get('completion_progress', '无')}")
            logger.info(f"当前进度: {current_completed + len(completed)}/{total_required}")
            
            # 更新阶段完成情况 - 累积完成，不重新初始化
            for element in completed:
                if element not in state["cbt_stage_completions"][stage_name]:
                    state["cbt_stage_completions"][stage_name].append(element)
                    logger.info(f"🎯 新完成要素: {element}")
            # 如果本轮补全的要素涵盖了阶段所需的全部要素，则显式标记阶段完成（使用布尔标记，避免混淆计数器）
            if len(state["cbt_stage_completions"][stage_name]) >= total_required and total_required > 0:
                state['cbt_stage_dialogues'][stage_name] = 1
                state[f'is_{stage_name}_complete'] = True
                logger.info(f"🎉 CBT {stage_name} 阶段所有要素已完成，标记 is_{stage_name}_complete = True")
                    
        except Exception as e:
            logger.error(f"评估阶段完成情况失败: {str(e)}")
            # 使用简单的评估逻辑作为后备
            logger.info("使用简化评估逻辑")

    async def _check_cbt_stage_complete(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """检查CBT阶段是否完成"""
        try:
            # 展示一下当前的state（简短）并记录 id 以便追踪是否为同一对象
            logger.info(f"当前 state id={id(state)}, keys={list(state.keys())}")

            # 确保CBT状态完整性：只有在尚未初始化过话题的情况下才允许自动重置
            if "cbt_stage_dialogues" not in state:
                if state.get("_cbt_topics_initialized"):
                    logger.error("cbt_stage_dialogues 丢失但已标记为已初始化，跳过重置以防覆盖")
                else:
                    state["cbt_stage_dialogues"] = {
                        "stage_1": 0,
                        "stage_2": 0, 
                        "stage_3": 0,
                        "stage_4": 0
                    }
                    logger.info("重新初始化cbt_stage_dialogues")

            if "cbt_stage_completions" not in state:
                if state.get("_cbt_topics_initialized"):
                    logger.error("cbt_stage_completions 丢失但已标记为已初始化，跳过重置以防覆盖")
                else:
                    state["cbt_stage_completions"] = {
                        "stage_1": [],
                        "stage_2": [],
                        "stage_3": [],
                        "stage_4": []
                    }
                    logger.info("重新初始化cbt_stage_completions")
            
            stage_name = state.get("current_cbt_stage", "stage_1")
            stage_config = self.cbt_config.get("cbt_stages", {}).get(stage_name, {})
            
            logger.info(f"=== 检查CBT {stage_name}({stage_config.get('name', stage_name)}) 阶段完成状态 ===")
            
            # 检查是否达到最大对话轮次
            max_dialogues = stage_config.get("max_dialogues", 5)
            current_dialogues = state["cbt_stage_dialogues"][stage_name]
            
            logger.info(f"当前对话轮次: {current_dialogues}/{max_dialogues}")
            
            if current_dialogues >= max_dialogues:
                state[f"is_{stage_name}_complete"] = True
                logger.info(f"🔄 CBT {stage_name} 达到最大轮次({max_dialogues})，强制完成阶段")
                return state
            
            # 检查是否满足完成条件
            required_elements = stage_config.get("completion_criteria", {}).get("required_elements", [])
            completion_threshold = stage_config.get("completion_criteria", {}).get("completion_threshold", len(required_elements))
            completed_elements = state["cbt_stage_completions"][stage_name]
            
            # 详细输出完成情况
            logger.info(f"完成要素检查:")
            logger.info(f"  要求的要素: {required_elements}")
            logger.info(f"  已完成要素: {completed_elements}")
            logger.info(f"  完成阈值: {completion_threshold}")
            logger.info(f"  当前进度: {len(completed_elements)}/{len(required_elements)} (需要: {completion_threshold})")
            
            if len(completed_elements) >= completion_threshold:
                state[f"is_{stage_name}_complete"] = True
                logger.info(f"✅ CBT {stage_name} 满足完成条件，可以进入下一阶段")
            else:
                state[f"is_{stage_name}_complete"] = False
                remaining = completion_threshold - len(completed_elements)
                logger.info(f"⏳ CBT {stage_name} 还需完成 {remaining} 个要素，继续当前阶段")
                
            return state
            
        except Exception as e:
            logger.error(f"检查CBT阶段完成状态失败: {str(e)}")
            raise ConsultationError("检查CBT阶段完成状态失败") from e

    def _should_continue_cbt_stage(self, state: Dict[str, Any], stage_name: str) -> bool:
        """判断是否继续当前CBT阶段"""
        is_complete = state.get(f"is_{stage_name}_complete", False)
        should_continue = not is_complete
        
        logger.info(f"🔍 阶段切换判断 - {stage_name}:")
        logger.info(f"   is_{stage_name}_complete = {is_complete}")
        logger.info(f"   should_continue = {should_continue}")
        logger.info(f"   下一步: {'继续当前阶段' if should_continue else '切换到下一阶段'}")
        
        return should_continue

    async def _handle_consultation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理咨询对话阶段(单轮)"""
        try:
            logger.info(f"咨询对话轮次: {state['current_consultation_dialogue_index']}")

            # 获取选中的咨询师
            selected_therapist = self.selected_therapist

            # 咨询师生成回应
            await selected_therapist.speak(state, self.supervisor_agent, self.memory_manager, self.ablation_str)

            # 获取用户回应
            user_response = await self._get_user_input(state, "咨询师")
            state["dialogue_history"].append(f"用户：{user_response}")
            
            if self.ablation_str != "wo-memory":
                # 咨询师更新工作记忆
                await selected_therapist.update_working_memory(state)

                # 指导员更新工作记忆
                await self.supervisor_agent.update_profile_working_memory(state)

            # 更新对话索引
            state["current_consultation_dialogue_index"] += 1

            logger.info("咨询对话轮次完成")
            return state
        except Exception as e:
            logger.error(f"咨询对话失败: {str(e)}")
            raise ConsultationError("咨询对话失败") from e

    async def _check_consultation_complete(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """检查咨询是否应该结束"""
        try:
            logger.info("检查咨询是否完成")

            # 添加轮次限制 (修改此处数字可调整最大对话轮次)
            MAX_CONSULTATION_TURNS = 10

            if state["current_consultation_dialogue_index"] >= MAX_CONSULTATION_TURNS:
                state["is_consultation_complete"] = True
                logger.info(f"咨询对话达到最大轮次({MAX_CONSULTATION_TURNS})，结束咨询阶段")
                return state

            # 由指导员判断是否完成咨询
            is_consultation_complete = await self.supervisor_agent.check_consultation_complete(state)

            # 更新状态
            if is_consultation_complete:
                state["is_consultation_complete"] = True
                logger.info("指导员判断咨询阶段完成")
            else:
                logger.info("指导员判断咨询阶段继续")

            return state
        except Exception as e:
            logger.error(f"检查咨询完成状态失败: {str(e)}")
            raise ConsultationError("检查咨询完成状态失败") from e

    def _should_continue_consultation(self, state: Dict[str, Any]) -> bool:
        """判断是否继续咨询"""
        return not state.get("is_consultation_complete", False)

    async def _handle_final_scale(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理最终量表填写"""
        try:
            logger.info("加载用户最终量表数据")

            # 在实际应用中，这里应该从数据库或API获取用户咨询后填写的量表数据
            # 此处使用模拟数据
            state["scales_result_after_consultation"] = {
                "GHQ-20": {
                    "final_score": 3,
                    "assessment": "心理状态良好"
                },
                "Campbell": {
                    "final_score": 15,
                    "assessment": "较高幸福感"
                },
                "CPSS": {
                    "final_score": 25,
                    "assessment": "轻度压力"
                }
            }

            logger.info("最终量表数据加载完成")
            return state
        except Exception as e:
            logger.error(f"加载最终量表数据失败: {str(e)}")
            raise ConsultationError("加载最终量表数据失败") from e

    async def _handle_evaluation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """评估咨询效果"""
        try:
            logger.info("开始评估咨询效果")

            # 获取选中的咨询师类型
            therapy_type = state.get("selected_therapist")

            # 由指导员评估咨询效果
            evaluation_result = await self.supervisor_agent.evaluate_therapist(
                state,
                therapy_type
            )

            state["evaluation_result"] = evaluation_result

            logger.info("咨询评估完成")
            return state
        except Exception as e:
            logger.error(f"评估咨询效果失败: {str(e)}")
            raise ConsultationError("评估咨询效果失败") from e

    async def _update_agent_skills(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """更新智能体技能"""
        try:
            logger.info("开始更新智能体技能")

            # 获取选中的咨询师
            therapy_type = state.get("selected_therapist")
            selected_therapist = next((t for t in self.therapist_agents if t.therapy_type == therapy_type), None)

            if not selected_therapist:
                logger.warning(f"找不到选定的咨询师: {therapy_type}")
                return state

            # 获取指导员的评估结果
            evaluation_result = state.get("evaluation_result", "")
            
            if self.ablation_str != "wo-memory":  # without memory 直接不更新 使所有的memory都为初始状态
                # 咨询师更新技能记忆
                await selected_therapist.strengthen_skill(state, evaluation_result, self.memory_manager)

                logger.info("智能体技能更新完成")
            return state
        except Exception as e:
            logger.error(f"更新智能体技能失败: {str(e)}")
            raise ConsultationError("更新智能体技能失败") from e

    async def _save_medical_record(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """保存病历记录"""
        try:
            logger.info("开始保存病历记录")

            # 获取选中的咨询师类型
            therapy_type = state.get("selected_therapist_type")

            # 确保有学生ID
            if "current_student_basic_info" not in state or "id" not in state["current_student_basic_info"]:
                # 生成随机ID
                import uuid
                random_id = f"user_{uuid.uuid4().hex[:8]}"

                if "current_student_basic_info" not in state:
                    state["current_student_basic_info"] = {}

                state["current_student_basic_info"]["id"] = random_id
                logger.info(f"为用户生成随机ID: {random_id}")

            # 生成并保存医疗记录
            record_id = await self.supervisor_agent.create_student_medical_record(
                state,
                therapy_type,
                self.memory_manager
            )

            if record_id:
                logger.info(f"病历记录已保存，ID: {record_id}")
                state["medical_record_id"] = record_id
            else:
                logger.warning("病历记录保存失败")

            return state
        except Exception as e:
            logger.error(f"保存病历记录失败: {str(e)}")
            raise ConsultationError("保存病历记录失败") from e

    async def _finalize_consultation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """完成咨询流程"""
        try:
            logger.info("完成咨询流程")

            # 添加结束语到对话历史
            conclusion = "感谢您使用心理咨询系统，希望此次咨询能够帮助到您。如有需要，欢迎随时回来继续咨询。祝您健康快乐！"
            state["dialogue_history"].append(f"系统：{conclusion}")

            # 在实际应用中，这里可以添加发送总结报告等功能

            # 标记咨询完成
            state["current_phase"] = "completed"

            logger.info("咨询流程已完成")
            return state
        except Exception as e:
            logger.error(f"完成咨询流程失败: {str(e)}")
            raise ConsultationError("完成咨询流程失败") from e

    async def _get_user_input(self, state: Dict[str, Any], agent_type: str = "侧写师") -> str:
        """获取用户输入

        在实际应用中，这里会与用户界面交互
        在研究原型中，简单使用控制台输入

        Args:
            state: 当前状态
            agent_type: 当前交互的智能体类型

        Returns:
            str: 用户输入
        """
        # 获取最后一条消息显示给用户
        if state["dialogue_history"]:
            last_message = state["dialogue_history"][-1]
            logger.info(f"\n{last_message}")

        # 获取用户输入
        user_input = input(f"\n请输入您的回复 (输入'结束'停止对话): ")

        # 检查是否要结束对话
        if user_input.strip().lower() in ["结束", "退出", "quit", "exit"]:
            if agent_type == "侧写师":
                state["is_profile_complete"] = True
            else:
                state["is_consultation_complete"] = True
            return "我想结束这次对话。"

        return user_input

    async def run(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """运行咨询流程"""
        try:
            logger.info("开始运行咨询流程")

            if not self.compiled_graph:
                logger.info("编译咨询流程图")
                self.compile()

            final_state = await self.compiled_graph.ainvoke(initial_state)

            logger.info("咨询流程成功完成")
            return final_state

        except Exception as e:
            logger.error(f"运行咨询流程失败: {str(e)}")
            raise ConsultationError("咨询流程执行失败") from e

    def _should_continue_stage_1(self, state: Dict[str, Any]) -> bool:
        """判断是否继续CBT阶段1"""
        should_continue = self._should_continue_cbt_stage(state, "stage_1")
        logger.info(f"阶段1完成检查: {'继续' if should_continue else '完成，进入阶段2'}")
        return should_continue

    def _should_continue_stage_2(self, state: Dict[str, Any]) -> bool:
        """判断是否继续CBT阶段2"""
        should_continue = self._should_continue_cbt_stage(state, "stage_2")
        logger.info(f"阶段2完成检查: {'继续' if should_continue else '完成，进入阶段3'}")
        return should_continue

    def _should_continue_stage_3(self, state: Dict[str, Any]) -> bool:
        """判断是否继续CBT阶段3"""
        should_continue = self._should_continue_cbt_stage(state, "stage_3")
        logger.info(f"阶段3完成检查: {'继续' if should_continue else '完成，进入阶段4'}")
        return should_continue

    def _should_continue_stage_4(self, state: Dict[str, Any]) -> bool:
        """判断是否继续CBT阶段4"""
        should_continue = self._should_continue_cbt_stage(state, "stage_4")
        logger.info(f"阶段4完成检查: {'继续' if should_continue else '完成，进入最终量表'}")
        return should_continue

    def _clean_numbering(self, text: str) -> str:
        """清理文本中的数字编号"""
        import re
        # 删除行首的数字编号如 "1. ", "2. ", "3. " 等
        text = re.sub(r'^\s*\d+\.\s*', '', text)
        # 删除句子开头的数字编号（处理多句话的情况）
        text = re.sub(r'(\.|！|？)\s*\d+\.\s*', r'\1 ', text)
        # 删除句子中间的数字编号如 " 1. ", " 2. " 等
        text = re.sub(r'\s+\d+\.\s+', ' ', text)
        # 删除括号编号如 "(1) ", "(2) " 等
        text = re.sub(r'\s*\(\d+\)\s*', ' ', text)
        # 删除中文编号如 "一、", "二、" 等
        text = re.sub(r'[一二三四五六七八九十]\s*[、．]\s*', '', text)
        # 清理多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        return text