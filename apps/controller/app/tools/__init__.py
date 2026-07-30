"""集成各工具 API 路由到 Controller（懒加载，容错）"""

from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)


async def init_tool_databases():
    for name, module_path in [
        ("skill_router", "app.tools.skill_router.db.init_db"),
        ("knowledge_tool", "app.tools.knowledge_tool.db.init_db"),
        ("memory_tool", "app.tools.memory_tool.db.init_db"),
        ("asset_tool", "app.tools.asset_tool.db.init_db"),
        ("sandbox_tool", "app.tools.sandbox_tool.db.init_db"),
        ("quality_tool", "app.tools.quality_tool.db.init_db"),
        ("context_optimizer", "app.tools.context_optimizer.db.init_db"),
        ("evolution_engine", "app.tools.evolution_engine.db.init_db"),
    ]:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            await mod.init_database()
        except Exception:
            pass
    pass


def register_tool_routes(app: FastAPI):
    print("[TOOLS] register_tool_routes START")
    tools = [
        ("skill_router", "/tool/skill-router", [
            "api.routes", "api.tool", "web.routes", "web.auth"
        ]),
        ("knowledge_tool", "/tool/knowledge", [
            "api.knowledge_bases", "api.documents", "api.search", "api.ingest", "api.bindings", "api.import_web"
        ]),
        ("memory_tool", "/tool/memory", [
            "api.memories", "api.search", "api.graph", "api.context", "api.review"
        ]),
        ("asset_tool", "/tool/asset", ["api.assets"]),
        ("sandbox_tool", "/tool/sandbox", ["api.execute"]),
        ("quality_tool", "/tool/quality", ["api.check"]),
        ("context_optimizer", "/tool/context-optimizer", ["api.optimize"]),
        ("evolution_engine", "/tool/evolution-engine", ["api.events"]),
        ("doc_index", "/tool/doc-index", ["api.doc_index", "api.tool"]),
        ("code_index", "/tool/code-index", ["api.code_index", "api.tool"]),
        ("importer_tool", "/tool/importer", ["api.tool"]),
    ]

    for tool_name, prefix, routes in tools:
        try:
            import importlib
            pkg = f"app.tools.{tool_name}"
            for route in routes:
                module = importlib.import_module(f"{pkg}.{route}")
                app.include_router(module.router, prefix=prefix)
            logger.warning(f"[TOOLS] Integrated: {tool_name} ({len(routes)} routes)")
        except Exception as e:
            logger.warning(f"[TOOLS] {tool_name} failed: {e}")

    # Mount project_importer (full FastAPI app, not just router)
    try:
        from app.tools.project_importer.main import app as pi_app
        app.mount("/tool/project-importer", pi_app)
        logger.info("Integrated tool: project-importer")
    except Exception as e:
        logger.warning(f"Tool project-importer unavailable: {e}")