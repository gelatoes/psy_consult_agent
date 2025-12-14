from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from app.models.schemas import ConsultationMessage, ConsultationResponse, ConsultationSurvey, StartSessionPayload, SessionMeta, User
from app.business_logic.controllers.consultation_controller import ConsultationController
from app.data_access.repositories.session_repository import SessionRepository
from app.api.auth import get_current_user

import json

with open('data/user.json', 'r', encoding='utf-8') as f:
    user_survey_dict = json.load(f)

router = APIRouter(prefix="/consultation", tags=["Consultation V2"])

def get_consultation_controller(request: Request) -> ConsultationController:
    return request.app.state.consultation_controller

def get_session_repository(request: Request) -> SessionRepository:
    return request.app.state.session_repository

@router.post("/start", response_model=ConsultationResponse)
async def start_session(
    payload: StartSessionPayload,
    current_user: User = Depends(get_current_user),
    controller: ConsultationController = Depends(get_consultation_controller),
    session_repo: SessionRepository = Depends(get_session_repository),
):
    if payload.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="禁止访问他人会话")

    session_id = await session_repo.create(
        user_id=current_user.id,
        initial_state={}
    )
    initial_state = await controller.start_new_session(session_id)

    initial_survey = {}
    for item in user_survey_dict:
        if item.get("年级") == current_user.grade and item.get("性别") == current_user.gender and item.get("学校") == current_user.university and item.get("专业") == current_user.major:
            initial_survey = item
            break
    initial_state["initial_scales_result"] = initial_survey
    initial_state["current_student_basic_info"] = current_user
    await session_repo.update(session_id, initial_state)
    return ConsultationResponse(session_id=session_id, agent_output=initial_state["dialogue_history"][-1][0], is_complete=False)

@router.post("/{session_id}/survey", response_model=ConsultationResponse)
async def send_survey(
    session_id: str,
    payload: ConsultationSurvey,
    current_user: User = Depends(get_current_user),
    controller: ConsultationController = Depends(get_consultation_controller),
    session_repo: SessionRepository = Depends(get_session_repository),
):
    session = await session_repo.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="禁止访问他人会话")
    if session['state'].get("is_complete", False):
        return ConsultationResponse(session_id=session_id, agent_output="本次会话已结束", is_complete=True)

    if not session['state'].get("wait_for_user_input", False):
        raise HTTPException(status_code=400, detail="当前不需要用户输入")
    
    updated_state = await controller.process_user_survey(session_id, session['state'], payload.user_survey)
    await session_repo.update(session_id, updated_state)

    return ConsultationResponse(
        session_id=session_id,
        agent_output=updated_state["dialogue_history"][-1][0],
        is_complete=updated_state.get("is_complete", False)
    )

@router.post("/{session_id}/message", response_model=ConsultationResponse)
async def send_message(
    session_id: str,
    payload: ConsultationMessage,
    current_user: User = Depends(get_current_user),
    controller: ConsultationController = Depends(get_consultation_controller),
    session_repo: SessionRepository = Depends(get_session_repository),
):
    session = await session_repo.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="禁止访问他人会话")
    if session['state'].get("is_complete", False):
        return ConsultationResponse(session_id=session_id, agent_output="本次会话已结束", is_complete=True)

    if not session['state'].get("wait_for_user_input", False):
        raise HTTPException(status_code=400, detail="当前不需要用户输入")
    
    updated_state = await controller.process_user_message(session_id, session['state'], payload.user_input)
    await session_repo.update(session_id, updated_state)

    return ConsultationResponse(
        session_id=session_id,
        agent_output=updated_state["dialogue_history"][-1][0],
        is_complete=updated_state.get("is_complete", False)
    )

@router.get("/{session_id}") # 暂时移除 response_model 以便直接返回字典
async def get_session_detail(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_repo: SessionRepository = Depends(get_session_repository),
) -> Dict[str, Any]: # 明确函数返回一个字典
    """
    获取单个会话的完整状态，用于前端聊天页面渲染。
    """
    session_data = await session_repo.get(session_id)
    
    if not session_data:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 你的 session_repo.get 返回的是字典，所以可以直接用 key 访问
    if session_data.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="禁止访问他人会话")
    
    # *** 关键修复 ***
    # 不再尝试用 SessionMeta() 包装，而是直接返回从 repo 获取的完整会话字典
    # 这个字典里应该包含了前端渲染需要的所有数据，特别是 'state' 和 'dialogue_history'
    return session_data

@router.get("/{user_id}/history", response_model=List[SessionMeta])
async def get_user_session_history(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session_repo: SessionRepository = Depends(get_session_repository),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="禁止访问他人历史会话")
    sessions = await session_repo.get_for_user(user_id)
    return [SessionMeta(**s) for s in sessions]
