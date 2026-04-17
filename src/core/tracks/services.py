from .ports import TracksCrudPort


class TracksCrudService:
    def __init__(self, tracks_crud_port: TracksCrudPort) -> None:
        self.tracks_crul = tracks_crud_port
