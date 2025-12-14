# src/schemas/agent_schemas.py
from typing import Dict, List, Any, Optional
from .base_schemas import BaseProfile
from .consultation_schemas import PsychologicalPortrait


class TherapistProfile(BaseProfile):
    """咨询师档案"""
    name: str
    therapy_type: str # 治疗流派
    specialties: List[str] # 擅长领域
    style: str # 说话风格


class ProfilerProfile(BaseProfile):
    """侧写师档案"""
    name: str
    style: str # 说话风格


class StudentProfile(BaseProfile):
    """学生档案"""
    basicInfo: Dict[str, Any] # 学生的基本信息，姓名、性别、年龄等
    background: Dict[str, Any] # 学生的背景信息，如家庭情况、教育经历等
    life_events: List[Dict[str, Any]] # 学生的生活事件列表
    true_portrait: Optional[Dict[str, Any]]  # 训练模式下使用的真实心理画像