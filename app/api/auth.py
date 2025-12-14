# app/api/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from fastapi.security import OAuth2PasswordBearer
from app.models.schemas import UserCreate, UserUpdate, User, Token
from app.core.security import verify_password, create_access_token, decode_access_token
from app.data_access.repositories.user_repository import UserRepository

# --- 从 app.state 获取实例 ---
def get_user_repository(request: Request) -> UserRepository:
    return request.app.state.user_repository

# 创建一个OAuth2.0的密码承载流实例
# tokenUrl 指的是获取token的接口的相对路径
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    """
    依赖项：验证JWT并返回当前登录的用户对象。
    这是一个“守卫”，保护需要登录才能访问的接口。
    """
    token_data = decode_access_token(token)
    if not token_data or not (username := token_data.get("sub")):
        # 使用 walrus operator (:=) for python 3.8+
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await user_repo.get_by_username(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证", # 保持错误信息模糊以策安全
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 将数据库ORM对象转换为Pydantic模型User再返回
    return User.model_validate(user)


# --- API 路由 ---
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserCreate,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """用户注册"""
    if await user_repo.get_by_username(payload.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    if await user_repo.get_by_email(payload.email):
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    db_user = await user_repo.create(user_create=payload)
    return db_user

@router.post("/login", response_model=Token)
async def login_for_access_token(
    payload: dict = Body(..., example={"username": "testuser", "password": "password123"}),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """用户登录，获取JWT"""
    user = await user_repo.get_by_username(payload.get("username"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 从密码表中取 password_hash
    password_hash = await user_repo.get_hashed_password(user.id)
    if not verify_password(payload.get("password"), password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")

@router.post("/logout")
def logout():
    """用户登出 (客户端实现)"""
    return {"message": "成功登出。请在客户端清除令牌。"}

@router.get("/profile", response_model=User)
async def read_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user

@router.put("/profile", response_model=User)
async def update_current_user_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    # 从数据库中获取的是ORM对象，而不是Pydantic模型
    db_user = await user_repo.get_by_id(current_user.id)

    # 检查更新的邮箱是否已被其他用户使用
    if payload.email and (user_with_new_email := await user_repo.get_by_email(payload.email)):
        if user_with_new_email.id != current_user.id:
            raise HTTPException(status_code=400, detail="此邮箱已被其他用户注册")

    updated_user = await user_repo.update(db_obj=db_user, obj_in=payload)
    return updated_user