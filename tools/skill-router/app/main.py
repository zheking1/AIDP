import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastmcp import FastMCP
from starlette.middleware.sessions import SessionMiddleware

from app.db.init_db import init_database
from app.mcp.tools import register_mcp_tools
from app.web.auth import router as auth_router
from app.web.routes import router as web_router
from app.api.routes import router as api_router
from app.api.tool import router as tool_router


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    await init_database()
    await register_mcp_tools(_mcp)
    app.state.mcp = _mcp
    yield


_mcp = FastMCP("SkillRouter")
_mcp_app = _mcp.http_app(path="/", transport="streamable-http")


@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    async with app_lifespan(app):
        async with _mcp_app.lifespan(app):
            yield


app = FastAPI(
    title="SkillRouter MCP Service",
    version="0.1.0",
    lifespan=combined_lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SKILLROUTER_SESSION_KEY", "change-me"), max_age=86400)

app.include_router(auth_router, prefix="")
app.include_router(web_router, prefix="")
app.include_router(api_router, prefix="")
app.include_router(tool_router)

app.mount("/mcp", _mcp_app)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return RedirectResponse(url="/login")
