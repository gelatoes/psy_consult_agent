# src/memory/json_schemas.py
"""
JSON记忆数据结构模式
定义各类记忆的标准结构
"""
from typing import TypedDict, Dict, List, Any, Optional, Literal, Union


# 侧写师技能记忆结构
class ProfilerSkillSchema(TypedDict):
    """侧写师技能记忆结构"""
    id: str  # 唯一标识
    content: str  # 技能内容
    timestamp: float  # 创建时间戳
    agent_type: Literal["profiler"]  # 智能体类型，固定为"profiler"
    source: Optional[str]  # 技能来源，如"training_session_001"
    tags: Optional[List[str]]  # 技能标签，如["emotion", "trauma"]


# 咨询师技能记忆结构
class TherapistSkillSchema(TypedDict):
    """咨询师技能记忆结构"""
    id: str  # 唯一标识
    content: str  # 技能内容
    timestamp: float  # 创建时间戳
    agent_type: Literal["therapist"]  # 智能体类型，固定为"therapist"
    therapy_type: str  # 疗法类型，如"cbt", "psychodynamic"
    source: Optional[str]  # 技能来源
    tags: Optional[List[str]]  # 技能标签
    difficulty_level: Optional[str]  # 技能难度，如"basic", "advanced"


# 学生医疗记录结构
class StudentMedicalRecordSchema(TypedDict):
    """学生医疗记录结构"""
    id: str  # 记录ID，例如"record_stu001_20240317_120000"
    student_id: str  # 学生ID，例如"stu001"
    created_at: float  # 创建时间戳
    updated_at: float  # 最后更新时间戳
    status: Literal["active", "archived"]  # 记录状态

    # 学生基本信息
    basic_info: Dict[str, Any]  # 包含姓名、年龄、性别等基本信息

    # 初始量表结果
    initial_scales: Dict[str, Dict[str, Any]]  # 量表名称 -> 结果

    # 心理画像
    psychological_portrait: Dict[str, Any]  # 侧写结果

    # 诊断和问题清单
    diagnoses: List[str]  # 诊断结果
    problems: List[str]  # 主要问题

    # 咨询计划
    treatment_plan: Optional[Dict[str, Any]]  # 咨询计划

    # 咨询过程记录
    sessions: List[Dict[str, Any]]  # 咨询会话记录

    # 最终量表结果
    final_scales: Optional[Dict[str, Dict[str, Any]]]  # 咨询后的量表结果

    # 咨询结果评估
    outcome: Optional[Dict[str, Any]]  # 咨询效果评估

    # 附加元数据
    metadata: Optional[Dict[str, Any]]  # 其他元数据


# JSON样例
profiler_skill_example = {
    "id": "profiler_skill_1710678921_123abc",
    "content": "在侧写过程中，应关注来访者谈论父母关系时的微表情和语气变化，这通常揭示了潜在的亲子关系问题。",
    "timestamp": 1710678921.123,
    "agent_type": "profiler",
    "source": "training_session_001",
    "tags": ["family_relationships", "microexpressions"]
}

therapist_skill_example = {
    "id": "therapist_skill_cbt_1710678921_456def",
    "content": "当来访者出现灾难化思维时，使用认知重构技术，引导其识别极端思维并寻找替代性解释。",
    "timestamp": 1710678921.456,
    "agent_type": "therapist",
    "therapy_type": "cbt",
    "source": "training_session_002",
    "tags": ["cognitive_restructuring", "catastrophizing"],
    "difficulty_level": "intermediate"
}

medical_record_example = {
    "id": "record_stu001_20240317_120000",
    "student_id": "stu001",
    "created_at": 1710678921.789,
    "updated_at": 1710678921.789,
    "status": "active",
    "basic_info": {
        "name": "李明",
        "age": 19,
        "gender": "男",
        "grade": "大一",
        "major": "计算机科学"
    },
    "initial_scales": {
        "PHQ-9": {
            "each_score": [2, 3, 2, 2, 1, 2, 1, 0, 0],
            "final_score": 13
        }
    },
    "psychological_portrait": {
        "main_issues": ["社交焦虑", "低自尊", "适应障碍"],
        "defense_mechanisms": ["回避", "理智化"],
        "cognitive_patterns": ["过度概括", "灾难化"],
        "emotional_state": {
            "anxiety_level": "高",
            "depression_level": "中等"
        },
        "childhood_trauma": "父母离异造成的分离焦虑",
        "relationship_patterns": ["对亲密关系恐惧", "难以建立深入关系"]
    },
    "diagnoses": ["社交焦虑障碍", "适应障碍"],
    "problems": ["大学环境适应困难", "社交回避", "学业压力"],
    "treatment_plan": {
        "approach": "认知行为疗法",
        "goals": ["降低社交焦虑", "提升自我效能感", "改善学习体验"],
        "estimated_duration": "8-10次会谈"
    },
    "sessions": [
        {
            "session_id": "stu001_session_001",
            "date": 1710679000.0,
            "therapist_id": "therapist_cbt_001",
            "focus_areas": ["建立关系", "问题评估"],
            "techniques_used": ["积极倾听", "开放式提问"],
            "progress_notes": "初次会谈，建立了良好的治疗关系...",
            "homework": "记录一周内的焦虑事件和相关想法"
        }
    ],
    "final_scales": {
        "PHQ-9": {
            "each_score": [1, 2, 1, 1, 1, 1, 0, 0, 0],
            "final_score": 7
        }
    },
    "outcome": {
        "improvement_areas": ["社交信心", "学业适应"],
        "remaining_issues": ["对新环境的适应能力还需继续提升"],
        "recommendations": ["继续练习社交技能", "定期复查"]
    },
    "metadata": {
        "referral_source": "自主来访",
        "priority_level": "常规"
    }
}