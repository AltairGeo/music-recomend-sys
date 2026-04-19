# /src/driven/filesystem/tracks_storage.py

import aiofiles
from pathlib import Path
import uuid

class LocalTracksStorage(): # соответствует TracksStoragePort
    def __init__(self, store_path: Path) -> None:
        self._store_path: Path = store_path

        self._store_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_safe_id(file_id: str) -> bool:
        """Проверяет, что идентификатор состоит только из безопасных символов."""

        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")

        return all(c in allowed for c in file_id)


    def _get_file_path(self, file_id: str) -> Path:
        """
        Преобразует идентификатор в путь файла внутри хранилища.
        Использует первые 4 символа для разбиения на подпапки.
        """

        if not self.is_safe_id(file_id):
            raise ValueError("Unsafe filename. Failed to get file path in TracksStorageSystem")

        subdir1 = file_id[:2]
        subdir2 = file_id[2:4]
        file_path = self._store_path / subdir1 / subdir2 / file_id

        return file_path


    async def save(self, data: bytes) -> str:
        file_id = str(uuid.uuid4())
        file_path = self._get_file_path(file_id)

        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)

        return file_id

    async def read(self, id: str) -> bytes:
        """
        Читает аудиоданные по идентификатору.
        Выбрасывает FileNotFoundError, если файл не найден.
        """

        file_path = self._get_file_path(id)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file with id '{id}' not found")

        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()
