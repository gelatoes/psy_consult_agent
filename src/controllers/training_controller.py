# src/controllers/training_controller.py
import copy
import datetime
import pprint
from typing import Dict, Any, List, Callable
from src.memory.memory_manager import MemoryManager
from src.agents import StudentAgent, TherapistAgent, ProfilerAgent, SupervisorAgent
from src.controllers.base_controller import BaseController
from src.utils.logger import logger
from src.utils.exceptions import ConsultationError
from pathlib import Path
import json


class TrainingController(BaseController):
    """训练模式控制器"""

    def __init__(
            self,
            student_configs: List[Dict[str, Any]],  # 学生配置列表
            profiler_agent: ProfilerAgent,
            therapist_agents: List[TherapistAgent],
            supervisor_agent: SupervisorAgent,
            memory_manager: MemoryManager,  
            ablation_str: str = "none" # 消融参数 影响注册节点和状态转换
    ):
        self.memory_manager = memory_manager
        # 初始化学生配置和索引
        self.student_configs = student_configs
        self.current_student_index = 0

        # 初始化agents
        self.profiler_agent = profiler_agent
        self.therapist_agents = therapist_agents
        self.supervisor_agent = supervisor_agent
        self.current_student_agent = None
        self.ablation_str = ablation_str

        # 治疗师索引和当前治疗师
        self.current_therapist_index = 0
        if self.therapist_agents:
            self.current_therapist_agent = self.therapist_agents[self.current_therapist_index]
            logger.info(f"初始化当前治疗师: {self.current_therapist_agent.therapy_type}")
        else:
            self.current_therapist_agent = None
            logger.warning("没有可用的治疗师")

        # state快照
        self.state_snapshots = {}

        super().__init__()

    def _register_nodes(self):
        """注册训练流程的所有节点"""
        try:
            self.graph.add_node("initialize", self._initialize_training)
            self.graph.add_node("initial_scale", self._handle_initial_scale)

            # 删除无用节点 create_portrait

            # 如果没有wo-profiler的消融 全部注册
            if self.ablation_str != "wo-profiler":
                self.graph.add_node("assess_portrait", self._handle_assess_portrait)
                self.graph.add_node("profiler_dialogue", self._handle_profiler_dialogue)
                self.graph.add_node("check_profiler_complete", self._check_profiler_complete)
                self.graph.add_node("save_post_profiler_state", self._save_post_profiler_state)
            self.graph.add_node("start_therapist_session", self._start_therapist_session)
            self.graph.add_node("therapist_dialogue", self._handle_therapist_dialogue)
            self.graph.add_node("check_session_complete", self._check_session_complete)
            self.graph.add_node("switch_to_next_therapist", self._switch_to_next_therapist)
            self.graph.add_node("evaluate_therapist", self._evaluate_therapist)
            # 每一个咨询师接诊完一个学生，都要形成一个病历
            self.graph.add_node("create_student_medical_record", self._create_student_medical_record)
            # 删除无用节点 check_all_therapists_complete，直接使用条件判断
            
            # 简化学生切换相关节点
            # 删除无用节点 check_next_student
            self.graph.add_node("switch_to_next_student", self._switch_to_next_student)

            self.graph.add_node("end_training", self._end_training)  # 添加结束训练节点

        except Exception as e:
            logger.error(f"Error registering training nodes: {str(e)}")
            raise ConsultationError("Failed to register training nodes") from e

    def _define_edges(self):
        """定义训练模式的状态转换规则"""
        try:
            # 设置入口点为initialize节点
            self.graph.set_entry_point("initialize")

            # 1. 初始化 -> 量表测评
            self.graph.add_edge("initialize", "initial_scale")
            
            # 如果没有wo-profiler的消融
            if self.ablation_str != "wo-profiler":
            # 2. 量表测评 -> 侧写对话
                self.graph.add_edge("initial_scale", "profiler_dialogue")

                # 3. 侧写对话循环
                self.graph.add_edge("profiler_dialogue", "check_profiler_complete")
                self.graph.add_conditional_edges(
                    "check_profiler_complete",
                    self._should_continue_profiler,
                    {
                        True: "profiler_dialogue",  # 继续侧写对话
                        False: "assess_portrait"  # 直接进入评估画像阶段，跳过创建画像
                    }
                )

                # 4. 评估画像
                self.graph.add_edge("assess_portrait", "save_post_profiler_state")

                # 5. 串行咨询流程
                self.graph.add_edge("save_post_profiler_state", "start_therapist_session")
            else:
                # 2. 量表测评 -> 咨询师选择
                self.graph.add_edge("initial_scale", "start_therapist_session")
                
            self.graph.add_edge("start_therapist_session", "therapist_dialogue")
            self.graph.add_edge("therapist_dialogue", "check_session_complete")

            # 6. 咨询师会话循环
            self.graph.add_conditional_edges(
                "check_session_complete",
                self._should_continue_session,
                {
                    True: "therapist_dialogue",  # 继续当前咨询师的会话
                    False: "evaluate_therapist"  # 结束当前咨询师的会话
                }
            )

            # 7. 咨询师切换流程
            self.graph.add_edge("evaluate_therapist", "create_student_medical_record")
            # 直接使用条件判断，无需额外的检查节点
            self.graph.add_conditional_edges(
                "create_student_medical_record",
                self._should_continue_therapists,
                {
                    True: "switch_to_next_therapist",  # 切换到下一个咨询师
                    False: "switch_to_next_student"  # 所有咨询师完成，检查是否有下一个学生
                }
            )

            self.graph.add_edge("switch_to_next_therapist", "start_therapist_session")

            # 8. 学生切换流程 - 简化，直接使用条件判断
            self.graph.add_conditional_edges(
                "switch_to_next_student",
                self._has_next_student,
                {
                    True: "initialize",  # 切换到新学生后重新开始训练流程
                    False: "end_training"  # 结束整个训练
                }
            )

            logger.info("Training edges defined successfully")

        except Exception as e:
            logger.error(f"Error defining training edges: {str(e)}")
            raise ConsultationError("Failed to define training edges") from e

    def _initialize_training(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """初始化训练状态，从配置创建学生智能体

        主要工作：
        1. 获取当前学生配置
        2. 根据配置创建一个学生智能体
        3. 更新训练状态

        Args:
            state: 当前状态

        Returns:
            初始化后的state
        """
        logger.info("---------------------------------_initialize_training---------------------------------")

        # 检查是否有有效的咨询师
        if not self.therapist_agents:
            # logger.error("没有可用的咨询师智能体，无法进行训练")
            raise ConsultationError("No therapist agents available for training")

        # 重置治疗师索引
        self.current_therapist_index = 0
        self.current_therapist_agent = self.therapist_agents[self.current_therapist_index]

        # 获取这一轮学生配置
        current_student_config = self.student_configs[self.current_student_index]

        # 根据学生配置生成学生智能体
        self.current_student_agent = StudentAgent(current_student_config)

        # 初始化state
        state["shared_memory"] = {}
        state["supervisor_working_memory"] = {}
        state["dialogue_history"] = []
        state["psychological_portraits"] = {}
        state["current_phase"] = 'initial'
        state["initial_scales_result"] = {}
        state["scales_result_after_consultation"] = {}
        state["current_student_basic_info"] = current_student_config["basic_info"]
        state["current_profile_dialogue_index"] = 0
        state["current_consultation_dialogue_index"] = 0
        state["is_profile_complete"] = False
        state["is_consultation_complete"] = False

        student_index = state["current_student_index"]
        student_id = current_student_config['basic_info'].get('id', 'unknown')
        logger.info(f"当前处理学生索引: {student_index}, ID: {student_id}")

        return state

    async def _handle_initial_scale(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """让上一部生成的学生进行量表测评，并把填写的结果挂在state上

        Args:
            state: 当前状态
        Returns:
            更新后的状态
        """

        logger.info("---------------------------------_handle_initial_scale---------------------------------")
        await self.current_student_agent.fill_scale("before_consultation", ["GHQ-20"], state)
        logger.info("学生已完成初始量表填写")

        return state

    async def _handle_profiler_dialogue(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理侧写师对话阶段 (单轮)

        侧写师说话，然后再学生回答。
        将对话记录挂在短期记忆的对话记录上（其实就是修改state）。
        同时咨侧写师更新工作记忆，指导员的工作记忆
        """
        logger.info("---------------------------------_handle_profiler_dialogue---------------------------------")
        logger.info(f"当前的侧写轮次是：{state['current_profile_dialogue_index']}")
        if state["current_profile_dialogue_index"] == 0:
            # 侧写师开头
            state["dialogue_history"].append("侧写师：同学你好！")
            # 学生说话
            await self.current_student_agent.speak(state)
        else:
            # 侧写师说话
            await self.profiler_agent.speak(state, self.supervisor_agent, self.memory_manager, self.ablation_str)
            # 学生说话
            await self.current_student_agent.speak(state)
        if self.ablation_str != "wo-memory":  
            # 侧写师更新工作记忆
            await self.profiler_agent.update_working_memory(state)
            # 指导员更新工作记忆
            await self.supervisor_agent.update_profile_working_memory(state)
        # 侧写师更新心理画像
        await self.profiler_agent.update_psychological_portraits(state)

        return state

    async def _check_profiler_complete(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """检查侧写师对话是否应该结束


        如果指导员判断下来可以结束侧写，那么把状态设置为profiler_complete=True。

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("---------------------------------_check_profiler_complete---------------------------------")
        is_profile_complete = await self.supervisor_agent.check_profile_complete(state)  # 返回true就是认为可以结束，返回false就是认为不能结束

        logger.info(f"指导员判断侧写是否完成: {is_profile_complete}")

        if is_profile_complete:
            state["is_profile_complete"] = True
        else:
            state["current_profile_dialogue_index"] = state["current_profile_dialogue_index"] + 1

        # 控制咨询轮次
        if state["current_profile_dialogue_index"] > 8:
            state['is_profile_complete'] = True

        return state

    def _should_continue_profiler(self, state: Dict[str, Any]) -> bool:
        """判断是否继续侧写对话

        由指导员判断是否信息收集完成，是否要结束侧写阶段。

        Returns:
            True表示继续对话,False表示结束侧写
        """
        logger.info("---------------------------------_should_continue_profiler---------------------------------")
        if state["is_profile_complete"]:
            return False
        else:
            return True

    # 删除无用的create_portrait函数，直接从check_profiler_complete跳到assess_portrait
    async def _handle_assess_portrait(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """指导员评估侧写师得出的心理画像（state上）和真实的心理画像（学生agent的属性上）的差异，给出指导意见
        侧写师收到指导意见后吸收总结，成为技能记忆
        """
        logger.info("---------------------------------_handle_assess_portrait---------------------------------")
        supervisor_overall_advice = await self.supervisor_agent.assess_portrait(state, self.current_student_agent.psychological_portrait)
        if self.ablation_str != 'wo-memory':
            await self.profiler_agent.strengthen_skill(state, supervisor_overall_advice, self.memory_manager)
        return state

    async def _save_post_profiler_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """保存侧写完成后的状态快照

        用于后续咨询师训练时的状态重置

        Args:f
            state: 当前状态

        Returns:
            保存快照后的状态
        """
        logger.info("---------------------------------_save_post_profiler_state---------------------------------")
        self.state_snapshots = copy.deepcopy(state)

        return state

    async def _start_therapist_session(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """开始新咨询师的会话
        重置状态到侧写后,初始化新咨询师相关状态
        我感觉就是把上一步保存的快照应用在这里，同时确定好当前轮到哪个咨询师

        Args:
            state: 当前状态

        Returns:
            重置后的状态
        """
        logger.info("---------------------------------_start_therapist_session---------------------------------")

        # 检查是否有有效的咨询师
        if not self.therapist_agents:
            logger.error("没有可用的咨询师智能体，无法开始咨询会话")
            raise ConsultationError("No therapist agents available for session")

        # 重置咨询相关状态
        state["current_consultation_dialogue_index"] = 0
        state["is_consultation_complete"] = False
        state["current_phase"] = "consultation"

        logger.info(
            f"开始咨询会话，当前治疗师: {self.current_therapist_agent.therapy_type}, 流派: {self.current_therapist_agent.name}")
        logger.info(f"对话历史长度: {len(state['dialogue_history'])}")

        return state

    async def _handle_therapist_dialogue(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理咨询师对话阶段 (单轮)

        咨询师说话，然后再学生回答。
        将对话记录挂在短期记忆的对话记录上（其实就是修改state）。
        同时咨询咨询师更新工作记忆，指导员的工作记忆
        这个过程中咨询师可能会使用工具

        Args:
            state: 当前状态

        Returns:
            更新后的状态,包含本轮对话结果
        """
        logger.info("--------------------------------_handle_therapist_dialogue--------------------------------")
        logger.info(f"当前的疗愈对话轮次是：{state['current_consultation_dialogue_index']}")
        logger.info(f"当前的咨询师流派是：{self.current_therapist_agent.therapy_type}")

        # 咨询师说话
        await self.current_therapist_agent.speak(state, self.supervisor_agent, self.memory_manager, self.ablation_str)
        # 学生说话
        await self.current_student_agent.speak(state)
        if self.ablation_str != "wo-memory":
            # 侧写师更新工作记忆
            await self.current_therapist_agent.update_working_memory(state)
            # 指导员更新工作记忆
            await self.supervisor_agent.update_profile_working_memory(state)

        return state

    async def _check_session_complete(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """检查当前咨询师的会话是否应该结束

        由指导员判断是否达到治疗目标，如果达到则将state中的is_consultation_complete设置为True

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("--------------------------------_check_session_complete--------------------------------")
        is_consultation_complete = await self.supervisor_agent.check_consultation_complete(state)  # 返回true就是认为可以结束，返回false就是认为不能结束

        logger.info(f"指导员判断疗愈是否完成: {is_consultation_complete}")

        if is_consultation_complete:
            state["is_consultation_complete"] = True
        else:
            state["current_consultation_dialogue_index"] = state["current_consultation_dialogue_index"] + 1

        # 控制咨询轮次
        if state["current_consultation_dialogue_index"] > 8:
            state['is_consultation_complete'] = True
        return state

    def _should_continue_session(self, state: Dict[str, Any]) -> bool:
        """判断是否继续当前咨询师的会话

        Returns:
            True表示继续对话,False表示结束会话
        """
        logger.info("--------------------------------_should_continue_session--------------------------------")

        # 检查状态中的标志
        result = not state.get('is_consultation_complete', False)
        logger.info(f"继续咨询会话? {result}")
        return result

    async def _evaluate_therapist(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """评估当前咨询师的表现

        学生再次填写量表测评，然后指导员据学生填写的前后量表结果对咨询师给出指导意见，
        咨询师总结吸收后成为技能记忆

        Args:
            state: 当前状态

        Returns:
            包含评估结果的状态
        """
        logger.info("--------------------------------_evaluate_therapist--------------------------------")
        # 学生昨完咨询后填写量表
        await self.current_student_agent.fill_scale("after_consultation", ["GHQ-20"], state)
        logger.info("学生已完成初始量表填写")

        supervisor_advice_for_current_therapist = await self.supervisor_agent.evaluate_therapist(state, self.current_therapist_agent.therapy_type)
        if self.ablation_str != "wo-memory":
            await self.current_therapist_agent.strengthen_skill(state, supervisor_advice_for_current_therapist, self.memory_manager)
        return state

    async def _create_student_medical_record(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成学生病历
        """
        logger.info("--------------------------------_create_student_medical_record--------------------------------")
        await self.supervisor_agent.create_student_medical_record(state, self.current_therapist_agent.therapy_type, self.memory_manager)
        return state

    # 保留_should_continue_therapists函数，但不需要单独的检查节点
    def _should_continue_therapists(self, state: Dict[str, Any]) -> bool:
        """判断是否还有未完成的咨询师

        Returns:
            True表示还有咨询师,False表示全部完成
        """
        logger.info("--------------------------------_should_continue_therapists--------------------------------")

        # 检查是否有下一个咨询师
        has_next = self.current_therapist_index < len(self.therapist_agents) - 1

        logger.info(f"是否有下一个咨询师? {has_next}")
        return has_next

    async def _switch_to_next_therapist(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """切换到下一个咨询师"""
        logger.info("--------------------------------_switch_to_next_therapist--------------------------------")
        self.current_therapist_index += 1
        self.current_therapist_agent = self.therapist_agents[self.current_therapist_index]
        state = copy.deepcopy(self.state_snapshots)
        return state

    # 删除无用的check_next_student函数，直接使用switch_to_next_student和条件判断

    def _has_next_student(self, state: Dict[str, Any]) -> bool:
        """检查是否还有未训练的学生

        直接读state里面的属性，然后返回是否有下一个学生的布尔值

        Returns:
            bool: 是否有下一个学生
            True表示有还有学生没有训练，要创建下一个学生，False表示没有，学生全部训练完成
        """
        logger.info("--------------------------------_has_next_student--------------------------------")
        return state["current_student_index"] < len(self.student_configs) - 1

    async def _switch_to_next_student(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        切换到下一个学生
        """
        logger.info("--------------------------------_switch_to_next_student--------------------------------")
        state["current_student_index"] += 1
        self.current_student_index = state["current_student_index"]
        return state

    async def _end_training(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理整个训练过程的结束

        感觉这个没啥要写的
        """
        logger.info("--------------------------------_end_training--------------------------------")
        return state

    async def run(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """运行训练流程"""
        try:
            if not self.compiled_graph:
                self.compile()
            return await self.compiled_graph.ainvoke(initial_state, config={"recursion_limit": 1000})
        except Exception as e:
            logger.error(f"Error running training: {str(e)}")
            raise ConsultationError("Training execution failed") from e