import logging
from typing import Optional
from annoy import AnnoyIndex

from src.core.recommendation.ports import RecommendationPort
from src.core.tracks.domains import Track
from src.driven.database.tracks.dao import TracksCrudDao, EmbeddingsCrudDAO
from src.driven.database.session import async_session_maker
from sqlalchemy import text
from typing import Literal

_log = logging.getLogger(__name__)


class AnnoyRecommendationAdapter(RecommendationPort):
    def __init__(
        self,
        tracks_dao: TracksCrudDao,
        embeddings_dao: EmbeddingsCrudDAO,
        n_trees: int = 10,
        metric: Literal[
            "angular", "euclidean", "manhattan", "hamming", "dot"
        ] = "angular",
    ):
        self._tracks_dao = tracks_dao
        self._embeddings_dao = embeddings_dao
        self._n_trees = n_trees
        self._metric: Literal["angular", "euclidean", "manhattan", "hamming", "dot"] = (
            metric
        )

        self._index: Optional[AnnoyIndex] = None
        self._id_to_track_id: list[int] = []
        self._vector_dim: Optional[int] = None

    async def build_index(self) -> None:
        """Загружает все эмбеддинги из БД и строит Annoy индекс."""
        _log.info("Building Annoy index...")

        # Загружаем все эмбеддинги с track_id
        async with async_session_maker() as session:
            stmt = text("""
                SELECT t.id, e.vector
                FROM tracks t
                JOIN tracks_embeddings e ON t.embedding_id = e.id
                ORDER BY t.id
            """)
            result = await session.execute(stmt)
            rows = result.fetchall()

        if not rows:
            raise RuntimeError(
                "No tracks found in database. Please run 'recomusic ingest' first."
            )

        # Автоопределение размерности по первому вектору
        first_vector = rows[0][1]
        self._vector_dim = len(first_vector)
        _log.info(f"Detected vector dimension: {self._vector_dim}")

        # Создаём индекс
        self._index = AnnoyIndex(self._vector_dim, self._metric)
        self._id_to_track_id = []

        for idx, (track_id, vector) in enumerate(rows):
            self._index.add_item(idx, vector)
            self._id_to_track_id.append(track_id)

        _log.info(f"Added {len(rows)} vectors to index")

        # Строим индекс
        self._index.build(self._n_trees)
        _log.info("Annoy index built successfully")

    async def find_similar_by_id(
        self, track_id: int, k: int = 10
    ) -> list[tuple[Track, float]]:
        """Находит похожие треки по ID существующего трека."""
        if self._index is None:
            raise RuntimeError("Index not built. Call build_index() first")

        # Находим индекс в Annoy по track_id
        try:
            annoy_id = self._id_to_track_id.index(track_id)
        except ValueError:
            _log.error(f"Track {track_id} not found in index")
            return []

        # Получаем вектор трека
        vector = self._index.get_item_vector(annoy_id)

        return await self._find_similar_by_vector(vector, k, exclude_track_id=track_id)

    async def find_similar_by_vector(
        self, vector: list[float], k: int = 10
    ) -> list[tuple[Track, float]]:
        """Находит похожие треки по вектору признаков."""
        if self._index is None:
            raise RuntimeError("Index not built. Call build_index() first")

        # Проверяем размерность вектора
        if self._vector_dim and len(vector) != self._vector_dim:
            raise ValueError(
                f"Vector dimension mismatch: expected {self._vector_dim}, got {len(vector)}"
            )

        return await self._find_similar_by_vector(vector, k)

    async def _find_similar_by_vector(
        self, vector: list[float], k: int, exclude_track_id: Optional[int] = None
    ) -> list[tuple[Track, float]]:
        """Внутренний метод поиска похожих треков по вектору."""
        # Запрашиваем k+1 на случай, если исходный трек попадёт в результаты
        search_k = k + 1 if exclude_track_id else k
        search_k = min(search_k, len(self._id_to_track_id))

        annoy_ids, distances = self._index.get_nns_by_vector(  # type: ignore
            vector, search_k, include_distances=True
        )

        results = []
        for annoy_id, distance in zip(annoy_ids, distances):
            track_id = self._id_to_track_id[annoy_id]

            # Пропускаем исходный трек
            if exclude_track_id and track_id == exclude_track_id:
                continue

            # Конвертируем angular distance в similarity (0-1)
            similarity = 1.0 - (distance / 2.0)

            track = await self._tracks_dao.get(track_id)
            if track:
                results.append((track, similarity))

            if len(results) >= k:
                break

        return results
