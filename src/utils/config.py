# src/utils/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """配置类"""
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    # 添加其他配置项