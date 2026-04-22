import librosa
import numpy as np
from typing import BinaryIO, Literal, TypedDict


class AudioFeatures(TypedDict):
    mfcc: np.ndarray
    spectral_centroid: np.ndarray
    spectral_bandwidth: np.ndarray
    spectral_contrast: np.ndarray
    chroma_stft: np.ndarray
    chroma_cqt: np.ndarray
    rmse: np.ndarray
    tempo: float
    zero_crossing_rate: np.ndarray
    tonnetz: np.ndarray


class AudioProcessor:
    def __init__(self, sample_rate: int = 22050, n_mfcc: int = 13) -> None:
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc

    def load_audio(self, file: BinaryIO) -> np.ndarray:
        """Загрузка аудио с помощью librosa + рессэмплинг"""
        y, _ = librosa.load(file, sr=self.sample_rate, mono=True)
        return y

    def extract_features(self, audio: np.ndarray) -> AudioFeatures:
        features: AudioFeatures = dict()  # type: ignore

        # MFCC
        features["mfcc"] = librosa.feature.mfcc(
            y=audio, sr=self.sample_rate, n_mfcc=self.n_mfcc
        )

        # Спектральные
        features["spectral_centroid"] = librosa.feature.spectral_centroid(
            y=audio, sr=self.sample_rate
        )
        features["spectral_bandwidth"] = librosa.feature.spectral_bandwidth(
            y=audio, sr=self.sample_rate
        )
        features["spectral_contrast"] = librosa.feature.spectral_contrast(
            y=audio, sr=self.sample_rate
        )

        # Chroma
        features["chroma_stft"] = librosa.feature.chroma_stft(
            y=audio, sr=self.sample_rate
        )
        features["chroma_cqt"] = librosa.feature.chroma_cqt(y=audio, sr=self.sample_rate)

        # Energy features
        features["rmse"] = librosa.feature.rms(y=audio)
        features["zero_crossing_rate"] = librosa.feature.zero_crossing_rate(y=audio)

        features["tempo"], *_ = librosa.beat.beat_track(y=audio, sr=self.sample_rate) # type: ignore

        features["zero_crossing_rate"] = librosa.feature.zero_crossing_rate(y=audio)


        # tonal

        tonnetz = librosa.feature.tonnetz(y=audio, sr=self.sample_rate)
        features["tonnetz"] = tonnetz

        return features

    def aggregate_features(self, features: AudioFeatures):
        vector_parts = []

        # MFCC
        mfcc = features["mfcc"]

        mfcc_mean = np.mean(mfcc, axis=1)
        mfcc_std = np.std(mfcc, axis=1)
        mfcc_delta = np.mean(librosa.feature.delta(mfcc), axis=1)

        vector_parts.extend([mfcc_mean, mfcc_std, mfcc_delta])

        # Спектральные
        for key in ("spectral_centroid", "spectral_bandwidth", "spectral_contrast"):
            if key in features:
                spec_feat = features[key]
                if spec_feat.ndim == 2:
                    time_mean = np.mean(spec_feat, axis=1)
                    band_mean = np.mean(time_mean)
                    vector_parts.append(np.array([band_mean]))
                else:
                    vector_parts.append(np.array([np.mean(spec_feat)]))

        # Chroma
        chroma = features["chroma_stft"]
        chroma_mean = np.mean(chroma, axis=1)
        vector_parts.append(chroma_mean)

        chroma_cqt = np.mean(features["chroma_cqt"], axis=1)
        vector_parts.append(chroma_cqt)

        # Тональные
        if "tonal" in features:
            tonal = features["tonal"]
            tonal_mean = np.mean(tonal, axis=1)
            vector_parts.append(tonal_mean)

        energy_keys = ["rmse", "zero_crossing_rate"]
        for key in energy_keys:
            if key in features:
                energy = features[key]
                energy_mean = np.mean(energy)
                vector_parts.append(np.array([energy_mean]))

        if "tempo" in features:
            tempo = features["tempo"]
            vector_parts.append(np.array([tempo]))

        # Tonnetz
        tonnetz_mean = np.mean(features["tonnetz"], axis=1)
        tonnetz_std = np.std(features["tonnetz"], axis=1)
        vector_parts.extend([tonnetz_mean, tonnetz_std])

        final_vector = np.concatenate([part.flatten() for part in vector_parts])

        return final_vector

    def normalize_vector(
        self, vector: np.ndarray, method: Literal["minmax", "zscore"] = "minmax"
    ) -> np.ndarray:
        if method == "minmax":
            # Min-max нормализация [0, 1]
            v_min = np.min(vector)
            v_max = np.max(vector)
            if v_max - v_min > 1e-8:
                return (vector - v_min) / (v_max - v_min)
            else:
                return np.zeros_like(vector)
        elif method == "zscore":
            # Z-score нормализация
            mean = np.mean(vector)
            std = np.std(vector)
            if std > 1e-8:
                return (vector - mean) / std
            else:
                return np.zeros_like(vector)
        else:
            return vector

    def create_embedding(self, file: BinaryIO) -> np.ndarray:
        # Загрузка аудио
        audio = self.load_audio(file)

        # Извлечение признаков
        features = self.extract_features(audio)

        # Агрегация в вектор
        raw_vector = self.aggregate_features(features)

        # Нормализация
        normalized_vector = self.normalize_vector(raw_vector, method="minmax")

        return normalized_vector
