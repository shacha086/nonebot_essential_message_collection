import re
import zlib
import asyncio
import aiohttp
import tinycss2
from PIL import Image
from lxml import etree
from io import BytesIO
from .Enums import Size
from pathlib import Path
from .objects import Object
from tinycss2.ast import QualifiedRule
from nonebot.adapters.onebot.v11.bot import Bot
from typing import Any, Coroutine, Dict, List, Optional, Tuple
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.adapters.onebot.v11.exception import ActionFailed


def check_type(segment: MessageSegment, type: str):
    if segment.type != type:
        raise TypeError(f"This segment's type is not '{type}'!")


def get_image_path(name: str) -> Path:
    return Object.image_path() / name


def is_image_existed(name: str) -> bool:
    return get_image_path(name).exists()

def get_downloaded_image_path(segment: MessageSegment) -> Path:
    check_type(segment, "image")
    return get_image_path(segment.data['file'].removeprefix("file:///").removesuffix(".image"))

def get_downloaded_image_segment(segment: MessageSegment) -> MessageSegment:
    check_type(segment, "image")
    segment = segment.copy()
    hash: str = segment.data['file'].removesuffix(".image")
    path: Path = get_image_path(hash)
    segment.data['url'] = f"file:///{path}"
    return segment


async def download_image_segment(segment: MessageSegment):
    check_type(segment, "image")
    hash: str = segment.data['file'].removesuffix(".image")
    path: Path = get_image_path(hash)
    if not is_image_existed(hash):
        await download_image_to_disk(segment.data['url'], path)


async def download_image_to_disk(url: str, path: Path):
    if path.exists():
        raise Exception("Existed path.")

    path.touch()

    try:
        with open(path, "wb") as f:
            f.write(await download_image(url))
    except Exception as e:
        path.unlink()
        raise e


async def download_image_as_pil_Image(url: str, convert = "RGB") -> Image.Image:
    return Image.open(BytesIO(await download_image(url))).convert(convert)


