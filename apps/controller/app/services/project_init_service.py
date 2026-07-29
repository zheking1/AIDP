import logging
from typing import Optional

from app.services.tool_invoker import invoke_tool
from app._config import settings

logger = logging.getLogger(__name__)


AGENT_GEN_PROMPT = """根据以下项目信息, 生成 2-3 个领域专属 Agent 配置。

项目: {name}, 技术栈: {tech_stack}, 描述: {description}, 架构: {architecture}

每个 Agent 必须包含:
  agent_key: 英文标识
  name: 中文名称
  role: 一句话角色定义
  instructions: 5-10条该技术栈版本相关的具体最佳实践, 用\\n分隔
  domain_tags:  从 [backend,frontend,testing,devops,database,security,ai_ml,docs,code_indexing] 选1-3个

严格规则:
  - 只生成项目技术栈涉及的领域 Agent
  - 纯后端项目不要生成前端Agent, 纯前端不要后端Agent
  - 每个Agent的instructions要有该技术栈版本相关的具体建议
  - 输出纯JSON数组, 不要额外解释

示例(输入: Python 3.13+FastAPI+PostgreSQL):
[{{
  "agent_key":"fastapi-backend","name":"FastAPI 后端专家",
  "role":"精通 Python 3.13 + FastAPI + PostgreSQL 后端开发",
  "instructions":"1. 数据库操作用 SQLAlchemy 2.0 async\\n2. 路由用 FastAPI 装饰器, Pydantic v2 验证\\n3. 统一用 HTTPException 处理错误\\n4. 数据库迁移用 Alembic",
  "domain_tags":["backend","api","database"]
}}]"""


async def load_agent_instructions(project_name: str = "", agent_type: str = "main") -> dict:
    """Stage 0: Load Agent Instructions from database."""
    from app.models.instructions import AgentInstruction
    from app.db.database import async_session_factory
    from sqlalchemy import select

    async with async_session_factory() as session:
        # Try project-specific instructions first
        project_id = 0
        if project_name:
            from app.models.project_new import Project as AidpProject
            result = await session.execute(select(AidpProject).where(AidpProject.name == project_name))
            proj = result.scalar_one_or_none()
            if proj:
                project_id = proj.id

        result = await session.execute(
            select(AgentInstruction).where(
                AgentInstruction.project_id == project_id,
                AgentInstruction.agent_type == agent_type,
            )
        )
        inst = result.scalar_one_or_none()

        if not inst and project_id != 0:
            # Fallback to global instructions (project_id=0)
            result = await session.execute(
                select(AgentInstruction).where(
                    AgentInstruction.project_id == 0,
                    AgentInstruction.agent_type == agent_type,
                )
            )
            inst = result.scalar_one_or_none()

        if not inst:
            return {
                "agent_type": agent_type,
                "role": "You are a helpful AI developer assistant.",
                "constraints": {},
                "rules": [],
            }

        return {
            "agent_type": inst.agent_type,
            "role": inst.role or "",
            "constraints": inst.constraints or {},
            "rules": inst.rules or [],
        }


