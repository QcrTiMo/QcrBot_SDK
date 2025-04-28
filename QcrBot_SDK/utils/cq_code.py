# QcrBot_SDK/utils/cq_code.py
import re
from typing import List, Dict, Any, Generator, Tuple, Union
from ..message.segment import SEGMENT_CLASS_MAP, BaseSegment, TextSegment
from ..message.message import Message as MessageChain
from .log import log


CQ_CODE_PATTERN = re.compile(r"\[CQ:(?P<type>[^,\]]+)(?P<params>(?:,[^,\]]+=[^\]]*)*)\]")

def escape(s: str, *, escape_comma: bool = True) -> str:
    """对 CQ 码参数值进行转义"""
    s = s.replace("&", "&").replace("[", "[").replace("]", "]")
    if escape_comma:
        s = s.replace(",", ",")
    return s

def unescape(s: str) -> str:
    """对 CQ 码参数值进行反转义"""
    s = s.replace(",", ",").replace("[", "[").replace("]", "]").replace("&", "&")
    return s

def parse_cq_params(params_str: str) -> Dict[str, str]:
    """解析 CQ 码的参数部分 ( ,key=value,key=value )"""
    params = {}
    pattern = re.compile(r',([^=,]+)=((?:[^,\\]*(?:\\.[^,\\]*)*|[^,]*))')
    for match in pattern.finditer(params_str):
        key = match.group(1)
        value = unescape(match.group(2)) # 反转义值
        params[key] = value
    return params

def cq_code_to_segment(cq_match: re.Match) -> BaseSegment:
    """将 CQ 码的 re.Match 对象转换为 BaseSegment 对象"""
    cq_type = cq_match.group("type")
    params_str = cq_match.group("params")
    cq_data = parse_cq_params(params_str)

    target_cls = SEGMENT_CLASS_MAP.get(cq_type, BaseSegment)
    try:
        segment = target_cls.model_validate({"type": cq_type, "data": cq_data})
        return segment
    except Exception as e:
        log.warning(f"创建消息段失败 (type={cq_type}): {e}, data={cq_data}")
        return BaseSegment(type=cq_type, data=cq_data)


def parse_cq_code_string(text: str) -> MessageChain:
    """
    将包含 CQ 码的字符串解析为 MessageChain 对象。
    Args:
        text: 包含 CQ 码的原始字符串。
    Returns:
        MessageChain: 解析后的消息链对象。
    """
    segments: List[Union[str, BaseSegment]] = []
    last_pos = 0

    for match in CQ_CODE_PATTERN.finditer(text):
        start, end = match.span()
        if start > last_pos:
            segments.append(text[last_pos:start]) # 字符串会被 MessageChain 自动转为 TextSegment

        # 处理 CQ 码本身
        segment = cq_code_to_segment(match)
        segments.append(segment)
        last_pos = end

    # 添加最后一个 CQ 码后面的文本部分
    if last_pos < len(text):
        segments.append(text[last_pos:])

    # 使用 MessageChain 初始化，它会处理字符串和合并文本
    return MessageChain(segments)


__all__ = ["parse_cq_code_string", "escape", "unescape"]