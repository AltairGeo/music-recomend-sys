from dataclasses import dataclass
from pathlib import Path

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
    path_to_file: Path

@dataclass(slots=True)
class TrackEmbedding:
    track_id: int
    vector: list[float]
