from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from .api import api_router
from src.logs import overwrite_uvicorn_logger

from contextlib import asynccontextmanager

import logging

_log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):

    overwrite_uvicorn_logger()

    from src.driven.database.tracks.dao import TracksCrudDao
    from src.core.tracks.services import TracksCrudService
    from src.driven.filesystem.tracks_storage import LocalTracksStorage
    from src.settings import app_config
    from src.driven.recommendation.annoy_adapter import AnnoyRecommendationAdapter
    from src.driven.database.tracks.dao import EmbeddingsCrudDAO
    from src.core.recommendation.services import RecommendationService
    from src.core.audio_processing.services import AudioEmbeddingService
    from src.core.audio_processing.processor import AudioProcessor

    tracks_dao = TracksCrudDao()
    storage = LocalTracksStorage(app_config.music_data_folder / "tracks")
    embeddings_dao = EmbeddingsCrudDAO()
    annoy_rec_adapter = AnnoyRecommendationAdapter(tracks_dao, embeddings_dao)
    tracks_service = TracksCrudService(tracks_dao)
    rec_service = RecommendationService(annoy_rec_adapter, tracks_dao)
    embeddings_service = AudioEmbeddingService(
        AudioProcessor(),
        embeddings_dao
    )

    app.state.tracks_service = tracks_service
    app.state.tracks_storage = storage
    app.state.rec_service = rec_service
    app.state.embeddings_service = embeddings_service


    _log.info("Build index annoy...")
    await rec_service.build_index()
    _log.info("App started!")

    yield

app = FastAPI(lifespan=lifespan)


# ======+ Middlewares +======
app.add_middleware(CORSMiddleware, "*", "*")

app.add_middleware(GZipMiddleware)

# ======+ Routers +========
app.include_router(api_router)
