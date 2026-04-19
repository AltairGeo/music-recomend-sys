# /src/ingest/pipeline.py
#
# 1. Найти все треки и записать пути к ним
# 2. Создать пул воркеров
# 3. запустить пайплайн
#   загрузка -> извлечение признаков -> парсинг метаданных -> сохранение
#



import asyncio
from pathlib import Path
import logging
from typing import List, Optional, Set
from concurrent.futures import ProcessPoolExecutor

from src.core.audio_processing.processor import AudioProcessor
from src.core.tracks.services import TracksCrudService
from src.driven.database.tracks.dao import TracksCrudDao, EmbeddingsCrudDAO
from src.core.audio_processing.services import AudioEmbeddingService
from src.driven.filesystem.tracks_storage import LocalTracksStorage
from src.driven.database.session import create_db_and_tables
from src.settings import app_config
from src.ingest.worker import process_file
from src.ingest.worker import compute_file_hash

from src.core.tracks.domains import Track
from src.core.audio_processing.domains import TrackEmbedding


_log = logging.getLogger(__name__)

class IngestPipeline:
    """Конвейер массовой обработки аудиофайлов."""

    def __init__(
        self,
        max_workers: int = 4,
        supported_extensions: Set[str] = {'.mp3', '.flac', '.m4a', '.ogg', '.wav'}
    ):
        self.max_workers = max_workers
        self.supported_extensions = supported_extensions

        # Инициализация зависимостей (в реальном проекте через DI)
        self.tracks_dao = TracksCrudDao()
        self.emb_dao = EmbeddingsCrudDAO()
        self.storage = LocalTracksStorage(app_config.music_data_folder / "tracks")
        self.emb_service = AudioEmbeddingService(
            AudioProcessor(sample_rate=22050, n_mfcc=13),
            self.emb_dao
        )
        self.tracks_service = TracksCrudService(
            self.tracks_dao
        )

    def find_audio_files(self, root_dir: Path) -> List[Path]:
        """Рекурсивно находит все аудиофайлы с поддерживаемыми расширениями."""
        files = []
        for ext in self.supported_extensions:
            files.extend(root_dir.glob(f"**/*{ext}"))
            files.extend(root_dir.glob(f"**/*{ext.upper()}"))
        return files

    async def process_file_async(self, file_path: Path, executor: ProcessPoolExecutor) -> tuple[bool, str]:
        loop = asyncio.get_running_loop()
        try:
            metadata, embedding, audio_bytes = await loop.run_in_executor(executor, process_file, file_path)

            print(f"длинна эмбеддинга - {len(embedding.tolist())}")

            file_hash = compute_file_hash(audio_bytes)

            existing_id = await self.tracks_dao.find_by_file_hash(file_hash)
            if existing_id:
                _log.info(f"⏭️ Skipping {file_path.name} (already exists, id={existing_id})")
                return False, 'skipped'

            file_id = await self.storage.save(audio_bytes)
            embedding_id = await self.emb_dao.create(embedding.tolist())

            if not embedding_id:
                _log.error(f"Failed to create embedding for {file_path}")
                return False, 'error'

            track = Track(
                id=0,
                title=metadata['title'],
                artist=metadata['artist'],
                genre=metadata['genre'],
                year=metadata['year'],
                album=metadata['album'],
                additional_info=metadata['additional_info'],
                license=metadata['license'],
                audio_url="",
                embedding=TrackEmbedding(id=embedding_id, vector=embedding.tolist()),
                file_id=file_id,
                file_hash=file_hash
            )

            track_id = await self.tracks_dao.create(track)
            if track_id:
                _log.info(f"✅ Added track {track_id}: {track.title} - {track.artist}")
                return True, 'success'
            else:
                return False, 'error'

        except Exception as e:
            _log.error(f"Failed to process {file_path}: {e}", exc_info=True)
            return False, 'error'

    async def run(self, root_dir: Path, limit: Optional[int] = None) -> dict:
        """
        Запускает полный конвейер обработки.
        Возвращает статистику: {'processed': int, 'succeeded': int, 'failed': int}
        """
        # Убедимся, что таблицы созданы
        await create_db_and_tables()

        # Находим все файлы
        files = self.find_audio_files(root_dir)
        if limit:
            files = files[:limit]

        _log.info(f"Found {len(files)} audio files to process")
        print(f"🎵 Найдено {len(files)} аудиофайлов. Начинаем обработку с {self.max_workers} воркерами...")

        succeeded = 0
        failed = 0
        skipped = 0

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            semaphore = asyncio.Semaphore(self.max_workers * 2)

            async def bounded_process(file_path: Path):
                nonlocal succeeded, failed, skipped
                async with semaphore:
                    success, status = await self.process_file_async(file_path, executor)
                    if success:
                        succeeded += 1
                    elif status == 'skipped':
                        skipped += 1
                    else:
                        failed += 1

                    processed = succeeded + failed + skipped
                    if processed % 10 == 0:
                        print(f"Прогресс: {processed}/{len(files)} [✅ {succeeded} | ⏭️ {skipped} | ❌ {failed}]")

            # Запускаем все задачи
            tasks = [bounded_process(f) for f in files]
            await asyncio.gather(*tasks)

        print(f"Завершено! Успешно: {succeeded}, Ошибок: {failed}")
        return {"processed": succeeded + failed, "succeeded": succeeded, "failed": failed, "skipped": skipped}
