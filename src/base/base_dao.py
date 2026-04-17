from logging import getLogger
from typing import Generic, Optional, Sequence, Tuple, Type, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.driven.database.session import BaseModel

log = getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseDAO(Generic[T]):
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session: AsyncSession = session

    async def create(self, obj: T) -> T:
        """
        Persist a new entity in the database.

        :param obj: Entity instance to be created and persisted.
        :type obj: T

        :return: The persisted entity with refreshed state from the database.
        :rtype: T

        :raises Exception: If the database operation fails.
        """
        try:
            self.session.add(obj)
            await self.session.commit()
            await self.session.refresh(obj)
            return obj
        except Exception as e:
            log.error(e)
            raise e

    async def read(
        self, skip: int = 0, limit: int = 100, **filters
    ) -> Tuple[Sequence[T], int]:
        """
        Read all entities with pagination and optional filters.
        :param skip: offset of order.
        :type skip: int

        :param limit: Determines how many entities to read after the offset
        :type limit: int

        :param filters: Define of filters in key-value format. Ex: id=123.

        :return: A tuple containing:
        - list of entities
        - total count of matched entitie

        :rtype: tuple[list[T], int]

        :raises Exception: If a database error occurs.

        .
        """
        try:
            stmt = select(self.model).filter_by(**filters).offset(skip).limit(limit)
            count_stmt = (
                select(func.count()).select_from(self.model).filter_by(**filters)
            )

            count = await self.session.execute(count_stmt)

            result = (
                (await self.session.execute(stmt)).scalars().all(),
                count.scalar_one(),
            )
            return result
        except Exception as e:
            log.error(e)
            raise e

    async def get(self, id: int) -> Optional[T]:
        """
        Retrieve a single entity by its primary key.

        :param id: Primary key of the entity to retrieve.
        :type id: int

        :return: The entity if found, otherwise ``None``.
        :rtype: Optional[T]

        :raises Exception: If the database operation fails.
        """
        try:
            result = await self.session.get(self.model, ident=id)
            return result
        except Exception as e:
            log.error(e)
            raise e

    async def update(self, update_data: dict, **filters) -> bool:
        """
        Update one or more entities in the database.

        :param update_data: Mapping of fields and their new values.
        :type update_data: dict[str, Any]

        :param filters: Filters to match entities that should be updated.
        :type filters: dict[str, Any]

        :return: ``True`` if the update was executed successfully, otherwise ``False``.
        :rtype: bool

        :raises Exception: If a database error occurs.
        """
        try:
            stmt = update(self.model).filter_by(**filters).values(**update_data)
            await self.session.execute(stmt)
            await self.session.commit()
            return True
        except Exception as e:
            log.error(e)
            return False

    async def delete(self, **kwargs):
        """
        Delete entities from the database matching the given filters.

        :param kwargs: Filters to match entities that should be deleted.
        :type kwargs: dict[str, Any]

        :return: ``True`` if the deletion was executed successfully.
        :rtype: bool

        :raises Exception: If the database operation fails.
        """
        try:
            stmt = delete(self.model).filter_by(**kwargs)
            await self.session.execute(stmt)
            await self.session.commit()
            return True
        except Exception as e:
            log.error(e)
            raise e
