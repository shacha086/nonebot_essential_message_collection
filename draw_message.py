from pathlib import Path
import textwrap
from PIL import ImageDraw, ImageFont, Image
from nonebot_plugin_imageutils import Text2Image
from ninepatch import Ninepatch
from Unistr import Unistr
from utils import handle_chinese_char, revert_listed_chinese_char
bubble_path = Path(__file__).parent / 'resources' / 'bubble.9.png'
bubble = Ninepatch(bubble_path)

text = "测试测试测试测试测试测试测试测试测试测试测试测试测试测试hello world this is a test please ignore hahahaha"
font = ImageFont.truetype(font=str(Path(__file__).parent / 'resources' / 'NotoSansMonoCJKsc-Regular.otf'), size=45)
text_image = Text2Image.from_text(text, 45).wrap(630.).to_image()
canvas = Image.new("RGBA", (630, 999), color=None)

canvas = bubble.render_wrap(text_image)
canvas.save(Path(__file__).parent / 'test.png')