from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.tools.knowledge_tool.config import settings
from app.tools.knowledge_tool.db.init_db import init_database
from app.tools.knowledge_tool.api.health import router as health_router
from app.tools.knowledge_tool.api.tool import router as tool_router
from app.tools.knowledge_tool.api.documents import router as documents_router
from app.tools.knowledge_tool.api.ingest import router as ingest_router
from app.tools.knowledge_tool.api.search import router as search_router
from app.tools.knowledge_tool.api.knowledge_bases import router as kb_router
from app.tools.knowledge_tool.api.bindings import router as bindings_router, kb_bindings_router
from app.tools.knowledge_tool.api.import_web import router as import_web_router
from app.tools.knowledge_tool.web.routes import router as web_router


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
app.include_router(documents_router)
app.include_router(ingest_router)
app.include_router(search_router)
app.include_router(kb_router)
app.include_router(kb_bindings_router)
app.include_router(bindings_router)
app.include_router(import_web_router)
app.include_router(web_router)
