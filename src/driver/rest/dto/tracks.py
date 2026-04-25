from typing import Annotated, List
from pydantic import BaseModel, Field
from src.core.tracks.domains import Track


class TrackDTO(BaseModel):
    id: int
    title: str
    artist: str
    genre: str
    year: int
    album: str
    additional_info: str
    license: str
    audio_url: str

    @classmethod
    def from_domain(cls, track: Track) -> "TrackDTO":
        return cls(
            id=track.id,
            title=track.title,
            artist=track.artist,
            genre=track.genre,
            year=track.year,
            album=track.album,
            additional_info=track.additional_info,
            license=track.license,
            audio_url=track.audio_url,
        )


class UploadTrackResult(BaseModel):
    result: List[tuple[TrackDTO, float]]

class GetRandomTrackResult(BaseModel):
    tracks: List[TrackDTO]
    total: Annotated[int, Field(gt=0, lt=20)]
