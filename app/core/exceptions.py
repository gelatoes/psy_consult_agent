# app/core/exceptions.py

class AppException(Exception):
    """应用中所有自定义异常的基类。"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class ConsultationError(AppException):
    """
    专用于咨询流程中的错误。
    例如，当一个状态节点未找到或流程无法继续时，可以抛出此异常。
    """
    pass

class AuthenticationError(AppException):
    """

    专用于认证流程中的错误。
    例如，当解码JWT令牌失败时。
    """
    pass

class DatabaseError(AppException):
    """
    专用于数据访问层发生的错误。
    """
    pass

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