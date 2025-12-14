# src/schemas/base_schemas.py
from typing import TypedDict, Dict, List, Any, Optional, Literal, NotRequired


class Message(TypedDict):
    """消息基础结构"""
    role: str
    content: str
    timestamp: float
    metadata: Dict[str, Any]

class BaseState(TypedDict):
    """基础状态类型"""
    session_id: str
    current_phase: str
    timestamp: float
    mode: Literal["training", "consultation"]
    metadata: Dict[str, Any]

class BaseMemory(TypedDict):
    """基础记忆类型"""
    messages: List[Message]
    notes: Dict[str, Any]
    metadata: Dict[str, Any]

class BaseProfile(TypedDict):
    """Agent身份与特征定义"""
    agent_id: str                # Agent唯一标识符
    agent_type: str              # Agent类型(profiler/therapist/student/supervisor)
    metadata: Dict[str, Any]     # 其他元数据信息