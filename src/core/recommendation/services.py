from src.core.recommendation.ports import RecommendationPort
from src.core.tracks.domains import Track
from src.core.tracks.ports import TracksCrudPort


class RecommendationService:
    MAX_K = 20  # Ограничение на количество рекомендаций

    def __init__(
        self,
        recommendation_port: RecommendationPort,
        tracks_port: TracksCrudPort
    ):
        self._rec_port = recommendation_port
        self._tracks_port = tracks_port

    async def build_index(self) -> None:
        """Перестроить индекс Annoy (вызывается при старте приложения)."""
        await self._rec_port.build_index()

    async def get_similar_tracks(self, track_id: int, k: int = 10) -> list[tuple[Track, float]]:
        """
        Получить похожие треки по ID существующего трека.

        Args:
            track_id: ID трека в БД
            k: количество рекомендаций (1-20)

        Raises:
            ValueError: если k вне диапазона или трек не найден
        """
        if not 1 <= k <= self.MAX_K:
            raise ValueError(f"k must be between 1 and {self.MAX_K}")

        # Проверяем существование трека
        track = await self._tracks_port.get(track_id)
        if track is None:
            raise ValueError(f"Track with id {track_id} not found")

        return await self._rec_port.find_similar_by_id(track_id, k)

    async def get_similar_by_vector(self, vector: list[float], k: int = 10) -> list[tuple[Track, float]]:
        """
        Получить похожие треки по вектору признаков (для загруженного файла).

        Args:
            vector: вектор признаков аудио
            k: количество рекомендаций (1-20)

        Raises:
            ValueError: если k вне диапазона или вектор пустой
        """
        if not 1 <= k <= self.MAX_K:
            raise ValueError(f"k must be between 1 and {self.MAX_K}")

        if not vector:
            raise ValueError("Vector cannot be empty")

        return await self._rec_port.find_similar_by_vector(vector, k)
