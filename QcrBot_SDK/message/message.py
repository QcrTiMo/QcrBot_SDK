# QcrBot_SDK/message/message.py
from typing import Dict, List, Union, Iterable, Optional, Type, Any, TypeVar, cast
from pydantic import Field
from .segment import BaseSegment, TextSegment, SEGMENT_CLASS_MAP
from ..utils.log import log

T_Segment = TypeVar("T_Segment", bound=BaseSegment)

class Message(List[BaseSegment]):
    """
    表示一条消息的消息链 (列表形式)。
    继承自 list，并提供方便的方法来构建和操作消息。
    支持使用 + 和 += 操作符连接段、字符串或其他消息链。
    """

    def __init__(self, segments: Optional[Iterable[Union[BaseSegment, str, Dict[str, Any]]]] = None):
        """初始化消息链"""
        super().__init__()
        if segments:
            self.extend(segments)

    def _parse_and_append(self, obj: Union[BaseSegment, str, Dict[str, Any]]):
        """内部方法：解析单个对象并尝试添加到链尾，处理文本合并"""
        segment_to_add: Optional[BaseSegment] = None
        is_text = False
        if isinstance(obj, BaseSegment):
            segment_to_add = obj
            is_text = isinstance(obj, TextSegment)
        elif isinstance(obj, str):
            if not obj:
                return
            segment_to_add = TextSegment.new(obj)
            is_text = True
        elif isinstance(obj, dict):
            seg_type = obj.get("type"); seg_data = obj.get("data")
            if seg_type and isinstance(seg_data, dict):
                target_cls = SEGMENT_CLASS_MAP.get(seg_type, BaseSegment)
                try: segment_to_add = target_cls.model_validate({"type": seg_type, "data": seg_data})
                except Exception as e: log.warning(f"Dict->Segment failed (type={seg_type}): {e}"); return
            else: log.warning(f"Invalid dict for Segment: {obj}"); return
        else:
            raise TypeError(f"Cannot append object of type {type(obj)} to Message")

        if segment_to_add:
            # 核心逻辑：文本合并
            if is_text and self and isinstance(self[-1], TextSegment):
                self[-1].data["text"] += segment_to_add.data["text"] # type: ignore
            else:
                super().append(segment_to_add)

    def append(self, obj: Union[BaseSegment, str, Dict[str, Any]]) -> "Message":
        """向消息链末尾添加单个消息段、文本或字典"""
        self._parse_and_append(obj)
        return self

    def extend(self, segments: Iterable[Union[BaseSegment, str, Dict[str, Any]]]) -> "Message":
        """将另一个消息链或可迭代对象合并到当前消息链"""
        for seg in segments:
            self._parse_and_append(seg)
        return self

    def __add__(self, other: Union[BaseSegment, str, Dict[str, Any], Iterable]) -> "Message":
        """使用 + 操作符连接: Message + other"""
        new_message = self.copy() # 创建副本dict
        if isinstance(other, (BaseSegment, str, )):
            new_message.append(other) # 添加单个元素
        elif isinstance(other, Iterable):
            new_message.extend(other) # 合并可迭代对象
        else:
            return NotImplemented
        return new_message

    def __radd__(self, other: Union[BaseSegment, str, Dict[str, Any]]) -> "Message":
        """使用 + 操作符连接: other + Message"""
        if isinstance(other, (BaseSegment, str, dict)):
            new_message = Message([other])
            new_message.extend(self)
            return new_message
        else:
            return NotImplemented

    def __iadd__(self, other: Union[BaseSegment, str, Dict[str, Any], Iterable]) -> "Message":
        """使用 += 操作符连接: message += other"""
        if isinstance(other, (BaseSegment, str, dict)):
            self.append(other)
        elif isinstance(other, Iterable):
            self.extend(other)
        else:
            return NotImplemented
        return self

    def copy(self) -> "Message":
        """创建消息链的浅拷贝"""
        return Message(super().copy())

    def export(self) -> List[Dict[str, Any]]:
        """将消息链导出为 OneBot v11 API 所需的字典列表格式"""
        return [seg.model_dump(mode='json', by_alias=True) for seg in self]


    def extract_plain_text(self) -> str:
        """提取消息链中的所有纯文本内容并合并"""
        return "".join(seg.data.get("text", "") for seg in self if seg.type == "text")

    def get(self, segment_type: Type[T_Segment], index: int = 0) -> Optional[T_Segment]:
        """
        获取指定类型的第 N 个消息段。

        Args:
            segment_type: 要获取的消息段类 (如 TextSegment, ImageSegment)。
            index: 索引 (0 表示第一个匹配的，1 表示第二个，以此类推)。

        Returns:
            Optional[T_Segment]: 找到的消息段对象，或 None。
        """
        count = 0
        for segment in self:
            if isinstance(segment, segment_type):
                if count == index:
                    return cast(T_Segment, segment)
                count += 1
        return None

    def get_all(self, segment_type: Type[T_Segment]) -> List[T_Segment]:
        """
        获取所有指定类型的消息段。
        Args:
            segment_type: 要获取的消息段类。
        Returns:
            List[T_Segment]: 包含所有匹配消息段对象的列表 (可能为空)。
        """
        return [cast(T_Segment, segment) for segment in self if isinstance(segment, segment_type)]

    def __contains__(self, item: Union[str, Type[BaseSegment]]) -> bool:
        """
        检查消息链是否包含特定文本或类型的消息段。
        Args:
            item: 要检查的内容 (字符串或消息段类)。
        Returns:
            bool: 如果包含则为 True，否则为 False。
        """
        if isinstance(item, str):
            return any(item in seg.data.get("text", "") for seg in self if seg.type == "text")
        elif isinstance(item, type) and issubclass(item, BaseSegment):
            return any(isinstance(seg, item) for seg in self)
        else:
            log.debug(f"不支持在 Message 中检查类型 {type(item)}")
            return False # 返回 False 而不是抛异常

    def only(self, *segment_types: Type[BaseSegment]) -> "Message":
        """
        只保留指定类型的消息段，返回一个新的 MessageChain。
        Args:
            *segment_types: 一个或多个要保留的消息段类。
        Returns:
            Message: 只包含指定类型段的新消息链。
        """
        if not segment_types: return self.copy()
        if not all(isinstance(t, type) and issubclass(t, BaseSegment) for t in segment_types):
            raise TypeError("only() 方法只接受 BaseSegment 的子类作为参数")
        return Message(seg for seg in self if isinstance(seg, segment_types))

    def exclude(self, *segment_types: Type[BaseSegment]) -> "Message":
        """
        移除指定类型的消息段，返回一个新的 MessageChain。
        Args:
            *segment_types: 一个或多个要移除的消息段类。
        Returns:
            Message: 不包含指定类型段的新消息链。
        """
        if not segment_types: return self.copy()
        if not all(isinstance(t, type) and issubclass(t, BaseSegment) for t in segment_types):
            raise TypeError("exclude() 方法只接受 BaseSegment 的子类作为参数")
        return Message(seg for seg in self if not isinstance(seg, segment_types))


__all__ = ["Message"]