# QcrBot_SDK/utils/exception.py
from typing import Optional

class QcrBotSDKError(Exception):
    """SDK 基础异常类"""
    pass

class NetworkError(QcrBotSDKError):
    """网络相关错误"""
    pass

class ConnectionError(NetworkError):
    """连接错误"""
    pass

class ActionFailed(QcrBotSDKError):
    """OneBot API 调用失败"""
    def __init__(self, retcode: int, message: Optional[str] = None, echo: Optional[str] = None):
        self.retcode = retcode
        self.message = message or "Unknown error"
        self.echo = echo
        super().__init__(f"Action failed (retcode={retcode}): {self.message} [echo={echo}]")

class ApiTimeoutError(QcrBotSDKError):
    """等待 API 响应超时"""
    def __init__(self, echo: Optional[str] = None, timeout: Optional[float] = None):
        self.echo = echo
        self.timeout = timeout
        super().__init__(f"Waiting for API response timed out [echo={echo}, timeout={timeout}s]")

class EventParseError(QcrBotSDKError):
    """事件解析失败"""
    def __init__(self, message: str, raw_data: Optional[dict] = None):
        self.raw_data = raw_data
        super().__init__(message)

