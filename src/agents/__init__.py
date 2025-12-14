# src/agents/__init__.py
from .student_agent import StudentAgent
from .profiler_agent import ProfilerAgent
from .therapist_agent import TherapistAgent
from .supervisor_agent import SupervisorAgent
from src.agents.therapist_factory import TherapistFactory

from abc import ABC, abstractmethod
from typing import Dict, Any
from langchain.chat_models import ChatOpenAI

class BaseAgent(ABC):
    """所有Agent的基类"""
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.state = "initial"


    @abstractmethod
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理输入状态并返回新状态"""
        pass



__all__ = [
    'TherapistAgent',
    'ProfilerAgent',
    'SupervisorAgent',
    'StudentAgent',
    'TherapistFactory'
]