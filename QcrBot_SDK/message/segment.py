# QcrBot_SDK/message/segment.py
from pydantic import BaseModel, Field, ConfigDict, validator, field_validator
from typing import Dict, Any, Literal, Optional, Union, List, Type
from ..utils.log import log

class BaseSegment(BaseModel):
    """消息段基类"""
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    def __str__(self) -> str:

        items_str = ','.join(f'{k}={v}' for k, v in self.data.items()) if self.data else ""
        return f"[{self.type}:{items_str}]"


class TextSegment(BaseSegment):
    """纯文本消息段"""
    type: Literal["text"] = "text"
    data: Dict[str, str] = Field(..., description="必须包含 'text' 键")

    @classmethod
    def new(cls, text: str) -> "TextSegment":
        """创建一个新的 TextSegment 实例"""
        return cls(data={"text": text})

class FaceSegment(BaseSegment):
    """QQ 表情消息段"""
    type: Literal["face"] = "face"
    data: Dict[str, str] # 必须包含 id 字段

    @classmethod
    def new(cls, id: int) -> "FaceSegment":
        """创建一个新的 FaceSegment 实例"""
        # 表情 ID 需要是字符串
        return cls(data={"id": str(id)})

class ImageSegment(BaseSegment):
    """图片消息段"""
    type: Literal["image"] = "image"
    data: Dict[str, Any] = Field(..., description="包含 file, type, url 等字段")

    @classmethod
    def new(cls,
            file: str, # 文件名/路径/URL/Base64
            type: Optional[Literal["flash"]] = None, # 图片类型 (闪照)
            cache: bool = True, # 是否使用缓存
            proxy: bool = True, # 是否通过代理下载 (1/0)
            timeout: Optional[int] = None, # 下载超时 (秒)
           ) -> "ImageSegment":
        """创建一个新的 ImageSegment 实例"""
        data_dict = {"file": file}
        if type:
            data_dict["type"] = type
        data_dict["cache"] = "1" if cache else "0"
        data_dict["proxy"] = "1" if proxy else "0"
        if timeout is not None:
            data_dict["timeout"] = str(timeout)
        return cls(data=data_dict)

class RecordSegment(BaseSegment):
    """语音消息段"""
    type: Literal["record"] = "record"
    data: Dict[str, Any] = Field(..., description="包含 file, magic, cache, proxy 等")

    @classmethod
    def new(cls,
            file: str, # 文件名/路径/URL/Base64
            magic: bool = False, # 是否变声
            cache: bool = True,
            proxy: bool = True,
            timeout: Optional[int] = None
           ) -> "RecordSegment":
        """创建一个新的 RecordSegment 实例"""
        data_dict = {"file": file}
        if magic:
            data_dict["magic"] = "1"
        data_dict["cache"] = "1" if cache else "0"
        data_dict["proxy"] = "1" if proxy else "0"
        if timeout is not None:
            data_dict["timeout"] = str(timeout)
        return cls(data=data_dict)

class VideoSegment(BaseSegment):
    """短视频消息段"""
    type: Literal["video"] = "video"
    data: Dict[str, Any] = Field(..., description="包含 file, cache, proxy 等")

    @classmethod
    def new(cls,
            file: str, # 文件名/路径/URL/Base64
            cache: bool = True,
            proxy: bool = True,
            timeout: Optional[int] = None
           ) -> "VideoSegment":
        """创建一个新的 VideoSegment 实例"""
        data_dict = {"file": file}
        data_dict["cache"] = "1" if cache else "0"
        data_dict["proxy"] = "1" if proxy else "0"
        if timeout is not None:
            data_dict["timeout"] = str(timeout)
        return cls(data=data_dict)

class AtSegment(BaseSegment):
    """@ 消息段"""
    type: Literal["at"] = "at"
    # data 应该包含 qq 字段，且其值为字符串
    data: Dict[str, str] = Field(..., description="必须包含 'qq' 键，值为字符串")

    @classmethod
    def new(cls, user_id: Union[int, Literal["all"]]) -> "AtSegment":
        """创建一个新的 AtSegment 实例"""
        # qq 字段需要是字符串
        return cls(data={"qq": str(user_id)})

class RpsSegment(BaseSegment):
    """猜拳魔法表情"""
    type: Literal["rps"] = "rps"

    @classmethod
    def new(cls) -> "RpsSegment":
        return cls(data={})

class DiceSegment(BaseSegment):
    """掷骰子魔法表情"""
    type: Literal["dice"] = "dice"
    # data 为空

    @classmethod
    def new(cls) -> "DiceSegment":
        return cls(data={})

class ShakeSegment(BaseSegment):
    """窗口抖动（戳一戳）"""
    type: Literal["shake"] = "shake"
    # data 为空

    @classmethod
    def new(cls) -> "ShakeSegment":
        return cls(data={})

class PokeSegment(BaseSegment):
    """戳一戳（需要 UIN） - 不同实现可能行为不一"""
    type: Literal["poke"] = "poke"
    data: Dict[str, str]

    @classmethod
    def new(cls, type: str, id: int) -> "PokeSegment":
        """创建戳一戳（需要类型和ID，具体含义查阅实现文档）"""
        return cls(data={"type": str(type), "id": str(id)})

