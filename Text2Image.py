import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional, Union
from ninepatch import Ninepatch
from PIL import ImageDraw, ImageFont, Image
from .emoji_utils import get_emoji_bitmap_size, is_emoji_strict
from nonebot.adapters.onebot.v11 import Message, MessageSegment, Bot
from .utils import crop_margin, get_member_plain_text_name, get_downloaded_image_path
from .objects import Object

ROOT = Path(__file__).parent / "resources"
ROOT.mkdir(parents=True, exist_ok=True)
font = ROOT / "MILanPro_Regular.ttf"
emoji_font = ROOT / "AppleColorEmoji.ttf"


def combine_img(*imgs: Image.Image):
    width_limit = max([i.width for i in imgs])
    height_limit = sum([i.height for i in imgs]) + len(imgs) * 2
    img = Image.new("RGBA", (width_limit, height_limit), color=None)
    y = 0
    for i in imgs:
        img.alpha_composite(i, (0, y))
        y += i.height + 2
    # return img
    return crop_margin(img)


class Text2Image:
    @staticmethod
    def from_text(
        text: Union[str, Message, List[Union[MessageSegment, str]]],
        font_path: str,
        emoji_font_path: str,
        emoji_scale: float = 1.0,
        emoji_padding = 0,
        qq_face_padding = 0,
        text_color: str = "black",
        font_size: int = 12,
        width_limit: Optional[int] = None,
        embedded_color=False,
        autosize = False
    ):
        if not text:
            raise Exception("NoneTypeException")

        if not width_limit:
            width_limit = 50000

        if emoji_scale <= 0:
            emoji_scale = 1
            
        fixed_emoji_font_size = get_emoji_bitmap_size(emoji_font_path)
        true_font = ImageFont.truetype(font=font_path, size=font_size)
        emoji_font = ImageFont.truetype(font=emoji_font_path, size=fixed_emoji_font_size)
        def draw_char(char: str, padding=0):
            font = true_font
            _padding = 0
            if isemoji := (isinstance(char, str) and is_emoji_strict(char)):
                _padding = padding
                font = emoji_font
            (_, _, rt, rb) = font.getbbox(char)
            text_overlay = Image.new("RGBA", (rt, int((rb + _padding) * (1 / emoji_scale))), color=None)
            image_draw = ImageDraw.Draw(text_overlay)
            image_draw.text(xy=(0, int(_padding * (1 / emoji_scale))), text=char, fill=text_color, font=font, embedded_color=embedded_color)
            if isemoji:  # return resized image
                resize_scale = font_size / fixed_emoji_font_size
                text_overlay = text_overlay.resize(tuple(int(size * resize_scale * emoji_scale) for size in text_overlay.size), resample=Image.Resampling.BILINEAR)
            return text_overlay

        def draw_qq_face(image_path: Path, autosize=False, padding=0):
            image: Image.Image = Image.open(image_path).convert("RGBA")
            if autosize:
                test_emoji = draw_char('🤔')
                image = image.resize(test_emoji.size, resample=Image.Resampling.BILINEAR) 
            (width, height) = image.size
            if not padding:
                return image
            image_overlay = Image.new("RGBA", (width, int((height + padding) * (1 / emoji_scale))), color=None)
            image_overlay.alpha_composite(image, (0, int(padding * (1 / emoji_scale))))
            return image_overlay

        def draw_image(image: Image.Image, max_size = 350, padding = 15) -> Image.Image:
            image = image.copy()
            ratio = image.width / image.height
            if ratio > (3 / 1):
                image = image.crop((0, 0, image.height * 3, image.height))
            elif ratio < (1 / 3):
                image = image.crop((0, 0, image.width, image.width * 3))

            if max(image.size) > max_size:
                scale = max_size / max(image.size)
                image = image.resize((int(image.width * scale), int(image.height * scale)), resample=Image.Resampling.BILINEAR)

            left_top: Image.Image = Image.open(Object.resources_path() / 'lu.png').convert("L")
            left_bottom: Image.Image = Image.open(Object.resources_path() / 'ld.png').convert("L")
            right_top: Image.Image = Image.open(Object.resources_path() / 'ru.png').convert("L")
            right_bottom: Image.Image = Image.open(Object.resources_path() / 'rd.png').convert("L")

            mask_scale = max_size / 600
            left_top = left_top.resize(tuple(int(it * mask_scale) for it in left_top.size), resample=Image.Resampling.BILINEAR)
            left_bottom = left_bottom.resize(tuple(int(it * mask_scale) for it in left_bottom.size), resample=Image.Resampling.BILINEAR)
            right_top = right_top.resize(tuple(int(it * mask_scale) for it in right_top.size), resample=Image.Resampling.BILINEAR)
            right_bottom = right_bottom.resize(tuple(int(it * mask_scale) for it in right_bottom.size), resample=Image.Resampling.BILINEAR)

            mask = Image.new('L', image.size, "#FFFFFF")
            mask.paste(left_top, (0, 0))
            mask.paste(left_bottom, (0, mask.height - left_bottom.height))
            mask.paste(right_top, (mask.width - right_top.width, 0))
            mask.paste(right_bottom, (mask.width - right_bottom.width, mask.height - right_bottom.height))

            image.putalpha(mask)
            final_img = Image.new("RGBA", (image.width, image.height + padding * 2), color=None)
            final_img.alpha_composite(image, (0, padding))
            return final_img

        def first_str(data: Union[str, Message, List[Union[MessageSegment, str]]]) -> str:
            for it in data:
                if isinstance(it, str):
                    return it
            return ""

        height = draw_char(first_str(text)).height
        canvas: List[Image.Image] = [Image.new("RGBA", (width_limit, height), color=None)]
        position = 0
        test_char = draw_char('我')
        padding = (test_char.height - crop_margin(test_char).height)
        def new_line():
            canvas.append(Image.new("RGBA", (width_limit, height), color=None))
            nonlocal position 
            position = 0

        for segment in text:  # type: ignore
            char_image: Optional[Image.Image] = None
            if isinstance(segment, MessageSegment):
                if segment.type == 'face':
                    segment: MessageSegment = segment
                    id = segment.data['id']
                    char_image = draw_qq_face(
                        Path(__file__).parent / 'resources' / 'QFace' / f's{id}.png', 
                        autosize=autosize, 
                        padding=padding + qq_face_padding
                    )
                elif segment.type == 'image':
                    canvas.append(draw_image(
                        Image.open(get_downloaded_image_path(segment)).convert("RGBA")
                    ))
                    new_line()
                    continue
            else:
                if segment == '\n':
                    new_line()
                    continue
                char_image = draw_char(segment, padding=padding + emoji_padding)
            
            if not char_image:
                raise Exception("NoneTypeException")

            if width_limit != None and position + char_image.width > width_limit:
                new_line()

            if height < char_image.height:
                height = char_image.height
                new_canvas = Image.new("RGBA", (width_limit, height), color=None)
                new_canvas.alpha_composite(canvas[-1])
                canvas[-1] = new_canvas
            # _ = int((canvas[-1].height-char_image.height)/2)
            # canvas[-1].alpha_composite(char_image, (position, _))
            canvas[-1].alpha_composite(char_image, (position, 0))
            position += char_image.width
        return combine_img(*canvas)

    @staticmethod
    async def from_message(
        message: Union[Message, List[MessageSegment]],
        font_path: str,
        emoji_font_path: str,
        emoji_scale: float = 1.0,
        emoji_padding = 0,
        qq_face_padding = 0,
        text_color: str = "black",
        font_size: int = 12,
        width_limit: Optional[int] = None,
        embedded_color=False,
        bot: Optional[Bot] = None,
        group_id: Optional[int] = None,
        autosize = False
    ):
        list_: List[Union[MessageSegment, str]] = []
        for segment in message:
            when = lambda _: segment.type == _

            if when("text"):
                for char in segment.data['text']:
                    list_.append(char)
                continue
            
            if when("at"):
                if not (bot and group_id):
                    raise Exception("missed argument: bot, group_id")
                name = await get_member_plain_text_name(bot, group_id, segment.data['qq'])
                list_.append('@')
                for char in name:
                    list_.append(char)
                continue

            if when("image"):
                list_.append(segment)

            if when("face"):
                list_.append(segment)

        return Text2Image.from_text(
            list_, 
            font_path, 
            emoji_font_path, 
            emoji_scale, 
            emoji_padding, 
            qq_face_padding, 
            text_color, 
            font_size, 
            width_limit, 
            embedded_color,
            autosize
        )

    @staticmethod
    def combine_message_image(bubble_image: Image.Image, user_icon: Image.Image, user_name: str, identities: Optional[List[Image.Image]]) -> Image.Image:
        circle_mask_path = Object.resources_path() / 'circle.png'
        circle_mask: Image.Image = Image.open(circle_mask_path).convert("L")
        user_icon = user_icon.resize((120, 120), resample=Image.Resampling.BILINEAR).convert("RGBA")
        circle_mask = circle_mask.resize(user_icon.size, resample=Image.Resampling.BILINEAR)
        user_icon.putalpha(circle_mask)

        ROOT = Path(__file__).parent / "resources"
        font = ROOT / "MILanPro_Regular.ttf"
        emoji_font = ROOT / "AppleColorEmoji.ttf"

        user_name_image = Text2Image.from_text(
            user_name, 
            font_path=str(font), 
            emoji_font_path=str(emoji_font), 
            text_color="#202125", 
            embedded_color=True,
            font_size=34
        )

        max_width = user_icon.width + max([bubble_image.width, sum([user_name_image.width, *[it.width for it in identities or []]])]) + 64  # give some extra pixels
        max_height = user_icon.height + bubble_image.height + 16

        canvas = Image.new('RGBA', (max_width, max_height), "#ECEDF1")

        top_padding = 42
        left_padding = 32
        left = left_padding
        canvas.alpha_composite(user_icon, (left, top_padding))
        left += user_icon.width + 36
        canvas.alpha_composite(user_name_image, (left, 16 + top_padding))
        left += user_name_image.width + 10
        if identities:
            for it in identities:
                scale = 3 / 4
                it = it.resize((int(it.width * scale), int(it.height * scale)), resample=Image.Resampling.BILINEAR)
                canvas.alpha_composite(it, (left, top_padding + 8))
                left += it.width + 4
        canvas.alpha_composite(bubble_image, (left_padding + user_icon.width - 8, int(user_icon.height * (8 / 16) + top_padding)))
        return canvas

async def main():
    img = await Text2Image.from_message(
        message=[MessageSegment.image(file=Path(__file__).parent / 'OP.png'), MessageSegment.text("我去，你们说的这个010是我妈妈😂"), MessageSegment.face(265), MessageSegment.face(265), MessageSegment.face(265)],
        font_path=str(font),
        emoji_font_path=str(emoji_font),
        font_size=45,
        emoji_scale=1,
        emoji_padding=8,
        qq_face_padding=-6,
        # font_size=get_emoji_bitmap_size(gb_2312),
        width_limit=600,
        embedded_color=True
    )
    bubble_path = Path(__file__).parent / 'resources' / 'bubble.9.png'
    bubble = Ninepatch(bubble_path)
    canvas = bubble.render_wrap(img)
    canvas.show()
    canvas.save(Path(__file__).parent / 'test.png')

if __name__ == '__main__':
    asyncio.run(main())