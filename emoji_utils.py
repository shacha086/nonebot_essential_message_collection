from os import PathLike
from pathlib import Path
from typing import Union
import unicodedata
from emoji.unicode_codes import EMOJI_DATA
from fontTools import ttLib

ROOT = Path(__file__).parent / "resources"
ROOT.mkdir(parents=True, exist_ok=True)
gb_2312 = ROOT / "zawgyitai.ttf"

def get_emoji_bitmap_size(path: Union[PathLike[str], Path, str]):
    font = ttLib.TTFont(path)
    sizetable = font['CBLC'].strikes[0].bitmapSizeTable  # type: ignore
    return max(sizetable.ppemX, sizetable.ppemY)

def is_emoji(string: str) -> bool:
    return unicodedata.category(string) in ['So', 'Cn']

def is_emoji_strict(string: str) -> bool:
    return string in EMOJI_DATA

