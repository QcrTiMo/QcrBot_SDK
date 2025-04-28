# QcrBot_SDK/event/parser.py
import json
from typing import Any, Dict, List, Optional, Tuple, Type, Union
from pydantic import ValidationError
from .base import BaseEvent
from .models import (
    PrivateMessageEvent, GroupMessageEvent, LifecycleMetaEvent, HeartbeatMetaEvent,
    GroupUploadNoticeEvent, GroupAdminNoticeEvent, GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent, GroupBanNoticeEvent, FriendAddNoticeEvent,
    GroupRecallNoticeEvent, FriendRecallNoticeEvent, HonorNotifyNoticeEvent,
    PokeNotifyNoticeEvent, FriendRequestEvent, GroupRequestEvent
)
from ..utils.log import log
from ..utils.exception import EventParseError
from ..message.message import Message as MessageChain
from ..utils.cq_code import parse_cq_code_string
from ..message.segment import BaseSegment, TextSegment, SEGMENT_CLASS_MAP



EVENT_MODEL_MAP: Dict[Tuple[str, Optional[str]], Type[BaseEvent]] = {
    ("message", "private"): PrivateMessageEvent,("message", "group"): GroupMessageEvent,
    ("meta_event", "lifecycle"): LifecycleMetaEvent,("meta_event", "heartbeat"): HeartbeatMetaEvent,
    ("notice", "group_upload"): GroupUploadNoticeEvent,("notice", "group_admin"): GroupAdminNoticeEvent,
    ("notice", "group_decrease"): GroupDecreaseNoticeEvent,("notice", "group_increase"): GroupIncreaseNoticeEvent,
    ("notice", "group_ban"): GroupBanNoticeEvent,("notice", "friend_add"): FriendAddNoticeEvent,
    ("notice", "group_recall"): GroupRecallNoticeEvent,("notice", "friend_recall"): FriendRecallNoticeEvent,
    ("notice", "notify"): {"honor": HonorNotifyNoticeEvent, "poke": PokeNotifyNoticeEvent},
    ("request", "friend"): FriendRequestEvent,("request", "group"): GroupRequestEvent,
}



def parse_message_segments(message_data: Union[str, List[Dict[str, Any]]]) -> MessageChain:
    """
    将消息数据 (字符串含 CQ 码 或 字典列表) 解析为 MessageChain 对象。
    Args:
        message_data: 原始消息数据。
    Returns:
        MessageChain: 解析后的消息链对象 (可能为空链)。
    """
    if isinstance(message_data, str):
        # 如果是字符串，使用 CQ 码解析器
        try:
            return parse_cq_code_string(message_data)
        except Exception as e:
            log.error(f"CQ 码字符串解析失败: {e}", exc_info=True)
            # 解析失败，返回一个包含原始文本的单 TextSegment 链或空链
            return MessageChain([TextSegment.new(message_data)]) # 保留原始文本
    elif isinstance(message_data, list):
        # 如果是列表，直接用 MessageChain 初始化
        try:
            return MessageChain(message_data)
        except Exception as e:
             log.error(f"从消息段列表创建 MessageChain 失败: {e}", exc_info=True)
             return MessageChain() # 返回空链
    else:
        # 未知类型
        log.warning(f"未知的消息数据类型传递给 parse_message_segments: {type(message_data)}")
        return MessageChain() # 返回空链


def parse_event(data: Dict[str, Any]) -> BaseEvent:
    """解析事件字典为 Pydantic v11 事件模型"""
    post_type = data.get("post_type")
    if not post_type: raise EventParseError("事件数据缺少 'post_type'", raw_data=data)

    model: Optional[Union[Type[BaseEvent], Dict[str, Type[BaseEvent]]]] = None
    sub_type_key: Optional[str] = None

    if post_type == "message": sub_type_key = data.get("message_type")
    elif post_type == "request": sub_type_key = data.get("request_type")
    elif post_type == "meta_event": sub_type_key = data.get("meta_event_type")
    elif post_type == "notice":
        sub_type_key = data.get("notice_type")
        if sub_type_key == "notify":
            notify_sub_type = data.get("sub_type")
            notify_map = EVENT_MODEL_MAP.get(("notice", "notify"))
            if isinstance(notify_map, dict) and notify_sub_type: model = notify_map.get(notify_sub_type)
        else: model = EVENT_MODEL_MAP.get((post_type, sub_type_key))
    if model is None and post_type != "notice": model = EVENT_MODEL_MAP.get((post_type, sub_type_key))
    if "message" in data:
        try:
            data["message"] = parse_message_segments(data["message"])
        except Exception as e:
            log.warning(f"预处理消息字段时出错: {e}", exc_info=True)
    if model and isinstance(model, type) and issubclass(model, BaseEvent):
        try: return model.model_validate(data)
        except ValidationError as e: log.warning(f"使用模型 {model.__name__} 校验失败: {e}")
    fallback_model: Optional[Type[BaseEvent]] = None
    if post_type == "notice": from .models import BaseNoticeEvent; fallback_model = BaseNoticeEvent
    elif post_type == "request": from .models import BaseRequestEvent; fallback_model = BaseRequestEvent
    if fallback_model:
         try: return fallback_model.model_validate(data)
         except ValidationError as e: log.warning(f"使用基类 {fallback_model.__name__} 校验失败: {e}")
    try:
        required = {"time", "self_id", "post_type"}; missing = list(required - data.keys())
        if missing: raise EventParseError(f"基础字段缺失: {missing}", raw_data=data)
        return BaseEvent.model_validate(data)
    except Exception as e: raise EventParseError(f"最终解析失败: {e}", raw_data=data) from e