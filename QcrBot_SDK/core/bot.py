# QcrBot_SDK/core/bot.py
import asyncio
import logging
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union, Pattern, Type, Literal
from contextlib import suppress, asynccontextmanager
from .dispatcher import EventDispatcher
from ..adapters.websocket import WebSocketAdapter
from ..api.client import ApiClient
from ..api.action import (
    FriendInfo, GroupInfo, GroupMemberInfo, GroupFile, GroupFileSystemInfo, GroupFileUrl, ForwardNode,
    StrangerInfo, CookiesData, CsrfTokenData, CredentialsData, RecordData, StatusData, VersionInfo, BaseResponse,
    GetLoginInfoResponseData
)
from ..message.segment import NodeSegment
from ..api.types import ActionMessage
from ..message.segment import NodeSegment
from ..event.base import BaseEvent
from ..event.parser import parse_event
from ..event.typing import EventHandler, EventMatcherRule
from ..event.models import PrivateMessageEvent, GroupMessageEvent, BaseMessageEvent  # 用于 send 方法
from ..message.segment import BaseSegment, TextSegment
from ..message.message import Message as MessageChain
from ..utils.log import log, setup_logger
from ..utils.exception import (
    QcrBotSDKError, ConnectionError as SDKConnectionError, EventParseError,
    ActionFailed, ApiTimeoutError
)


SendMessage = Union[str, BaseSegment, List[Union[str, BaseSegment]]]

