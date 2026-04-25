from typing import BinaryIO, TypedDict

import librosa
import numpy as np


class AudioFeatures(TypedDict):
    mfcc: np.ndarray
    spectral_centroid: np.ndarray
    spectral_bandwidth: np.ndarray
    spectral_contrast: np.ndarray
    spectral_rolloff: np.ndarray
    spectral_flatness: np.ndarray
    chroma_stft: np.ndarray
    chroma_cqt: np.ndarray
    rms: np.ndarray
    zero_crossing_rate: np.ndarray
    tonnetz: np.ndarray


class AudioProcessor:
    def __init__(
        self,
        sample_rate: int = 22050,
        n_mfcc: int = 20,
        n_fft: int = 2048,
        hop_length: int = 512,
    ) -> None:
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.n_fft = n_fft
        self.hop_length = hop_length

    def load_audio(self, file: BinaryIO) -> np.ndarray:
        """
        Загружает аудио, приводит к mono и ресэмплит к нужной частоте.
        Если это file-like объект, пытается перемотать в начало.
        """
        if hasattr(file, "seek"):
            try:
                file.seek(0)
            except Exception:
                pass

        y, _ = librosa.load(
            file,
            sr=self.sample_rate,
            mono=True,
        )

        if y.size == 0:
            raise ValueError("Пустой аудиофайл или не удалось прочитать аудио.")

        # Нормализация амплитуды
        y = librosa.util.normalize(y)

        # Убираем тишину по краям
        y, _ = librosa.effects.trim(y, top_db=30)

        if y.size == 0:
            raise ValueError("После удаления тишины аудио стало пустым.")

        return y

    def extract_features(self, audio: np.ndarray) -> AudioFeatures:
        features: AudioFeatures = {} # type: ignore

        features["mfcc"] = librosa.feature.mfcc(
            y=audio,
            sr=self.sample_rate,
            n_mfcc=self.n_mfcc,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
        )

        features["spectral_centroid"] = librosa.feature.spectral_centroid(
            y=audio,
            sr=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
        )

        features["spectral_bandwidth"] = librosa.feature.spectral_bandwidth(
            y=audio,
            sr=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
        )

        features["spectral_contrast"] = librosa.feature.spectral_contrast(
            y=audio,
            sr=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
        )

        features["spectral_rolloff"] = librosa.feature.spectral_rolloff(
            y=audio,
            sr=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
        )

        features["spectral_flatness"] = librosa.feature.spectral_flatness(
            y=audio,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
        )

        features["chroma_stft"] = librosa.feature.chroma_stft(
            y=audio,
            sr=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
        )

        # chroma_cqt иногда может падать на проблемных фрагментах
        try:
            features["chroma_cqt"] = librosa.feature.chroma_cqt(
                y=audio,
                sr=self.sample_rate,
                hop_length=self.hop_length,
            )
        except Exception:
            # Если CQT не удалось посчитать
            features["chroma_cqt"] = np.zeros((12, max(1, len(audio) // self.hop_length + 1)))

        features["rms"] = librosa.feature.rms(
            y=audio,
            frame_length=self.n_fft,
            hop_length=self.hop_length,
        )

        features["zero_crossing_rate"] = librosa.feature.zero_crossing_rate(
            y=audio,
            frame_length=self.n_fft,
            hop_length=self.hop_length,
        )

        try:
            features["tonnetz"] = librosa.feature.tonnetz(
                y=audio,
                sr=self.sample_rate,
                hop_length=self.hop_length,
            )
        except Exception:
            features["tonnetz"] = np.zeros((6, max(1, len(audio) // self.hop_length + 1)))


        return features

    @staticmethod
    def _safe_stats_2d(x: np.ndarray) -> list[np.ndarray]:
        """
        Для матрицы (n_features, frames) возвращает:
        mean по времени, std по времени, delta_mean по времени.
        """
        if x.ndim != 2:
            x = np.atleast_2d(x)

        mean = np.mean(x, axis=1)
        std = np.std(x, axis=1)

        try:
            delta = librosa.feature.delta(x)
            delta_mean = np.mean(delta, axis=1)
        except Exception:
            delta_mean = np.zeros_like(mean)

        return [mean, std, delta_mean]

    @staticmethod
    def _safe_stats_1d(x: float | np.ndarray) -> np.ndarray:
        if isinstance(x, np.ndarray):
            value = float(np.mean(x))
        else:
            value = float(x)
        return np.array([value], dtype=np.float32)

    def aggregate_features(self, features: AudioFeatures) -> np.ndarray:
        parts: list[np.ndarray] = []

        # Основной спектрально-тембральный блок
        parts.extend(self._safe_stats_2d(features["mfcc"]))
        parts.extend(self._safe_stats_2d(features["spectral_centroid"]))
        parts.extend(self._safe_stats_2d(features["spectral_bandwidth"]))
        parts.extend(self._safe_stats_2d(features["spectral_contrast"]))
        parts.extend(self._safe_stats_2d(features["spectral_rolloff"]))
        parts.extend(self._safe_stats_2d(features["spectral_flatness"]))

        # Гармония
        parts.extend(self._safe_stats_2d(features["chroma_stft"]))
        parts.extend(self._safe_stats_2d(features["chroma_cqt"]))
        parts.extend(self._safe_stats_2d(features["tonnetz"]))

        # Энергия и ритм
        parts.extend(self._safe_stats_2d(features["rms"]))
        parts.extend(self._safe_stats_2d(features["zero_crossing_rate"]))

        vector = np.concatenate([p.astype(np.float32).ravel() for p in parts])

        # Финальная нормализация вектора для cosine/L2 search.
        norm = np.linalg.norm(vector)
        if norm > 1e-12:
            vector = vector / norm
        else:
            vector = np.zeros_like(vector)

        return vector.astype(np.float32)

    def create_embedding(self, file: BinaryIO) -> np.ndarray:
        audio = self.load_audio(file)
        features = self.extract_features(audio)
        return self.aggregate_features(features)
