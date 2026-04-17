from dataclasses import dataclass


@dataclass(slots=True)
class Track:
    id: str
    title: str
    artist: str
    genre: str
    year: int
    album: str
    additional_info: str
    license: str
    audio_url: str


@dataclass(slots=True)
class TrackEmbedding:
    track_id: str
    vector: list[float]
