import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db.init_db import init_database
from app.api.health import router as health_router
from app.api.tools import router as tools_router
from app.api.auth import router as auth_router
from app.api.metrics import router as metrics_router
from app.api.audit import router as audit_router
from app.api.projects import router as projects_router
from app.api.configs import router as configs_router
from app.api.reviews import router as reviews_router
from app.api.nas_storage import router as nas_storage_router
from app.api.instructions import router as instructions_router
from app.api.ws_logs import ws_handler
from app.web.routes import router as web_router
from app.mcp.server import mcp


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    await init_database()
    yield


_mcp_app = mcp.http_app(path="/", transport="streamable-http")


@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    async with app_lifespan(app):
        async with _mcp_app.lifespan(app):
            yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=combined_lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    description="AIDP Controller - AI DevOps Platform unified API gateway. Manage tools, projects, configs, audit logs, and invoke AI coding capabilities.",
)

app.add_middleware(SessionMiddleware, secret_key=os.environ.get("CONTROLLER_SESSION_KEY", "change-me"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(metrics_router)
app.include_router(audit_router)
app.include_router(tools_router)
app.include_router(projects_router)
app.include_router(configs_router)
app.include_router(reviews_router)
app.include_router(nas_storage_router)
app.include_router(instructions_router)
app.include_router(web_router)
app.add_api_websocket_route("/ws/logs", ws_handler)

# Mount static files
static_dir = Path(__file__).parent / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.mount("/mcp", _mcp_app)
