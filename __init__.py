import base64
import hashlib
from asyncio import Task
from dataclasses import asdict
from json import JSONDecodeError

import nonebot.config
import pyzbar.pyzbar
from aiohttp import FormData
from dacite import from_dict
from secrets import choice
from typing import Union

from nonebot.internal.params import Arg, ArgPlainText

from .Text2Image import Text2Image
from pydantic import parse_obj_as
from nonebot.plugin import on_notice, on_command
from nonebot.adapters.onebot.v11.message import Message as v11Message, Message
from nonebot.adapters.onebot.v11.event import NoticeEvent, GroupMessageEvent
from .utils import *
from .database import *
from ninepatch import Ninepatch
from .EventDummy.EssenceMessageEvent import EssenceMessageEvent
from .Message.EssenceMessage import *


async def add_essence_message(bot: Bot, message_id: int, group_id: int, operator_id: int, sender_id: int, time: int,
                              message: Union[v11Message, List[MessageSegment]]):
    new_message = v11Message()
    tasks: List[Task] = []
    images: List[str] = []
    for segment in message:
        if segment.type == 'text':
            new_message.append(segment)
            continue
        elif segment.type == 'image':
            new_segment = get_downloaded_image_segment(segment)
            new_message.append(new_segment)
            images.append(new_segment.data['file'].removesuffix(".image"))
            tasks.append(asyncio.create_task(
                download_image_segment(segment)))
            continue
        elif segment.type == 'face':
            new_message.append(segment)
            continue
        elif segment.type == 'at':
            card = await get_member_plain_text_name(bot, group_id, segment.data["qq"])
            new_message.append(MessageSegment.text(f"@{card}"))
            continue
        elif segment.type == 'share':
            # TODO
            new_message.append(MessageSegment.text(f"#TODO\n[SHARE]{segment.data['url']}"))
            continue
        elif segment.type == 'file':
            # TODO
            new_message.append(MessageSegment.text(f"#TODO\n[FILE]{segment.data['file_id']}"))
            continue
        elif segment.type == 'music':
            # TODO
            new_message.append(MessageSegment.text(f"#TODO\n[{segment.data['type']}_music] {segment.data['id']}"))
        else:
            raise Exception("Unexcepted state.")
    if tasks:
        await asyncio.wait(tasks)

    if not new_message:
        return

    ess = Essences(
        message_id=message_id,
        group_id=group_id,
        operator_id=operator_id,
        sender_id=sender_id,
        time=time,
        message=json.dumps([asdict(i)
                            for i in new_message], ensure_ascii=False)
    )
    with Session() as session:
        session.add(ess)
        if images:
            img = [Pictures(
                message_id=message_id,
                hash=image
            ) for image in images]
            session.add_all(img)
        session.commit()


matcher = on_notice(
    rule=lambda event: event.notice_type == 'essence'
)


async def sync_to_telegram(bot: Bot, event: EssenceMessageEvent, message: v11Message, group: Groups):
    buffer = BytesIO()
    canvas = await render_message(bot, event.sender_id, event.group_id, message)
    canvas.save(buffer, "png")
    headers = {
        "Authorization": f"Bearer {group.token}"
    }
    async with aiohttp.ClientSession(headers=headers) as aiosession:
        data = FormData()
        data.add_field('data', buffer.getvalue())
        return await aiosession.post("http://127.0.0.1:8081/haruka/post_photo",
                                     params={'chat_id': group.tg_chat_id},
                                     data=data)


