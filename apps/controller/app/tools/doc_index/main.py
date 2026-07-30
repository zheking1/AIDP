from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.tools.doc_index.config import settings
from app.tools.doc_index.db.init_db import init_database
from app.tools.doc_index.api.health import router as health_router
from app.tools.doc_index.api.doc_index import router as doc_index_router
from app.tools.doc_index.api.tool import router as tool_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health_router)
app.include_router(doc_index_router)
app.include_router(tool_router)