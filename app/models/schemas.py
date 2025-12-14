# app/models/schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import datetime

# ===================================================================
# 1. 用户认证 (Authentication) 相关的模型
# ===================================================================

class UserBase(BaseModel):
    """用户的基本信息模型，用于继承。"""
    username: str = Field(..., example="testuser", description="用户名")
    email: str = Field(..., example="test@example.com", description="用户邮箱")
    grade: str
    gender: str
    university: str
    major: str
    """name: str
    only_child: str
    academic_performance: str
    parents_residence: str
    mother_education: str
    monthly_allowance: int
    self_rated_health: str
    academic_involution_level: int
    perceived_academic_involution: int
    psychological_resilience: int"""

class UserCreate(UserBase):
    """创建用户时使用的模型，包含了密码。"""
    password: str = Field(..., example="strongpassword123", description="用户密码")

class UserUpdate(BaseModel):
    """更新用户信息时使用的模型，所有字段都是可选的。"""
    email: Optional[str] = Field(None, example="new_email@example.com", description="新的邮箱地址")
    password: Optional[str] = Field(None, example="new_strong_password", description="新的密码")

class User(UserBase):
    """从API返回用户信息时使用的模型，不包含密码。"""
    id: int = Field(..., description="用户唯一ID")
    created_at: datetime.datetime = Field(..., description="账户创建时间")
    updated_at: Optional[datetime.datetime] = Field(None, description="账户最后更新时间") # 数据库会自动更新，所以可以为None

    class Config:
        from_attributes = True

class Token(BaseModel):
    """用户登录成功后返回的JWT令牌模型。"""
    access_token: str = Field(..., description="JWT访问令牌")
    token_type: str = Field(..., example="bearer", description="令牌类型")

# ===================================================================
# 2. 复杂咨询流程 (V2) 相关的模型
# ===================================================================

class SessionMeta(BaseModel):
    session_id: str
    user_id: int
    session_status: str
    pre_survey_data: Optional[Dict] = None
    post_survey_data: Optional[Dict] = None
    psychological_profile: Optional[str] = None
    selected_therapist_type: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

class StartSessionPayload(BaseModel):
    user_id: int

class ConsultationResponse(BaseModel):
    session_id: str
    agent_output: str
    is_complete: bool

class ConsultationSurvey(BaseModel):
    user_survey: str

class ConsultationMessage(BaseModel):
    user_input: str = Field(..., description="用户的消息内容")

# ===================================================================
# 3. 问卷 (Survey) 相关的模型
# ===================================================================

class SurveySubmission(BaseModel):
    """用户提交问卷时的数据模型。"""
    session_id: str = Field(..., description="问卷所属的会话ID")
    answers: Dict[str, Any] = Field(..., example={"question1": "A", "question2": 4}, description="问卷的答案")

class SurveyResponse(BaseModel):
    """提交问卷后的成功响应模型。"""
    message: str = Field("Survey submitted successfully", description="操作结果信息")
    survey_type: str = Field(..., example="pre_survey_data", description="被记录的问卷类型（前测或后测）")