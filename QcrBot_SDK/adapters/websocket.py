# QcrBot_SDK/adapters/websocket.py

import asyncio
import json
import logging
import random
from contextlib import suppress
from typing import Optional, Callable, Awaitable, Dict, Any
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError, InvalidStatusCode, WebSocketException


from ..utils.log import log
from ..utils.exception import ConnectionError as SDKConnectionError

class WebSocketAdapter:
    """
    管理与 OneBot v11 实现端的 WebSocket 连接，并支持自动重连。
    """
    def __init__(
        self,
        url: str,
        access_token: Optional[str] = None,
        reconnect_interval: float = 5.0,
        max_reconnect_attempts: Optional[int] = 10
    ):
        self.url = url
        self.access_token = access_token
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._raw_data_handler: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
        self._running = False
        self._connected = False
        self._connection_task: Optional[asyncio.Task] = None
        self._closed_event = asyncio.Event()
        self._reconnect_interval = reconnect_interval
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_attempts = 0
        self._stop_connecting = False
        self.on_connect: Optional[Callable[[], Awaitable[None]]] = None
        self.on_disconnect: Optional[Callable[[int, str], Awaitable[None]]] = None
        self.on_connect_failed: Optional[Callable[[int], Awaitable[None]]] = None

    def set_raw_data_handler(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        self._raw_data_handler = handler
        log.debug(f"WS 适配器: 原始数据处理器已设置: {handler.__name__ if handler else 'None'}")

    async def start(self):
        """启动适配器，开始连接并保持连接"""
        if self._running:
            log.warning("WS 适配器: 已在运行中。")
            return
        log.info("WS 适配器: 开始启动...")
        self._running = True
        self._stop_connecting = False
        self._reconnect_attempts = 0
        self._connection_task = asyncio.create_task(self._connection_loop())

    async def stop(self):
        """停止适配器，断开连接并不再重连"""
        if not self._running:
            log.warning("WS 适配器: 未在运行中。")
            return
        log.info("WS 适配器: 请求停止...")
        self._running = False
        self._stop_connecting = True
        await self.disconnect()
        if self._connection_task and not self._connection_task.done():
            self._connection_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._connection_task
        log.info("WS 适配器: 已停止。")

    async def _connection_loop(self):
        """主连接循环，负责连接、接收和重连"""
        while self._running:
            try:
                log.info(f"WS 适配器: 第 {self._reconnect_attempts + 1} 次尝试连接...")
                await self._connect_once()
                await self._receive_loop()
                if not self._running: break
                log.info("WS 适配器: 连接已断开，准备重连...")
            except SDKConnectionError as e:
                log.error(f"WS 适配器: 连接失败: {e}")
                if self.on_connect_failed:
                     asyncio.create_task(self.on_connect_failed(self._reconnect_attempts + 1))

            except asyncio.CancelledError:
                 log.info("WS 适配器: 连接循环被取消。")
                 break
            except Exception as e:
                 log.critical(f"WS 适配器: 连接循环发生未知严重错误: {e}", exc_info=True)

            if not self._running: break

            self._reconnect_attempts += 1
            if self._max_reconnect_attempts is not None and self._reconnect_attempts >= self._max_reconnect_attempts:
                log.error(f"WS 适配器: 已达到最大重连次数 ({self._max_reconnect_attempts})，放弃连接。")
                self._running = False
                break

            delay = min(self._reconnect_interval * (2 ** (self._reconnect_attempts - 1)), 60)
            delay += random.uniform(0, delay * 0.1)
            log.info(f"WS 适配器: {delay:.2f} 秒后进行第 {self._reconnect_attempts + 1} 次重连...")

            try:
                await asyncio.wait_for(asyncio.sleep(delay), timeout=delay + 1)
            except asyncio.CancelledError:
                 log.info("WS 适配器: 重连等待被取消。")
                 break
            except asyncio.TimeoutError:
                 pass

            if self._stop_connecting:
                 log.info("WS 适配器: 检测到停止信号，取消重连。")
                 break

        log.info("WS 适配器: 连接循环已退出。")
        self._connected = False
        self._closed_event.set()

    async def _connect_once(self):
        """尝试进行一次 WebSocket 连接"""
        headers = {}
        if self.access_token: headers["Authorization"] = f"Bearer {self.access_token}"
        try:
            connect_timeout = max(self._reconnect_interval, 10.0)
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self.url, extra_headers=headers, ping_interval=20, ping_timeout=20
                ),
                timeout=connect_timeout
            )
            self._connected = True
            self._reconnect_attempts = 0
            log.info("WS 适配器: 连接成功！")
            if self.on_connect:
                asyncio.create_task(self.on_connect())
        except asyncio.TimeoutError as e: raise SDKConnectionError(f"连接超时 ({connect_timeout}s)") from e
        except InvalidStatusCode as e: raise SDKConnectionError(f"无效状态码: {e.status_code}") from e
        except ConnectionRefusedError as e: raise SDKConnectionError("连接被拒绝") from e
        except OSError as e: raise SDKConnectionError(f"网络错误: {e}") from e
        except WebSocketException as e:
            raise SDKConnectionError(f"WebSocket 错误: {e}") from e
        except Exception as e: raise SDKConnectionError(f"未知连接错误: {e}") from e

    async def _receive_loop(self):
        """持续接收消息 (连接成功后由 _connection_loop 调用)"""
        log.debug("WS 适配器: 接收循环已启动。")
        try:
            while self._connected and self.websocket and not self.websocket.closed:
                try:
                    message = await self.websocket.recv()
                    if isinstance(message, str):
                        try:
                            data: Dict[str, Any] = json.loads(message)
                            if self._raw_data_handler: asyncio.create_task(self._raw_data_handler(data))
                            else: log.warning("未设置原始数据处理器，消息被忽略。")
                        except json.JSONDecodeError: log.warning(f"收到无效 JSON: {message[:100]}...")
                        except Exception as e: log.error(f"处理接收字典时出错: {e}", exc_info=True)
                    elif isinstance(message, bytes): log.warning(f"收到二进制消息 (长度 {len(message)})，已忽略。")
                except ConnectionClosedOK:
                    log.info("WS 适配器: 连接由对方正常关闭。")
                    self._connected = False; code = 1000; reason = "Closed OK"
                    break
                except ConnectionClosedError as e:
                    log.error(f"WS 适配器: 连接意外断开: Code={e.code}, Reason='{e.reason}'")
                    self._connected = False; code = e.code; reason = e.reason or ""
                    break
                except asyncio.CancelledError: raise
                except Exception as e:
                    log.error(f"WS 适配器: 接收循环中发生错误: {e}", exc_info=True)
                    await asyncio.sleep(0.1)
            # 循环结束后调用断开连接回调
            if self.on_disconnect:
                # 使用最后获取的 code 和 reason
                asyncio.create_task(self.on_disconnect(code, reason))
        finally:
             self._connected = False
             log.debug("WS 适配器: 接收循环结束。")


    async def disconnect(self):
        """关闭当前 WebSocket 连接 (不停止重连循环)"""
        log.debug("WS 适配器: 请求断开当前连接...")
        if self.websocket and not self.websocket.closed:
            try: await self.websocket.close(code=1000, reason="Client disconnecting")
            except Exception as e: log.error(f"关闭 WebSocket 时发生错误: {e}", exc_info=True)
        self.websocket = None
        self._connected = False
        log.debug("WS 适配器: 当前连接已关闭。")

    async def send(self, data: str):
        """发送原始字符串数据"""
        if self._connected and self.websocket and self.websocket.open:
            try: await self.websocket.send(data); log.debug(f"WS Sent: {data[:100]}")
            except WebSocketException as e: raise SDKConnectionError(f"发送时 WebSocket 错误: {e}") from e
            except Exception as e: raise SDKConnectionError(f"发送数据失败: {e}") from e
        else: raise SDKConnectionError("WebSocket 未连接，无法发送。")

    async def wait_closed(self):
        """等待连接完全关闭 (重连循环结束)"""
        await self._closed_event.wait()