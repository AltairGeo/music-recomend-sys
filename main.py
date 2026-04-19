import click
import asyncio
from pathlib import Path
from src.ingest.pipeline import IngestPipeline


@click.group()
def cli():
    """RecoMusic - музыкальная рекомендательная система"""
    pass


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--limit", default=None, type=int, help="Максимальное количество файлов для обработки")
@click.option("--workers", default=4, type=int, help="Количество параллельных воркеров")
def ingest(directory: str, limit: int, workers: int):
    """Загрузить аудиофайлы из ДИРЕКТОРИИ в систему"""
    pipeline = IngestPipeline(max_workers=workers)

    try:
        stats = asyncio.run(pipeline.run(Path(directory), limit))

        # Красивый вывод итогов
        print("\n" + "="*50)
        print("📊 ИТОГИ ОБРАБОТКИ")
        print("="*50)
        print(f"✅ Успешно добавлено: {stats['succeeded']}")
        print(f"⏭️ Пропущено (уже в БД): {stats['skipped']}")
        print(f"❌ Ошибок: {stats['failed']}")
        print(f"📁 Всего обработано: {stats['succeeded'] + stats['failed'] + stats['skipped']}")
        print("="*50)

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
    cli()
