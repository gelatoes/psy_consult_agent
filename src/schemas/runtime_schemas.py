# src/schemas/runtime_schemas.py
from typing import TypedDict, Dict, List, Any, Literal


class RuntimeState(TypedDict, total=False):
    """运行时状态"""
    session_id: str                    # 会话ID
    mode: Literal["training", "consultation"]  # 运行模式
    shared_memory: Dict[str, Any]      # 侧写师、咨询师共享的工作记忆
    supervisor_working_memory: Dict[str, Any]      # 监督者的工作记忆
    dialogue_history: List[str]  # 对话历史
    psychological_portraits: Dict[str, Dict[str, Any]]  # 运行过程中的心理画像
    current_phase: str                # 当前阶段
    initial_scales_result: Dict[str, Any] # consultation前的量表填写结果
    scales_result_after_consultation: Dict[str, Any] # consultation后的量表填写结果
    current_student_index: int       # 当前学生索引
    current_student_basic_info: Dict[str, Any]
    current_profile_dialogue_index: int  # 当前学生的profile对话的轮次
    current_consultation_dialogue_index: int      # 当前学生和咨询师的对话轮次
    is_profile_complete: bool  # 是否完成profile
    is_consultation_complete: bool  # 是否完成consultation
    metadata: Dict[str, Any]  # 元数据

    # CBT相关运行时状态（新增字段，匹配 consultation_controller 的初始化）
    current_cbt_stage: str  # 当前CBT阶段，例如: "stage_1"
    cbt_stage_dialogues: Dict[str, int]  # 每个CBT阶段已进行的对话轮次数
    cbt_stage_completions: Dict[str, List[Any]]  # 每个CBT阶段的完成记录（可包含话题或回答等）
    topic_scores: Dict[str, Any]  # 话题得分记录表
    core_topic: str  # 核心话题
    _cbt_topics_initialized: bool  # 标志：CBT话题是否已初始化，防止重复初始化覆盖已有记忆
