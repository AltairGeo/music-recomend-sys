from fastapi import Request
from src.core.tracks.services import TracksCrudService


def get_tracks_service(request: Request) -> TracksCrudService:
    service = getattr(request.app.state, "tracks_service", None)

    if service is None:
        raise RuntimeError("TracksCrudService not initialized")

    return service


def get_tracks_storage(request: Request) -> TracksStoragePort:
    storage = getattr(request.app.state, "tracks_storage", None)

    if storage is None:
        raise RuntimeError("TracksStorage not initialized")

    return storage