class Bot:
    """
    QcrBot SDK 的核心 Bot 类。
    协调适配器、API 客户端和事件分发器，管理机器人的生命周期。
    提供便捷的事件注册和 API 调用接口。
    """
    def __init__(
        self,
        url: str,
        access_token: Optional[str] = None,
        log_level: int = logging.INFO,
        command_prefixes: Union[str, List[str]] = "/",
        reconnect_interval: float = 5.0,
        max_reconnect_attempts: Optional[int] = 10
    ):
        """
        初始化 Bot。

        Args:
            url: OneBot v11 WebSocket URL。
            access_token: 访问令牌。
            log_level: SDK 的日志级别。
            command_prefixes: 命令前缀 (字符串或列表)。
            reconnect_interval: 初始重连间隔 (秒)。
            max_reconnect_attempts: 最大重连次数 (None 表示无限)。
        """
        setup_logger(log_level) # 设置日志级别

        self.adapter = WebSocketAdapter(
            url,
            access_token,
            reconnect_interval=reconnect_interval,
            max_reconnect_attempts=max_reconnect_attempts
        )
        self.api = ApiClient(self.adapter)
        self.dispatcher = EventDispatcher()

        # 设置适配器的回调
        self.adapter.set_raw_data_handler(self._handle_raw_data)
        self.adapter.on_connect = self._on_adapter_connect
        self.adapter.on_disconnect = self._on_adapter_disconnect

        self._running = False # Bot 的期望运行状态
        self._self_id: Optional[int] = None # 机器人 QQ 号
        self._nickname: Optional[str] = None # 机器人昵称

        # 处理命令前缀配置
        if isinstance(command_prefixes, str):
            self.command_prefixes = [command_prefixes]
        elif isinstance(command_prefixes, list):
            self.command_prefixes = command_prefixes
        else:
            log.warning(f"无效的命令前缀类型: {type(command_prefixes)}，将禁用命令处理。")
            self.command_prefixes = []
        log.info(f"Bot 初始化完成，命令前缀: {self.command_prefixes}")


    @property
    def self_id(self) -> Optional[int]:
        """获取当前连接的机器人 QQ 号 (如果已获取)"""
        return self._self_id

    @property
    def nickname(self) -> Optional[str]:
         """获取当前连接的机器人昵称 (如果已获取)"""
         return self._nickname

    @property
    def is_connected(self) -> bool:
        """检查底层 WebSocket 是否已连接"""
        return self.adapter._connected


    async def _on_adapter_connect(self):
        """适配器连接成功时的回调，获取机器人信息"""
        log.info("适配器连接成功，尝试获取机器人信息...")
        try:
            login_info = await self.get_login_info(timeout=10.0)
            self._self_id = login_info.user_id
            self._nickname = login_info.nickname
            log.info(f"成功获取/更新机器人信息: Nick={self.nickname}, ID={self.self_id}")
        except Exception as e:
            log.error(f"连接成功后获取机器人信息失败: {e}，部分功能可能受限。")

    async def _on_adapter_disconnect(self, code: int, reason: str):
        """适配器连接断开时的回调，清理状态"""
        log.warning(f"适配器连接已断开: Code={code}, Reason='{reason}'")
        self.api.clear_futures(SDKConnectionError(f"Connection closed: {code} - {reason}"))



    async def _handle_raw_data(self, data: Dict[str, Any]):
        """处理从适配器收到的原始字典数据，区分响应和事件"""
        echo = data.get("echo")
        future = self.api._action_futures.get(echo) # 假设 api client 有此属性
        is_response = future is not None and "status" in data

        if is_response:
            try:
                response = BaseResponse.model_validate(data)
                self.api.resolve_future(echo, response)
            except Exception as e:
                log.error(f"解析动作响应失败 (echo={echo}): {e}\n原始数据: {data}", exc_info=True)
                self.api.reject_future(echo, ValueError(f"Failed to parse action response: {e}"))
            return


        try:
            event = parse_event(data)
            log.debug(f"成功解析事件: {type(event).__name__}")
            # 将事件交给分发器处理
            await self.dispatcher.dispatch(event)
        except EventParseError as e:
            log.error(f"事件解析失败: {e}")
        except Exception as e:
            log.error(f"处理传入数据时发生未知错误: {e}\n原始数据: {data}", exc_info=True)

    #生命周期管理
    async def start(self):
        """启动 Bot，由适配器负责连接和重连，并等待其结束。"""
        if self._running: log.warning("Bot 已请求启动或正在运行中。"); return
        log.info("Bot 开始启动..."); self._running = True
        try:
            await self.adapter.start() # 启动并等待适配器循环结束
            log.info("Bot: 等待适配器连接循环结束...") # adapter.start 内部会打印连接信息
            await self.adapter.wait_closed() # 等待适配器发出关闭信号
            log.info("Bot: 适配器连接循环已结束。")
        except asyncio.CancelledError: log.info("Bot 启动/运行任务被取消。"); await self.adapter.stop()
        except Exception as e: log.critical(f"Bot 启动或运行时发生致命错误: {e}", exc_info=True); await self.adapter.stop()
        finally: self._running = False; log.info("Bot start 方法执行完毕或异常退出。")

    async def stop(self):
        """请求 Bot 停止运行"""
        log.info("收到停止 Bot 的请求...")
        # 直接请求适配器停止其循环和连接
        await self.adapter.stop()

    @asynccontextmanager
    async def lifespan(self):
        """异步上下文管理器，管理 Bot 启动和停止"""
        if self._running: raise RuntimeError("Bot is already running via another context or start().")
        log.debug("进入 Bot lifespan 上下文")
        # 在后台启动 start 任务
        start_task = asyncio.create_task(self.start(), name="BotLifespanStart")
        try:
            await asyncio.sleep(0.1)
            yield self
        finally:
            log.info("退出 Bot lifespan 上下文，开始停止...")
            await self.stop()
            if not start_task.done():
                 start_task.cancel()
                 with suppress(asyncio.CancelledError): await start_task
            log.info("Bot lifespan 清理完毕。")

    #事件注册
    def on_event(self, rule: Optional[EventMatcherRule] = None, priority: Optional[int] = 50) -> Callable[[EventHandler], EventHandler]:
        """注册事件处理器的装饰器"""
        actual_rule = rule if rule is not None else lambda event: True
        def decorator(func: EventHandler) -> EventHandler:
            self.dispatcher.add_handler(func, actual_rule, priority)
            return func
        return decorator

    def on_command(self, command: str, priority: Optional[int] = 50) -> Callable[[EventHandler], EventHandler]:
        """注册命令处理器的装饰器"""
        if not self.command_prefixes:
             log.warning(f"注册命令 '{command}' 但未配置任何命令前缀，此处理器可能永远不会被触发。")
        def command_rule(event: BaseEvent) -> Optional[Dict[str, Any]]:
            if not isinstance(event, BaseMessageEvent): return None
            msg = event.raw_message.strip(); matched_prefix = None
            for prefix in self.command_prefixes:
                if msg.startswith(prefix): matched_prefix = prefix; break
            if not matched_prefix: return None
            content = msg[len(matched_prefix):].lstrip(); parts = content.split(maxsplit=1)
            cmd = parts[0]; args = parts[1] if len(parts) > 1 else ""
            if cmd == command: return {"rule_type": "command", "command": command, "args": args}
            return None
        return self.on_event(rule=command_rule, priority=priority)

    #息发送
    def _prepare_message_param(self, message: SendMessage) -> ActionMessage:
        """内部辅助函数，转换消息格式"""
        if isinstance(message, str): return message
        elif isinstance(message, BaseSegment): return [message.model_dump(mode='json', by_alias=True)]
        elif isinstance(message, list):
            try: return MessageChain(message).export() # 使用 MessageChain 处理列表
            except Exception as e: raise TypeError(f"处理消息列表失败: {e}") from e
        else: raise TypeError(f"不支持的消息类型: {type(message)}")

    async def send_private_msg(self, user_id: int, message: SendMessage, auto_escape: bool = False, **kwargs) -> BaseResponse:
        """发送私聊消息"""
        api_message = self._prepare_message_param(message)
        return await self.api.send_private_msg(user_id, api_message, auto_escape, **kwargs)

    async def send_group_msg(self, group_id: int, message: SendMessage, auto_escape: bool = False, **kwargs) -> BaseResponse:
        """发送群聊消息"""
        api_message = self._prepare_message_param(message)
        return await self.api.send_group_msg(group_id, api_message, auto_escape, **kwargs)

    async def send(self, event: BaseEvent, message: SendMessage, **kwargs) -> Optional[BaseResponse]:
        """便捷的发送消息方法，根据事件上下文自动回复"""
        if isinstance(event, PrivateMessageEvent):
            return await self.send_private_msg(user_id=event.user_id, message=message, **kwargs)
        elif isinstance(event, GroupMessageEvent):
            return await self.send_group_msg(group_id=event.group_id, message=message, **kwargs)
        else:
            log.warning(f"便捷发送方法不支持回复此事件类型: {type(event).__name__}")
            return None

    async def call_action(self, action_name: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> BaseResponse:
        return await self.api.call_action(action_name, params, **kwargs)

    async def get_login_info(self, **kwargs) -> GetLoginInfoResponseData:
        return await self.api.get_login_info(**kwargs)

    async def delete_msg(self, message_id: int, **kwargs) -> BaseResponse:
        return await self.api.delete_msg(message_id, **kwargs)

    async def set_friend_add_request(self, flag: str, approve: bool = True, remark: Optional[str] = None, **kwargs) -> BaseResponse:
        return await self.api.set_friend_add_request(flag, approve, remark, **kwargs)

    async def set_group_add_request(self, flag: str, sub_type: Literal["add", "invite"], approve: bool = True, reason: Optional[str] = None, **kwargs) -> BaseResponse:
        return await self.api.set_group_add_request(flag, sub_type, approve, reason, **kwargs)

    async def send_poke(self, user_id: Optional[int] = None, group_id: Optional[int] = None, **kwargs) -> BaseResponse:
        return await self.api.send_poke(user_id=user_id, group_id=group_id, **kwargs)

    async def get_friend_list(self, **kwargs) -> List[FriendInfo]:
        return await self.api.get_friend_list(**kwargs)

    async def get_group_list(self, **kwargs) -> List[GroupInfo]:
        return await self.api.get_group_list(**kwargs)

    async def get_group_info(self, group_id: int, no_cache: bool = False, **kwargs) -> GroupInfo:
        return await self.api.get_group_info(group_id, no_cache, **kwargs)

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = False, **kwargs) -> GroupMemberInfo:
        return await self.api.get_group_member_info(group_id, user_id, no_cache, **kwargs)

    async def get_group_member_list(self, group_id: int, **kwargs) -> List[GroupMemberInfo]:
        return await self.api.get_group_member_list(group_id, **kwargs)

    async def set_group_kick(self, group_id: int, user_id: int, reject_add_request: bool = False, **kwargs) -> BaseResponse:
        """踢出群成员"""
        return await self.api.set_group_kick(group_id, user_id, reject_add_request, **kwargs)

    async def set_group_ban(self, group_id: int, user_id: int, duration: int = 1800, **kwargs) -> BaseResponse:
        """禁言群成员 (user_id=0 为全员禁言，需实现端支持)"""
        return await self.api.set_group_ban(group_id, user_id, duration, **kwargs)

    async def set_group_whole_ban(self, group_id: int, enable: bool = True, **kwargs) -> BaseResponse:
        """设置全员禁言状态"""
        return await self.api.set_group_whole_ban(group_id, enable, **kwargs)

    async def set_group_card(self, group_id: int, user_id: int, card: str = "", **kwargs) -> BaseResponse:
        """设置群成员名片"""
        return await self.api.set_group_card(group_id, user_id, card, **kwargs)

    async def set_group_leave(self, group_id: int, is_dismiss: bool = False, **kwargs) -> BaseResponse:
        """退出或解散群聊"""
        return await self.api.set_group_leave(group_id, is_dismiss, **kwargs)

    async def set_group_admin(self, group_id: int, user_id: int, enable: bool = True, **kwargs) -> BaseResponse:
        """设置或取消群管理员"""
        return await self.api.set_group_admin(group_id, user_id, enable, **kwargs)

    async def get_stranger_info(self, user_id: int, no_cache: bool = False, **kwargs) -> StrangerInfo:
        """获取陌生人信息"""
        return await self.api.get_stranger_info(user_id, no_cache, **kwargs)

    async def set_group_anonymous_ban(self, group_id: int, anonymous_flag: str, duration: int = 1800,
                                      **kwargs) -> BaseResponse:
        """禁言群匿名成员 (需实现端支持 flag)"""
        return await self.api.set_group_anonymous_ban(group_id, anonymous_flag, duration, **kwargs)

    async def get_cookies(self, domain: Optional[str] = None, **kwargs) -> str:
        """获取 Cookies"""
        return await self.api.get_cookies(domain, **kwargs)

    async def get_csrf_token(self, **kwargs) -> int:
        """获取 CSRF Token"""
        return await self.api.get_csrf_token(**kwargs)

    async def get_credentials(self, domain: Optional[str] = None, **kwargs) -> CredentialsData:
        """获取 Cookies 和 CSRF Token"""
        return await self.api.get_credentials(domain, **kwargs)

    async def get_record(self, file: str, out_format: str, **kwargs) -> str:
        """
        获取语音文件。

        Args:
            file: 收到的语音文件名 (通常在 'file' 字段)。
            out_format: 期望的输出格式 (mp3, amr, silk 等)。

        Returns:
            str: Base64 编码的语音文件内容或本地文件路径 (取决于实现)。
        """
        result = await self.api.get_record(file, out_format, **kwargs)
        return result.file  # 返回包含路径或 Base64 的 'file' 字段

    async def can_send_record(self, **kwargs) -> bool:
        """检查是否能发送语音"""
        return await self.api.can_send_record(**kwargs)

    async def can_send_image(self, **kwargs) -> bool:
        """检查是否能发送图片"""
        return await self.api.can_send_image(**kwargs)

    async def get_status(self, **kwargs) -> StatusData:
        """获取运行状态"""
        return await self.api.get_status(**kwargs)

    async def get_version_info(self, **kwargs) -> VersionInfo:
        """获取 OneBot 实现版本信息"""
        return await self.api.get_version_info(**kwargs)

    async def upload_group_file(self, group_id: int, file: str, name: str, folder: Optional[str] = None,
                                **kwargs) -> BaseResponse:
        """上传群文件 (file 应为绝对路径)"""
        return await self.api.upload_group_file(group_id, file, name, folder, **kwargs)

    async def delete_group_file(self, group_id: int, file_id: str, busid: int, **kwargs) -> BaseResponse:
        """删除群文件"""
        return await self.api.delete_group_file(group_id, file_id, busid, **kwargs)

    async def create_group_file_folder(self, group_id: int, name: str, parent_id: str = "/", **kwargs) -> BaseResponse:
        """创建群文件文件夹"""
        return await self.api.create_group_file_folder(group_id, name, parent_id, **kwargs)

    async def delete_group_folder(self, group_id: int, folder_id: str, **kwargs) -> BaseResponse:
        """删除群文件文件夹"""
        return await self.api.delete_group_folder(group_id, folder_id, **kwargs)

    async def get_group_file_system_info(self, group_id: int, **kwargs) -> GroupFileSystemInfo:
        """获取群文件系统信息"""
        return await self.api.get_group_file_system_info(group_id, **kwargs)

    async def get_group_root_files(self, group_id: int, **kwargs) -> List[Union[GroupFile, Dict[str, Any]]]:
        """获取群根目录文件列表 (可能包含文件和文件夹字典)"""
        return await self.api.get_group_root_files(group_id, **kwargs)

    async def get_group_file_url(self, group_id: int, file_id: str, busid: int, **kwargs) -> str:
        """获取群文件下载链接 (直接返回 URL 字符串)"""
        result = await self.api.get_group_file_url(group_id, file_id, busid, **kwargs)
        return result.url

    async def make_forward_node(self, user_id: int, nickname: str, content: SendMessage) -> ForwardNode:
        """
        创建一个合并转发节点。

        Args:
            user_id: 发送者 QQ 号。
            nickname: 发送者昵称。
            content: 节点内容 (str, Segment, List[str|Segment])。

        Returns:
            ForwardNode: 可用于合并转发的节点对象。
        """
        api_content = self._prepare_message_param(content)
        node_data = {"user_id": str(user_id), "nickname": nickname, "content": api_content}
        return ForwardNode(data=node_data)

    async def send_group_forward_msg(self, group_id: int, nodes: List[ForwardNode], **kwargs) -> BaseResponse:
        """
        发送合并转发消息 (群聊)。

        Args:
            group_id: 目标群号。
            nodes: 包含 ForwardNode 对象的列表。
                   可以使用 bot.make_forward_node() 来创建节点。
        """
        return await self.api.send_group_forward_msg(group_id, nodes, **kwargs)
