# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """
    应用配置模型。
    使用 Pydantic-Settings 自动从环境变量或 .env 文件中读取配置。
    """
    APP_NAME: str = "Psy-Consult"
    DEBUG_MODE: bool = False

    # --- 硅基流动 API 配置 ---
    SILICON_FLOW_API_KEY: str
    SILICON_FLOW_API_BASE: str

    # --- 其他 API 配置 ---
    API_KEY: str
    API_BASE: str

    # --- JWT 安全配置 ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Pydantic-Settings的配置类
    model_config = SettingsConfigDict(
        env_file=".env",            # 指定要读取的.env文件
        env_file_encoding='utf-8'   # 指定文件编码
    )

@lru_cache
def get_settings() -> Settings:
    """
    获取配置实例的函数。
    使用lru_cache装饰器可以确保Settings类只被实例化一次（单例模式），
    避免了每次请求都重新读取.env文件的开销。
    """
    print("Loading application settings...")
    return Settings()

# 创建一个全局可用的配置实例，方便在应用各处导入和使用
settings = get_settings()