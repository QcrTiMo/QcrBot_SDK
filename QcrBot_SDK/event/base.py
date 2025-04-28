# QcrBot_SDK/event/base.py
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict

class BaseEvent(BaseModel):
    """OneBot v11 事件基类"""
    time: datetime
    self_id: int
    post_type: str

    model_config = ConfigDict(
        extra='allow',
        populate_by_name=True
    )

    @field_validator('time', mode='before')
    @classmethod
    def format_time(cls, v):
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        return v

    def __str__(self):
        return f"<{self.__class__.__name__} time={self.time} post_type={self.post_type} self_id={self.self_id}>"

    def get_session_id(self) -> str:
        """获取此事件的会话标识符 (子类应重写)"""
        user_id = getattr(self, 'user_id', None)
        group_id = getattr(self, 'group_id', None)
        if group_id:
            return f"group_{group_id}"
        elif user_id:
            return f"private_{user_id}"
        return f"unknown_{self.self_id}"