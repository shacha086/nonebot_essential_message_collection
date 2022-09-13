import json
from typing import Any, List, Optional
from urllib import parse
from ..Enums import EssenceMessageSegmentType
from pydantic import BaseModel, Field
from nonebot.adapters.onebot.v11 import MessageSegment
import aiohttp
from ..utils import *


class EssenceMessageSegment(BaseModel):
    type: EssenceMessageSegmentType = Field(None, alias='msg_type')
    # _EssenceMessageSegmentType.Text
    text: Optional[str]
    # _EssenceMessageSegmentType.Face
    face_id: Optional[int] = Field(None, alias='face_index')
    face_text: Optional[str]
    # _EssenceMessageSegmentType.Image
    image_url: Optional[str]
    # _EssenceMessageSegmentType.File
    file_name: Optional[str]
    file_bus_id: Optional[int]
    file_id: Optional[str]
    file_size: Optional[str]
    file_type: Optional[str]
    # _EssenceMessageSegmentType.Link
    # 
    # This contains link in text and share link
    share_title: Optional[str]
    share_summary: Optional[str]
    share_brief: Optional[str]
    share_url: Optional[str]
    share_action: Optional[str]
    share_source: Optional[str]
    share_image_url: Optional[str]
    
    url: Optional[str]


class EssenceMessage(BaseModel):
    type: EssenceMessageSegmentType = Field(None, alias='msg_type')
    group_id: str = Field(None, alias='group_code')
    message_id: int = Field(None)
    msg_seq: int
    msg_random: int
    sender_id: str = Field(None, alias='sender_uin')
    sender_nick: str
    sender_time: int
    operator_id: str = Field(None, alias='add_digest_uin')
    operator_nick: str = Field(None, alias='add_digest_nick')
    operator_time: int = Field(None, alias='add_digest_time')
    segments: List[EssenceMessageSegment] = Field(None, alias='msg_content')

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self.message_id = seq_to_global_id(int(self.group_id), self.msg_seq)

    async def to_message(self):
        when = lambda type: self.type == type
        new_message: List[MessageSegment] = []
        if when(EssenceMessageSegmentType.Text):
            for segment in self.segments:
                when = lambda type: segment.type == type
                if when(EssenceMessageSegmentType.Face) and segment.face_id:
                    new_segment = MessageSegment.face(segment.face_id)
                elif when(EssenceMessageSegmentType.Text) and segment.text:
                    new_segment = MessageSegment.text(segment.text)
                elif when(EssenceMessageSegmentType.Link) and segment.url:
                    new_segment = MessageSegment.text(segment.url)
                elif when(EssenceMessageSegmentType.Image) and segment.image_url:
                    hash = f"{segment.image_url.split('/')[-1].split('.')[0]}.image"
                    new_segment = MessageSegment('image', data={'url': segment.image_url, 'file': hash})
                else:
                    raise Exception("Unknown Segment.")
                new_message.append(new_segment)
        elif when(EssenceMessageSegmentType.File):
            # MessageType为File, 仅可能为上传的文件，故构造一个不存在的MessageSegment备用
            # 
            segment = self.segments[0]
            if not segment.file_id and segment.file_bus_id:
                raise Exception("Unexcepted state.")
            new_message = [MessageSegment(
                "file", 
                {
                    "group_id": self.group_id, 
                    "file_id": segment.file_id,
                    "busid": segment.file_bus_id
                }
            )]
        elif when(EssenceMessageSegmentType.Link):
            # MessageType为Link, 大概率为转发链接
            segment = self.segments[0]
            if not segment.share_url:
                raise Exception("Unexcepted state.")
            if segment.share_source == 'QQ音乐':
                async with aiohttp.ClientSession() as session:
                    async with session.get(segment.share_url) as resp:
                        html = await resp.text()
                        dom = etree.HTML(html, etree.HTMLParser())
                        song_info = json.loads(''.join(dom.xpath("/html/body/script[1]/text()")[0].split('=')[1:]))
                        new_message = [MessageSegment.music('qq', int(song_info['songList'][0]['id']))]
            elif segment.share_source == '网易云音乐':
                id = parse.parse_qs(parse.urlparse(segment.share_url).query)['id'][0]
                new_message = [MessageSegment.music('163', int(id))]
            else:
                new_message = [MessageSegment.share(url=segment.share_url, title=segment.share_title or "", image=segment.share_image_url)]
        elif when(EssenceMessageSegmentType.Image):
            segment = self.segments[0]
            if not segment.image_url:
                raise Exception("Unexcepted state.")
            hash = f"{segment.image_url.split('/')[-1].split('.')[0]}.image"
            new_message = [MessageSegment('image', data={'url': segment.image_url, 'file': hash})]
        return new_message


async def get_essence_list(group_id: int, cookie: str) -> "List[EssenceMessage]":
    api = f"https://qun.qq.com/essence/index?gc={group_id}"
    ua = "Mozilla/5.0 (Linux; Android 11; Redmi K30 5G Build/RKQ1.200826.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/89.0.4389.72 MQQBrowser/6.2 TBS/046124 Mobile Safari/537.36 V1_AND_SQ_8.8.68_2538_YYB_D A_8086800 QQ/8.8.68.7265 NetType/4G WebP/0.3.0 Pixel/1080 StatusBarHeight/96 SimpleUISwitch/0 QQTheme/2105 InMagicWin/0 StudyMode/0 CurrentMode/0 CurrentFontScale/1.0 GlobalDensityScale/0.9818182 AppId/537112593"
    headers = { "User-Agent": ua }
    cookies = cookies_to_map(cookie)
    async with aiohttp.ClientSession() as session:
        async with session.get(api, headers=headers, cookies=cookies) as resp:
            html = await resp.text()
            dom = etree.HTML(html, etree.HTMLParser())
            message_list = [EssenceMessage(**it) for it in json.loads(dom.xpath("/html/body/script[2]/text()")[0].removeprefix("window.__INITIAL_STATE__="))['msgList']]

            return message_list
