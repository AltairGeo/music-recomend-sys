from dataclasses import dataclass


@dataclass(slots=True)
class TrackEmbedding:
    id: int
    vector: list[float]
