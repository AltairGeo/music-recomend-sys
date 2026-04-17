from src.core.tracks.domains import Track
from src.driven.database.session import async_session_maker
from src.utils.conv.from_domain_to_model import trackDomTOtrackMod

class TracksCrudDao:
    async def create(self, model: Track) -> bool:
        async with async_session_maker() as session:
            db_track = trackDomTOtrackMod(model)

            session.add(db_track)
            await session.commit()
            return True

    async def get(self, id: str) -> Track: ...
    async def read(self, skip: int = 0, limit: int = 100) -> list[Track]: ...
    async def find_by_name(self, name: str) -> list[Track]: ...
