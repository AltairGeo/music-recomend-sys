from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.audio_processing.domains import TrackEmbedding


@dataclass(slots=True)
class Track:
    id: int
    title: str
    artist: str
    genre: str
    year: int
    album: str
    additional_info: str
    license: str
    audio_url: str
    embedding: "TrackEmbedding"
    file_id: str
    file_hash: str
