# QcrBot_SDK/core/dispatcher.py
import asyncio
import logging
import re
import inspect
from typing import List, Callable, Awaitable, Optional, Pattern, Type, Union, Tuple, Dict, Any
from pydantic import BaseModel
from ..event.base import BaseEvent
from ..event.models import BaseMessageEvent, PrivateMessageEvent, GroupMessageEvent
from ..event.typing import EventHandler, EventMatcherRule, HandlerTuple
from ..utils.log import log

class EventDispatcher:
    """
    负责管理和分发事件给匹配规则的处理器。
    支持按事件类型、命令前缀、正则表达式等规则进行匹配。
    能够将匹配结果 (如命令参数) 注入到处理器函数参数中。
    """
    def __init__(self):
        # 存储处理器及其规则和优先级
        self._handlers: List[HandlerTuple] = []

    def add_handler(self, handler: EventHandler, rule: EventMatcherRule, priority: Optional[int] = 50):
        if not asyncio.iscoroutinefunction(handler):
            raise TypeError(f"事件处理器 {handler.__name__} 必须是 async 函数")
        self._handlers.append((handler, rule, priority))
        self._handlers.sort(key=lambda x: x[2] if x[2] is not None else 50)
        log.info(f"事件分发器: 已注册处理器 {handler.__name__} (规则: {rule}, 优先级: {priority})")

    def remove_handler(self, handler: EventHandler):
        initial_len = len(self._handlers)
        self._handlers = [h for h in self._handlers if h[0] != handler]
        removed_count = initial_len - len(self._handlers)
        if removed_count > 0:
            log.info(f"事件分发器: 已移除处理器 {handler.__name__} 的 {removed_count} 条规则。")
        else:
            log.warning(f"事件分发器: 尝试移除未注册的处理器 {handler.__name__}")

    def match(self, event: BaseEvent, rule: EventMatcherRule) -> Optional[Dict[str, Any]]:
        if isinstance(rule, type) and issubclass(rule, BaseEvent):
            return {} if isinstance(event, rule) else None
        elif isinstance(rule, tuple) and len(rule) == 2 and isinstance(rule[0], type) and issubclass(rule[0], BaseEvent) and isinstance(rule[1], str):
             event_type, sub_type = rule
             return {} if isinstance(event, event_type) and getattr(event, 'sub_type', None) == sub_type else None
        elif isinstance(rule, str):
             if isinstance(event, BaseMessageEvent):
                 raw_msg = event.raw_message.strip()
                 if raw_msg.startswith(rule):
                     args = raw_msg[len(rule):].strip()
                     return {"rule_type": "prefix", "prefix": rule, "args": args}
             return None
        elif isinstance(rule, Pattern):
             if isinstance(event, BaseMessageEvent):
                 match = rule.search(event.raw_message)
                 return {"rule_type": "regex", "match": match} if match else None
             return None
        elif callable(rule):
             try:
                 result = rule(event)
                 if isinstance(result, dict):
                     if "rule_type" not in result: result["rule_type"] = "callable"
                     return result
                 elif result: # bool True
                     return {"rule_type": "callable"}
                 else:
                     return None
             except Exception as e:
                 log.error(f"执行自定义匹配规则函数 {rule.__name__} 时出错: {e}", exc_info=True)
                 return None
        else:
            log.warning(f"不支持的事件匹配规则类型: {type(rule)}")
            return None


    async def dispatch(self, event: BaseEvent):
        """
        将事件按优先级分发给第一个匹配规则的处理器。
        尝试将匹配结果注入到处理器的参数中。
        """
        log.debug(f"事件分发器: 收到事件 {type(event).__name__}，开始匹配处理器...")
        for handler, rule, priority in self._handlers:
            match_result = self.match(event, rule)

            if match_result is not None:
                log.info(f"事件分发器: 事件匹配成功 -> 处理器 {handler.__name__} (规则: {rule}, 优先级: {priority})")
                log.debug(f"匹配结果: {match_result}")


                handler_signature = inspect.signature(handler)
                handler_params = handler_signature.parameters

                # 准备传递给处理器的参数
                call_args = {}
                provided_params = set() # 记录已经提供的参数名

                # 1. 优先注入事件本身
                for name, param in handler_params.items():
                    # 如果参数类型是 BaseEvent 或其子类，注入事件对象
                    if isinstance(param.annotation, type) and issubclass(param.annotation, BaseEvent) and isinstance(event, param.annotation):
                        call_args[name] = event
                        provided_params.add(name)
                        break # 通常只有一个事件参数
                    # 如果没有类型注解但参数名为 'event' (或其他约定名称)，也注入
                    elif param.annotation == inspect.Parameter.empty and name == "event":
                         call_args[name] = event
                         provided_params.add(name)
                         break

                # 如果连 event 参数都没有，但函数需要参数，可能无法调用
                if not call_args and handler_params:
                     first_param = next(iter(handler_params.values()))
                     if first_param.default == inspect.Parameter.empty: # 检查第一个参数是否有默认值
                        log.warning(f"处理器 {handler.__name__} 需要参数，但无法确定如何注入 'event' 对象。")
                        # 可以选择跳过或尝试调用 (如果参数有默认值)
                        # continue

                # 2. 尝试注入匹配结果中的数据
                for name, param in handler_params.items():
                    if name in provided_params: # 跳过已经注入的 event
                        continue
                    if name in match_result:
                        expected_type = param.annotation
                        value = match_result[name]
                        # 简单类型检查
                        if expected_type != inspect.Parameter.empty and not isinstance(value, expected_type):
                             try:
                                 if expected_type is int: value = int(value)
                                 elif expected_type is float: value = float(value)
                                 elif isinstance(expected_type, type) and issubclass(expected_type, BaseModel):
                                     value = expected_type.model_validate(value)

                                 # 检查转换后的类型
                                 if not isinstance(value, expected_type):
                                     log.warning(f"处理器 {handler.__name__} 参数 '{name}' 类型不匹配: "
                                                 f"期望 {expected_type}, 得到 {type(value)} (来自匹配结果)，无法自动转换。")
                                     continue
                             except Exception as convert_err:
                                 log.warning(f"处理器 {handler.__name__} 参数 '{name}' 自动类型转换失败: {convert_err}")
                                 continue

                        call_args[name] = value
                        provided_params.add(name)

                # 检查是否所有必需参数都已提供
                missing_params = []
                for name, param in handler_params.items():
                    if name not in provided_params and param.default == inspect.Parameter.empty:
                         missing_params.append(name)

                if missing_params:
                    log.error(f"无法调用处理器 {handler.__name__}: 缺少必需参数 {missing_params}。")
                    continue # 跳过这个处理器

                try:
                    log.debug(f"调用处理器 {handler.__name__}，参数: {list(call_args.keys())}")
                    await handler(**call_args)
                    log.debug(f"处理器 {handler.__name__} 执行完毕。")
                    return
                except Exception as e:
                    log.error(f"事件分发器: 执行处理器 {handler.__name__} 时发生错误: {e}", exc_info=True)
                    return

        log.debug(f"事件分发器: 没有找到匹配事件 {type(event).__name__} 的处理器。")