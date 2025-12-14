# src/schemas/phase_schemas.py
from typing import TypedDict, Dict, List, Any, Literal

class PhaseState(TypedDict):
    """阶段状态基类"""
    current_phase: str              # 当前阶段
    previous_phase: str            # 上一阶段
    next_phases: List[str]         # 可转换的下一阶段
    metadata: Dict[str, Any]      # 阶段相关元数据

class TrainingPhase(PhaseState):
    """训练模式的阶段状态"""
    mode: Literal["training"]      # 标识是训练模式
    training_phase: Literal[
        "initial",                # 初始化阶段
        "scale_assessment",       # 量表测评阶段
        "profiler_assessment",    # 侧写师评估阶段
        "therapist_selection",    # 咨询师选择阶段
        "consultation",           # 咨询阶段
        "evaluation",            # 评估阶段
        "completed"              # 完成阶段
    ]

class ConsultationPhase(PhaseState):
    """咨询模式的阶段状态"""
    mode: Literal["consultation"]  # 标识是咨询模式
    status: Literal[
        "initial",               # 初始化阶段
        "assessment",            # 评估阶段
        "therapist_selection",   # 咨询师选择阶段
        "consultation",          # 咨询阶段
        "completed"             # 完成阶段
    ]

class PhaseTransitionRules(TypedDict):
    """阶段转换规则定义"""
    allowed_transitions: Dict[str, List[str]]  # 从某阶段可以转到哪些阶段
    conditions: Dict[str, Dict[str, Any]]     # 转换的条件
    validators: Dict[str, List[str]]          # 转换的验证器
