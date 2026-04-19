from src.driven.database.session import BaseModel
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ARRAY, FLOAT, ForeignKey, String
from src.core.tracks.domains import Track
from src.core.audio_processing.domains import TrackEmbedding


class TrackModel(BaseModel):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    artist: Mapped[str] = mapped_column(String(200), nullable=False)
    genre: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    album: Mapped[str] = mapped_column(String(150), nullable=False)
    additional_info: Mapped[str]
    license: Mapped[str]
    embedding_id: Mapped[int] = mapped_column(
        ForeignKey("tracks_embeddings.id"), nullable=False
    )
    embedding: Mapped["TrackEmbeddingModel"] = relationship(lazy="joined")
    file_id: Mapped[str] = mapped_column(String(256), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    @property
    def audio_url(self) -> str:
        return f"/api/tracks/{self.id}/audio"

    def dump_to_domain(self) -> Track:
        return Track(
            additional_info=self.additional_info,
            album=self.album,
            artist=self.artist,
            audio_url=self.audio_url,
            genre=self.genre,
            id=self.id,
            license=self.license,
            title=self.title,
            year=self.year,
            embedding=TrackEmbedding(
                id=self.embedding_id, vector=self.embedding.vector
            ),
            file_id=self.file_id,
            file_hash=self.file_hash,
        )


class TrackEmbeddingModel(BaseModel):
    __tablename__ = "tracks_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    vector: Mapped[list[float]] = mapped_column(ARRAY(FLOAT), nullable=False)
