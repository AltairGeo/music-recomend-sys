from src.driven.database.session import BaseModel
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ARRAY, FLOAT, ForeignKey, String
from src.core.tracks.domains import Track, TrackEmbedding
from pathlib import Path


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
    embedding_id: Mapped[int] = mapped_column(ForeignKey("tracks_embeddings.id"), nullable=False)
    embedding: Mapped["TrackEmbeddingModel"] = relationship(lazy="joined")
    path_to_file: Mapped[str] = mapped_column(String(512), nullable=False)


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
            embedding=TrackEmbedding(id=self.embedding_id, vector=self.embedding.vector),
            path_to_file=Path(self.path_to_file)
        )

class TrackEmbeddingModel(BaseModel):
    __tablename__ = "tracks_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    vector: Mapped[list[float]] = mapped_column(ARRAY(FLOAT), nullable=False)
