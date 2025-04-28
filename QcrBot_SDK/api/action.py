# QcrBot_SDK/api/action.py
import uuid
from typing import Optional, Any, Dict, Literal, List, Union
from pydantic import BaseModel, Field, ConfigDict

from .types import ActionMessage

class BaseResponse(BaseModel):
    status: Literal["ok", "failed"]; retcode: int; data: Optional[Any]=None; message: Optional[str]=None; error_message: Optional[str]=Field(None, alias="msg"); wording: Optional[str]=None; echo: Optional[str]=None; model_config=ConfigDict(extra='allow', populate_by_name=True);
    @property
    def error_msg(self): return self.message or self.error_message or self.wording;
    @property
    def is_success(self): return self.status=="ok" and self.retcode==0
class GetLoginInfoResponseData(BaseModel): user_id: int; nickname: str
class FriendInfo(BaseModel): user_id: int; nickname: str; remark: str
class GroupInfo(BaseModel): group_id: int; group_name: str; member_count: Optional[int]=None; max_member_count: Optional[int]=None
class GroupMemberInfo(BaseModel):
    group_id: int; user_id: int; nickname: str; card: Optional[str]=""; sex: Optional[Literal["male","female","unknown"]]=None; age: Optional[int]=None; area: Optional[str]=None; join_time: Optional[int]=None; last_sent_time: Optional[int]=None; level: Optional[str]=None; role: Optional[Literal["owner","admin","member"]]=None; unfriendly: Optional[bool]=None; title: Optional[str]=None; title_expire_time: Optional[int]=None; card_changeable: Optional[bool]=None; model_config=ConfigDict(extra='allow')


class GroupFile(BaseModel):
    group_id: int
    file_id: str # 文件 ID
    file_name: str
    busid: int # 文件类型
    file_size: int # 文件大小 (字节)
    upload_time: int # 上传时间戳 (秒)
    dead_time: int # 过期时间戳 (秒)，0 表示永不过期
    modify_time: int # 最后修改时间戳 (秒)
    download_times: int # 下载次数
    uploader: int # 上传者 QQ 号
    uploader_name: Optional[str] = None # 上传者名称

class GroupFileSystemInfo(BaseModel):
    file_count: int
    limit_count: int
    used_space: int
    total_space: int

class GroupFileUrl(BaseModel):
    url: str

class StrangerInfo(BaseModel):
    user_id: int
    nickname: str
    sex: Optional[Literal["male", "female", "unknown"]] = None
    age: Optional[int] = None
    model_config = ConfigDict(extra='allow')

class CookiesData(BaseModel):
    cookies: str

class CsrfTokenData(BaseModel):
    token: int

class CredentialsData(CookiesData, CsrfTokenData):
    pass

class RecordData(BaseModel):
    file: str

class StatusData(BaseModel):
    online: Optional[bool] = None
    good: Optional[bool] = None
    model_config = ConfigDict(extra='allow')

class VersionInfo(BaseModel):
    app_name: Optional[str] = None
    app_version: Optional[str] = None
    protocol_version: Literal["v11"] = "v11"
    model_config = ConfigDict(extra='allow')


class BaseAction(BaseModel): action: str; params: Dict[str, Any]; echo: str = Field(default_factory=lambda: str(uuid.uuid4()))
class SendPrivateMsgParams(BaseModel): user_id: int; message: ActionMessage; auto_escape: bool = False
class SendGroupMsgParams(BaseModel): group_id: int; message: ActionMessage; auto_escape: bool = False
class SetFriendAddRequestParams(BaseModel): flag: str; approve: bool = True; remark: Optional[str] = None
class SetGroupAddRequestParams(BaseModel): flag: str; sub_type: Literal["add", "invite"]; approve: bool = True; reason: Optional[str] = None
class DeleteMsgParams(BaseModel): message_id: int
class SendPokeParams(BaseModel): user_id: Optional[int] = None; group_id: Optional[int] = None
class SetGroupKickParams(BaseModel): group_id: int; user_id: int; reject_add_request: bool = False
class SetGroupBanParams(BaseModel): group_id: int; user_id: int; duration: int = 1800
class SetGroupWholeBanParams(BaseModel): group_id: int; enable: bool = True
class SetGroupCardParams(BaseModel): group_id: int; user_id: int; card: str = ""
class SetGroupLeaveParams(BaseModel): group_id: int; is_dismiss: bool = False
class SetGroupAdminParams(BaseModel): group_id: int; user_id: int; enable: bool = True


class UploadGroupFileParams(BaseModel):
    group_id: int
    file: str # 本地文件路径
    name: str # 文件名
    folder: Optional[str] = None # 父目录ID (根目录通常是 None 或 "/")

class DeleteGroupFileParams(BaseModel):
    group_id: int
    file_id: str
    busid: int

class CreateGroupFileFolderParams(BaseModel):
    group_id: int
    name: str
    parent_id: str = "/" # 父目录ID，默认为根目录 "/"

class DeleteGroupFolderParams(BaseModel):
    group_id: int
    folder_id: str

class GetGroupFileSystemInfoParams(BaseModel):
    group_id: int

class GetGroupFileUrlParams(BaseModel):
    group_id: int
    file_id: str
    busid: int

class ForwardNode(BaseModel):
    type: Literal["node"] = "node"
    data: Dict[str, Any] # 包含 user_id, nickname, content

class SendGroupForwardMsgParams(BaseModel):
    group_id: int
    messages: List[ForwardNode]

class GetStrangerInfoParams(BaseModel):
    user_id: int
    no_cache: bool = False

class SetGroupAnonymousBanParams(BaseModel):
    group_id: int
    anonymous_flag: Optional[str] = None
    duration: int = 30 * 60

class GetRecordParams(BaseModel):
    file: str
    out_format: str # 输出格式 (mp3, amr, wma, m4a, spx, ogg, wav, flac)



__all__ = [
    "BaseResponse", "GetLoginInfoResponseData", "FriendInfo", "GroupInfo", "GroupMemberInfo",
    "GroupFile", "GroupFileSystemInfo", "GroupFileUrl",
    "StrangerInfo", "CookiesData", "CsrfTokenData", "CredentialsData", "RecordData", "StatusData", "VersionInfo",
    "BaseAction", "ActionMessage",
    "SendPrivateMsgParams", "SendGroupMsgParams", "SetFriendAddRequestParams", "SetGroupAddRequestParams",
    "DeleteMsgParams", "SendPokeParams", "SetGroupKickParams", "SetGroupBanParams",
    "SetGroupWholeBanParams", "SetGroupCardParams", "SetGroupLeaveParams", "SetGroupAdminParams",
    "UploadGroupFileParams", "DeleteGroupFileParams", "CreateGroupFileFolderParams",
    "DeleteGroupFolderParams", "GetGroupFileSystemInfoParams", "GetGroupFileUrlParams",
    "ForwardNode", "SendGroupForwardMsgParams",
    "GetStrangerInfoParams", "SetGroupAnonymousBanParams", "GetRecordParams",
]