import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db.database import Base, engine
from app.db.init_db import init_database

# Import all models to ensure they are registered with SQLAlchemy
from app.models.instructions import AgentInstruction
from app.models.review import Review

# Import auth models (permissions, system_settings, etc.)
from app.db import auth_models

# Import new project models (AIDP Unified Platform)
from app.models.project_new import (
    Project as AidpProject,
    ProjectMember,
    ProjectSettings,
    ProjectAccessLog
)

# Import Knowledge module models
from app.modules.knowledge.models import (
    KnowledgeBase,
    KnowledgeDocument,
    DocumentChunk,
    KnowledgeSearchLog
)

# Import Memory module models
from app.modules.memory.models import (
    MemoryEntry,
    MemoryRelation,
    MemoryAccessLog
)

# Import Skills module models
from app.modules.skills.models import (
    Skill,
    SkillGroup,
    SkillFile,
    SkillEvolution
)

# Import Assets module models
from app.modules.assets.models import (
    Asset,
    AssetTag
)

# Import Sandbox module models
from app.modules.sandbox.models import Execution as SandboxExecution

# Import Quality module models
from app.modules.quality.models import CheckResult
import app.modules.quality  # register module

# Import Rules module models
from app.modules.rules.models import Rule, RuleGroup
import app.modules.rules  # register module

# Import Agents module models
from app.modules.agents.models import Agent
import app.modules.agents  # register module

# Import Workflows module models
from app.modules.workflows.models import Workflow, WorkflowStep, WorkflowExecution, WorkflowExecutionStep
import app.modules.workflows  # register module

# Import Evolution module models
from app.modules.evolution.models import EvolutionVersion
import app.modules.evolution  # register module

from app.api.health import router as health_router
from app.api.tools import router as tools_router
from app.api.auth import router as auth_router
from app.api.metrics import router as metrics_router
from app.api.audit import router as audit_router
from app.api.configs import router as configs_router
from app.api.reviews import router as reviews_router
from app.api.nas_storage import router as nas_storage_router
from app.api.instructions import router as instructions_router
from app.api.models import router as models_router
from app.api.settings import router as settings_router
from app.api.ws_logs import ws_handler
from app.web.routes import router as web_router
from app.mcp.server import mcp

# Import new project router (AIDP Unified Platform)
from app.routers.projects_new import router as projects_new_router

# Import document classification router
from app.api.classification import router as classification_router


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Initialize default data
    await init_database()
    
    # Initialize AIDP Platform modules (new architecture)
    from app.modules import init_all_modules
    initialized_modules = init_all_modules(app)
    print(f"[AIDP] Initialized modules: {initialized_modules}")
    
    # Initialize integrated tool databases
    from app.tools import init_tool_databases
    await init_tool_databases()
    print(f"[AIDP] Tool databases initialized")
    
    # Initialize seed data (templates)
    try:
        from app.services.seed_data import seed_templates
        await seed_templates()
        print(f"[AIDP] Seed data initialized")
    except Exception as e:
        print(f"[AIDP] Seed data skipped: {e}")
    except Exception as e:
        print(f"[AIDP] Seed data skipped: {e}")
    
    yield
    
    # Shutdown modules on exit
    from app.modules import shutdown_all_modules
    shutdown_all_modules()


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
app.include_router(models_router)
app.include_router(settings_router)
app.include_router(configs_router)
app.include_router(reviews_router)
app.include_router(nas_storage_router)
app.include_router(instructions_router)
app.include_router(web_router)

# Register new project router (AIDP Unified Platform)
app.include_router(projects_new_router, prefix="/api/projects")

# Register document classification router (auto-import)
app.include_router(classification_router, prefix="/api/classification")

app.add_api_websocket_route("/ws/logs", ws_handler)

# Register external tool routes (integrated into Controller)
from app.tools import register_tool_routes, init_tool_databases
print("[MAIN] Registering external tool routes...")
register_tool_routes(app)

# Mount static files
static_dir = Path(__file__).parent / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.mount("/mcp", _mcp_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)
