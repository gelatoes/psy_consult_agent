# app/business_logic/services/llm_service.py

import re
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings

class LLMService(ABC):
    """抽象LLM服务基类"""
    @abstractmethod
    async def invoke(self, prompt: str, temperature: Optional[float] = None) -> str:
        pass

    @abstractmethod
    async def invoke_json(self, prompt: str, temperature: Optional[float] = None, default_value: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass

class OpenAIService(LLMService):
    """OpenAI兼容接口的LLM服务实现（可用于OpenAI, 硅基流动等）"""
    def __init__(self, api_key: str, model_name: str, default_temperature: float, api_base: Optional[str]):
        self.model = ChatOpenAI(
            model_name=model_name,
            temperature=default_temperature,
            api_key=api_key,
            base_url=api_base,
            request_timeout=120,
        )
        self.default_temperature = default_temperature
        print(f"OpenAIService initialized for model '{model_name}' at base_url '{api_base}'.")

    async def invoke(self, prompt: str, temperature: Optional[float] = None) -> str:
        try:
            current_temp = self.model.temperature
            if temperature is not None:
                self.model.temperature = temperature
            
            response = await self.model.ainvoke([HumanMessage(content=prompt)])
            
            if temperature is not None:
                self.model.temperature = current_temp

            return response.content
        except Exception as e:
            print(f"Error: LLM call failed: {str(e)}")
            raise

    async def invoke_json(self, prompt: str, temperature: Optional[float] = None, default_value: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            if not prompt.strip().endswith("JSON"):
                prompt += "\n\n请只返回JSON格式的内容，不要添加任何额外的解释或说明。"

            response_text = await self.invoke(prompt, temperature)

            json_match = re.search(r'({.*})', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)

                # print("-----------------------invoke_json的prompt是-----------------------")
                # print(prompt)
                # print("-----------------------invoke_json的response是-----------------------")
                # print(json_str)
                return json.loads(json_str)
            else:
                return json.loads(response_text)
        except json.JSONDecodeError as e:
            if default_value is not None:
                return default_value
            return {"error": f"JSON解析失败: {str(e)}"}
        except Exception as e:
            if default_value is not None:
                return default_value
            raise

def create_llm_service(service_type="siliconflow", model_name="THUDM/GLM-4-9B-0414", default_temperature=0.7) -> LLMService:
    """
    LLM服务工厂函数。
    它会根据配置决定创建并返回哪种LLM服务实例。
    """
    print(f"Creating LLM service of type: '{service_type}'")
    
    if service_type.lower() == "siliconflow":
        return OpenAIService(
            api_key=settings.SILICON_FLOW_API_KEY,
            api_base=settings.SILICON_FLOW_API_BASE,
            model_name=model_name,
            default_temperature=default_temperature
        )
    else:
        return OpenAIService(
            api_key=settings.API_KEY,
            api_base=settings.API_BASE,
            model_name=model_name,
            default_temperature=default_temperature
        )