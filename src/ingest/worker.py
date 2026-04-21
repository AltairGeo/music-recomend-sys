from pathlib import Path
from typing import Dict, Any
import io
import traceback
import hashlib
import logging

from src.core.audio_processing.processor import AudioProcessor
from src.ingest.metadata import extract_metadata
from src.settings import app_config

_log = logging.getLogger(__name__)


def compute_file_hash(file_bytes: bytes) -> str:
    """
    Стабильный SHA-256 хэш содержимого файла.
    Используется для защиты от дубликатов.
    """
    return hashlib.sha256(file_bytes).hexdigest()


def process_file_job(file_path: str, result_queue) -> None:
    """
    Обрабатывает один файл в отдельном процессе.

    Формат успешного ответа:
        {
            "file_path": "...",
            "ok": True,
            "metadata": {...},
            "embedding": [float, float, ...],
            "error": None
        }

    Формат ошибки:
        {
            "file_path": "...",
            "ok": False,
            "metadata": None,
            "embedding": None,
            "error": "traceback..."
        }
    """
    path = Path(file_path)

    try:
        # Создаём процессор внутри процесса.
        # Так безопаснее, чем пытаться шарить его между процессами.
        processor = AudioProcessor(
            sample_rate=22050,
            n_mfcc=app_config.n_mfcc,
        )

        # Метаданные читаем отдельно.
        metadata = extract_metadata(path)

        # Читаем байты только в worker-процессе.
        # Это нужно для вычисления embedding.
        with path.open("rb") as f:
            audio_bytes = f.read()

        audio_io = io.BytesIO(audio_bytes)

        embedding = processor.create_embedding(audio_io)

        # Переводим embedding в обычный list,
        # чтобы результат был простым для передачи через очередь.
        if hasattr(embedding, "tolist"):
            embedding_list = embedding.tolist()
        else:
            embedding_list = list(embedding)

        result_queue.put(
            {
                "file_path": file_path,
                "ok": True,
                "metadata": metadata,
                "embedding": embedding_list,
                "error": None,
            }
        )

    except Exception:
        # Возвращаем traceback как строку.
        # Это сильно упрощает отладку.
        result_queue.put(
            {
                "file_path": file_path,
                "ok": False,
                "metadata": None,
                "embedding": None,
                "error": traceback.format_exc(),
            }
        )
