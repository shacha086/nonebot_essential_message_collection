from enum import Enum


class Size(Enum):
    px40 = 1
    px100 = 3
    px140 = 4
    px640 = 5
    px1080 = 0

class EssenceMessageSegmentType(int, Enum):
    Text = 1
    Face = 2
    Image = 3
    File = 4
    Link = 5