from typing import TypedDict


class ReadTrackFilters(TypedDict):
    id: int
    title: str
    artist: str
    genre: str
    year: int
    album: str
    license: str
