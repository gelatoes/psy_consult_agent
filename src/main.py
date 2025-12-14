# src/main.py
import os
from typing import List, Dict, Any
import asyncio
from src.system import System
from src.utils.logger import logger
from src.utils.exceptions import ConsultationError
from src.memory.system_initializer import MemorySystemInitializer
import json
import argparse
import sys


def parse_args():
    """命令行参数解析"""
    parser = argparse.ArgumentParser(description="心理咨询系统")
    parser.add_argument('--ablation', type=str, required=True, help='ablation parameters, e.g., "none" for no ablation,  "wo-profiler" for without profiler, "wo-memory" for without memory')
    return parser.parse_args()

async def load_student_configs() -> List[Dict[str, Any]]:
    """加载学生配置数据

    从src目录下的students_config.json文件加载所有训练用学生的配置数据

    Returns:
        List[Dict[str, Any]]: 学生配置列表,每个配置包含:
        - basic_info: 基本信息(姓名、年龄等)
        - life_memory: 背景信息(家庭、学习等)
        - psychological_portrait: 真实心理画像
        - personality: 性格特点
    """
    try:
        # 确定配置文件路径
        # config_file = os.path.join(os.path.dirname(__file__), "students_config_0718.json")
        config_file = os.path.join(os.path.dirname(__file__), "test.json")
        

        # 检查文件是否存在
        if not os.path.exists(config_file):
            logger.warning(f"未找到学生配置文件: {config_file}")
            return _create_default_configs()

        # 从文件加载学生配置
        with open(config_file, 'r', encoding='utf-8') as f:
            student_configs = json.load(f)

        logger.info(f"成功加载了 {len(student_configs)} 个学生配置")
        return student_configs

    except Exception as e:
        logger.error(f"加载学生配置失败: {str(e)}")
        # 如果出错，返回一个基础配置
        return _create_default_configs()


async def load_therapist_configs() -> Dict[str, Any]:
    """加载心理咨询师配置数据

    从src目录下的therapists_config.json文件加载所有咨询师的配置数据

    Returns:
        Dict[str, Any]: 咨询师配置，包含所有流派信息
    """
    try:
        # 确定配置文件路径
        config_file = os.path.join(os.path.dirname(__file__), "therapists_config.json")

        # 检查文件是否存在
        if not os.path.exists(config_file):
            logger.warning(f"未找到咨询师配置文件: {config_file}")
            return {"therapists": []}

        # 从文件加载咨询师配置
        with open(config_file, 'r', encoding='utf-8') as f:
            therapist_configs = json.load(f)

        therapist_count = len(therapist_configs.get("therapists", []))
        logger.info(f"成功加载了 {therapist_count} 个心理咨询师配置")
        return therapist_configs

    except Exception as e:
        logger.error(f"加载咨询师配置失败: {str(e)}")
        return {"therapists": []}


def _create_default_configs() -> List[Dict[str, Any]]:
    """创建默认学生配置（当配置文件不存在或读取失败时使用）"""
    logger.info("使用默认学生配置")
    return [
        {
            "basic_info": {
                "id": "stu001",
                "name": "李明",
                "age": 19,
                "gender": "男",
                "grade": "大一",
                "major": "计算机科学"
            },
            "life_memory": [
                {
                    "age": 18,
                    "event": "进入大学后难以适应新环境",
                    "emotion": "焦虑、孤独",
                    "impact": "逐渐封闭自己，很少与人交流"
                }
            ],
            "psychological_portrait": {
                "main_issues": ["社交焦虑", "适应障碍"],
                "emotional_state": {
                    "anxiety_level": "高",
                    "depression_level": "中等"
                }
            },
            "personality": {
                "introversion": "高",
                "sensitivity": "高"
            }
        }
    ]


async def create_app(mode: str = "consultation", ablation_str = 'none') -> System:
    try:
        # 首先初始化记忆系统
        logger.info("初始化记忆系统...")
        memory_manager = await MemorySystemInitializer.initialize_memory_system()
        logger.info("记忆系统初始化完成")

        # 加载学生配置(训练模式需要)
        student_configs = await load_student_configs() if mode == "training" else None

        # 创建系统实例
        system = System(
            ablation_str=ablation_str,  # 新增传参
            mode=mode,
            student_configs=student_configs,
            memory_manager=memory_manager
        )

        await system.initialize()
        return system

    except Exception as e:
        logger.error(f"创建应用程序时出错: {str(e)}")
        raise ConsultationError("Failed to create application") from e


async def main():
    """应用程序主入口"""
    try:
        args = parse_args()
        ablation_str = args.ablation


        # 设置 OpenAI API 密钥
        os.environ["OPENAI_API_KEY"] = "sk-TE14HRIUzbuh4m9E562e1b832a2f46E4B3B408992a281e55"
        # 设置 硅基流动 API 密钥
        os.environ["SILICONFLOW_API_KEY"] = "sk-gtaoixzcmchnxigbqqchabjfoofkbndawrfnbkxyedktqqsc"
        # 设置较长的HTTP超时时间（秒）
        os.environ["HTTPX_TIMEOUT"] = "10"
        # 此时导入 logger.py，logger 会读取环境变量
        logger.info(f"ablation 参数为: {ablation_str}")
        # 创建应用（默认咨询模式）
        # 修改模式
        app = await create_app(mode="consultation", ablation_str=ablation_str)
        # app = await create_app(mode="training", ablation_str=ablation_str)
        
        # 运行系统
        result = await app.run()

        # 清理资源
        await app.cleanup()

        return result

    except Exception as e:
        logger.error(f"应用程序错误: {str(e)}")
        raise



if __name__ == "__main__":
    asyncio.run(main())