@matcher.handle()
async def onEssenceMessageEvent(bot: Bot, event: NoticeEvent):
    event: EssenceMessageEvent = event

    if event.sub_type == 'add':
        try:
            message_dict = await bot.get_msg(message_id=event.message_id)
            message: v11Message = parse_obj_as(v11Message, message_dict['message'])
            await add_essence_message(bot, event.message_id, event.group_id, event.operator_id, event.sender_id,
                                      event.time, message)
        except ActionFailed as e:
            if e.info['wording'] == "消息不存在":
                await bot.send_group_msg(group_id=event.group_id, message="出了点小问题, Bot 没有收到这条信息 ;w;")
                return
            else:
                raise e
        with Session() as session:
            if group := session.query(Groups).filter(Groups.qq_group_id == event.group_id).first():
                result = await sync_to_telegram(bot, event, message, group)
                if not result.ok:
                    await matcher.send(f"警告：上传至TG时出错\n{result}")

        await bot.send_group_msg(group_id=event.group_id, message="🤖检测到新增精华消息, NTBot 已帮您备份")
    elif event.sub_type == 'delete':
        with Session() as session:
            session.query(Essences).filter(
                Essences.message_id == event.message_id).delete()
            session.query(Pictures).filter(
                Pictures.message_id == event.message_id).delete()
            session.commit()
        await bot.send_group_msg(group_id=event.group_id, message="🤖检测到移除精华消息, 已处理数据库中的相关信息")


matcher = on_command("deep_sync")


@matcher.handle()
async def handle_deep_sync(bot: Bot, event: GroupMessageEvent):
    if event.sender.role not in ['owner', 'admin', 'superuser'] :
        await matcher.finish("这个操作只有管理员及以上才能完成！")

    with Session() as session:
        session.query(Essences).filter(
            Essences.group_id == event.group_id).delete()
        session.commit()

    await handle_sync(bot, event)


matcher = on_command("同步精华消息")


@matcher.handle()
async def handle_sync(bot: Bot, event: GroupMessageEvent):
    essence_list: List[EssenceMessage] = await get_essence_list(group_id=event.group_id,
                                                                cookie=await get_cookie(bot, domain="qun.qq.com"))
    with Session() as session:
        saved_essence: List[Tuple[int, int]] = session.query(Essences.group_id, Essences.message_id).all() or []
    if not essence_list or saved_essence:
        await matcher.finish("没有新增的精华消息🤔")
    count = 0
    task: List[Task] = []
    for essence in essence_list:
        if (event.group_id, essence.message_id) not in saved_essence:
            task.append(asyncio.create_task(add_essence_message(
                bot,
                essence.message_id,
                event.group_id,
                int(essence.operator_id),
                int(essence.sender_id),
                essence.sender_time,
                await essence.to_message()
            )))
            count += 1
    if task:
        await asyncio.wait(task)
    await matcher.finish(f"同步完成，新增了{count}条消息")


matcher = on_command("来个典", aliases={"爆个典", "爆典", "典"})


@matcher.handle()
async def handle_dian(bot: Bot, event: GroupMessageEvent):
    with Session() as session:
        dians: List[Essences] = session.query(Essences).filter(
            Essences.group_id == event.group_id
        ).all()
        if not dians:
            await matcher.finish("你群还没有典 /w\\")
        dian: Essences = choice(dians)
        message: v11Message = [from_dict(data_class=MessageSegment, data=it)
                               for it in json.loads(dian.message)]  # type: ignore
        canvas = await render_message(bot, dian.sender_id, dian.group_id, message)

        buffer = BytesIO()
        canvas.save(buffer, 'png')
    try:
        await matcher.send(MessageSegment.image(buffer))
    except:
        await matcher.finish("出错了")


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


matcher = on_command("unbind")


@matcher.got("confirm", prompt="此操作将重置本群绑定的TG频道。是否确定？（是/否）")
async def handle_unbind(bot: Bot, event: GroupMessageEvent, confirm = ArgPlainText("confirm")):
    if confirm.strip() != "是":
        await matcher.finish("操作已取消。")
    if (event.sender.role not in ['owner', 'admin']) and (str(event.sender.user_id) not in nonebot.get_driver().config.superusers):
        await matcher.finish("这个操作只有管理员及以上才能完成！")

    with Session() as session:
        session.query(Groups).filter(Groups.qq_group_id == event.group_id).delete()
        session.commit()

    await matcher.finish("操作已完成。")

