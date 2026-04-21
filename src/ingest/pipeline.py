# /src/ingest/pipeline.py

import asyncio
import logging
import multiprocessing as mp
from pathlib import Path
from typing import Optional, Set, List
from concurrent.futures import ProcessPoolExecutor

from sqlalchemy.exc import IntegrityError

from src.driven.database.session import create_db_and_tables
from src.driven.database.tracks.dao import TracksCrudDao, EmbeddingsCrudDAO
from src.driven.filesystem.tracks_storage import LocalTracksStorage

from src.ingest.worker import process_file, compute_file_hash

from src.core.tracks.domains import Track
from src.core.audio_processing.domains import TrackEmbedding
from src.settings import app_config


_log = logging.getLogger(__name__)


class IngestPipeline:
    """
    Массовый ingestion аудио файлов.

    Архитектура:
        main process:
            - управляет очередью
            - сохраняет в БД
            - сохраняет файлы

        worker process:
            - читает аудио
            - извлекает embedding
            - парсит metadata

    Важно:
        worker НЕ возвращает audio_bytes
        это предотвращает OOM и BrokenProcessPool
    """

    def __init__(
        self,
        max_workers: int = 4,
        supported_extensions: Optional[Set[str]] = None,
    ):
        self.max_workers = max_workers

        self.supported_extensions = supported_extensions or {
            ".mp3",
            ".flac",
            ".m4a",
            ".ogg",
            ".wav",
        }

        # DAO
        self.tracks_dao = TracksCrudDao()
        self.emb_dao = EmbeddingsCrudDAO()

        # storage
        self.storage = LocalTracksStorage(
            app_config.music_data_folder / "tracks"
        )

    # ------------------------------------------------------------
    # FILE DISCOVERY
    # ------------------------------------------------------------

    def find_audio_files(self, root_dir: Path) -> List[Path]:
        """
        Рекурсивно находит все аудиофайлы.
        Без glob (он медленный на больших директориях)
        """
        result: List[Path] = []

        for path in root_dir.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() in self.supported_extensions:
                result.append(path)

        return result

    # ------------------------------------------------------------
    # WORKER CALL
    # ------------------------------------------------------------

    async def process_file_async(
        self,
        file_path: Path,
        executor: ProcessPoolExecutor,
    ):
        """
        Запускает CPU-heavy обработку в отдельном процессе.

        Важно:
            worker возвращает только metadata + embedding
            НЕ возвращает audio bytes
        """

        loop = asyncio.get_running_loop()

        metadata, embedding, *_ = await loop.run_in_executor(
            executor,
            process_file,
            file_path,
        )

        return metadata, embedding, file_path

    # ------------------------------------------------------------
    # DATABASE SAVE
    # ------------------------------------------------------------

    async def save_result(
        self,
        metadata,
        embedding,
        file_path: Path,
    ) -> tuple[bool, str]:
        """
        Сохраняет результат обработки в БД и storage.
        """

        try:
            # читаем файл только в main процессе
            audio_bytes = file_path.read_bytes()

            file_hash = compute_file_hash(audio_bytes)

            # проверка на существование
            existing = await self.tracks_dao.find_by_file_hash(file_hash)
            if existing:
                return False, "skipped"

            # сохраняем файл
            file_id = await self.storage.save(audio_bytes)

            # сохраняем embedding
            embedding_list = embedding.tolist()
            embedding_id = await self.emb_dao.create(embedding_list)

            if not embedding_id:
                return False, "failed"

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
                    vector=embedding_list,
                ),
                file_id=file_id,
                file_hash=file_hash,
            )

            track_id = await self.tracks_dao.create(track)

            if track_id:
                return True, "success"

            return False, "error"

        except IntegrityError:
            # защита от race condition
            return False, "skipped"

        except Exception:
            _log.exception("Failed to save result")
            return False, "error"

    # ------------------------------------------------------------
    # WORKER LOOP
    # ------------------------------------------------------------

    async def worker(
        self,
        queue: asyncio.Queue,
        executor: ProcessPoolExecutor,
        stats,
        stats_lock,
        total,
    ):
        """
        Один worker coroutine.

        Берёт файл из очереди:
            -> отправляет в process pool
            -> сохраняет результат
        """

        while True:
            try:
                file_path = queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            try:
                metadata, embedding, file_path = await self.process_file_async(
                    file_path,
                    executor,
                )

                success, status = await self.save_result(
                    metadata,
                    embedding,
                    file_path,
                )

            except Exception:
                _log.exception("Worker crash")
                success = False
                status = "error"

            # обновление статистики
            async with stats_lock:
                if success:
                    stats["succeeded"] += 1
                elif status == "skipped":
                    stats["skipped"] += 1
                else:
                    stats["failed"] += 1

                processed = (
                    stats["succeeded"]
                    + stats["failed"]
                    + stats["skipped"]
                )

                if processed % 10 == 0:
                    print(
                        f"Прогресс: {processed}/{total} "
                        f"[✅ {stats['succeeded']} "
                        f"| ⏭ {stats['skipped']} "
                        f"| ❌ {stats['failed']}]"
                    )

            queue.task_done()

    # ------------------------------------------------------------
    # MAIN ENTRY
    # ------------------------------------------------------------

    async def run(
        self,
        root_dir: Path,
        limit: Optional[int] = None,
    ):
        """
        Запускает ingestion pipeline.
        """

        await create_db_and_tables()

        files = self.find_audio_files(root_dir)

        if limit is not None:
            files = files[:limit]

        total = len(files)

        print(f"Найдено файлов: {total}")
        print(f"Workers: {self.max_workers}")

        queue: asyncio.Queue[Path] = asyncio.Queue()

        for f in files:
            queue.put_nowait(f)

        stats = {
            "succeeded": 0,
            "failed": 0,
            "skipped": 0,
        }

        stats_lock = asyncio.Lock()

        # ВАЖНО:
        # используем spawn вместо fork
        ctx = mp.get_context("spawn")

        with ProcessPoolExecutor(
            max_workers=self.max_workers,
            mp_context=ctx,
        ) as executor:

            workers = [
                asyncio.create_task(
                    self.worker(
                        queue,
                        executor,
                        stats,
                        stats_lock,
                        total,
                    )
                )
                for _ in range(self.max_workers)
            ]

            await asyncio.gather(*workers)

        print()
        print("Готово:")
        print("успешно:", stats["succeeded"])
        print("пропущено:", stats["skipped"])
        print("ошибок:", stats["failed"])

        return {
            "processed": sum(stats.values()),
            **stats,
        }
