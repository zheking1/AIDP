from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.init_db import init_database
from app.db.database import async_session
from app.api.health import router as health_router
from app.api.watcher import router as watcher_router
from app.api.tool import router as tool_router
from app.services.watcher import watcher_service
from app.services.project_mapper import ProjectMapper


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    await watcher_service.start()

    async with async_session() as db:
        watcher_service.set_db_factory(async_session)
        mapper = ProjectMapper(db)
        projects = await mapper.list_active_projects()
        for project in projects:
            await watcher_service.add_watched_project(project)

    yield
    await watcher_service.stop()


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health_router)
app.include_router(watcher_router)
app.include_router(tool_router)
