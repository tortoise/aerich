import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from tortoise.backends import sqlite as _sqlite_backend  # noqa: F401

from aerich import Command

from .models import Widget
from .orm_config import TORTOISE_ORM


@asynccontextmanager
async def init_and_migrate() -> AsyncGenerator:
    migrations_path = str((Path(__file__).resolve().parent / "migrations").resolve())
    async with Command(TORTOISE_ORM, location=migrations_path) as command:
        await command.init()
        await command.upgrade()
        yield command


async def demo_write() -> tuple[int, str]:
    obj = await Widget.create(name="hello")
    count = await Widget.all().count()
    return count, obj.name


def bootstrap() -> tuple[int, str]:
    async def _run():
        async with init_and_migrate():
            return await demo_write()

    return asyncio.run(_run())
