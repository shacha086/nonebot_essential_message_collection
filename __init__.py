from asyncio import Task
import asyncio
from dataclasses import asdict
from dacite import from_dict
import json
from secrets import choice
from typing import List
from pydantic import parse_obj_as
from nonebot.plugin import on_notice, on_command
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import NoticeEvent, GroupMessageEvent
from .utils import *
from .database import *
from .EventDummy.EssenceMessageEvent import EssenceMessageEvent


matcher = on_notice(
    rule=lambda event: event.notice_type == 'essence'
)

@matcher.handle()
async def onEssenceMessageEvent(bot: Bot, event: NoticeEvent):
    event: EssenceMessageEvent = event
    if event.sub_type == 'add':
        try:
            message_dict = await bot.get_msg(message_id=event.message_id)
        except ActionFailed as e:
            if e.info['wording'] == "消息不存在":
                await bot.send_group_msg(group_id=event.group_id, message="出了点小问题, Bot 没有收到这条信息 ;w;")
                return
            else:
                raise e
        message: Message = parse_obj_as(Message, message_dict['message'])
        new_message = Message()
        tasks: List[Task] = []
        images: List[str] = []
        for segment in message:
            if segment.type == 'text':
                new_message.append(segment)
                continue
            
            if segment.type == 'image':
                new_segment = get_downloaded_image_segment(segment)
                new_message.append(new_segment)
                images.append(new_segment.data['file'].removesuffix(".image"))
                tasks.append(asyncio.create_task(download_image_segment(segment)))
                continue
            
            if segment.type == 'face':
                new_message.append(segment)
                continue
            
            if segment.type == 'at':
                card = await get_member_plain_text_name(bot, event.group_id, segment.data["qq"])
                new_message.append(f"@{MessageSegment.text(card)}")
                continue
        
        if tasks:
            await asyncio.wait(tasks)

        ess = Essences(
            message_id = event.message_id,
            group_id = event.group_id,
            operator_id = event.operator_id,
            sender_id = event.sender_id,
            time = event.time,
            message = json.dumps([asdict(i) for i in new_message], ensure_ascii=False)
        )
        with Session() as session:
            session.add(ess)
            if images:
                img = [Pictures(
                    message_id = event.message_id,
                    hash = image
                ) for image in images]
                session.add_all(img)
            session.commit()
        await bot.send_group_msg(group_id=event.group_id, message="🤖检测到新增精华消息, NTBot 已帮您备份")
    elif event.sub_type == 'delete':
        with Session() as session:
            session.query(Essences).filter(Essences.message_id == event.message_id).delete()
            session.query(Pictures).filter(Pictures.message_id == event.message_id).delete()
            session.commit()
        await bot.send_group_msg(group_id=event.group_id, message="🤖检测到移除精华消息, 已处理数据库中的相关信息")


matcher = on_command("来个典")
@matcher.handle()
async def handle_dian(bot: Bot, event: GroupMessageEvent):
    with Session() as session:
        dians = session.query(Essences).filter(Essences.group_id == event.group_id).all()
        if not dians:
            await matcher.finish("你群还没有典 /w\\")
        dian: Dict[str, Any] = choice(dians)
        message: Message = [from_dict(data_class=MessageSegment, data=it) for it in json.loads(dian.message)]  # type: ignore
    await matcher.finish(message)


matcher = on_command("清理图片")
@matcher.handle()
async def handle_clear(bot: Bot, event: GroupMessageEvent):
    del_list: List[Path] = []
    with Session() as session:
        pictures = set([_[0] for _ in session.query(Pictures.hash)])
        for file in Object.image_path().iterdir():
            if file.is_dir():
                continue

            if file.name not in pictures:
                del_list.append(file)
        
    for _ in del_list:
        _.unlink()
    await matcher.finish(f"清理完成！本次清除了{len(del_list)}张图片 .w.")
    

matcher = on_command("info")
@matcher.handle()
async def handle_info(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    at: MessageSegment
    for arg in args:
        if arg.type == 'at':
            at = arg
            break

    if not at:
        await matcher.finish("无法解析")
    identity_list = await get_member_identity(qq=at.data['qq'], group_id=event.group_id, cookie=(await bot.get_cookies(domain="qun.qq.com"))['cookies'])
    member_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
    member_level = member_info
    await matcher.finish(list_)
    
