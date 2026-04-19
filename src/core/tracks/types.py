from typing import TypedDict, NotRequired


class ReadTrackFilters(TypedDict):
    id: NotRequired[int]
    title: NotRequired[str]
    artist: NotRequired[str]
    genre: NotRequired[str]
    year: NotRequired[int]
    album: NotRequired[str]
    license: NotRequired[str]