class AnonymousSegment(BaseSegment):
    """匿名发消息（仅群聊可用）"""
    type: Literal["anonymous"] = "anonymous"
    data: Dict[str, Any]

    @classmethod
    def new(cls, ignore_failure: bool = False) -> "AnonymousSegment":
        """
        创建一个匿名消息段。
        注意：实际是否匿名发送取决于群是否开启及权限。
        发送消息时包含此段，并不能保证一定匿名成功。
        Args:
            ignore_failure: 如果为 True，匿名失败时是否继续发送（默认 False）。
                           此字段可能不被所有实现支持。
        """
        data_dict = {}
        if ignore_failure:
            data_dict["ignore"] = "true"
        return cls(data=data_dict)

class ShareSegment(BaseSegment):
    """链接分享"""
    type: Literal["share"] = "share"
    data: Dict[str, str] # url, title, content, image

    @classmethod
    def new(cls, url: str, title: str, content: Optional[str] = None, image_url: Optional[str] = None) -> "ShareSegment":
        """创建一个链接分享消息段"""
        data_dict = {"url": url, "title": title}
        if content:
            data_dict["content"] = content
        if image_url:
            data_dict["image"] = image_url
        return cls(data=data_dict)

class ContactSegment(BaseSegment):
    """推荐好友/群 (合并了 contact 和 recommend)"""
    type: Literal["contact"] = "contact"
    data: Dict[str, str] # type ("qq" or "group"), id

    @classmethod
    def new(cls, type: Literal["qq", "group"], id: int) -> "ContactSegment":
        """创建一个推荐联系人消息段"""
        return cls(data={"type": type, "id": str(id)})

class LocationSegment(BaseSegment):
    """位置消息"""
    type: Literal["location"] = "location"
    data: Dict[str, Any] # lat, lon, title, content

    @classmethod
    def new(cls, latitude: float, longitude: float, title: Optional[str] = None, content: Optional[str] = None) -> "LocationSegment":
        """创建一个位置消息段"""
        data_dict = {"lat": str(latitude), "lon": str(longitude)}
        if title:
            data_dict["title"] = title
        if content:
            data_dict["content"] = content
        return cls(data=data_dict)

class ReplySegment(BaseSegment):
    """回复消息"""
    type: Literal["reply"] = "reply"
    data: Dict[str, str] # id (被回复的消息 ID)

    @classmethod
    def new(cls, message_id: int) -> "ReplySegment":
        """创建一个回复消息段"""
        # 消息 ID 需要是字符串
        return cls(data={"id": str(message_id)})

class NodeSegment(BaseSegment):
    """合并转发节点"""
    type: Literal["node"] = "node"
    data: Dict[str, Any] # user_id, nickname, content (消息段列表或字符串)

    @field_validator('data')
    def check_node_data(cls, v):
        if 'user_id' not in v or 'nickname' not in v or 'content' not in v:
             raise ValueError("Node segment data must contain 'user_id', 'nickname', and 'content'")
        # content 可以是字符串或列表，这里不做强制转换
        return v

    @classmethod
    def new(cls, user_id: int, nickname: str, content: Union[str, List[BaseSegment], 'Message']) -> "NodeSegment": # 允许传入 Message 对象
        """
        创建一个合并转发节点。

        Args:
            user_id: 发送者 QQ 号。
            nickname: 发送者昵称。
            content: 节点内容 (字符串、消息段列表或 Message 对象)。
        """
        # 如果 content 是 Message 对象，需要先导出
        if isinstance(content, List) and all(isinstance(seg, BaseSegment) for seg in content):
             # 如果是 BaseSegment 列表，需要转换为字典列表
             content_data = [seg.model_dump(mode='json', by_alias=True) for seg in content]
        elif isinstance(content, str):
             content_data = content # 字符串直接使用
        else:
             try:
                  content_data = content.export() # type: ignore
             except AttributeError:
                  log.error(f"无法处理 Node content 类型: {type(content)}，请传入字符串、BaseSegment 列表或包含 export 方法的对象。")
                  raise TypeError("Invalid content type for NodeSegment")

        return cls(data={"user_id": str(user_id), "nickname": nickname, "content": content_data})


class XmlSegment(BaseSegment):
    """XML 消息 (卡片)"""
    type: Literal["xml"] = "xml"
    data: Dict[str, str] # data (原始 XML 字符串)

    @classmethod
    def new(cls, xml_data: str) -> "XmlSegment":
        """创建一个 XML 消息段"""
        return cls(data={"data": xml_data})

class JsonSegment(BaseSegment):
    """JSON 消息 (通常用于特殊用途)"""
    type: Literal["json"] = "json"
    data: Dict[str, str] # data (原始 JSON 字符串)

    @classmethod
    def new(cls, json_data: str) -> "JsonSegment":
        """创建一个 JSON 消息段"""
        return cls(data={"data": json_data})


__all__ = [
    "BaseSegment",
    "TextSegment",
    "FaceSegment",
    "ImageSegment",
    "RecordSegment",
    "VideoSegment",
    "AtSegment",
    "RpsSegment",
    "DiceSegment",
    "ShakeSegment",
    "PokeSegment",
    "AnonymousSegment",
    "ShareSegment",
    "ContactSegment",
    "LocationSegment",
    "ReplySegment",
    "NodeSegment",
    "XmlSegment",
    "JsonSegment",
]


SegmentData = Union[str, Dict[str, Any]]
SEGMENT_CLASS_MAP: Dict[str, Type[BaseSegment]] = {
    seg_cls.model_fields['type'].default: seg_cls
    for seg_cls in BaseSegment.__subclasses__()
    if 'type' in seg_cls.model_fields and isinstance(seg_cls.model_fields['type'].default, str)
}
SEGMENT_CLASS_MAP["text"] = TextSegment
log.debug(f"消息段类映射已创建: {list(SEGMENT_CLASS_MAP.keys())}")