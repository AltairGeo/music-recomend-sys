from fastapi import Request
from src.core.audio_processing.services import AudioEmbeddingService


def get_embedding_service(request: Request) -> AudioEmbeddingService:
    service = getattr(request.app.state, "embeddings_service", None)

    if service is None:
        raise RuntimeError("embeddings_service not initialized")

    return service
