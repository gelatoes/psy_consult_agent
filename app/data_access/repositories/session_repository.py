# app/data_access/repositories/session_repository.py

import uuid
import json
import uuid
import json
import os
from typing import Dict, Any, Optional, List
import datetime
from pydantic import BaseModel
import aiofiles

# data dir
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '..', '..', 'data', 'user_data')
DATA_DIR = os.path.normpath(DATA_DIR)
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")
USER_INDEX_FILE = os.path.join(DATA_DIR, "user_sessions_index.json")

os.makedirs(DATA_DIR, exist_ok=True)

# in-memory stores
_sessions_table: Dict[str, Dict[str, Any]] = {}
_user_sessions_index: Dict[int, List[str]] = {}


def _default_json_serializer(obj):
    from datetime import date
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"type {type(obj)} is not JSON serializable")


async def _save_data():
    async with aiofiles.open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(_sessions_table, indent=4, default=_default_json_serializer, ensure_ascii=False))

    async with aiofiles.open(USER_INDEX_FILE, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(_user_sessions_index, indent=4))


async def _load_data():
    global _sessions_table, _user_sessions_index
    try:
        async with aiofiles.open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
            content = await f.read()
            if content.strip():
                loaded_sessions = json.loads(content)
                for session_id, session_data in loaded_sessions.items():
                    if session_data.get('created_at'):
                        try:
                            session_data['created_at'] = datetime.datetime.fromisoformat(session_data['created_at'])
                        except Exception:
                            pass
                    if session_data.get('updated_at'):
                        try:
                            session_data['updated_at'] = datetime.datetime.fromisoformat(session_data['updated_at'])
                        except Exception:
                            pass
                _sessions_table = loaded_sessions
            else:
                _sessions_table = {}
    except (FileNotFoundError, json.JSONDecodeError):
        _sessions_table = {}

    try:
        async with aiofiles.open(USER_INDEX_FILE, 'r', encoding='utf-8') as f:
            content = await f.read()
            if content.strip():
                _user_sessions_index = {int(k): v for k, v in json.loads(content).items()}
            else:
                _user_sessions_index = {}
    except (FileNotFoundError, json.JSONDecodeError):
        _user_sessions_index = {}


class SessionRepository:
    def __init__(self):
        pass

    @classmethod
    async def create_repo(cls) -> "SessionRepository":
        # async factory to load data then return repository instance
        await _load_data()
        return cls()

    async def create(self, user_id: int, initial_state: Dict[str, Any]) -> str:
        session_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc)

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "session_status": initial_state.get("session_status", "initial"),
            "pre_survey_data": None,
            "post_survey_data": None,
            "psychological_profile": None,
            "selected_therapist_type": None,
            "created_at": now,
            "updated_at": now,
            "state": initial_state
        }

        _sessions_table[session_id] = session_data
        _user_sessions_index.setdefault(user_id, []).append(session_id)

        await _save_data()
        return session_id

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return _sessions_table.get(session_id)

    async def update(self, session_id: str, new_state: Dict[str, Any]):
        if session_id in _sessions_table:
            _sessions_table[session_id]['state'] = new_state
            _sessions_table[session_id]["session_status"] = new_state.get("current_phase")
            _sessions_table[session_id]["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
            await _save_data()

    async def get_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        session_ids = _user_sessions_index.get(user_id, [])
        return [_sessions_table[sid] for sid in session_ids if sid in _sessions_table]

    async def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        return _sessions_table[session_id]['state']["dialogue_history"]