import asyncio
import logging
import multiprocessing as mp
from multiprocessing.context import SpawnContext, SpawnProcess
import queue as queue_module
from collections import deque
from pathlib import Path
from typing import Optional, Set, List, Dict, Any

from sqlalchemy.exc import IntegrityError


from src.driven.database.session import create_db_and_tables
from src.driven.database.tracks.dao import TracksCrudDao, EmbeddingsCrudDAO
from src.driven.filesystem.tracks_storage import LocalTracksStorage
from src.ingest.worker import process_file_job, compute_file_hash

from src.core.tracks.domains import Track
from src.core.audio_processing.domains import TrackEmbedding
from src.settings import app_config


_log = logging.getLogger(__name__)


class IngestPipeline:
    """
    Надёжный ingestion pipeline для аудиофайлов.

    Архитектура:
        main process:
            - находит файлы
            - запускает отдельные процессы на обработку
            - сохраняет данные в БД и storage
            - следит за падениями воркеров

        worker process:
            - читает файл
            - извлекает метаданные
            - считает embedding
            - возвращает результат через очередь

    Отличие от ProcessPoolExecutor:
        - здесь падение одного процесса не ломает весь пайплайн
        - можно безопасно перезапустить упавший job
    """

    def __init__(
        self,
        max_workers: int = 4,
        supported_extensions: Optional[Set[str]] = None,
        max_retries: int = 1,
    ):
        self.max_workers = max_workers
        self.max_retries = max_retries

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
        Рекурсивно находит аудиофайлы с поддерживаемыми расширениями.
        """
        result: List[Path] = []

        for path in root_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in self.supported_extensions:
                result.append(path)

        return result

    # ------------------------------------------------------------
    # WORKER MANAGEMENT
    # ------------------------------------------------------------

    def _start_job(
        self,
        ctx: SpawnContext,
        file_path: Path,
        result_queue,
    ) -> SpawnProcess:
        """
        Запускает отдельный процесс для одного файла.
        """
        proc = ctx.Process(
            target=process_file_job,
            args=(str(file_path), result_queue),
            daemon=False,
        )
        proc.start()
        return proc

    async def _get_result(self, result_queue):
        """
        Неблокирующее ожидание результата из multiprocessing.Queue.
        """
        try:
            return await asyncio.to_thread(result_queue.get, True, 0.5)
        except queue_module.Empty:
            return None

    # ------------------------------------------------------------
    # DATABASE SAVE
    # ------------------------------------------------------------

    async def save_result(
        self,
        metadata: Dict[str, Any],
        embedding: List[float],
        file_path: Path,
    ) -> tuple[bool, str]:
        """
        Сохраняет результат обработки в storage и БД.
        """

        try:
            # Читаем файл только в main процессе.
            # Это нужно для хэша и сохранения файла.
            audio_bytes = file_path.read_bytes()
            file_hash = compute_file_hash(audio_bytes)

            # Ранняя проверка на дубликат.
            existing = await self.tracks_dao.find_by_file_hash(file_hash)
            if existing:
                return False, "skipped"

            # Сохраняем файл в storage.
            file_id = await self.storage.save(audio_bytes)

            # Сохраняем embedding.
            embedding_id = await self.emb_dao.create(embedding)
            if not embedding_id:
                return False, "failed"

            # Собираем доменную модель трека.
            track = Track(
                id=0,
                title=metadata.get("title", file_path.stem),
                artist=metadata.get("artist", "Unknown"),
                genre=metadata.get("genre", ""),
                year=metadata.get("year", 0),
                album=metadata.get("album", ""),
                additional_info=metadata.get("additional_info", ""),
                license=metadata.get("license", ""),
                audio_url="",
                embedding=TrackEmbedding(
                    id=embedding_id,
                    vector=embedding,
                ),
                file_id=file_id,
                file_hash=file_hash,
            )

            track_id = await self.tracks_dao.create(track)
            if track_id:
                return True, "success"

            return False, "error"

        except IntegrityError:
            # Защита от гонки между одинаковыми файлами.
            return False, "skipped"

        except Exception:
            _log.exception("Failed to save result for %s", file_path)
            return False, "error"

    # ------------------------------------------------------------
    # MAIN ENTRY
    # ------------------------------------------------------------

    async def run(
        self,
        root_dir: Path,
        limit: Optional[int] = None,
    ) -> dict:
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

        if total == 0:
            return {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}

        ctx = mp.get_context("spawn")
        result_queue = ctx.Queue()

        pending = deque(files)

        # active[file_path] = process
        active: Dict[str, mp.Process] = {}

        # Сколько раз уже пытались обработать конкретный файл.
        retries: Dict[str, int] = {str(path): 0 for path in files}

        stats = {
            "succeeded": 0,
            "failed": 0,
            "skipped": 0,
        }

        def processed_count() -> int:
            return stats["succeeded"] + stats["failed"] + stats["skipped"]

        def print_progress() -> None:
            done = processed_count()
            print(
                f"Прогресс: {done}/{total} "
                f"[✅ {stats['succeeded']} | ⏭ {stats['skipped']} | ❌ {stats['failed']}]"
            )

        try:
            while pending or active:
                # 1) Дозапускаем процессы, если есть свободные слоты.
                while pending and len(active) < self.max_workers:
                    file_path = pending.popleft()
                    proc = self._start_job(ctx, file_path, result_queue)
                    active[str(file_path)] = proc

                # 2) Пытаемся получить результат.
                message = await self._get_result(result_queue)

                if message is not None:
                    file_path_str = message["file_path"]
                    ok = message["ok"]

                    # Процесс для этого файла больше не нужен.
                    proc = active.pop(file_path_str, None)
                    if proc is not None:
                        proc.join(timeout=0.1)

                    if ok:
                        metadata = message["metadata"]
                        embedding = message["embedding"]

                        success, status = await self.save_result(
                            metadata,
                            embedding,
                            Path(file_path_str),
                        )

                        if success:
                            stats["succeeded"] += 1
                        elif status == "skipped":
                            stats["skipped"] += 1
                        else:
                            stats["failed"] += 1
                    else:
                        _log.error(
                            "Worker error for %s:\n%s",
                            file_path_str,
                            message["error"],
                        )
                        stats["failed"] += 1

                    if processed_count() % 10 == 0:
                        print_progress()

                    continue

                # 3) Если результатов нет, проверяем, не умер ли какой-то процесс.
                # Это нужно для случая, когда воркер упал без сообщения в result_queue.
                crashed_files: List[str] = []

                for file_path_str, proc in list(active.items()):
                    if proc.is_alive():
                        continue

                    proc.join(timeout=0.1)

                    # Если процесс завершился, а результата так и не пришло,
                    # считаем это падением.
                    crashed_files.append(file_path_str)

                for file_path_str in crashed_files:
                    proc = active.pop(file_path_str, None)
                    if proc is not None:
                        proc.join(timeout=0.1)

                    if retries[file_path_str] < self.max_retries:
                        retries[file_path_str] += 1
                        pending.appendleft(Path(file_path_str))
                        _log.warning(
                            "Restarting crashed job: %s (attempt %d/%d)",
                            file_path_str,
                            retries[file_path_str],
                            self.max_retries,
                        )
                    else:
                        _log.error(
                            "Giving up on crashed job: %s",
                            file_path_str,
                        )
                        stats["failed"] += 1

                        if processed_count() % 10 == 0:
                            print_progress()

            print()
            print("Готово:")
            print("успешно:", stats["succeeded"])
            print("пропущено:", stats["skipped"])
            print("ошибок:", stats["failed"])

            return {
                "processed": processed_count(),
                **stats,
            }

        finally:
            # Аккуратно завершаем все оставшиеся процессы.
            for proc in active.values():
                if proc.is_alive():
                    proc.terminate()
                proc.join(timeout=0.5)

            result_queue.close()
            result_queue.join_thread()
