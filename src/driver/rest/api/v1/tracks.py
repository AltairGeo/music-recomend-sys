import io
from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File, status
from src.core.tracks.services import TracksCrudService
from src.driver.rest.depends.tracks import get_tracks_service, get_tracks_storage
from src.driver.rest.dto.tracks import SimilarTracksResult, TrackDTO, TrackListResult, TrackSimilar
from src.core.tracks.ports import TracksStoragePort
from src.driver.rest.depends.recommendation import get_recommendation_service
from src.core.recommendation.services import RecommendationService
from src.core.audio_processing.services import AudioEmbeddingService
from src.driver.rest.depends.audio_processing import get_embedding_service
from src.driver.rest.dto.tracks import ListTracksResult

router = APIRouter(prefix="/tracks")


@router.get(
    "/random",
    summary="Get random track",
    status_code=status.HTTP_200_OK,
    response_model=ListTracksResult
)
async def get_random_track(
    n: int = Query(1, gt=0, lt=20),
    tracks_service: TracksCrudService = Depends(get_tracks_service)
):
    tracks = await tracks_service.get_random_track(n)

    tracks = [TrackDTO.from_domain(i) for i in tracks]

    return ListTracksResult(
        total=len(tracks),
        tracks=tracks
    )



@router.get("/search", response_model=ListTracksResult)
async def search_tracks(
    q: str,
    service: TracksCrudService = Depends(get_tracks_service),
):
    tracks = await service.search(q)
    tracks = [TrackDTO.from_domain(t) for t in tracks]

    return ListTracksResult(tracks=tracks, total=len(tracks))


@router.get("/{track_id}", response_model=TrackDTO)
async def get_track(
    track_id: int,
    service: TracksCrudService = Depends(get_tracks_service),
):
    track = await service.get_track(track_id)

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    return TrackDTO.from_domain(track)


@router.get("", response_model=TrackListResult)
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

    return TrackListResult(
        items=[TrackDTO.from_domain(t) for t in result.entities],
        count=result.count_entities,
        skip=result.offset,
        limit=result.limit,
    )


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


@router.get("/{track_id}/similar", response_model=SimilarTracksResult)
async def similar_tracks(
    track_id: int,
    k: int = Query(10, ge=1, le=20),
    service: RecommendationService = Depends(get_recommendation_service),
):
    results = await service.get_similar_tracks(track_id, k)

    return SimilarTracksResult(
        tracks=[TrackSimilar(track=TrackDTO.from_domain(track), score=score) for track, score in results]
    )


@router.post("/", response_model=SimilarTracksResult, description="Поиск похожих треков в базе данных на загруженный пользователем")
async def upload_track(
    file: UploadFile = File(...),
    emb_service: AudioEmbeddingService = Depends(get_embedding_service),
    rec_service: RecommendationService = Depends(get_recommendation_service),
):

    audio_bytes = await file.read()
    file_io = io.BytesIO(audio_bytes)

    embedding =  emb_service.get_embedding(file_io)

    similar = await rec_service.get_similar_by_vector(
            embedding,
            k=10
    )


    return SimilarTracksResult(
        tracks=[TrackSimilar(track=TrackDTO.from_domain(track), score=score) for track, score in similar]
    )
