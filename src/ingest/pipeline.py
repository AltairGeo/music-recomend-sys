# /src/ingest/pipeline.py

import asyncio
from pathlib import Path
import logging
from typing import List, Optional, Set
from concurrent.futures import ProcessPoolExecutor

from sqlalchemy.exc import IntegrityError

from src.core.audio_processing.processor import AudioProcessor
from src.core.tracks.services import TracksCrudService
from src.driven.database.tracks.dao import TracksCrudDao, EmbeddingsCrudDAO
from src.core.audio_processing.services import AudioEmbeddingService
from src.driven.filesystem.tracks_storage import LocalTracksStorage
from src.driven.database.session import create_db_and_tables
from src.settings import app_config
from src.ingest.worker import process_file, compute_file_hash

from src.core.tracks.domains import Track
from src.core.audio_processing.domains import TrackEmbedding

_log = logging.getLogger(__name__)


class IngestPipeline:
    """Конвейер массовой обработки аудиофайлов."""

    def __init__(
        self,
        max_workers: int = 4,
        supported_extensions: Optional[Set[str]] = None
    ):
        self.max_workers = max_workers
        self.supported_extensions = supported_extensions or {
            ".mp3", ".flac", ".m4a", ".ogg", ".wav"
        }

        self.tracks_dao = TracksCrudDao()
        self.emb_dao = EmbeddingsCrudDAO()
        self.storage = LocalTracksStorage(app_config.music_data_folder / "tracks")

    def find_audio_files(self, root_dir: Path) -> List[Path]:
        """Рекурсивно находит все аудиофайлы."""
        files = []
        for path in root_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in self.supported_extensions:
                files.append(path)
        return files

    async def process_file_async(
        self,
        file_path: Path,
        executor: ProcessPoolExecutor,
    ) -> tuple[bool, str]:

        loop = asyncio.get_running_loop()

        try:
            metadata, embedding, audio_bytes = await loop.run_in_executor(
                executor,
                process_file,
                file_path
            )

            file_hash = compute_file_hash(audio_bytes)

            # ранняя проверка
            existing_id = await self.tracks_dao.find_by_file_hash(file_hash)
            if existing_id:
                _log.info(
                    f"Skipping {file_path.name} (already exists, id={existing_id})"
                )
                return False, "skipped"

            file_id = await self.storage.save(audio_bytes)
            embedding_list = embedding.tolist()

            try:
                embedding_id = await self.emb_dao.create(embedding_list)

                if not embedding_id:
                    raise ValueError("NO EMBEDDING ID!!!!")

                track = Track(
                    id=0,
                    title=metadata["title"],
                    artist=metadata["artist"],
                    genre=metadata["genre"],
                    year=metadata["year"],
                    album=metadata["album"],
                    additional_info=metadata["additional_info"],
                    license=metadata["license"],
                    audio_url="",
                    embedding=TrackEmbedding(
                        id=embedding_id,
                        vector=embedding_list
                    ),
                    file_id=file_id,
                    file_hash=file_hash,
                )

                track_id = await self.tracks_dao.create(track)

            except IntegrityError:
                # защита от гонки
                _log.info(f"Duplicate detected (race): {file_path.name}")
                return False, "skipped"

            if track_id:
                _log.info(
                    f"Added track {track_id}: {track.title} - {track.artist}"
                )
                return True, "success"

            return False, "error"

        except Exception as e:
            _log.error(f"Failed to process {file_path}: {e}", exc_info=True)
            return False, "error"

    async def run(
        self,
        root_dir: Path,
        limit: Optional[int] = None
    ) -> dict:
        """Запускает конвейер."""

        await create_db_and_tables()

        files = self.find_audio_files(root_dir)

        if limit is not None:
            files = files[:limit]

        total = len(files)

        _log.info(f"Found {total} audio files")
        print(f"Найдено {total} файлов, воркеров: {self.max_workers}")

        queue: asyncio.Queue[Path] = asyncio.Queue()

        for f in files:
            queue.put_nowait(f)

        succeeded = 0
        failed = 0
        skipped = 0

        counter_lock = asyncio.Lock()

        async def worker(executor: ProcessPoolExecutor):
            nonlocal succeeded, failed, skipped

            while True:
                try:
                    file_path = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return

                success, status = await self.process_file_async(
                    file_path,
                    executor
                )

                async with counter_lock:
                    if success:
                        succeeded += 1
                    elif status == "skipped":
                        skipped += 1
                    else:
                        failed += 1

                    processed = succeeded + failed + skipped

                    if processed % 10 == 0:
                        print(
                            f"Прогресс: {processed}/{total} "
                            f"[Успешно - {succeeded} | Пропущено - {skipped} | Провалено - {failed}]"
                        )

                queue.task_done()

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            workers = [
                asyncio.create_task(worker(executor))
                for _ in range(self.max_workers)
            ]

            await asyncio.gather(*workers)

        print(
            f"Завершено! "
            f"Успешно: {succeeded} | Пропущено: {skipped} | Провалено: {failed}"
        )

        return {
            "processed": succeeded + failed + skipped,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
        }
