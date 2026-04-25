from .ports import TracksCrudPort
from typing import Sequence
from src.core.tracks.domains import Track


class TracksCrudService:
    def __init__(self, tracks_crud_port: TracksCrudPort) -> None:
        self._tracks = tracks_crud_port

    async def get_track(self, track_id: int) -> Track | None:
        return await self._tracks.get(track_id)

    async def list_tracks(self, skip: int = 0, limit: int = 25):
        return await self._tracks.read(skip=skip, limit=limit)

    async def find_by_name(self, name: str) -> Sequence[Track]:
        return await self._tracks.find_by_name(name)

    async def get_random_track(self, n: int = 1) -> Sequence[Track]:
        if n < 1:
            raise ValueError("TracksCrudService: get_random_track. n cant be less than 1")

        return await self._tracks.get_random(n=n)
