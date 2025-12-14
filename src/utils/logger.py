# src/utils/logger.py
import logging
import os
import datetime
from pathlib import Path
import sys

def setup_logger() -> logging.Logger:
    """设置日志"""

    # sys.exit(0)
    logs_dir = Path(__file__).parents[2] / "runtime-logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # 创建带时间戳的日志文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"log_{timestamp}.txt"
    
    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 清除可能存在的处理程序，防止重复
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # 创建控制台处理程序
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # 创建文件处理程序
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # 添加处理程序到日志记录器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# # 读取环境变量
# ablation_str = os.environ.get('ABLATION_STR', 'none')
# print(ablation_str)
logger = setup_logger()
# logger = None