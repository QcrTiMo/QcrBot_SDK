# QcrBot_SDK/api/client.py
import asyncio
import logging
from typing import Optional, Dict, Any, Union, List, Type, cast, Literal
from pydantic import BaseModel, ValidationError

from ..adapters.websocket import WebSocketAdapter
from .types import T_ParamsModel, T_ResponseData, ActionMessage
from .action import (
    BaseAction, BaseResponse, SendPrivateMsgParams, SendGroupMsgParams, SetFriendAddRequestParams,
    SetGroupAddRequestParams, DeleteMsgParams, SendPokeParams, GetLoginInfoResponseData,
    FriendInfo, GroupInfo, GroupMemberInfo, SetGroupKickParams, SetGroupBanParams, SetGroupWholeBanParams,
    SetGroupCardParams, SetGroupLeaveParams, SetGroupAdminParams, GroupFile, GroupFileSystemInfo,
    GroupFileUrl, UploadGroupFileParams, DeleteGroupFileParams, CreateGroupFileFolderParams,
    DeleteGroupFolderParams, GetGroupFileSystemInfoParams, GetGroupFileUrlParams,
    ForwardNode, SendGroupForwardMsgParams,
    StrangerInfo, CookiesData, CsrfTokenData, CredentialsData, RecordData, StatusData, VersionInfo,
    GetStrangerInfoParams, SetGroupAnonymousBanParams, GetRecordParams
)
from ..utils.exception import ConnectionError as SDKConnectionError, ApiTimeoutError, ActionFailed
from ..utils.log import log


