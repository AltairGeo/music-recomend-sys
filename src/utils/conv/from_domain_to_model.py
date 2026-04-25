from src.core.tracks.domains import Track
from src.driven.database.tracks.models import TrackModel


def trackDomTOtrackMod(track: Track, embedding_id: int) -> TrackModel:
    return TrackModel(
        title=track.title,
        artist=track.artist,
        genre=track.genre,
        year=track.year,
        album=track.album,
        additional_info=track.additional_info,
        license=track.license,
        embedding_id=embedding_id,
        file_hash=track.file_hash,
        file_id=track.file_id,
    )
