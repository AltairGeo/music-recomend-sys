from fastapi import APIRouter, Depends, HTTPException
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
