import logging
from src.core.audio_processing.processor import AudioProcessor
from multiprocessing import Queue
from .dto import TrackProcessed, TrackQueueIn
from pathlib import Path
from .metadata import extract_metadata
import io

_log = logging.getLogger(__name__)

def embedding_worker(input_queue: Queue[TrackQueueIn|None], output_queue: Queue[TrackProcessed|None]):
    audio_processor = AudioProcessor()
    print("WORKER START!", flush=True)

    while True:
        try:
            item = input_queue.get()

            if item is None:
                break

            with open(item.tpath, "rb") as file:
                audio_bytes = file.read()


            result: list[float] = audio_processor.create_embedding(io.BytesIO(audio_bytes)).tolist()
            print("Create embedding for \"%s\"", item)

            metadata = extract_metadata(item.tpath)

            output_queue.put(
                TrackProcessed(
                    title=metadata.get("title", item.tpath.stem),
                    artist=metadata.get("artist", "Unknown"),
                    genre=metadata.get("genre", "Undefined"),
                    year=metadata.get("year", 0),
                    album=metadata.get("album", "Undefined"),
                    additional_info=metadata.get("additional_info", ""),
                    license=metadata.get("license", "Creative Commons"),
                    embedding=result,
                    file_hash=item.thash,
                    audio_raw=audio_bytes
                )
            )
        except Exception as e:
            print(f"Error in ingest embedding_worker: {e}")

    print("WORKER STOP!")
