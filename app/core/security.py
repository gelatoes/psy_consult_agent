# app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings  # 从我们自己的配置模块导入

# 1. --- 密码哈希 ---
# 创建一个CryptContext实例，指定使用bcrypt算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码是否与哈希后的密码匹配。

    Args:
        plain_password: 用户输入的明文密码。
        hashed_password: 数据库中存储的哈希密码。

    Returns:
        如果匹配则返回 True，否则返回 False。
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    将明文密码进行哈希处理。

    Args:
        password: 要哈希的明文密码。

    Returns:
        哈希后的密码字符串。
    """
    # 将密码字符串编码为字节，以便准确计算长度
    password_bytes = password.encode('utf-8')

    # bcrypt 算法只处理前 72 个字节
    if len(password_bytes) > 72:
        # 如果密码过长，截取前 72 个字节
        password_bytes = password_bytes[:72]
    
    # 将可能被截断的字节解码回字符串，以便 passlib 处理
    # 使用 'ignore' 参数以防截断时破坏多字节字符
    processed_password = password_bytes.decode('utf-8', 'ignore')

    return pwd_context.hash(processed_password)



# 2. --- JWT 令牌处理 ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建一个新的访问令牌 (JWT)。

    Args:
        data: 要编码到令牌中的数据 (payload)，通常包含用户标识。
        expires_delta: 令牌的过期时间增量。如果为None，则使用配置中的默认值。

    Returns:
        编码后的JWT字符串。
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """
    解码并验证一个访问令牌。

    Args:
        token: JWT字符串。

    Returns:
        如果令牌有效且未过期，则返回解码后的payload字典。
        否则返回None。
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        # 如果解码失败（例如，签名不匹配、令牌过期等），返回None
        return None