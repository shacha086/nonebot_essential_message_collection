from ast import operator
from typing import Literal
from nonebot.adapters.onebot.v11.event import NoticeEvent

class EssenceMessageEvent(NoticeEvent):
    time: int
    self_id: int
    post_type: Literal["notice"]
    notice_type: Literal["essence"]
    sub_type: Literal["add", "delete"]
    group_id: int
    sender_id: int
    operator_id: int
    message_id: int
