import asyncio
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database
from database import Base
import app as app_module
import mcp_server as mcp_module
from rate_limit import auth_rate_limiter

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    engine = create_async_engine(TEST_DATABASE_URL)
    session_local = async_sessionmaker(bind=engine, expire_on_commit=False)

    database.engine = engine
    database.AsyncSessionLocal = session_local

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    auth_rate_limiter._hits.clear()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client():
    # StreamableHTTPSessionManager.run() can only be invoked once per instance,
    # so each test gets a fresh FastMCP ASGI app swapped into the mounted route.
    mcp_module.mcp._session_manager = None
    fresh_mcp_app = mcp_module.mcp.streamable_http_app()
    for route in app_module.app.router.routes:
        if getattr(route, "path", None) == "/agent/{token}":
            route.app = fresh_mcp_app
            break

    async with fresh_mcp_app.router.lifespan_context(fresh_mcp_app):
        async with AsyncClient(transport=ASGITransport(app=app_module.app), base_url="http://test") as ac:
            yield ac
