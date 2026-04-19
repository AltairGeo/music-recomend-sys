from pydantic import BaseModel
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
