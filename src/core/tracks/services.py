from pathlib import Path
from .ports import TracksCrudPort


class TracksCrudService:
    def __init__(self, tracks_crud_port: TracksCrudPort) -> None:
        self.tracks_crud = tracks_crud_port

    async def add_track_and_create_embedding(self, path_to_file: Path) -> bool: ...
