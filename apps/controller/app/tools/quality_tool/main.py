from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.tools.quality_tool.config import settings
from app.tools.quality_tool.db.init_db import init_database
from app.tools.quality_tool.api.health import router as health_router
from app.tools.quality_tool.api.tool import router as tool_router
from app.tools.quality_tool.api.check import router as check_router
from app.tools.quality_tool.web.routes import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(tool_router)
app.include_router(check_router)
app.include_router(web_router)
