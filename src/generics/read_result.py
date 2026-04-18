from dataclasses import dataclass

@dataclass(slots=True)
class ReadDTO[M]:
    entities: list[M]

    count_entities: int
    offset: int
    limit: int
