import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class DataBaseConfig:
    def __init__(self) -> None:
        self.dsn_url: str = os.getenv("DATABASE_DSN", "postgresql+asyncpg:///postgres:postgres@localhost:/music_app")


class MainConfig:
    def __init__(self, db_config: DataBaseConfig = DataBaseConfig()) -> None:
        self.db = db_config
        self.per_page: int = 25
        self.n_mfcc: int = 13
        self.music_data_folder: Path = Path("mus_storage")


app_config = MainConfig()