async def download_image(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.read()


def get_member_name(member: Dict[str, Any]) -> str:
    return member["card"] or member["nickname"]


async def get_member_icon(user_id: int, size: Size = Size.px1080) -> Image.Image:
    url = f"https://q1.qlogo.cn/g?b=qq&s={size.value}&nk={user_id}"
    return await download_image_as_pil_Image(url, convert='RGBA')


async def get_member_plain_text_name(bot: Bot, group_id: int, user_id: int) -> str:
    try:
        return get_member_name(
            await bot.get_group_member_info(
                group_id=group_id, user_id=user_id
            )
        )
    except ActionFailed as e:
        if e.info['wording'] == "群员不存在":
            return str(user_id)
        else: 
            raise e


def cookies_to_map(cookies: str) -> Dict[str, Any]:
    map = {}
    for it in cookies.split("; "):
        if it[-1] == ';':
            it = it[:-1]
        pair = it.split('=')
        map[pair[0]] = "".join(pair[1:])
    return map


def parse_css(css_text: str) -> Dict[str, Dict[str, str]]:
    css = tinycss2.parse_stylesheet(css_text)
    result: Dict[str, Dict[str, str]] = {}
    for node in css:
        if node.type == 'whitespace':
            continue
        
        if node.type == 'comment':
            continue

        if node.type == 'qualified-rule':
            node: QualifiedRule
            pre = ""
            for prelude in node.prelude:
                pre += prelude.serialize().replace('\n', ' ')

            pre = pre.strip()

            content_map = {}
            
            key = ""; value = ""
            mode = 'key'

            for content in node.content:
                if content.type == 'whitespace' and mode == 'key':
                    continue
                
                val = ""

                if content.type == 'function':
                    stringify = f"{content.name}("
                    for arg in content.arguments:
                        stringify += str(arg.value)
                    stringify += ")"
                    val = stringify
                elif content.type == 'hash':
                    val = f"#{content.value}"
                elif content.type == 'literal':
                    if content.value == ':':
                        #  handle (key, value) pair
                        ignore_space = True
                        mode = 'value'
                        continue
                        ...
                    
                    if content.value == ';':
                        #  handle end of compression
                        content_map[key] = value.strip()
                        key = ""; value = ""
                        mode = "key"
                        continue
                        ...

                if mode == "key":
                    key += str(val or content.value)
                    continue
                elif mode == "value":
                    value += str(val or content.value)
                    continue
                else:
                    raise Exception("Unexcepted State.")
            
            result[pre] = content_map

    return result


async def wrap(func: Coroutine, **kwargs):
    if 'result' in kwargs.keys():
        raise Exception("Can't use keyword 'result'.")
    _ = kwargs.copy()
    _['result'] = await func
    return _


def seq_to_global_id(code: int, msg_id: int) -> int:
    return zlib.crc32(bytes(f"{code}-{msg_id}", 'utf8'))


async def get_cookie(bot: Bot, domain: str = "") -> str:
    return (await bot.get_cookies(domain=domain))['cookies']


async def get_member_identity(qq: int, group_id: int, cookie: str) -> List[Image.Image]:
    api = rf"https://qun.qq.com/interactive/userhonor?uin={qq}&gc={group_id}&_wv=3&&_wwv=128"
    ua = "Mozilla/5.0 (Linux; Android 11; Redmi K30 5G Build/RKQ1.200826.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/89.0.4389.72 MQQBrowser/6.2 TBS/046124 Mobile Safari/537.36 V1_AND_SQ_8.8.68_2538_YYB_D A_8086800 QQ/8.8.68.7265 NetType/4G WebP/0.3.0 Pixel/1080 StatusBarHeight/96 SimpleUISwitch/0 QQTheme/2105 InMagicWin/0 StudyMode/0 CurrentMode/0 CurrentFontScale/1.0 GlobalDensityScale/0.9818182 AppId/537112593"
    headers = { "User-Agent": ua }
    cookies=cookies_to_map(cookie)
    cookies['qq_locale_id'] = 2052
    async with aiohttp.ClientSession() as session:
        async with session.get(api, headers=headers, cookies=cookies) as resp:
            html = await resp.text()
            dom = etree.HTML(html, etree.HTMLParser())
            css_link = dom.xpath("/html/body/link[@rel='stylesheet']/@href")[0]
            async with session.get(css_link, headers=headers, cookies=cookies) as css_resp:
                css = parse_css(await css_resp.text())
                elements = dom.xpath("//div[@class='row']/div[1]/div[@class='icon']")
                image_list: List[Optional[Image.Image]] = [None] * len(elements)
                tasks = []
                for index, element in enumerate(elements):
                    class_name = element.getchildren()[0].attrib['class'].replace("image ", ".")
                    resource_url = css[class_name]['background-image']
                    task = asyncio.create_task(
                        wrap(func=download_image_as_pil_Image(resource_url, convert='RGBA'), index=index)
                    )
                    def _(context):
                        if e := context.exception():
                            raise e
                        result = context.result()
                        image_list[result['index']]=result['result']
                    task.add_done_callback(_)
                    tasks.append(task)

                await asyncio.wait(tasks)
                if None in image_list:
                    raise Exception("NoneTypeException")
                return image_list


def handle_chinese_char(text: str) -> Tuple[str, Optional[Dict[str, str]]]:
    new_text = ""
    changes_dict: Dict[str, str] = {}
    chinese = re.findall(r'[^\x00-\xff]', text)
    if not chinese:
        return (text, None)
    for char in text:
        if char in chinese:
            changes_dict[char * 2] = char
            new_text += char * 2
        else:
            new_text += char
    return (new_text, changes_dict)


def revert_chinese_char(pair: Tuple[str, Optional[Dict[str, str]]]) -> str:
    text, map = pair

    if not map:
        return text
    
    new_text = text
    for changed, original in map.items():
        new_text = new_text.replace(changed, original)
    
    return new_text


def revert_listed_chinese_char(pair: Tuple[List[str], Optional[Dict[str, str]]]) -> List[str]:
    text_list, map = pair

    if not map:
        return text_list

    last_text = " "
    new_list = []
    for text in [revert_chinese_char((it, map)) for it in text_list]:
        if text[0] == last_text[-1]:
            new_text = ''.join(text[1:])
        else:
            new_text = text
        
        last_text = new_text
        new_list.append(new_text)
    
    return new_list


def crop_margin(image: Image.Image, crops: Tuple[bool, bool, bool, bool]=(True, True, True, True), padding: Tuple[int, int, int, int]=(0, 0, 0, 0)):
    bbox = image.getbbox()
    left = bbox[0] - padding[0]
    top = bbox[1] - padding[1]
    right = bbox[2] + padding[2]
    bottom = bbox[3] + padding[3]
    return image.crop([left, top, right, bottom])

