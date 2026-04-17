from src.core.tracks.domains import Track
from src.driven.database.tracks.models import TrackModel

def trackDomTOtrackMod(track: Track) -> TrackModel:
    return TrackModel(
        title=track.title,
        artist=track.artist,
        genre=track.genre,
        year=track.year,
        album=track.album,
        additional_info=track.additional_info,
        license=track.license,
    )
