# QcrBot_SDK/utils/log.py
import logging
import sys

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


root_logger = logging.getLogger()
sdk_logger = logging.getLogger("QcrBot_SDK")


default_level = logging.INFO
if not sdk_logger.handlers:
    stream_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    stream_handler.setFormatter(formatter)
    sdk_logger.addHandler(stream_handler)
    sdk_logger.setLevel(default_level)
    sdk_logger.propagate = False

def setup_logger(level: int = logging.INFO):
    """
    设置 QcrBot_SDK 日志记录器的级别。
    Args:
        level: 日志级别 (例如 logging.DEBUG, logging.INFO)。
    """
    global default_level
    default_level = level
    sdk_logger.setLevel(level)
    sdk_logger.info(f"日志级别已设置为: {logging.getLevelName(level)}")

log = sdk_logger
