import asyncio
import logging
from multiprocessing import Queue, Process, process
from src.core.tracks.domains import Track
from src.settings import app_config
from src.driven.database.tracks.dao import EmbeddingsCrudDAO, TracksCrudDao
from src.driven.filesystem.tracks_storage import LocalTracksStorage
from src.driven.database.session import create_db_and_tables
from .dto import TrackProcessed, TrackQueueIn
from .async_saver import async_embedding_saver

from pathlib import Path
from .hasher import compute_file_hash
from .worker import embedding_worker


_log = logging.getLogger(__name__)

class IngestPipeline:
    def __init__(self, max_workers: int = 4) -> None:
        self._max_workers = max_workers

        self.supported_extensions = {
            ".mp3",
            ".flac",
            ".m4a",
            ".ogg",
            ".wav",
        }

        self.tracks_dao = TracksCrudDao()
        self.emb_dao = EmbeddingsCrudDAO()

        self.storage = LocalTracksStorage(
            app_config.music_data_folder / "tracks"
        )

    def __find_audio_files(self, root_dir: Path) -> list[Path]:

        result: list[Path] = []

        for path in root_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in self.supported_extensions:
                result.append(path)

        _log.info("Find %s audios to ingest", len(result))

        return result

    def __get_paths_to_hash(self, paths: list[Path]) -> dict[Path, str]:
        table_path_to_hash: dict[Path, str] = {}

        for trackpath in paths:
            with open(trackpath, "rb") as file:
                trackhash = compute_file_hash(file.read())

            table_path_to_hash[trackpath] = trackhash

        _log.info("create table_path_to_hash")

        return table_path_to_hash

    async def __get_processed_hashs(self) -> set[str]:
        hashs = await self.tracks_dao.get_hashs()
        return set(hashs)

    async def __get_unprocessed_paths(self, paths: list[Path]) -> dict[Path, str]:
        paths_to_hash = self.__get_paths_to_hash(paths)

        processed_hashs = await self.__get_processed_hashs()

        for tpath, thash in list(paths_to_hash.items()):
            if thash in processed_hashs:
                del paths_to_hash[tpath]

        unprocessed_tracks = [tpath for tpath in paths_to_hash.keys()]

        _log.info("Skipped - %s tracks.", (len(paths) - len(unprocessed_tracks)))

        return paths_to_hash

    async def run(self, root_dir: Path, limit: int|None = None):
        loop = asyncio.get_event_loop()


        await create_db_and_tables()

        #
        # Создание очередей и их заполнение
        #
        input_q: Queue[TrackQueueIn|None] = Queue()
        output_q: Queue[TrackProcessed|None] = Queue()

        _log.info("Ingest: Create rqueues!")



        files = self.__find_audio_files(root_dir)

        if  (limit is not None) and (limit < 2):
            limit = None

        if limit:
            files = files[:limit]


        unprocessed_paths = await self.__get_unprocessed_paths(files)

        _log.info("Ingest: Find audio and getted only unprocessed")

        for tpath, thash in unprocessed_paths.items():
            input_q.put(TrackQueueIn(tpath=tpath, thash=thash))

        #
        # Создание процессов-воркеров
        #

        processes = [Process(target=embedding_worker, args=(input_q, output_q)) for _ in range(self._max_workers)]

        for p in processes:
            p.start()

        async def __run_writter():
            await async_embedding_saver(output_queue=output_q, storage=self.storage, tracks_dao=self.tracks_dao, embeddings_dao=self.emb_dao)

        loop.create_task(
            __run_writter()
        )

        for _ in processes:
            input_q.put(None)

        _log.info("Workers has started!")

        for p in processes:
            p.join()

        _log.info("END OF WORK!")
