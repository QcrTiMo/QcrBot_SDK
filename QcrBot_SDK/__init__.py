# QcrBot_SDK/__init__.py
from .api import action
from .api.types import ActionMessage
from .api.action import (
    BaseResponse, GetLoginInfoResponseData, FriendInfo, GroupInfo, GroupMemberInfo,
    GroupFile, GroupFileSystemInfo, GroupFileUrl, ForwardNode,
    StrangerInfo, CookiesData, CsrfTokenData, CredentialsData, RecordData, StatusData, VersionInfo
)
from .event import *
from .message import segment
from .message.segment import *
from .message.message import Message as MessageChain
from .core.bot import Bot
from .utils import exception
from .utils.log import setup_logger, log
from .utils.exception import *


try:
    from .core.bot import Bot
    __core_exports = ["Bot"]
except ImportError as e:
     log.critical(f"无法导入核心 Bot 类: {e}", exc_info=True)
     Bot = None
     __core_exports = []


__version__ = "0.3.3"


__all__ = [
    "Bot", *event.__all__, "BaseSegment", "MessageChain", *segment.__all__,
    "QcrBotSDKError", "NetworkError", "ConnectionError", "ActionFailed", "ApiTimeoutError", "EventParseError",
    "BaseResponse", "ActionMessage", "GetLoginInfoResponseData", "FriendInfo", "GroupInfo",
    "GroupMemberInfo", "GroupFile", "GroupFileSystemInfo", "GroupFileUrl", "ForwardNode",
    "StrangerInfo", "CookiesData", "CsrfTokenData", "CredentialsData", "RecordData", "StatusData", "VersionInfo",
    "setup_logger", "log", "__version__",
]

try: del event
except NameError: pass
try: del segment
except NameError: pass
try: del exception
except NameError: pass
try: del action
except NameError: pass