class ApiClient:
    def __init__(self, adapter: WebSocketAdapter): self._adapter = adapter; self._action_futures = {}
    def add_pending_future(self, echo: str, future: asyncio.Future[BaseResponse]): self._action_futures[echo] = future
    def resolve_future(self, echo: str, response: BaseResponse):
        if echo in self._action_futures: future = self._action_futures.pop(echo);
        if not future.done(): future.set_result(response); log.debug(f"Future resolved (echo={echo})")
        else: log.warning(f"Future (echo={echo}) already done when resolving.")
    def reject_future(self, echo: str, exception: Exception):
        if echo in self._action_futures: future = self._action_futures.pop(echo);
        if not future.done(): future.set_exception(exception); log.debug(f"Future rejected (echo={echo})")
        else: log.warning(f"Future (echo={echo}) already done when rejecting.")
    def clear_futures(self, exception: Optional[Exception] = None):
        reason = exception or ConnectionAbortedError("Conn closed"); count = len(self._action_futures)
        if count > 0: log.warning(f"Clearing {count} pending futures: {reason}"); futures_to_clear=list(self._action_futures.items()); self._action_futures.clear(); [fut.set_exception(reason) for _, fut in futures_to_clear if not fut.done()]
    async def call_action( self, action_name: str, params: Optional[Dict[str, Any]] = None, params_model: Optional[Type[T_ParamsModel]] = None, timeout: Optional[float] = 30.0) -> BaseResponse:
        if not self._adapter.websocket or not self._adapter.websocket.open: raise SDKConnectionError("WS not connected")
        if params_model and params:
            try: validated = params_model.model_validate(params); params = validated.model_dump(mode='json', by_alias=True)
            except Exception as e: raise ValueError(f"Action '{action_name}' params invalid: {e}") from e
        req = BaseAction(action=action_name, params=params or {}); echo = req.echo
        fut: asyncio.Future[BaseResponse] = asyncio.get_running_loop().create_future(); self.add_pending_future(echo, fut); log.debug(f"Prep future for '{action_name}' (echo={echo})")
        try:
            await self._adapter.send(req.model_dump_json()); log.info(f"Sent action (echo={echo}): {action_name}"); log.debug(f"Params(echo={echo}): {params}")
            resp = await asyncio.wait_for(fut, timeout=timeout); log.info(f"Got response (echo={echo}): status={resp.status}")
            if not resp.is_success: raise ActionFailed(resp.retcode, resp.error_msg, echo)
            return resp
        except asyncio.TimeoutError: log.error(f"Timeout(echo={echo}, timeout={timeout}s): {action_name}"); self._action_futures.pop(echo, None); raise ApiTimeoutError(echo=echo, timeout=timeout) from None
        except SDKConnectionError as e: log.error(f"Send failed(echo={echo}): {e}"); self._action_futures.pop(echo, None); raise
        except ActionFailed as e: self._action_futures.pop(echo, None); raise
        except Exception as e: log.error(f"Unknown error calling action(echo={echo}): {e}", exc_info=True); self._action_futures.pop(echo, None); raise RuntimeError(f"Failed action {action_name}: {e}") from e
    def _parse_response_data(self, response: BaseResponse, model: Type[T_ResponseData]) -> T_ResponseData:
        if response.data is not None:
            try: return model.model_validate(response.data) # type: ignore
            except ValidationError as e: raise ValueError(f"Invalid data (expected {model.__name__})") from e
        raise ValueError(f"Missing 'data' in response (action echo: {response.echo})")
    def _parse_response_data_list(self, response: BaseResponse, item_model: Type[T_ResponseData]) -> List[T_ResponseData]:
        if isinstance(response.data, list):
            parsed = []; errors = []
            for index, item in enumerate(response.data):
                 try: parsed.append(item_model.model_validate(item)) # type: ignore
                 except ValidationError as e: errors.append(f"Item {index}: {e}"); log.warning(f"List item validation failed ({item_model.__name__}, index={index}): {e}")
            return parsed
        elif response.data is None: return []
        raise ValueError(f"Invalid data format (expected list, got {type(response.data)})")

    async def send_private_msg(self, user_id: int, message: ActionMessage, auto_escape: bool = False, **kwargs) -> BaseResponse: params={"user_id": user_id,"message": message,"auto_escape": auto_escape}; return await self.call_action("send_private_msg",params,SendPrivateMsgParams,**kwargs)
    async def send_group_msg(self, group_id: int, message: ActionMessage, auto_escape: bool = False, **kwargs) -> BaseResponse: params={"group_id": group_id,"message": message,"auto_escape": auto_escape}; return await self.call_action("send_group_msg",params,SendGroupMsgParams,**kwargs)
    async def get_login_info(self, **kwargs) -> GetLoginInfoResponseData: resp=await self.call_action("get_login_info",**kwargs); return self._parse_response_data(resp, GetLoginInfoResponseData)
    async def set_friend_add_request(self, flag: str, approve: bool = True, remark: Optional[str] = None, **kwargs) -> BaseResponse: params={"flag": flag,"approve": approve}; (remark is not None) and params.update({"remark": remark}); return await self.call_action("set_friend_add_request",params,SetFriendAddRequestParams,**kwargs)
    async def set_group_add_request(self, flag: str, sub_type: Literal["add", "invite"], approve: bool = True, reason: Optional[str] = None, **kwargs) -> BaseResponse: params={"flag": flag,"sub_type": sub_type,"approve": approve}; (reason is not None) and params.update({"reason": reason}); return await self.call_action("set_group_add_request",params,SetGroupAddRequestParams,**kwargs)
    async def delete_msg(self, message_id: int, **kwargs) -> BaseResponse: params={"message_id": message_id}; return await self.call_action("delete_msg",params,DeleteMsgParams,**kwargs)
    async def send_poke(self, user_id: Optional[int] = None, group_id: Optional[int] = None, **kwargs) -> BaseResponse:
        params={};
        if group_id is not None and user_id is not None: params={"group_id":group_id,"user_id":user_id}
        elif group_id is not None: params={"group_id":group_id}
        elif user_id is not None: params={"user_id":user_id}
        else: raise ValueError("send_poke 需要 user_id 或 group_id")
        return await self.call_action("send_poke",params,SendPokeParams,**kwargs)
    async def get_friend_list(self, **kwargs) -> List[FriendInfo]: resp=await self.call_action("get_friend_list",**kwargs); return self._parse_response_data_list(resp,FriendInfo)
    async def get_group_list(self, **kwargs) -> List[GroupInfo]: resp=await self.call_action("get_group_list",**kwargs); return self._parse_response_data_list(resp,GroupInfo)
    async def get_group_info(self, group_id: int, no_cache: bool = False, **kwargs) -> GroupInfo: params={"group_id":group_id,"no_cache":no_cache}; resp=await self.call_action("get_group_info",params,**kwargs); return self._parse_response_data(resp,GroupInfo)
    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = False, **kwargs) -> GroupMemberInfo: params={"group_id":group_id,"user_id":user_id,"no_cache":no_cache}; resp=await self.call_action("get_group_member_info",params,**kwargs); return self._parse_response_data(resp,GroupMemberInfo)
    async def get_group_member_list(self, group_id: int, **kwargs) -> List[GroupMemberInfo]: params={"group_id":group_id}; resp=await self.call_action("get_group_member_list",params,**kwargs); return self._parse_response_data_list(resp,GroupMemberInfo)
    async def set_group_kick(self, group_id: int, user_id: int, reject_add_request: bool = False, **kwargs) -> BaseResponse: params={"group_id":group_id,"user_id":user_id,"reject_add_request":reject_add_request}; return await self.call_action("set_group_kick",params,SetGroupKickParams,**kwargs)
    async def set_group_ban(self, group_id: int, user_id: int, duration: int = 1800, **kwargs) -> BaseResponse: params={"group_id":group_id,"user_id":user_id,"duration":duration}; return await self.call_action("set_group_ban",params,SetGroupBanParams,**kwargs)
    async def set_group_whole_ban(self, group_id: int, enable: bool = True, **kwargs) -> BaseResponse: params={"group_id":group_id,"enable":enable}; return await self.call_action("set_group_whole_ban",params,SetGroupWholeBanParams,**kwargs)
    async def set_group_card(self, group_id: int, user_id: int, card: str = "", **kwargs) -> BaseResponse: params={"group_id":group_id,"user_id":user_id,"card":card}; return await self.call_action("set_group_card",params,SetGroupCardParams,**kwargs)
    async def set_group_leave(self, group_id: int, is_dismiss: bool = False, **kwargs) -> BaseResponse: params={"group_id":group_id,"is_dismiss":is_dismiss}; return await self.call_action("set_group_leave",params,SetGroupLeaveParams,**kwargs)
    async def set_group_admin(self, group_id: int, user_id: int, enable: bool = True, **kwargs) -> BaseResponse: params={"group_id":group_id,"user_id":user_id,"enable":enable}; return await self.call_action("set_group_admin",params,SetGroupAdminParams,**kwargs)

    async def get_stranger_info(self, user_id: int, no_cache: bool = False, **kwargs) -> StrangerInfo:
        """获取陌生人信息"""
        params = {"user_id": user_id, "no_cache": no_cache}
        response = await self.call_action("get_stranger_info", params, GetStrangerInfoParams, **kwargs)
        return self._parse_response_data(response, StrangerInfo)

    async def set_group_anonymous_ban(self, group_id: int, anonymous_flag: str, duration: int = 1800,
                                      **kwargs) -> BaseResponse:
        """
        禁言群匿名成员 (需要实现端支持 flag 方式)。
        注意: 参数 'anonymous_flag' 可能需要从匿名消息事件中获取。
        """
        params = {"group_id": group_id, "flag": anonymous_flag, "duration": duration}
        return await self.call_action("set_group_anonymous_ban", params, SetGroupAnonymousBanParams, **kwargs)

    async def get_cookies(self, domain: Optional[str] = None, **kwargs) -> str:
        """获取 Cookies"""
        params = {"domain": domain} if domain else None
        response = await self.call_action("get_cookies", params, **kwargs)
        if isinstance(response.data, dict) and "cookies" in response.data:
            return response.data["cookies"]
        elif isinstance(response.data, str):
            return response.data
        raise ValueError("获取 Cookies 失败或响应格式不正确")

    async def get_csrf_token(self, **kwargs) -> int:
        """获取 CSRF Token (go-cqhttp 扩展)"""
        response = await self.call_action("get_csrf_token", **kwargs)
        if isinstance(response.data, dict) and "token" in response.data and isinstance(response.data["token"], int):
            return response.data["token"]
        raise ValueError("获取 CSRF Token 失败或响应格式不正确")

    async def get_credentials(self, domain: Optional[str] = None, **kwargs) -> CredentialsData:
        """获取 Cookies 和 CSRF Token (go-cqhttp 扩展)"""
        params = {"domain": domain} if domain else None
        response = await self.call_action("get_credentials", params, **kwargs)
        return self._parse_response_data(response, CredentialsData)

    async def get_record(self, file: str, out_format: str, **kwargs) -> RecordData:
        """获取语音文件"""
        params = {"file": file, "out_format": out_format}
        response = await self.call_action("get_record", params, GetRecordParams, **kwargs)
        return self._parse_response_data(response, RecordData)

    async def can_send_record(self, **kwargs) -> bool:
        """检查是否能发送语音"""
        response = await self.call_action("can_send_record", **kwargs)
        if isinstance(response.data, dict) and "yes" in response.data:
            return bool(response.data["yes"])
        log.warning("can_send_record 响应格式不符合预期")
        return False

    async def can_send_image(self, **kwargs) -> bool:
        """检查是否能发送图片"""
        response = await self.call_action("can_send_image", **kwargs)
        if isinstance(response.data, dict) and "yes" in response.data:
            return bool(response.data["yes"])
        log.warning("can_send_image 响应格式不符合预期")
        return False

    async def get_status(self, **kwargs) -> StatusData:
        """获取运行状态"""
        response = await self.call_action("get_status", **kwargs)
        return self._parse_response_data(response, StatusData)

    async def get_version_info(self, **kwargs) -> VersionInfo:
        """获取 OneBot 实现版本信息"""
        response = await self.call_action("get_version_info", **kwargs)
        return self._parse_response_data(response, VersionInfo)

    async def upload_group_file(self, group_id: int, file: str, name: str, folder: Optional[str] = None,
                                **kwargs) -> BaseResponse:
        """上传群文件"""
        # 注意：这里的 file 参数通常需要是绝对路径
        params = {"group_id": group_id, "file": file, "name": name}
        if folder is not None: params["folder"] = folder
        return await self.call_action("upload_group_file", params, UploadGroupFileParams, **kwargs)

    async def delete_group_file(self, group_id: int, file_id: str, busid: int, **kwargs) -> BaseResponse:
        """删除群文件"""
        params = {"group_id": group_id, "file_id": file_id, "busid": busid}
        return await self.call_action("delete_group_file", params, DeleteGroupFileParams, **kwargs)

    async def create_group_file_folder(self, group_id: int, name: str, parent_id: str = "/", **kwargs) -> BaseResponse:
        """创建群文件文件夹"""
        params = {"group_id": group_id, "name": name, "parent_id": parent_id}
        return await self.call_action("create_group_file_folder", params, CreateGroupFileFolderParams, **kwargs)

    async def delete_group_folder(self, group_id: int, folder_id: str, **kwargs) -> BaseResponse:
        """删除群文件文件夹"""
        params = {"group_id": group_id, "folder_id": folder_id}
        return await self.call_action("delete_group_folder", params, DeleteGroupFolderParams, **kwargs)

    async def get_group_file_system_info(self, group_id: int, **kwargs) -> GroupFileSystemInfo:
        """获取群文件系统信息"""
        params = {"group_id": group_id}
        response = await self.call_action("get_group_file_system_info", params, GetGroupFileSystemInfoParams, **kwargs)
        return self._parse_response_data(response, GroupFileSystemInfo)

    async def get_group_root_files(self, group_id: int, **kwargs) -> List[
        Union[GroupFile, Dict[str, Any]]]:  # 返回可能包含文件夹和文件的列表
        """获取群根目录文件列表 (通常实现会返回混合列表)"""
        response = await self.call_action("get_group_root_files", {"group_id": group_id}, **kwargs)
        if isinstance(response.data, list):
            # 由于无法确定是文件还是文件夹，暂时返回原始字典列表
            # TODO: 可以尝试根据字段判断类型并解析
            return response.data
        elif response.data is None:
            return []
        raise ValueError(f"get_group_root_files 响应 data 非列表: {type(response.data)}")

    async def get_group_file_url(self, group_id: int, file_id: str, busid: int, **kwargs) -> GroupFileUrl:
        """获取群文件下载链接"""
        params = {"group_id": group_id, "file_id": file_id, "busid": busid}
        response = await self.call_action("get_group_file_url", params, GetGroupFileUrlParams, **kwargs)
        return self._parse_response_data(response, GroupFileUrl)

    async def send_group_forward_msg(self, group_id: int, messages: List[ForwardNode], **kwargs) -> BaseResponse:
        """发送合并转发消息 (群聊)"""
        if not all(isinstance(node, ForwardNode) for node in messages):
            raise TypeError("messages 参数必须是 ForwardNode 对象的列表")
        # 将节点列表转换为字典列表
        params = {"group_id": group_id, "messages": [node.model_dump(mode='json') for node in messages]}
        return await self.call_action("send_group_forward_msg", params, SendGroupForwardMsgParams, **kwargs)

