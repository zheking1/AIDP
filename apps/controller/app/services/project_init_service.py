import logging
from typing import Optional

import httpx
from app.services.tool_invoker import invoke_tool

logger = logging.getLogger(__name__)


async def load_agent_instructions(project_name: str = "", agent_type: str = "main") -> dict:
    """Stage 0: Load Agent Instructions from database."""
    from app.models.instructions import AgentInstruction
    from app.db.database import async_session_factory
    from sqlalchemy import select

    async with async_session_factory() as session:
        # Try project-specific instructions first
        project_id = 0
        if project_name:
            from app.models.project import Project
            result = await session.execute(select(Project).where(Project.name == project_name))
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
        from app.models.project import Project
        async with async_session_factory() as session:
            project = Project(
                name=project_name,
                description=description or f"{project_name} - initialized via aidp init",
                project_type=(tech_stack or "unknown")[:64],
                owner_id=str(user_id) if user_id else "0",
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

    # Step 2.5: Code indexing
    code_indexed = 0
    try:
        ci_pid = None
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "http://127.0.0.1:18086/api/projects",
                json={"name": project_name, "path": nas_path or "/tmp/aidp"},
            )
            if r.status_code == 200:
                ci_pid = r.json().get("id")

        if ci_pid and nas_path:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"http://127.0.0.1:18086/api/projects/{ci_pid}/scan",
                    json={},
                )
                if r.status_code == 200:
                    data = r.json()
                    code_indexed = data.get("file_count", 0)

        step("code_index", {"project_id": ci_pid, "files_indexed": code_indexed})
    except Exception as e:
        step("code_index", err=e)

    # Step 2.6: Upload key files for indexing (Windows projects without NAS path)
    if key_files and not nas_path and project_id:
        code_uploaded = 0
        for f in key_files[:50]:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(
                        "http://127.0.0.1:18086/api/index/file-content",
                        json={
                            "project_id": ci_pid or 0,
                            "file_path": f.get("path", "unknown"),
                            "content": f.get("content", ""),
                            "language": f.get("type", "python"),
                        },
                    )
                    code_uploaded += 1
            except Exception:
                pass
        if code_uploaded:
            step("code_index_upload", {"files_uploaded": code_uploaded})

    # Step 3: Store docs into knowledge-tool
    docs_imported = 0
    if docs:
        for doc in docs[:50]:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(
                        "http://127.0.0.1:18081/api/documents",
                        json={
                            "workspace_id": "default",
                            "title": doc.get("title", "untitled"),
                            "doc_type": "markdown",
                            "content": doc.get("content", ""),
                            "project_id": str(project_id) if project_id else "",
                            "source_uri": doc.get("title", ""),
                        },
                    )
                    docs_imported += 1
            except Exception:
                pass
        step("import_docs", {"docs_attempted": len(docs[:50]), "docs_imported": docs_imported})

    # Step 4: Store architecture knowledge into memory-tool
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
            if r.get("status") == "success":
                memories_created += 1
        except Exception:
            pass

    if memory_entries:
        step("create_memories", {"memories_created": memories_created, "memories_attempted": len(memory_entries)})

    # Step 5: Register key files into asset-tool
    assets_registered = 0
    if key_files:
        for f in key_files[:30]:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(
                        "http://127.0.0.1:18082/api/assets",
                        json={
                            "name": f.get("path", "unknown"),
                            "content": f.get("content", ""),
                            "asset_type": f.get("type", "code"),
                            "tags": [f.get("type", "code")],
                            "project_id": str(project_id) if project_id else "",
                        },
                    )
                    assets_registered += 1
            except Exception:
                pass
        step("register_assets", {"assets_attempted": len(key_files[:30]), "assets_registered": assets_registered})

    # Step 6: Sync all tool capabilities
    try:
        from app.services.tool_registry import sync_capabilities
        for tool_name in ["knowledge-tool", "memory-tool", "asset-tool", "sandbox-tool", "quality-tool", "skillrouter"]:
            try:
                await sync_capabilities(tool_name)
            except Exception:
                pass
        step("sync_capabilities")
    except Exception as e:
        step("sync_capabilities", err=e)

    return {
        "project_id": project_id,
        "project_name": project_name,
        "steps": steps,
        "errors": errors,
        "summary": {
            "docs_imported": docs_imported,
            "memories_created": memories_created,
            "assets_registered": assets_registered,
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
        if mem_result.get("status") == "success" and mem_result.get("result"):
            mem_data = mem_result["result"]
            if isinstance(mem_data, dict) and mem_data.get("success"):
                context["memories"] = mem_data.get("output", [])
            else:
                context["memories"] = mem_data
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
            if ctx_result.get("status") == "success" and ctx_result.get("result"):
                ctx_data = ctx_result["result"]
                if isinstance(ctx_data, dict) and ctx_data.get("success"):
                    context["context_package"] = ctx_data.get("output", {})
                else:
                    context["context_package"] = ctx_data
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
            if kn_result.get("status") == "success" and kn_result.get("result"):
                kn_data = kn_result["result"]
                if isinstance(kn_data, dict) and kn_data.get("success"):
                    context["knowledge"] = kn_data.get("output", {})
                else:
                    context["knowledge"] = kn_data
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
            if asset_result.get("status") == "success" and asset_result.get("result"):
                asset_data = asset_result["result"]
                if isinstance(asset_data, dict) and asset_data.get("success"):
                    context["assets"] = asset_data.get("output", {})
                else:
                    context["assets"] = asset_data
        except Exception as e:
            context["assets_error"] = str(e)

    # Skill resolution
    if query:
        try:
            skill_result = await invoke_tool(
                "skillrouter",
                "resolve_task",
                {"task": query, "api_key": "sk-1234567890", "top_k": 5},
            )
            if skill_result.get("status") == "success" and skill_result.get("result"):
                skill_data = skill_result["result"]
                if isinstance(skill_data, dict) and skill_data.get("success"):
                    context["skills"] = skill_data.get("output", {})
                else:
                    context["skills"] = skill_data
        except Exception as e:
            context["skills_error"] = str(e)

    return context
