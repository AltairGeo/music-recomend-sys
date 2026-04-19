import io
from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File
from src.core.tracks.services import TracksCrudService
from src.driver.rest.depends.tracks import get_tracks_service, get_tracks_storage
from src.driver.rest.dto.tracks import TrackDTO
from src.core.tracks.ports import TracksStoragePort
from src.driver.rest.depends.recommendation import get_recommendation_service
from src.core.recommendation.services import RecommendationService
from src.core.audio_processing.services import AudioEmbeddingService
from src.driver.rest.depends.audio_processing import get_embedding_service
from src.driver.rest.dto.tracks import UploadTrackResult

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


@router.get("/{track_id}/similar")
async def similar_tracks(
    track_id: int,
    k: int = Query(10, ge=1, le=20),
    service: RecommendationService = Depends(get_recommendation_service),
):
    results = await service.get_similar_tracks(track_id, k)

    return [
        {
            "track": TrackDTO.from_domain(track),
            "score": score,
        }
        for track, score in results
    ]


@router.post("/")
async def upload_track(
    file: UploadFile = File(...),
    tracks_service: TracksCrudService = Depends(get_tracks_service),
    emb_service: AudioEmbeddingService = Depends(get_embedding_service),
    rec_service: RecommendationService = Depends(get_recommendation_service),
) -> UploadTrackResult:

    audio_bytes = await file.read()
    file_io = io.BytesIO(audio_bytes)

    embedding =  emb_service.get_embedding(file_io)

    similar = await rec_service.get_similar_by_vector(
            embedding,
            k=10
    )
    result = []
    for track, score in similar:
        result.append(
            (TrackDTO.from_domain(track), score)
        )

    return UploadTrackResult(
        result=result
    )
