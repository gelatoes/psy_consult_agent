# src/utils/exceptions.py
class ConsultationError(Exception):
    """咨询系统基础异常类"""
    pass

class StateError(ConsultationError):
    """状态相关异常"""
    pass

class ToolError(ConsultationError):
    """工具相关异常"""
    pass

class AgentError(ConsultationError):
    """Agent相关异常"""
    pass