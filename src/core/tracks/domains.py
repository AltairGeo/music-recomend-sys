from dataclasses import dataclass


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

@dataclass(slots=True)
class TrackEmbedding:
    track_id: int
    vector: list[float]
