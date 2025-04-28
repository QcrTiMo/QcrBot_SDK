# QcrBot_SDK/utils/helpers.py
import time

def get_current_timestamp_ms() -> int:
    """获取当前时间的毫秒级时间戳"""
    return int(time.time() * 1000)