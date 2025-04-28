# QcrBot_SDK/event/typing.py
from typing import Callable, Awaitable, Any, Tuple, Pattern, Type, Optional, \
    Union
from .base import BaseEvent


EventHandler = Callable[[BaseEvent], Awaitable[None]]

EventMatcherRule = Union[
    Type[BaseEvent],
    Tuple[Type[BaseEvent], str],
    str,
    Pattern[str],
    Callable[[BaseEvent], bool]
]

HandlerTuple = Tuple[EventHandler, EventMatcherRule, Optional[int]]