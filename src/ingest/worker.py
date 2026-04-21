from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import logging
import io
import hashlib

from src.core.audio_processing.processor import AudioProcessor
from src.ingest.metadata import extract_metadata
from src.settings import app_config

_log = logging.getLogger(__name__)

_audio_processor = None


def _get_processor():
    global _audio_processor

    if _audio_processor is None:
        _audio_processor = AudioProcessor(
            sample_rate=22050,
            n_mfcc=app_config.n_mfcc
        )

    return _audio_processor


def process_file(file_path: Path) -> Tuple[Dict[str, Any], np.ndarray]:
    """
    Worker process entrypoint
    """

    metadata = extract_metadata(file_path)

    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    audio_io = io.BytesIO(audio_bytes)

    processor = _get_processor()
    embedding = processor.create_embedding(audio_io)

    return metadata, embedding

def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()
