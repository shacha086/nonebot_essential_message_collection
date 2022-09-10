from ast import arg
import re
import sys
import textwrap
from typing import Any, Mapping, Sequence, SupportsIndex, overload
from typing_extensions import LiteralString
from pydantic import parse_obj_as

class Unistr(str):
    def __new__(cls, value):
        return str.__new__(cls, value)

    def __init__(self, value):
        str.__init__(value)

    def __len__(self) -> int:
        chinese = re.findall(r'[^\x00-\xff]', self)
        return len(str(self)) + len(chinese)

    def capitalize(self) -> 'Unistr':  # type: ignore[misc]
        return Unistr(str(self).capitalize())

    def casefold(self) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).casefold())
        
    def center(self, __width: SupportsIndex, __fillchar: str = ...) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).center(__width, __fillchar))

    if sys.version_info >= (3, 8):
        def expandtabs(self, tabsize: SupportsIndex = ...) -> 'Unistr':   # type: ignore[misc]
            return Unistr(str(self).expandtabs(tabsize))
    else:
        def expandtabs(self, tabsize: int = ...) -> 'Unistr':   # type: ignore[misc]
            return Unistr(str(self).expandtabs(tabsize))

    def format(self, *args: object, **kwargs: object) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).format(args, kwargs))

    def format_map(self, map) -> 'Unistr': 
        return Unistr(str(self).format_map(map))

    def join(self, __iterable) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).join(__iterable))
        
    def ljust(self, __width: SupportsIndex, __fillchar: str = ...) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).ljust(__width, __fillchar))

    def lower(self) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).lower())

    def lstrip(self, __chars: str | None = ...) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).lstrip(__chars))
        
    def partition(self, __sep: str) -> tuple['Unistr', 'Unistr', 'Unistr']:   # type: ignore[misc]
        a, b, c = str(self).partition(__sep)
        return Unistr(a), Unistr(b), Unistr(c)

    def replace(self, __old: str, __new: str, __count: SupportsIndex = ...) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).replace(__old, __new, __count))

    if sys.version_info >= (3, 9):
        def removeprefix(self, __prefix: str) -> 'Unistr':   # type: ignore[misc]
            return Unistr(str(self).removeprefix(__prefix))

        def removesuffix(self, __suffix: str) -> 'Unistr':   # type: ignore[misc]
            return Unistr(str(self).removesuffix(__suffix))

    def rjust(self, __width: SupportsIndex, __fillchar: str = ...) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).rjust(__width, __fillchar))
        
    def rpartition(self, __sep: str) -> tuple['Unistr', 'Unistr', 'Unistr']:   # type: ignore[misc]
        a, b, c = str(self).rpartition(__sep)
        return Unistr(a), Unistr(b), Unistr(c)

    def rsplit(self, sep: str | None = ..., maxsplit: SupportsIndex = ...) -> list['Unistr']:   # type: ignore[misc]
        return [Unistr(it) for it in str(self).rsplit(sep, maxsplit)]

    def rstrip(self, __chars: str | None = ...) -> str:   # type: ignore[misc]
        return Unistr(str(self).rstrip(__chars))

    def split(self, sep: str | None = ..., maxsplit: SupportsIndex = ...) -> list['Unistr']:   # type: ignore[misc]
        return [Unistr(it) for it in str(self).split(sep, maxsplit)]

    def splitlines(self, keepends: bool = ...) -> list['Unistr']:   # type: ignore[misc]
        return [Unistr(it) for it in str(self).splitlines(keepends)]

    def strip(self, __chars: str | None = ...) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).strip(__chars))
        
    def swapcase(self) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).swapcase())

    def title(self) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).title())

    def translate(self, __table: Mapping[int, int | str | None] | Sequence[int | str | None]) -> 'Unistr': 
        return Unistr(str(self).translate(__table))
        
    def upper(self) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).upper())

    def zfill(self, __width: SupportsIndex) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).zfill(__width))

    def __add__(self, __s: str) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).__add__(__s))

    def __getitem__(self, __i: SupportsIndex | slice) -> 'Unistr': ...
    
    def __iter__(self):   # type: ignore[misc]
        iter = str(self).__iter__()
        print(iter)

    def __mod__(self, __x: Any) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).__mod__(__x))

    def __mul__(self, __n: SupportsIndex) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).__mul__(__n))

    def __rmul__(self, __n: SupportsIndex) -> 'Unistr':   # type: ignore[misc]
        return Unistr(str(self).__rmul__(__n))

