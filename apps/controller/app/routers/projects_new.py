"""Projects API Routes"""
from datetime import datetime
from typing import List, Optional
import json
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import async_session_factory
from app.models.project_new import Project, ProjectMember, ProjectRole
from app.core.permissions import require_permissions
from app.core.utils import get_current_user_id
from app.api.auth import get_current_user

router = APIRouter()


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None
    tech_stack: Optional[str] = None
    status: Optional[str] = None


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


async def _check_project_access(project_id: int, user_id: str, db: AsyncSession, require_write: bool = False):
    """Check user has access to a project. Returns (project, membership) tuple.
    Raises 404 if project not found or user has no access.
    """
    result = await db.execute(
        select(Project).where(and_(Project.id == project_id, Project.deleted_at.is_(None)))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id == user_id:
        return project, ProjectMember(project_id=project_id, user_id=user_id, role="admin")

    result = await db.execute(
        select(ProjectMember).where(
            and_(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        if project.visibility == "public" and not require_write:
            return project, None
        raise HTTPException(status_code=404, detail="Project not found")

    if require_write and membership.role not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="Insufficient project permissions")

    return project, membership


def _project_filter(user_id: str = None):
    """Filter projects accessible to the given user: their owned + member + public"""
    if not user_id:
        return Project.visibility == "public"
    return or_(
        Project.owner_id == user_id,
        Project.id.in_(
            select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
        ),
        Project.visibility == "public",
    )


@router.get("")
async def list_projects(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    query = select(Project).where(and_(
        Project.deleted_at.is_(None),
        _project_filter(user_id),
    ))
    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))
    query = query.order_by(desc(Project.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    projects = result.scalars().all()
    items = []
    for p in projects:
        d = p.to_dict()
        if user_id:
            mem = await db.execute(
                select(ProjectMember).where(
                    and_(ProjectMember.project_id == p.id, ProjectMember.user_id == user_id)
                )
            )
            m = mem.scalar_one_or_none()
            d["my_role"] = m.role if m else ("owner" if p.owner_id == user_id else None)
            members = await db.execute(
                select(ProjectMember).where(ProjectMember.project_id == p.id)
            )
            d["member_count"] = len(members.scalars().all())
        items.append(d)
    return {"items": items}


@router.post("")
async def create_project(
    name: str = Query(...),
    description: Optional[str] = Query(None),
    visibility: str = Query("private", description="private, internal, public"),
    tech_stack: Optional[str] = Query(None, description="JSON array string"),
    user=require_permissions("project:create"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    project = Project(
        name=name, description=description, owner_id=user_id,
        visibility=visibility, tech_stack=tech_stack,
    )
    db.add(project)
    await db.flush()

    member = ProjectMember(project_id=project.id, user_id=user_id, role="admin")
    db.add(member)

    await db.commit()
    await db.refresh(project)
    return project.to_dict()


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    project, _ = await _check_project_access(project_id, user_id, db)
    d = project.to_dict()
    if user_id:
        mem = await db.execute(
            select(ProjectMember).where(
                and_(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
            )
        )
        m = mem.scalar_one_or_none()
        d["my_role"] = m.role if m else ("owner" if project.owner_id == user_id else None)
        members = await db.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_id)
        )
        d["member_count"] = len(members.scalars().all())
    return d


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    user=require_permissions("project:create"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    project, _ = await _check_project_access(project_id, user_id, db, require_write=True)
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(project, field, val)
    await db.commit()
    await db.refresh(project)
    return project.to_dict()


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    user=require_permissions("project:create"),
    db: AsyncSession = Depends(get_db)
):
    user_id = get_current_user_id(user)
    project, membership = await _check_project_access(project_id, user_id, db, require_write=True)
    if membership and membership.role != "admin" and project.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only project admin can delete")
    project.deleted_at = datetime.now()
    await db.commit()
    return {"success": True}


@router.post("/{project_id}/members")
async def add_member(
    project_id: int,
    user_id: str = Query(...),
    role: str = Query("viewer"),
    user=require_permissions("project:create"),
    db: AsyncSession = Depends(get_db)
):
    current_user_id = get_current_user_id(user)
    await _check_project_access(project_id, current_user_id, db, require_write=True)
    existing = await db.execute(
        select(ProjectMember).where(
            and_(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member")
    member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
    db.add(member)
    await db.commit()
    return {"success": True}


@router.get("/{project_id}/members")
async def list_members(
    project_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    current_user_id = get_current_user_id(user)
    await _check_project_access(project_id, current_user_id, db)
    result = await db.execute(
        select(ProjectMember).where(ProjectMember.project_id == project_id)
    )
    return {"items": [m.to_dict() for m in result.scalars().all()]}


@router.delete("/{project_id}/members/{member_user_id}")
async def remove_member(
    project_id: int,
    member_user_id: str,
    user=require_permissions("project:create"),
    db: AsyncSession = Depends(get_db)
):
    current_user_id = get_current_user_id(user)
    await _check_project_access(project_id, current_user_id, db, require_write=True)
    result = await db.execute(
        select(ProjectMember).where(
            and_(ProjectMember.project_id == project_id, ProjectMember.user_id == member_user_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.delete(member)
    await db.commit()
    return {"success": True}


# ── Init Status ─────────────────────────────────────

@router.get("/{project_id}/init-status")
async def get_init_status(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    from app.models.project_new import ProjectInitTask, INIT_TASKS

    result = await db.execute(
        select(Project).where(and_(Project.id == project_id, Project.deleted_at.is_(None)))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for tdef in INIT_TASKS:
        existing = await db.execute(
            select(ProjectInitTask).where(
                ProjectInitTask.project_id == project_id,
                ProjectInitTask.task_id == tdef["id"],
            )
        )
        if not existing.scalar_one_or_none():
            db.add(ProjectInitTask(project_id=project_id, task_id=tdef["id"], status="pending"))

    await db.commit()

    result = await db.execute(
        select(ProjectInitTask).where(ProjectInitTask.project_id == project_id)
    )
    tasks = result.scalars().all()

    all_done = all(t.status == "completed" for t in tasks if t.task_id != "file_watcher")
    has_running = any(t.status == "running" for t in tasks)
    has_failed = any(t.status == "failed" for t in tasks)

    return {
        "project_id": project_id,
        "tasks": [t.to_dict() for t in sorted(tasks, key=lambda x: x.id)],
        "overall": "completed" if all_done else ("running" if has_running else ("failed" if has_failed else "pending")),
    }


# ── Init Execute ─────────────────────────────────────

class InitRequest(BaseModel):
    tasks: List[str] = []  # empty = run all pending


@router.post("/{project_id}/init")
async def run_init(
    project_id: int,
    req: InitRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.models.project_new import ProjectInitTask, INIT_TASKS, INIT_TASK_IDS

    result = await db.execute(
        select(Project).where(and_(Project.id == project_id, Project.deleted_at.is_(None)))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Seed and select tasks
    tasks_to_run = []
    for tdef in INIT_TASKS:
        existing = await db.execute(
            select(ProjectInitTask).where(
                ProjectInitTask.project_id == project_id,
                ProjectInitTask.task_id == tdef["id"],
            )
        )
        record = existing.scalar_one_or_none()
        if not record:
            record = ProjectInitTask(project_id=project_id, task_id=tdef["id"], status="pending")
            db.add(record)
            await db.flush()
            await db.refresh(record)

        if req.tasks:
            if tdef["id"] in req.tasks:
                tasks_to_run.append(record)
        else:
            # Always run all tasks on init call (underlying APIs handle dedup)
            tasks_to_run.append(record)

    await db.commit()
    results = []

    from datetime import datetime

    for record in tasks_to_run:
        task_id = record.task_id
        record.status = "running"
        record.started_at = datetime.utcnow()
        record.error_msg = None
        await db.commit()

        try:
            if task_id == "code_index":
                result_data = await _run_code_index(project_id, project.name or "unknown")
            elif task_id == "doc_import":
                result_data = await _run_doc_import(project_id)
            elif task_id == "mcp_register":
                result_data = await _run_mcp_register()
            elif task_id == "file_watcher":
                result_data = await _run_local_setup(project_id, "file_watcher")
            elif task_id == "git_hook":
                result_data = await _run_local_setup(project_id, "git_hook")
            elif task_id == "tech_analysis":
                result_data = await _run_local_setup(project_id, "tech_scan")
            elif task_id == "official_docs":
                result_data = await _run_official_docs(project_id)
            elif task_id == "rules_extract":
                result_data = await _run_rules_extract(project_id)
            elif task_id == "agent_setup":
                result_data = await _run_agent_setup(project_id)
            else:
                result_data = {"error": f"Task '{task_id}' not implemented yet", "skip": True}

            if result_data.get("error"):
                if result_data.get("skip"):
                    record.status = "skipped"
                else:
                    record.status = "failed"
                record.error_msg = result_data["error"][:500]
            else:
                record.status = "completed"
                record.metadata_json = json.dumps(result_data)
        except Exception as e:
            record.status = "failed"
            record.error_msg = str(e)[:500]

        record.completed_at = datetime.utcnow()
        await db.commit()
        results.append(record.to_dict())

    status_resp = await get_init_status(project_id, db)
    return {"project_id": project_id, "results": results, "status": status_resp}


async def _run_code_index(project_id: int, project_name: str) -> dict:
    import httpx
    from sqlalchemy import text as sql_text
    from app.models.project_new import ProjectMapping

    controller = os.environ.get("CONTROLLER_URL", "http://localhost:8883")

    async with async_session_factory() as dbs:
        p = await dbs.execute(sql_text("SELECT id, name FROM aidp_projects WHERE id = :id"), {"id": project_id})
        proj = p.fetchone()
        if not proj:
            return {"error": "Project not found"}

    # Create project in code-index via httpx
    create_payload = {"capability": "code.create_project", "arguments": {"name": project_name, "path": project_name}}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{controller}/api/tools/code-index/invoke",
                json=create_payload,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 200:
                return {"error": f"code-index create failed: {resp.status_code} {resp.text[:200]}"}
            create_res = resp.json()
            ci_project_id = None
            output = create_res.get("output", create_res)
            if isinstance(output, dict):
                ci_project_id = output.get("project_id") or output.get("id")
    except Exception as e:
        return {"error": f"code-index create failed: {e}"}

    if not ci_project_id:
        return {"error": "Failed to get project_id from code-index"}

    # Register mapping
    async with async_session_factory() as dbs:
        existing = await dbs.execute(
            select(ProjectMapping).where(
                ProjectMapping.controller_project_id == project_id,
                ProjectMapping.tool_name == "code-index",
            )
        )
        if not existing.scalar_one_or_none():
            dbs.add(ProjectMapping(
                controller_project_id=project_id,
                tool_name="code-index",
                tool_project_id=str(ci_project_id),
            ))
            await dbs.commit()

    return {"code_index_project_id": ci_project_id, "note": "Ready. Run local scan from your machine."}


async def _run_doc_import(project_id: int) -> dict:
    # Create project knowledge base if not exists
    from app.modules.knowledge.models import KnowledgeBase
    async with async_session_factory() as db:
        existing = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.project_id == project_id,
                KnowledgeBase.kb_level == "project",
                KnowledgeBase.deleted_at.is_(None),
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            return {"kb": "already exists", "note": "Knowledge base ready"}

        kb = KnowledgeBase(
            project_id=project_id,
            name=f"project-{project_id}-docs",
            slug=f"project-{project_id}-docs",
            description="Project documentation",
            kb_level="project",
            visibility="private",
        )
        db.add(kb)
        await db.commit()
        return {"kb_id": kb.id, "note": "Knowledge base created. Run local import to populate."}


async def _run_mcp_register() -> dict:
    from app.services.tool_registry import list_tools
    tools = await list_tools()
    names = {t.get("name") for t in tools if t.get("status") == "healthy"}
    required = {"code-index", "doc-index", "skillrouter"}
    missing = required - names
    if missing:
        return {"warning": f"Tools not healthy: {missing}", "healthy": list(names & required)}
    return {"healthy": list(names & required)}


async def _run_local_setup(project_id: int, task: str) -> dict:
    controller = os.environ.get("CONTROLLER_URL", "http://localhost:8883")
    cmds = {
        "file_watcher": f"python scripts/aidp_init.py --project-id {project_id} --controller-url {controller} --task file_watcher",
        "git_hook": f"python scripts/aidp_init.py --project-id {project_id} --controller-url {controller} --task git_hook",
        "tech_scan": f"python scripts/tech_scan.py --project-id {project_id} --controller-url {controller}",
    }
    cmd = cmds.get(task, f"python scripts/aidp_init.py --project-id {project_id} --controller-url {controller} --task {task}")
    return {"task": task, "command": cmd, "note": "Run this on your local machine"}


async def _run_official_docs(project_id: int) -> dict:
    # Check if framework-level KB already exists
    from app.modules.knowledge.models import KnowledgeBase
    async with async_session_factory() as db:
        existing = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.project_id == project_id,
                KnowledgeBase.kb_level == "framework",
                KnowledgeBase.deleted_at.is_(None),
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            return {"kb": "already exists", "note": "Framework docs already imported"}

    # Get project tech stack
    async with async_session_factory() as db:
        from app.models.project_new import Project
        p = await db.execute(select(Project).where(Project.id == project_id))
        proj = p.scalar_one_or_none()
        tech_stack = json.loads(proj.tech_stack) if proj and proj.tech_stack else []

    if not tech_stack:
        return {"warning": "No tech stack detected. Run tech_analysis first.", "note": "Skipping official docs"}

    # Try to import via knowledge-tool's web import
    official_doc_urls = []
    tech_lower = [t.lower() for t in tech_stack]
    if "spring boot" in str(tech_lower):
        official_doc_urls.append("https://docs.spring.io/spring-boot/docs/current/reference/htmlsingle/")
    if "vue" in str(tech_lower) or "vue.js" in str(tech_lower):
        official_doc_urls.append("https://vuejs.org/guide/introduction.html")
    if "react" in str(tech_lower):
        official_doc_urls.append("https://react.dev/learn")
    if "fastapi" in str(tech_lower):
        official_doc_urls.append("https://fastapi.tiangolo.com/")

    return {
        "tech_stack": tech_stack,
        "official_doc_urls": official_doc_urls,
        "note": f"Found {len(official_doc_urls)} official doc sources. Import via knowledge-tool or skip.",
    }


async def _run_rules_extract(project_id: int) -> dict:
    from app.modules.rules.models import Rule
    async with async_session_factory() as db:
        existing = await db.execute(
            select(Rule).where(Rule.project_id == project_id).limit(1)
        )
        if existing.scalar_one_or_none():
            return {"rules": "already exist", "note": "Rules already extracted"}

    # Check if there are rule-type knowledge documents to extract from
    from app.modules.knowledge.models import KnowledgeDocument
    async with async_session_factory() as db:
        rule_docs = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.project_id == project_id,
                KnowledgeDocument.category == "code_style",
                KnowledgeDocument.deleted_at.is_(None),
            ).limit(20)
        )
        docs = rule_docs.scalars().all()

    if not docs:
        return {"note": "No rule-type documents found. Import docs first."}

    extracted = len(docs)
    return {
        "extracted": extracted,
        "note": f"Found {extracted} rule-type documents. Rules can be extracted on demand.",
    }


async def _run_agent_setup(project_id: int) -> dict:
    from app.modules.agents.models import Agent
    from app.core.utils import gen_uuid
    from app.models.project_new import Project
    from app.modules.knowledge.models import KnowledgeBase

    async with async_session_factory() as db:
        existing = await db.execute(
            select(Agent).where(
                Agent.project_id == project_id,
                Agent.is_active == True,
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            return {"agents": "already exist", "note": "Agents already set up"}

        p = await db.execute(select(Project).where(Project.id == project_id))
        proj = p.scalar_one_or_none()
        project_name = proj.name if proj else f"Project-{project_id}"

        kb = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.project_id == project_id,
                KnowledgeBase.deleted_at.is_(None),
            ).limit(1)
        )
        kb_obj = kb.scalar_one_or_none()
        kb_id = kb_obj.id if kb_obj else None

        agent = Agent(
            id=gen_uuid(),
            name=f"{project_name} Assistant",
            role="developer",
            instructions=f"You are an AI assistant for {project_name}. Help with code, docs, and architecture.",
            scope="project",
            project_id=project_id,
        )
        db.add(agent)
        await db.commit()
        return {"agent_id": agent.id, "note": f"Created default agent for {project_name}"}


# ── Init Verify ─────────────────────────────────────

VERIFY_CHECKS = [
    {"id": "code_index",    "name": "代码索引校验"},
    {"id": "doc_import",    "name": "文档导入校验"},
    {"id": "tech_analysis", "name": "技术栈分析校验"},
    {"id": "official_docs", "name": "官方文档校验"},
    {"id": "rules_extract", "name": "规则提取校验"},
    {"id": "agent_setup",   "name": "Agent 创建校验"},
    {"id": "mcp_register",  "name": "MCP 注册校验"},
]


@router.get("/{project_id}/verify")
async def verify_init(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(and_(Project.id == project_id, Project.deleted_at.is_(None)))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    checks = []

    # 1. code_index: check code-index has nodes
    ci_nodes = 0
    try:
        import httpx, sqlite3
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get("http://localhost:18086/health")
            if r.status_code == 200:
                conn = sqlite3.connect("/app/data/code_index.db", timeout=5)
                ci_nodes = conn.execute("SELECT COUNT(*) FROM nodes WHERE project_id=?", (project_id,)).fetchone()[0]
                conn.close()
    except:
        pass
    checks.append({
        "task_id": "code_index",
        "name": "代码索引",
        "passed": ci_nodes > 0,
        "detail": f"code-index 中 {ci_nodes} 个节点",
        "severity": "error" if ci_nodes == 0 else ("warn" if ci_nodes < 50 else "ok"),
    })

    # 2. doc_import: check knowledge docs exist
    from app.modules.knowledge.models import KnowledgeDocument
    doc_count = await db.execute(
        select(func.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.project_id == project_id,
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    kd_count = doc_count.scalar() or 0
    checks.append({
        "task_id": "doc_import",
        "name": "文档导入",
        "passed": kd_count > 0,
        "detail": f"knowledge 库中 {kd_count} 篇文档",
        "severity": "error" if kd_count == 0 else "ok",
    })

    # 3. tech_analysis: check tech_stack
    ts = json.loads(project.tech_stack) if project.tech_stack else []
    checks.append({
        "task_id": "tech_analysis",
        "name": "技术栈分析",
        "passed": len(ts) > 0,
        "detail": f"检测到技术栈: {', '.join(ts[:5]) or '(无)'}",
        "severity": "warn" if not ts else "ok",
    })

    # 4. official_docs: check framework-level KB
    from app.modules.knowledge.models import KnowledgeBase
    kb_count = await db.execute(
        select(func.count(KnowledgeBase.id)).where(
            KnowledgeBase.project_id == project_id,
            KnowledgeBase.kb_level == "framework",
            KnowledgeBase.deleted_at.is_(None),
        )
    )
    fw_kb = kb_count.scalar() or 0
    checks.append({
        "task_id": "official_docs",
        "name": "官方文档",
        "passed": fw_kb > 0,
        "detail": f"{fw_kb} 个 framework 级知识库",
        "severity": "warn" if fw_kb == 0 else "ok",
    })

    # 5. rules_extract: check rules exist
    from app.modules.rules.models import Rule
    rule_count = await db.execute(
        select(func.count(Rule.id)).where(Rule.project_id == project_id)
    )
    rc = rule_count.scalar() or 0
    checks.append({
        "task_id": "rules_extract",
        "name": "规则提取",
        "passed": rc > 0,
        "detail": f"系统中 {rc} 条规则",
        "severity": "warn" if rc == 0 else "ok",
    })

    # 6. agent_setup: check agents exist
    from app.modules.agents.models import Agent
    agent_count = await db.execute(
        select(func.count(Agent.id)).where(
            Agent.project_id == project_id,
            Agent.is_active == True,
        )
    )
    ac = agent_count.scalar() or 0
    checks.append({
        "task_id": "agent_setup",
        "name": "Agent 创建",
        "passed": ac > 0,
        "detail": f"系统中 {ac} 个 Agent",
        "severity": "warn" if ac == 0 else "ok",
    })

    # 7. mcp_register: check all tools healthy
    from app.services.tool_registry import list_tools
    tools = await list_tools()
    healthy = sum(1 for t in tools if t.get("status") == "healthy")
    total = len(tools)
    required = {"code-index", "doc-index", "skillrouter", "memory-tool", "knowledge-tool"}
    registered = {t.get("name") for t in tools if t.get("status") == "healthy"}
    missing = required - registered
    checks.append({
        "task_id": "mcp_register",
        "name": "MCP 注册",
        "passed": len(missing) == 0,
        "detail": f"{healthy}/{total} 工具 healthy" + (f"，缺失: {missing}" if missing else ""),
        "severity": "error" if missing else "ok",
    })

    passed = sum(1 for c in checks if c["passed"])
    total_checks = len(checks)

    # Mappings info
    from app.models.project_new import ProjectMapping
    mappings_raw = await db.execute(
        select(ProjectMapping).where(ProjectMapping.controller_project_id == project_id)
    )
    mappings = [m.to_dict() for m in mappings_raw.scalars().all()]

    return {
        "project_id": project_id,
        "project_name": project.name,
        "owner_id": project.owner_id,
        "checks": checks,
        "mappings": mappings,
        "summary": f"{passed}/{total_checks} 检查通过",
        "all_passed": passed == total_checks,
    }
