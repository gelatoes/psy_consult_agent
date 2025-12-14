# src/schemas/memory_schemas.py
from typing import TypedDict, Dict, List, Any, NotRequired, Literal
from .base_schemas import BaseMemory, Message

class DialogueMemory(BaseMemory):
    """对话记忆"""
    current_turn: int

class SharedWorkingMemory(BaseMemory):
    """侧写师和咨询师共享的工作记忆"""
    patient_info: Dict[str, Any]
    symptoms_tracking: Dict[str, Any]
    assessment_records: Dict[str, Any]
    tasks: List[Dict[str, Any]]

class SupervisorWorkingMemory(BaseMemory):
    """指导员工作记忆"""
    symptoms_status: Dict[str, List[str]]  # confirmed, pending, denied
    dialogue_progress: Dict[str, Any]
    quality_metrics: Dict[str, Any]

class SkillMemory(TypedDict):
    """技能记忆"""
    id: str
    content: str
    therapy_type: NotRequired[str]
    timestamp: float

class MedicalRecord(TypedDict):
    """电子病历"""
    record_id: str
    student_id: str
    basic_info: Dict[str, Any]
    symptoms: List[str]
    portrait: Dict[str, Any]
    plan: NotRequired[Dict[str, Any]]
    process: NotRequired[str]
    result: NotRequired[Dict[str, Any]]
    status: Literal["active", "archived"]
    created_at: float
    updated_at: float