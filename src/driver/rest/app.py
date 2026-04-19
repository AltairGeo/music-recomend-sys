from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from .api import api_router

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.driven.database.tracks.dao import TracksCrudDao
    from src.core.tracks.services import TracksCrudService
    from src.driven.filesystem.tracks_storage import LocalTracksStorage
    from src.settings import app_config

    tracks_dao = TracksCrudDao()
    storage = LocalTracksStorage(app_config.music_data_folder / "tracks")

    tracks_service = TracksCrudService(tracks_dao)

    app.state.tracks_service = tracks_service
    app.state.tracks_storage = storage

    yield

app = FastAPI(lifespan=lifespan)

app.state.tracks_dao = None
app.state.storage = None

# ======+ Middlewares +======
app.add_middleware(CORSMiddleware, "*", "*")

app.add_middleware(GZipMiddleware)

# ======+ Routers +========
app.include_router(api_router)
