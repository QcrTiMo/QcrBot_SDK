# QcrBot_SDK/api/typing.py

from typing import TypeVar, Dict, Any, List, Union, Type
from pydantic import BaseModel


T_ParamsModel = TypeVar('T_ParamsModel', bound=BaseModel)


T_ResponseData = TypeVar('T_ResponseData')
ActionMessage = Union[str, List[Dict[str, Any]]]

__all__ = ["T_ParamsModel", "T_ResponseData", "ActionMessage"]