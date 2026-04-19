from typing import BinaryIO
from .processor import AudioProcessor
from src.core.audio_processing.domains import TrackEmbedding
from src.core.tracks.ports import EmbeddingsCrudPort


class AudioEmbeddingService:
    def __init__(
        self, audio_processor: AudioProcessor, emb_dao: EmbeddingsCrudPort
    ) -> None:
        self.emb_dao = emb_dao
        self._audio_proccessor = audio_processor

    def get_embedding(self, file: BinaryIO) -> list[float]:
        embedding = self._audio_proccessor.create_embedding(file)
        return embedding.tolist()

    async def create_embedding(self, file: BinaryIO) -> TrackEmbedding:
        embedding = self._audio_proccessor.create_embedding(file)
        vector = embedding.tolist()
        embedding_id = await self.emb_dao.create(vector=vector)

        if not embedding_id:
            raise Exception("Embedding: fail to create in database! file: %s", BinaryIO)

        return TrackEmbedding(id=embedding_id, vector=vector)
