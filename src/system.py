# src/system.py
"""
系统主类，协调所有组件的工作
"""
from typing import List, Optional, Dict, Any, Literal

# from schemas import RuntimeState
from src.schemas.runtime_schemas import RuntimeState
from src.memory.memory_manager import MemoryManager
from src.agents import (
    ProfilerAgent, TherapistAgent,
    SupervisorAgent
)
from src.agents.therapist_factory import TherapistFactory
from src.controllers import (
    TrainingController, ConsultationController
)
from src.utils.logger import logger
from src.utils.exceptions import ConsultationError
import copy
import sys


class System:
    """系统主类，协调所有组件工作"""

    def __init__(
            self,
            mode: str = "training",
            ablation_str: str = "none",
            student_configs: Optional[List[Dict[str, Any]]] = None,  # 添加学生配置参数
            memory_manager: Optional[MemoryManager] = None  # 新参数，允许传入已初始化的记忆管理器
    ):
        self.mode = mode
        self.student_configs = student_configs
        self.ablation_str = ablation_str  

        # 控制器
        self.training_controller: Optional[TrainingController] = None
        self.consultation_controller: Optional[ConsultationController] = None

        # Agents
        self.profiler_agent: Optional[ProfilerAgent] = None
        self.supervisor_agent: Optional[SupervisorAgent] = None
        self.therapist_agents: List[TherapistAgent] = []

        # 使用传入的记忆管理器或创建新的
        self.memory_manager = memory_manager if memory_manager else MemoryManager()

        # 咨询师工厂
        self.therapist_factory = TherapistFactory(memory_manager=self.memory_manager)

    async def initialize(self):
        """初始化系统"""
        try:
            # 如果没有提供记忆管理器，则初始化默认的
            if not hasattr(self.memory_manager, '_collection_mapping'):
                logger.info("初始化默认记忆管理器")
                await self.memory_manager.initialize_memories()
            else:
                logger.info("使用已初始化的记忆管理器")

            # 创建共享的LLM服务
            from src.utils.llm_service import create_llm_service
            llm_service = create_llm_service(
                service_type="siliconflow",
                model_name="Tongyi-Zhiwen/QwenLong-L1-32B",
                default_temperature=0.5,
                api_base="https://api.siliconflow.cn/v1"
            )

            # 创建指导员Agent
            self.supervisor_agent = SupervisorAgent(llm_service=llm_service)

            # 创建侧写师Agent
            self.profiler_agent = ProfilerAgent(llm_service=llm_service)

            # 加载咨询师配置
            self.therapist_factory = TherapistFactory(
                memory_manager=self.memory_manager,
                llm_service=llm_service
            )

            # 确保所有咨询师的记忆集合存在
            await self.therapist_factory.ensure_therapist_memories()

            # 创建心理咨询师团队（从配置动态创建）
            self.therapist_agents = self.therapist_factory.create_all_therapists()

            if not self.therapist_agents:
                logger.warning("没有从配置创建到任何咨询师，将使用默认咨询师")
                # 如果没有成功创建咨询师，使用默认配置
                self.therapist_agents = [
                    TherapistAgent(therapy_type="cbt", llm_service=llm_service),
                    TherapistAgent(therapy_type="psychodynamic", llm_service=llm_service)
                ]

            logger.info(f"成功创建了 {len(self.therapist_agents)} 个咨询师")

            # 根据模式初始化特定组件
            if self.mode == "training":
                await self._initialize_training_mode()
            else:
                await self._initialize_consultation_mode()

            logger.info(f"系统已在{self.mode}模式下初始化完成")

        except Exception as e:
            logger.error(f"初始化系统时出错: {str(e)}")
            raise ConsultationError("System initialization failed") from e

    async def _initialize_training_mode(self):
        """初始化训练模式特定组件

        主要工作:
        2. 创建训练控制器并传入学生配置
        3. 编译训练流程图
        """
        try:

            # 创建训练控制器(不再创建学生Agent,改为传入配置)
            self.training_controller = TrainingController(
                student_configs=self.student_configs,  # 传入配置列表
                profiler_agent=self.profiler_agent,
                therapist_agents=self.therapist_agents,
                supervisor_agent=self.supervisor_agent,
                memory_manager=self.memory_manager,
                ablation_str=self.ablation_str  # 新增传参
            )

            # 编译训练流程图
            self.training_controller.compile()

            logger.info("训练模式初始化完成")

        except Exception as e:
            logger.error(f"初始化训练模式时出错: {str(e)}")
            raise ConsultationError("Training mode initialization failed") from e

    async def _initialize_consultation_mode(self):
        """初始化咨询模式特定组件"""
        try:
            # 创建咨询控制器
            self.consultation_controller = ConsultationController(
                profiler_agent=self.profiler_agent,
                therapist_agents=self.therapist_agents,
                supervisor_agent=self.supervisor_agent,
                memory_manager=self.memory_manager,
                ablation_str=self.ablation_str  # 新增传参
            )

            # 编译咨询流程图
            self.consultation_controller.compile()

            logger.info("咨询模式初始化完成")

        except Exception as e:
            logger.error(f"初始化咨询模式时出错: {str(e)}")
            raise ConsultationError("Consultation mode initialization failed") from e

    def _create_initial_state(self) -> Dict[str, Any]:
        """创建初始状态"""
        try:
            mode: Literal["training", "consultation"] = "training" if self.mode == "training" else "consultation"

            initial_state: RuntimeState = {
                "session_id": "111",
                "mode": mode,
                "shared_memory": {},
                "supervisor_working_memory": {},
                "dialogue_history": [],
                "psychological_portraits": {},
                "current_phase": "initial",
                "initial_scales_result": {},
                "scales_result_after_consultation": {},  # consultation后的量表填写结果
                "current_student_index": 0,  # 当前学生索引
                "current_student_basic_info": {},  # 当前学生的基本信息
                "current_profile_dialogue_index": 0,  # 当前学生的profile对话的轮次
                "current_consultation_dialogue_index": 0,  # 当前学生和咨询师的对话轮次
                "is_profile_complete": False,  # 是否完成profile
                "is_consultation_complete": False,  # 是否完成consultation
                "metadata": {}
            }
            return initial_state

        except Exception as e:
            logger.error(f"创建初始状态时出错: {str(e)}")
            raise ConsultationError("Initial state creation failed") from e

    async def run(self) -> Dict[str, Any]:
        """系统主运行逻辑"""
        try:
            # 初始化全局状态
            initial_state = self._create_initial_state()

            # 根据模式运行相应控制器
            if self.mode == "training":
                logger.info("开始训练模式...")
                if self.training_controller:
                    final_state = await self.training_controller.run(initial_state)
                    logger.info("训练成功完成")
                else:
                    raise ConsultationError("训练控制器未初始化")
            else:
                logger.info("开始咨询模式...")
                if self.consultation_controller:
                    final_state = await self.consultation_controller.run(initial_state)
                    logger.info("咨询成功完成")
                else:
                    raise ConsultationError("咨询控制器未初始化")

            return final_state

        except Exception as e:
            logger.error(f"系统执行错误: {str(e)}")
            raise ConsultationError("System execution failed") from e

    async def cleanup(self):
        """清理系统资源"""
        try:
            # 注意：在 ChromaDB 0.6.3 中，数据会自动持久化，此调用仅为兼容性保留
            await self.memory_manager.persist_memories()
            logger.info("记忆系统已配置为自动持久化")

            # 然后清理记忆系统
            await self.memory_manager.cleanup()

            # 记录系统运行完成
            logger.info("系统资源清理完成")

        except Exception as e:
            logger.error(f"系统清理时出错: {str(e)}")
            raise ConsultationError("System cleanup failed") from e