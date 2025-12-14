# src/schemas/consultation_schemas.py
from typing import TypedDict, Dict, Any, List


class PsychologicalPortrait(TypedDict, total=False):
    """心理画像"""
    main_issues: List[str]                      # 主要的症状
    defense_mechanisms: List[str]               # 防御机制
    cognitive_patterns: List[str]               # 认知模式
    emotional_state: Dict[str, Any]             # 情感状态，格式为Dict[str, Any]，可以包含anxiety_level、depression_level、anger_level等等
    childhood_trauma: List[str]                 # 孩童时期的创伤
    relationship_patterns: List[str]            # 关系模式