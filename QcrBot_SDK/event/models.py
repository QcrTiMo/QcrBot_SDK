# QcrBot_SDK/event/models.py
from typing import Optional, List, Any, Dict, Literal, Union
from ..message.message import Message as MessageChain
from ..message.segment import BaseSegment
from pydantic import BaseModel, Field, ConfigDict, field_validator
from .base import BaseEvent
from ..utils.log import log
class SenderInfo(BaseModel): user_id: Optional[int]=None; nickname: Optional[str]=None;sex: Optional[Literal["male","female","unknown"]]=None; age: Optional[int]=None;card: Optional[str]=""; area: Optional[str]=None; level: Optional[str]=None;role: Optional[Literal["owner","admin","member"]]=None; title: Optional[str]=None;model_config=ConfigDict(extra='allow')


class BaseMessageEvent(BaseEvent):
    post_type: Literal["message"] = "message"
    message_type: str
    sub_type: str
    message_id: int
    user_id: int
    message: MessageChain
    raw_message: str
    font: int
    sender: SenderInfo


    model_config = ConfigDict(
        extra='allow',
        arbitrary_types_allowed=True
    )

class PrivateMessageEvent(BaseMessageEvent):
    message_type: Literal["private"] = "private"
    sub_type: Literal["friend", "group", "other"]
    def get_session_id(self) -> str: return f"private_{self.user_id}"

class GroupMessageEvent(BaseMessageEvent):
    message_type: Literal["group"] = "group"
    sub_type: Literal["normal", "anonymous", "notice"]
    group_id: int
    anonymous: Optional[Any] = None
    def get_session_id(self) -> str: return f"group_{self.group_id}"


class BaseMetaEvent(BaseEvent): post_type: Literal["meta_event"]="meta_event"; meta_event_type: str
class LifecycleMetaEvent(BaseMetaEvent): meta_event_type: Literal["lifecycle"]="lifecycle"; sub_type: Literal["enable","disable","connect"]
class Status(BaseModel): online: Optional[bool]=None; good: Optional[bool]=True; model_config=ConfigDict(extra='allow')
class HeartbeatMetaEvent(BaseMetaEvent): meta_event_type: Literal["heartbeat"]="heartbeat"; status: Status; interval: int
class BaseNoticeEvent(BaseEvent): post_type: Literal["notice"]="notice"; notice_type: str
class GroupUploadNoticeEvent(BaseNoticeEvent): notice_type: Literal["group_upload"]="group_upload"; group_id: int; user_id: int; file: Dict[str, Any]
class GroupAdminNoticeEvent(BaseNoticeEvent): notice_type: Literal["group_admin"]="group_admin"; sub_type: Literal["set","unset"]; group_id: int; user_id: int
class GroupDecreaseNoticeEvent(BaseNoticeEvent): notice_type: Literal["group_decrease"]="group_decrease"; sub_type: Literal["leave","kick","kick_me"]; group_id: int; operator_id: int; user_id: int
class GroupIncreaseNoticeEvent(BaseNoticeEvent): notice_type: Literal["group_increase"]="group_increase"; sub_type: Literal["approve","invite"]; group_id: int; operator_id: int; user_id: int
class GroupBanNoticeEvent(BaseNoticeEvent): notice_type: Literal["group_ban"]="group_ban"; sub_type: Literal["ban","lift_ban"]; group_id: int; operator_id: int; user_id: int; duration: int
class FriendAddNoticeEvent(BaseNoticeEvent): notice_type: Literal["friend_add"]="friend_add"; user_id: int
class GroupRecallNoticeEvent(BaseNoticeEvent): notice_type: Literal["group_recall"]="group_recall"; group_id: int; user_id: int; operator_id: int; message_id: int
class FriendRecallNoticeEvent(BaseNoticeEvent): notice_type: Literal["friend_recall"]="friend_recall"; user_id: int; message_id: int
class HonorNotifyNoticeEvent(BaseNoticeEvent): notice_type: Literal["notify"]="notify"; sub_type: Literal["honor"]="honor"; group_id: int; user_id: int; honor_type: str
class PokeNotifyNoticeEvent(BaseNoticeEvent): notice_type: Literal["notify"]="notify"; sub_type: Literal["poke"]="poke"; group_id: Optional[int]=None; user_id: int; target_id: int
class BaseRequestEvent(BaseEvent): post_type: Literal["request"]="request"; request_type: str
class FriendRequestEvent(BaseRequestEvent): request_type: Literal["friend"]="friend"; user_id: int; comment: str; flag: str
class GroupRequestEvent(BaseRequestEvent): request_type: Literal["group"]="group"; sub_type: Literal["add","invite"]; group_id: int; user_id: int; comment: str; flag: str



__all__ = [
    "BaseEvent", "SenderInfo",
    "BaseMessageEvent", "PrivateMessageEvent", "GroupMessageEvent",
    "BaseMetaEvent", "LifecycleMetaEvent", "Status", "HeartbeatMetaEvent",
    "BaseNoticeEvent", "GroupUploadNoticeEvent", "GroupAdminNoticeEvent",
    "GroupDecreaseNoticeEvent", "GroupIncreaseNoticeEvent", "GroupBanNoticeEvent",
    "FriendAddNoticeEvent", "GroupRecallNoticeEvent", "FriendRecallNoticeEvent",
    "HonorNotifyNoticeEvent", "PokeNotifyNoticeEvent",
    "BaseRequestEvent", "FriendRequestEvent", "GroupRequestEvent",
]