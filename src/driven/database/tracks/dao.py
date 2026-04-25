from typing import Sequence, Unpack
from src.core.tracks.types import ReadTrackFilters
from src.driven.database.tracks.models import TrackModel, TrackEmbeddingModel
from src.core.tracks.domains import Track
from src.driven.database.session import async_session_maker
from src.utils.conv.from_domain_to_model import trackDomTOtrackMod
from sqlalchemy import func, select, delete
from src.generics.read_result import ReadDTO
import logging

_log = logging.getLogger(__name__)


class TracksCrudDao:
    async def create(self, model: Track) -> int | None:
        try:
            async with async_session_maker() as session:
                db_track = trackDomTOtrackMod(model, model.embedding.id)

                session.add(db_track)
                await session.commit()
                await session.flush()
                return db_track.id
        except Exception as e:
            _log.error("TracksCrudDao error in create method: %s", e)
            return None

    async def get(self, id: int) -> Track | None:
        async with async_session_maker() as session:
            res = await session.get(TrackModel, ident=id)
            if not res:
                return

            return res.dump_to_domain()

    async def read(
        self, skip: int = 0, limit: int = 100, **filters: Unpack[ReadTrackFilters]
    ) -> ReadDTO[Track] | None:
        try:
            async with async_session_maker() as session:
                stmt = select(TrackModel).filter_by(**filters).offset(skip).limit(limit)

                count_stmt = (
                    select(func.count()).select_from(TrackModel).filter_by(**filters)
                )

                return ReadDTO[Track](
                    entities=[
                        i.dump_to_domain()
                        for i in (await session.execute(stmt)).scalars().all()
                    ],
                    count_entities=(await session.execute(count_stmt)).scalar_one(),
                    limit=limit,
                    offset=skip,
                )
        except Exception as e:
            _log.error("TracksCrudDao error in read method: %s", e)
            return None

    async def find_by_name(self, name: str) -> Sequence[Track]:
        async with async_session_maker() as session:
            stmt = select(TrackModel).filter(TrackModel.title.match(name))
            res = (await session.execute(stmt)).scalars().all()

            return [i.dump_to_domain() for i in res]

    async def find_by_file_hash(self, file_hash: str) -> int | None:
            """Возвращает ID трека по хешу файла или None."""
            try:
                async with async_session_maker() as session:
                    stmt = select(TrackModel.id).where(TrackModel.file_hash == file_hash)
                    result = await session.execute(stmt)
                    return result.scalar_one_or_none()
            except Exception as e:
                _log.error("TracksCrudDao error in find_by_file_hash: %s", e)
                return None

    async def get_hashs(self) -> Sequence[str]:
        try:
            async with async_session_maker() as session:
                stmt = select(TrackModel.file_hash)
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            _log.error("TracksCrudDAO error in get_hashs metod: %s", e)
            return []


    async def get_random(self, n: int = 1) -> Sequence[Track]:
        if n < 1:
            raise ValueError(
                "Error in get_random method of TracksCrudDAO. N cant be less than 1"
            )

        async with async_session_maker() as session:
            res = await session.execute(
                select(TrackModel).order_by(func.random()).limit(n)
            )
            return [i.dump_to_domain() for i in res.scalars().all()]


class EmbeddingsCrudDAO:
    async def create(self, vector: list[float]) -> int | None:
        try:
            async with async_session_maker() as session:
                obj = TrackEmbeddingModel(vector=vector)
                session.add(obj)
                await session.commit()
                await session.flush()
                return obj.id
        except Exception as e:
            _log.error("EmbeddingCrudDAO error in create method: %s", e)
            return

    async def delete(self, id: int) -> bool:
        try:
            async with async_session_maker() as session:
                stmt = delete(TrackEmbeddingModel).where(TrackEmbeddingModel.id == id)
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception as e:
            _log.error(
                "EmbeddingCrudDAO error in delete method. ID to delete = %s. Error: %s",
                id,
                e,
            )
            return False