async def init_project(
    project_name: str,
    description: str = "",
    tech_stack: str = "",
    nas_path: str = "",
    docs: list = None,
    key_files: list = None,
    architecture_summary: str = "",
    user_id: int = 0,
) -> dict:
    steps = []
    errors = []

    def step(name, data=None, err=None):
        entry = {"step": name, "status": "ok" if not err else "error"}
        if data:
            entry["result"] = data
        if err:
            entry["error"] = str(err)
            errors.append(str(err))
        steps.append(entry)

    # Step 1: Create project record in Controller DB
    project_id = None
    try:
        from app.db.database import async_session_factory
        from app.models.project_new import Project as AidpProject
        async with async_session_factory() as session:
            project = AidpProject(
                name=project_name,
                description=description or f"{project_name} - initialized via aidp init",
                status="active",
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            project_id = project.id
        step("create_project", {"project_id": project_id})
    except Exception as e:
        step("create_project", err=e)
        logger.warning(f"Project creation skipped or already exists: {e}")

    # Step 2: If nas_path provided, trigger project-importer full scan
    if nas_path:
        try:
            importer_result = await invoke_tool(
                "project-importer",
                "project.import",
                {"path": nas_path, "name": project_name, "type": tech_stack or "python"},
                user_id=user_id,
            )
            step("import_via_project_importer", importer_result.get("result", importer_result))
        except Exception as e:
            step("import_via_project_importer", err=e)

    # Step 3: Code indexing via code-index tool
    code_indexed = 0
    ci_pid = None
    try:
        # Use default NAS_PATH if not provided
        effective_path = nas_path or settings.NAS_PATH

        # Create project in code-index
        r = await invoke_tool(
            "code-index",
            "code.create_project",
            {"name": project_name, "path": effective_path},
            user_id=user_id,
        )
        if r.get("success"):
            ci_pid = r.get("output", {}).get("id")

        # Scan files
        if ci_pid:
            scan_result = await invoke_tool(
                "code-index",
                "code.scan_project",
                {"project_id": ci_pid},
                user_id=user_id,
            )
            if scan_result.get("success"):
                code_indexed = scan_result.get("output", {}).get("file_count", 0)

        step("code_index", {"project_id": ci_pid, "files_indexed": code_indexed, "path": effective_path})
    except Exception as e:
        step("code_index", err=e)

    # Step 4: Upload key files for indexing (if no nas_path or as supplement)
    if key_files and ci_pid:
        code_uploaded = 0
        for f in key_files[:50]:
            try:
                r = await invoke_tool(
                    "code-index",
                    "code.index_file",
                    {
                        "project_id": ci_pid,
                        "file_path": f.get("path", "unknown"),
                        "content": f.get("content", ""),
                        "language": f.get("type", "python"),
                    },
                    user_id=user_id,
                )
                if r.get("success"):
                    code_uploaded += 1
            except Exception:
                pass
        if code_uploaded:
            step("code_index_upload", {"files_uploaded": code_uploaded})

    # Step 5: Store docs into knowledge-tool
    docs_imported = 0
    if docs:
        for doc in docs[:50]:
            try:
                r = await invoke_tool(
                    "knowledge-tool",
                    "knowledge.create_document",
                    {
                        "workspace_id": "default",
                        "title": doc.get("title", "untitled"),
                        "doc_type": "markdown",
                        "content": doc.get("content", ""),
                        "project_id": str(project_id) if project_id else "",
                        "source_uri": doc.get("title", ""),
                    },
                    user_id=user_id,
                )
                if r.get("success"):
                    docs_imported += 1
            except Exception:
                pass
        step("import_docs", {"docs_attempted": len(docs[:50]), "docs_imported": docs_imported})

    # Step 6: Store architecture knowledge into memory-tool
    memories_created = 0
    memory_entries = []

    if architecture_summary:
        memory_entries.append({
            "project": project_name,
            "category": "architecture",
            "title": "架构概述",
            "content": architecture_summary,
            "tags": "architecture,overview",
        })

    if tech_stack:
        memory_entries.append({
            "project": project_name,
            "category": "architecture",
            "title": "技术栈",
            "content": f"{project_name} 技术栈: {tech_stack}",
            "tags": "tech-stack",
        })

    if description:
        memory_entries.append({
            "project": project_name,
            "category": "architecture",
            "title": "项目描述",
            "content": description,
            "tags": "description",
        })

    for entry in memory_entries:
        try:
            r = await invoke_tool("memory-tool", "memory.create", entry, user_id=user_id)
            if r.get("success"):
                memories_created += 1
        except Exception:
            pass

    if memory_entries:
        step("create_memories", {"memories_created": memories_created, "memories_attempted": len(memory_entries)})

    # Step 7: Register key files into asset-tool
    assets_registered = 0
    if key_files:
        for f in key_files[:30]:
            try:
                r = await invoke_tool(
                    "asset-tool",
                    "asset.create",
                    {
                        "name": f.get("path", "unknown"),
                        "content": f.get("content", ""),
                        "asset_type": f.get("type", "code"),
                        "tags": [f.get("type", "code")],
                        "project_id": str(project_id) if project_id else "",
                    },
                    user_id=user_id,
                )
                if r.get("success"):
                    assets_registered += 1
            except Exception:
                pass
        step("register_assets", {"assets_attempted": len(key_files[:30]), "assets_registered": assets_registered})

    # Step 8: Sync all tool capabilities
    try:
        from app.services.tool_registry import sync_capabilities
        for tool_name in ["knowledge-tool", "memory-tool", "asset-tool", "sandbox-tool", "quality-tool", "skillrouter", "code-index"]:
            try:
                await sync_capabilities(tool_name)
            except Exception:
                pass
        step("sync_capabilities")
    except Exception as e:
        step("sync_capabilities", err=e)

    # Step 9: 智能生成 Agent (LLM 分析技术栈)
    agents_created = 0
    if tech_stack and project_id:
        try:
            from app.modules.agents.models import Agent
            import json as _json
            from app.services.context_optimizer.services.llm_client import LLMClient
            import httpx

            llm = LLMClient()
            await llm._ensure_config()
            prompt = AGENT_GEN_PROMPT.format(
                name=project_name,
                tech_stack=tech_stack,
                description=description or "",
                architecture=architecture_summary or "",
            )
            response = await llm.call(prompt, max_tokens=2000)
            if response:
                response = response.strip()
                if response.startswith("```"):
                    response = response.split("\n", 1)[-1].rsplit("```", 1)[0]
                agents_data = _json.loads(response)

                if not isinstance(agents_data, list):
                    agents_data = agents_data.get("agents", [])

                for ad in agents_data:
                    if not isinstance(ad, dict):
                        continue
                    ak = ad.get("agent_key", "")
                    if not ak:
                        continue
                    # 去重
                    existing = await (await async_session_factory()).execute(
                        select(Agent).where(
                            Agent.agent_key == ak,
                            Agent.project_id == project_id,
                            Agent.deleted_at.is_(None),
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    async with async_session_factory() as s:
                        agent = Agent(
                            name=ad.get("name", ak),
                            agent_key=ak,
                            role=ad.get("role", ""),
                            instructions=ad.get("instructions", ""),
                            domain_tags=_json.dumps(ad.get("domain_tags", [])),
                            scope="project",
                            project_id=project_id,
                            source="auto",
                            source_version=tech_stack,
                        )
                        s.add(agent)
                        await s.commit()
                        agents_created += 1

            step("generate_agents", {"agents_created": agents_created})
        except Exception as e:
            step("generate_agents", err=e)

    return {
        "project_id": project_id,
        "project_name": project_name,
        "steps": steps,
        "errors": errors,
        "summary": {
            "docs_imported": docs_imported,
            "memories_created": memories_created,
            "assets_registered": assets_registered,
            "agents_created": agents_created,
            "total_steps": len(steps),
            "total_errors": len(errors),
        },
    }


async def load_project_context(
    project_name: str,
    query: str = "",
) -> dict:
    context = {"project_name": project_name, "query": query}

    # Memory context
    try:
        mem_result = await invoke_tool(
            "memory-tool",
            "memory.search",
            {"project": project_name, "query": query, "limit": 10},
        )
        if mem_result.get("success"):
            context["memories"] = mem_result.get("output", [])
    except Exception as e:
        context["memories_error"] = str(e)

    # Memory context package (broader)
    if query:
        try:
            ctx_result = await invoke_tool(
                "memory-tool",
                "memory.context",
                {"project": project_name, "query": query, "limit": 10},
            )
            if ctx_result.get("success"):
                context["context_package"] = ctx_result.get("output", {})
        except Exception as e:
            context["context_package_error"] = str(e)

    # Knowledge search
    if query:
        try:
            kn_result = await invoke_tool(
                "knowledge-tool",
                "knowledge.search",
                {"query": query, "top_k": 8},
            )
            if kn_result.get("success"):
                context["knowledge"] = kn_result.get("output", {})
        except Exception as e:
            context["knowledge_error"] = str(e)

    # Asset search
    if query:
        try:
            asset_result = await invoke_tool(
                "asset-tool",
                "asset.search",
                {"query": query, "top_k": 8},
            )
            if asset_result.get("success"):
                context["assets"] = asset_result.get("output", {})
        except Exception as e:
            context["assets_error"] = str(e)

    # Skill resolution
    if query:
        try:
            skill_result = await invoke_tool(
                "skillrouter",
                "resolve_task",
                {"task": query, "top_k": 5},
            )
            if skill_result.get("success"):
                context["skills"] = skill_result.get("output", {})
        except Exception as e:
            context["skills_error"] = str(e)

    return context
