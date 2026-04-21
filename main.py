import click
import asyncio
from pathlib import Path
from src.ingest.pipeline import IngestPipeline
from src.logs import set_logs



@click.group()
def cli():
    """RecoMusic - музыкальная рекомендательная система"""
    pass


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--limit", default=0, type=int)
@click.option("--workers", default=4, type=int, help="Количество параллельных воркеров")
def ingest(directory: str, limit: int, workers: int):
    """Загрузить аудиофайлы из ДИРЕКТОРИИ в систему"""
    pipeline = IngestPipeline(max_workers=workers)

    try:
        asyncio.run(
           pipeline.run(Path(directory), None if limit == 0 else limit)
       )
    except KeyboardInterrupt:
        print("\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        raise


@cli.command()
@click.option("--host", default="0.0.0.0", help="Хост для запуска сервера")
@click.option("--port", default=8000, help="Порт для запуска сервера")
@click.option("--reload", is_flag=True, help="Автоматическая перезагрузка при изменениях (dev-режим)")
def serve(host: str, port: int, reload: bool):
    """Запустить REST API сервер"""
    import uvicorn
    from src.driver.rest.app import app

    print(f"🚀 Запуск сервера на http://{host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload
    )


@cli.command()
def init_db():
    """Создать таблицы в базе данных"""
    from src.driven.database.session import create_db_and_tables

    async def init():
        await create_db_and_tables()
        print("Таблицы успешно созданы")

    asyncio.run(init())


if __name__ == "__main__":
    set_logs()
    cli()