matcher = on_command("bind")


@matcher.got("qrcode", prompt="请在群聊中发送绑定的二维码")
async def handle_bind(bot: Bot, event: GroupMessageEvent, qr_code: v11Message = Arg("qrcode")):
    with Session() as session:
        if session.query(Groups.qq_group_id).filter(Groups.qq_group_id == event.group_id).all():
            await matcher.finish("这个群已经绑定过了")
    if qr_code[0].type != 'image':
        await matcher.reject("无效的二维码")
    image = await download_image_as_pil_Image(qr_code[0].data['url'])
    qr = pyzbar.pyzbar.decode(image)
    if len(qr) > 1:
        await matcher.reject("检测到了多个二维码，试试裁剪后重新发送？")
    qr = qr[0]
    try:
        data = json.loads(base64.b64decode(qr.data))

        with Session() as session:
            session.add(
                Groups(
                    qq_group_id=event.group_id,
                    tg_chat_id=data['group_id'],
                    token=data['token']
                )
            )
            session.commit()
        await matcher.finish("绑定成功！")
    except JSONDecodeError as e:
        await matcher.reject("无效的二维码")


async def render_message(bot: Bot, user_id: int, group_id: int, message: v11Message) -> Image.Image:
    ROOT = Path(__file__).parent / "resources"
    font = ROOT / "MILanPro_Regular.ttf"
    emoji_font = ROOT / "AppleColorEmoji.ttf"

    tasks = []
    new_message = []

    for segment in message:
        if segment.type == 'image':
            new_segment = get_downloaded_image_segment(segment)
            new_message.append(new_segment)
            tasks.append(asyncio.create_task(
                download_image_segment(segment)))
            continue
        new_message.append(segment)

    if tasks:
        await asyncio.wait(tasks)

    if len(new_message) == 1 and new_message[0].type == 'image':
        return Image.open(get_downloaded_image_path(new_message[0])).convert("RGBA")

    img = await Text2Image.from_message(  # type: ignore
        message=new_message,
        font_path=str(font),
        emoji_font_path=str(emoji_font),
        font_size=49,
        emoji_scale=1,
        emoji_padding=8,
        qq_face_padding=-5,
        # font_size=get_emoji_bitmap_size(gb_2312),
        width_limit=675,
        embedded_color=True,
        bot=bot,
        group_id=group_id,
        autosize=True
    )
    bubble_path = Path(__file__).parent / 'resources' / 'bubble.9.png'
    bubble = Ninepatch(bubble_path)
    bubble_image = bubble.render_wrap(img)

    user_name = get_member_plain_text_name(bot, group_id, user_id)
    user_icon = get_member_icon(user_id, size=Size.px100)
    identities = get_member_identity(user_id, group_id, await get_cookie(bot, domain="qun.qq.com"))
    canvas = Text2Image.combine_message_image(bubble_image, await user_icon, await user_name,
                                              await identities)  # type: ignore
    return canvas
    # buffer = BytesIO()
    # canvas.save(buffer, 'png')
    # await matcher.finish(MessageSegment.image(buffer))

# matcher = on_command("test")
# @matcher.handle()
# async def _(bot: Bot, event: GroupMessageEvent):
#     with Session() as session:
#         dians: List[Essences] = session.query(Essences).filter(
#             Essences.group_id == event.group_id
#         ).all()
#         if not dians:
#             await matcher.finish("你群还没有典 /w\\")
#         for dian in dians:
#             message: v11Message = [from_dict(data_class=MessageSegment, data=it)
#                                 for it in json.loads(dian.message)]  # type: ignore
#             canvas = await render_message(bot, dian.sender_id, dian.group_id, message)

#             buffer = BytesIO()
#             canvas.save(buffer, 'png')
#             await matcher.send(MessageSegment.image(buffer))
