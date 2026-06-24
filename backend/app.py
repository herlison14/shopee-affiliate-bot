import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import auth, campaigns, webhooks
from mcp_server import mcp as mcp_server

mcp_asgi_app = mcp_server.streamable_http_app()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_asgi_app.router.lifespan_context(mcp_asgi_app))
        yield


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

app.mount("/agent/{token}", mcp_asgi_app)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"name": "ShopeeViral.AI API", "status": "running"}
