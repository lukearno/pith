from contextlib import asynccontextmanager

from psycopg_pool import AsyncConnectionPool

from .enviro import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS


DB_DSN = f"dbname='{DB_NAME}' user='{DB_USER}' host='{DB_HOST}' port='{DB_PORT}' password='{DB_PASS}'"
POOL = None


async def pool():
    global POOL
    POOL = AsyncConnectionPool(DB_DSN, open=False)
    await POOL.open()
    await POOL.wait()


@asynccontextmanager
async def cursor(key=None):
    async with POOL.connection() as cxn:
        yield cxn.cursor()
