from pathlib import Path
from typing import Dict, Any
import mutagen
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
import logging

_log = logging.getLogger(__name__)


def extract_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Извлекает метаданные из аудиофайла.
    Возвращает словарь с ключами:
        title, artist, album, genre, year, license, additional_info
    """
    metadata = {
        "title": file_path.stem,
        "artist": "Unknown",
        "album": "",
        "genre": "",
        "year": 0,
        "license": "",
        "additional_info": "",
    }

    try:
        audio = mutagen.File(file_path)  # type: ignore
        if audio is None:
            return metadata

        # Общие поля для разных форматов
        if isinstance(audio, MP3):
            _extract_id3(audio, metadata)
        elif isinstance(audio, FLAC):
            _extract_vorbis(audio, metadata)
        elif isinstance(audio, MP4):
            _extract_mp4(audio, metadata)
        else:
            # Пробуем получить теги как словарь для других форматов
            if hasattr(audio, "tags") and audio.tags:
                for key, value in audio.tags.items():
                    _log.debug(f"Unknown format tag: {key} = {value}")

    except Exception as e:
        _log.warning(f"Failed to extract metadata from {file_path}: {e}")

    return metadata


def _extract_id3(audio: MP3, metadata: Dict[str, Any]) -> None:
    """Извлечение ID3 тегов (MP3)."""
    tags = audio.tags
    if not tags:
        return

    # TIT2 - название
    if "TIT2" in tags:
        metadata["title"] = str(tags["TIT2"])
    # TPE1 - исполнитель
    if "TPE1" in tags:
        metadata["artist"] = str(tags["TPE1"])
    # TALB - альбом
    if "TALB" in tags:
        metadata["album"] = str(tags["TALB"])
    # TCON - жанр
    if "TCON" in tags:
        metadata["genre"] = str(tags["TCON"])
    # TDRC / TYER - год
    if "TDRC" in tags:
        try:
            year_text = str(tags["TDRC"])
            # Может быть "2020-01-01" или просто "2020"
            metadata["year"] = int(year_text[:4]) if year_text else 0
        except ValueError, IndexError:
            pass
    elif "TYER" in tags:
        try:
            metadata["year"] = int(str(tags["TYER"]))
        except ValueError:
            pass
    # TCOP - копирайт (можно как license)
    if "TCOP" in tags:
        metadata["license"] = str(tags["TCOP"])
    # COMM - комментарий (additional_info)
    if "COMM" in tags:
        metadata["additional_info"] = str(tags["COMM"])


def _extract_vorbis(audio: FLAC, metadata: Dict[str, Any]) -> None:
    """Извлечение Vorbis комментариев (FLAC, OGG)."""
    tags = audio.tags
    if not tags:
        return

    metadata["title"] = tags.get("TITLE", [metadata["title"]])[0]  # type: ignore
    metadata["artist"] = tags.get("ARTIST", [metadata["artist"]])[0]  # type: ignore
    metadata["album"] = tags.get("ALBUM", [""])[0]  # type: ignore
    metadata["genre"] = tags.get("GENRE", [""])[0]  # type: ignore
    year_str = tags.get("DATE", ["0"])[0]  # type: ignore
    try:
        metadata["year"] = int(year_str[:4]) if year_str else 0
    except ValueError:
        pass
    metadata["license"] = tags.get("COPYRIGHT", [""])[0]  # type: ignore
    metadata["additional_info"] = tags.get("DESCRIPTION", [""])[0]  # type: ignore


def _extract_mp4(audio: MP4, metadata: Dict[str, Any]) -> None:
    """Извлечение тегов из MP4/M4A."""
    tags = audio.tags
    if not tags:
        return

    # \xa9nam - название
    if "\xa9nam" in tags:
        metadata["title"] = tags["\xa9nam"][0]
    # \xa9ART - исполнитель
    if "\xa9ART" in tags:
        metadata["artist"] = tags["\xa9ART"][0]
    # \xa9alb - альбом
    if "\xa9alb" in tags:
        metadata["album"] = tags["\xa9alb"][0]
    # \xa9gen - жанр
    if "\xa9gen" in tags:
        metadata["genre"] = tags["\xa9gen"][0]
    # \xa9day - год
    if "\xa9day" in tags:
        try:
            metadata["year"] = int(tags["\xa9day"][0][:4])
        except ValueError, IndexError:
            pass
    # cprt - копирайт
    if "cprt" in tags:
        metadata["license"] = tags["cprt"][0]
    # desc - описание
    if "desc" in tags:
        metadata["additional_info"] = tags["desc"][0]
