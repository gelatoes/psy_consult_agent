# src/utils/llm_service.py
import os
import re
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from src.utils.logger import logger


class LLMService(ABC):
    """抽象LLM服务基类"""

    @abstractmethod
    async def invoke(self, prompt: str, temperature: Optional[float] = None) -> str:
        """向LLM发送请求并获取纯文本响应"""
        pass

    @abstractmethod
    async def invoke_json(self, prompt: str, temperature: Optional[float] = None,
                          default_value: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """向LLM发送请求并将响应解析为JSON"""
        pass


class OpenAIService(LLMService):
    """OpenAI LLM服务实现"""

    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo", default_temperature: float = 0.5,
                 api_base: Optional[str] = None):

        if api_base:
            base_url = api_base

        self.model = ChatOpenAI(
            model_name=model_name,
            temperature=default_temperature,
            api_key=api_key,
            base_url=base_url,
        )
        self.default_temperature = default_temperature

    async def invoke(self, prompt: str, temperature: Optional[float] = None) -> str:
        try:
            if temperature is not None:
                original_temp = self.model.temperature
                self.model.temperature = temperature

            response = self.model.invoke([HumanMessage(content=prompt)])

            if temperature is not None:
                self.model.temperature = original_temp

            return response.content
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            raise

    async def invoke_json(self, prompt: str, temperature: Optional[float] = None,
                          default_value: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            if not prompt.strip().endswith("JSON"):
                prompt += "\n\n请只返回JSON格式的内容，不要添加任何额外的解释或说明。"

            response_text = await self.invoke(prompt, temperature)

            json_match = re.search(r'({.*})', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)

                logger.info("-----------------------invoke_json的prompt是-----------------------")
                logger.info(prompt)
                logger.info("-----------------------invoke_json的response是-----------------------")
                logger.info(json_str)
                return json.loads(json_str)
            else:
                return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}\n原始响应: {response_text}")
            if default_value is not None:
                return default_value
            return {"error": f"JSON解析失败: {str(e)}"}
        except Exception as e:
            logger.error(f"LLM JSON调用失败: {str(e)}")
            if default_value is not None:
                return default_value
            raise


def create_llm_service(service_type: str = "openai", **kwargs) -> LLMService:
    if service_type.lower() == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        return OpenAIService(api_key, **kwargs)
    elif service_type.lower() == "siliconflow":
        api_key = os.getenv("SILICONFLOW_API_KEY", "")
        return OpenAIService(api_key, **kwargs)
    else:
        raise ValueError(f"不支持的LLM服务类型: {service_type}")