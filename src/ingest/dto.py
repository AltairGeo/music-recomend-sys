from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrackProcessed:
    title: str
    artist: str
    genre: str
    year: int
    album: str
    additional_info: str
    license: str
    embedding: list[float]
    file_hash: str
    audio_raw: bytes


@dataclass(frozen=True)
class TrackQueueIn:
    tpath: Path
    thash: str
