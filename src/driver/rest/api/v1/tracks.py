from fastapi import APIRouter, Depends, HTTPException, Query, Response
from src.core.tracks.services import TracksCrudService
from src.driver.rest.depends.tracks import get_tracks_service, get_tracks_storage
from src.driver.rest.dto.tracks import TrackDTO
from src.core.tracks.ports import TracksStoragePort


router = APIRouter(prefix="/tracks")



@router.get("/search")
async def search_tracks(
    q: str,
    service: TracksCrudService = Depends(get_tracks_service),
):
    tracks = await service.find_by_name(q)

    return [TrackDTO.from_domain(t) for t in tracks]


@router.get("/{track_id}")
async def get_track(
    track_id: int,
    service: TracksCrudService = Depends(get_tracks_service),
):
    track = await service.get_track(track_id)

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    return TrackDTO.from_domain(track)


@router.get("")
async def list_tracks(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    service: TracksCrudService = Depends(get_tracks_service),
):
    result = await service.list_tracks(skip=skip, limit=limit)

    if not result:
        return {
            "items": [],
            "count": 0,
            "skip": skip,
            "limit": limit,
        }

    return {
        "items": [TrackDTO.from_domain(t) for t in result.entities],
        "count": result.count_entities,
        "skip": result.offset,
        "limit": result.limit,
    }


@router.get("/{track_id}/audio")
async def get_track_audio(
    track_id: int,
    service: TracksCrudService = Depends(get_tracks_service),
    storage: TracksStoragePort = Depends(get_tracks_storage),
):
    track = await service.get_track(track_id)

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    try:
        audio_bytes = await storage.read(track.file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Audio file not found")

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'inline; filename="{track.title}.mp3"'
        }
    )
