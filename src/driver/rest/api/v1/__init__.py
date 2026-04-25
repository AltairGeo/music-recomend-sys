from fastapi import APIRouter
from .tracks import router as tracks_router

v1_router = APIRouter(prefix="/v1")


v1_router.include_router(tracks_router)
