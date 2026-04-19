from fastapi import APIRouter, Depends, HTTPException, Query
from src.core.tracks.services import TracksCrudService
from src.driver.rest.depends.tracks import get_tracks_service
from src.driver.rest.dto.tracks import TrackDTO

router = APIRouter(prefix="/tracks")

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

