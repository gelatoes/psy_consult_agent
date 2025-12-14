# src/controllers/base_controller.py
from typing import Dict, Any, List, TypedDict
from abc import ABC, abstractmethod
from langgraph.graph import StateGraph
# 从schemas模块导入RuntimeState，而不是重新定义
from src.schemas.runtime_schemas import RuntimeState

class BaseController(ABC):
    """控制器基类"""

    def __init__(self):
        self.graph = StateGraph(state_schema=RuntimeState)
        self._register_nodes()
        self._define_edges()
        self.compiled_graph = None

    @abstractmethod
    def _register_nodes(self):
        """注册节点到图中"""
        pass

    @abstractmethod
    def _define_edges(self):
        """定义节点之间的连接"""
        pass


    def compile(self):
        """编译图"""
        self.compiled_graph = self.graph.compile()

    @abstractmethod
    async def run(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """运行控制流程"""
        pass