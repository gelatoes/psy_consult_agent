# app/data_access/repositories/user_repository.py

import json
import os
import datetime
from typing import Optional, Dict, Any

from app.models.schemas import User, UserCreate, UserUpdate
from app.core.security import get_password_hash

# --- 数据持久化设置 ---
DATA_DIR = r"D:\ruc\Code\Codefield\Code_Python\aaai\psy-app\data\user_data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
PASSWORDS_FILE = os.path.join(DATA_DIR, "passwords.json")

# 确保数据目录存在
import json
import os
import datetime
from typing import Optional, Dict, Any
import aiofiles

from app.models.schemas import User, UserCreate, UserUpdate
from app.core.security import get_password_hash

# --- data dir (keep existing path if running on windows dev machine, but prefer relative for deployment)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '..', '..', 'data', 'user_data')
DATA_DIR = os.path.normpath(DATA_DIR)
USERS_FILE = os.path.join(DATA_DIR, "users.json")
PASSWORDS_FILE = os.path.join(DATA_DIR, "passwords.json")

# ensure data dir exists
os.makedirs(DATA_DIR, exist_ok=True)

# --- in-memory structures (initialized during async initialize) ---
_users_db: Dict[int, User] = {}
_passwords_db: Dict[int, str] = {}
_next_user_id = 1


def _default_json_serializer(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"type {type(obj)} is not JSON serializable")


async def _save_data():
    serializable_users = {uid: user.model_dump() for uid, user in _users_db.items()}
    async with aiofiles.open(USERS_FILE, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(serializable_users, indent=4, ensure_ascii=False, default=_default_json_serializer))

    async with aiofiles.open(PASSWORDS_FILE, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(_passwords_db, indent=4, ensure_ascii=False, default=_default_json_serializer))


async def _load_data():
    global _users_db, _passwords_db, _next_user_id
    # load users
    try:
        async with aiofiles.open(USERS_FILE, 'r', encoding='utf-8') as f:
            content = await f.read()
            if content.strip():
                loaded_users_raw = json.loads(content)
                _users_db = {int(uid): User.model_validate(data) for uid, data in loaded_users_raw.items()}
            else:
                _users_db = {}
    except (FileNotFoundError, json.JSONDecodeError):
        _users_db = {}

    # load passwords
    try:
        async with aiofiles.open(PASSWORDS_FILE, 'r', encoding='utf-8') as f:
            content = await f.read()
            if content.strip():
                _passwords_db = {int(k): v for k, v in json.loads(content).items()}
            else:
                _passwords_db = {}
    except (FileNotFoundError, json.JSONDecodeError):
        _passwords_db = {}

    if _users_db:
        _next_user_id = max(_users_db.keys()) + 1


class UserRepository:
    """Async user repository (file-backed). Call `await UserRepository.create()` to get an initialized instance."""
    def __init__(self):
        pass

    @classmethod
    async def create_repo(cls) -> "UserRepository":
        # async factory to load data then return repository instance
        await _load_data()
        return cls()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        return _users_db.get(user_id)

    async def get_by_username(self, username: str) -> Optional[User]:
        for user in _users_db.values():
            if user.username == username:
                return user
        return None

    async def get_by_email(self, email: str) -> Optional[User]:
        for user in _users_db.values():
            if user.email == email:
                return user
        return None

    async def get_hashed_password(self, user_id: int) -> Optional[str]:
        return _passwords_db.get(user_id)

    async def create(self, user_create: UserCreate) -> User:
        global _next_user_id
        now = datetime.datetime.now(datetime.timezone.utc)
        new_user = User(
            id=_next_user_id,
            username=user_create.username,
            email=user_create.email,
            created_at=now,
            updated_at=now,
            grade=user_create.grade,
            gender=user_create.gender,
            university=user_create.university,
            major=user_create.major,
        )

        _users_db[_next_user_id] = new_user
        _passwords_db[_next_user_id] = get_password_hash(user_create.password)
        _next_user_id += 1
        await _save_data()
        return new_user

    async def update(self, *, db_obj: User, obj_in: UserUpdate) -> User:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "password":
                _passwords_db[db_obj.id] = get_password_hash(value)
            else:
                setattr(db_obj, field, value)

        db_obj.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await _save_data()
        return db_obj