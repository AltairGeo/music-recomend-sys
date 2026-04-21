import logging
from multiprocessing import Queue
import asyncio
from .dto import TrackProcessed
from src.core.tracks.ports import TracksCrudPort, EmbeddingsCrudPort
from src.core.tracks.ports import TracksStoragePort
from src.core.tracks.domains import Track
from src.core.audio_processing.domains import TrackEmbedding

_log = logging.getLogger(__name__)


async def async_embedding_saver(output_queue: Queue[TrackProcessed|None], tracks_dao: TracksCrudPort, storage: TracksStoragePort, embeddings_dao: EmbeddingsCrudPort):

    print("Track saver STARTED!")
    while True:
        try:
            result = await asyncio.to_thread(output_queue.get)

            if result is None:
                break

            file_id = await storage.save(result.audio_raw)

            embedding_id = await embeddings_dao.create(result.embedding)

            if not embedding_id:
                raise ValueError("NO EMBEDDING ID!!!")

            track = Track(
                id=0,
                title=result.title,
                artist=result.artist,
                genre=result.genre,
                year=result.year,
                album=result.album,
                additional_info=result.additional_info,
                license=result.license,
                audio_url="",
                embedding=TrackEmbedding(
                    id=embedding_id,
                    vector=result.embedding
                ),
                file_id=file_id,
                file_hash=result.file_hash
            )

            track_id = await tracks_dao.create(track)



            if not track_id:
                _log.warning("NO TRACK ID: %s, RESULT_OBJ: %s, track_OBJ: %s", track_id, result, track)

            print(f"Ingest a track with id: {track_id}")

        except Exception as e:
            print(f"Error in async_embedding_saver: {e}")

def embedding_writer_process(
    output_queue: Queue,
    tracks_dao,
    storage,
    embeddings_dao,
):
    asyncio.run(
        async_embedding_saver(
            output_queue=output_queue,
            tracks_dao=tracks_dao,
            storage=storage,
            embeddings_dao=embeddings_dao,
        )
    )
