from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.init_db import init_database
from app.api.health import router as health_router
from app.api.tool import router as tool_router
from app.api.memory import router as memory_router
from app.api.memories import router as memories_v2_router
from app.api.graph import router as graph_router
from app.api.search import router as search_router
from app.api.context import router as context_router
from app.api.review import router as review_router
from app.web.routes import router as web_router


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
app.include_router(memory_router)
app.include_router(memories_v2_router)
app.include_router(graph_router)
app.include_router(search_router)
app.include_router(context_router)
app.include_router(review_router)
app.include_router(web_router)
