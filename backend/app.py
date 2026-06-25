import contextlib
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import agent, auth, campaigns, webhooks
from mcp_server import mcp as mcp_server
from services.agent_service import run_agent_cycle

mcp_asgi_app = mcp_server.streamable_http_app()
logger = logging.getLogger("shopeeviral.agent")


async def _run_agent_cycle_job() -> None:
    try:
        result = await run_agent_cycle()
        logger.info("Ciclo do agente James concluido: %s", result)
    except Exception:
        logger.exception("Falha no ciclo do agente James")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    if settings.AGENT_ENABLED:
        scheduler.add_job(
            _run_agent_cycle_job,
            trigger="interval",
            hours=settings.AGENT_CYCLE_HOURS,
            id="james_agent_cycle",
        )
        scheduler.start()

    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_asgi_app.router.lifespan_context(mcp_asgi_app))
        try:
            yield
        finally:
            if settings.AGENT_ENABLED:
                scheduler.shutdown(wait=False)


app = FastAPI(title="ShopeeViral.AI API", debug=settings.DEBUG, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(campaigns.router)
app.include_router(webhooks.router)
app.include_router(agent.router)

app.mount("/agent/{token}", mcp_asgi_app)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"name": "ShopeeViral.AI API", "status": "running"}
