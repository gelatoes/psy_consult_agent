# src/utils/prompt_loader.py
import os
import json
import pprint

import yaml
from typing import Dict, Any
from src.utils.logger import logger


class PromptLoader:
    """提示词加载器，用于从配置文件加载提示词模板"""

    @staticmethod
    def load_prompts(agent_type: str) -> Dict[str, str]:
        """从配置文件加载特定智能体的提示词"""
        try:
            # 构建配置文件路径
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "prompts", f"{agent_type}_prompts.yaml")

            # 检查文件是否存在
            if not os.path.exists(config_path):
                logger.warning(f"找不到提示词配置文件: {config_path}")
                return {}

            # 从YAML文件加载提示词
            with open(config_path, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f)

            logger.info(f"成功加载了 {agent_type} 智能体的 {len(prompts)} 个提示词模板")
            return prompts

        except Exception as e:
            logger.error(f"加载提示词配置失败: {str(e)}")
            return {}

    @staticmethod
    def format_prompt(template: str, **kwargs) -> str:
        """格式化提示词模板"""
        # Protect against None templates to avoid AttributeError in callers
        if template is None:
            logger.error("尝试格式化空的提示词模板 (None)。请检查对应的 prompts.yaml 是否包含该键名。")
            return ""
        # 将所有字典类型的参数转换为JSON字符串
        formatted_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, dict) or isinstance(value, list):
                formatted_kwargs[key] = json.dumps(value, ensure_ascii=False, indent=2)
            else:
                formatted_kwargs[key] = value

        # 先处理双花括号，将JSON示例中的双花括号替换为临时标记
        template = template.replace("{{", "DOUBLE_LEFT_BRACE")
        template = template.replace("}}", "DOUBLE_RIGHT_BRACE")

        # 格式化模板
        try:
            formatted_template = template.format(**formatted_kwargs)

            # 还原双花括号
            formatted_template = formatted_template.replace("DOUBLE_LEFT_BRACE", "{")
            formatted_template = formatted_template.replace("DOUBLE_RIGHT_BRACE", "}")

            return formatted_template
        except KeyError as e:
            logger.error(f"格式化提示词时缺少参数: {e}")
            # 返回原始模板，避免程序崩溃
            return template