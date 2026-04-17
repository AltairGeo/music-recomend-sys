import os
from dotenv import load_dotenv

load_dotenv()

class DataBaseConfig:
    def __init__(self) -> None:
        self.dsn_url: str = os.getenv("DATABASE_DSN", "sqlite+aiosqlite:///blog.db")

class MainConfig:
    def __init__(self, db_config: DataBaseConfig = DataBaseConfig()) -> None:
        self.db = db_config
        self.per_page: int = 25


app_config = MainConfig()
