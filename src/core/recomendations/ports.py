from typing import Protocol
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.tracks.domains import Track

class RecommendationPort(Protocol):
    async def build_index(self) -> None: ...
    async def find_similar_by_id(self, track_id: int, k: int = 10) -> list[tuple["Track", float]]: ...
    async def find_similar_by_vector(self, vector: list[float], k: int = 10) -> list[tuple["Track", float]]: ...
