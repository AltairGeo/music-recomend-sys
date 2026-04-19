from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import logging
from src.core.audio_processing.processor import AudioProcessor
from src.ingest.metadata import extract_metadata
from src.settings import app_config
import hashlib

_log = logging.getLogger(__name__)

# Инициализируем аудиопроцессор глобально в модуле, чтобы не пересоздавать
_audio_processor = AudioProcessor(sample_rate=22050, n_mfcc=app_config.n_mfcc)


def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def process_file(file_path: Path) -> Tuple[Dict[str, Any], np.ndarray, bytes]:
    """
    Обрабатывает один аудиофайл: читает данные, извлекает признаки и метаданные.
    Возвращает кортеж: (метаданные, вектор эмбеддинга, байты файла).

    Эта функция синхронная и будет запускаться в отдельном процессе.
    """

    # Читаем байты файла для сохранения в хранилище
    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    # Извлекаем метаданные
    metadata = extract_metadata(file_path)

    import io
    audio_io = io.BytesIO(audio_bytes)
    embedding = _audio_processor.create_embedding(audio_io)

    return metadata, embedding, audio_bytes
