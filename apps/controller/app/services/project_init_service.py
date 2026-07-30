import json as _json
import logging
from collections import Counter
from pathlib import Path
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


AGENT_TEMPLATES = {
    "java": [
        {"agent_key": "java-backend", "name": "Java 后端工程师",
         "role": "Java + Spring 后端开发专家",
         "instructions": "1. 遵循 Spring Boot 最佳实践\n2. Service 层做事务管理\n3. Controller 只做参数校验和路由\n4. 用 MyBatis-Plus 或 JPA 做持久化\n5. 异常统一用 @ControllerAdvice 处理",
         "domain_tags": ["backend", "database"]},
        {"agent_key": "devops-engineer", "name": "DevOps 工程师",
         "role": "CI/CD 和部署运维专家",
         "instructions": "1. 用 Docker Compose 管理服务编排\n2. Nacos 做配置中心和服务发现\n3. 日志统一收集到 ELK\n4. 健康检查端点必须暴露",
         "domain_tags": ["devops"]},
        {"agent_key": "code-reviewer", "name": "代码审查员",
         "role": "代码质量和安全审查专家",
         "instructions": "1. 检查 SQL 注入和 XSS 风险\n2. 确保敏感接口有权限校验\n3. 避免 N+1 查询\n4. 检查事务边界是否正确",
         "domain_tags": ["backend", "security"]},
    ],
    "python": [
        {"agent_key": "python-backend", "name": "Python 后端工程师",
         "role": "Python 后端开发专家",
         "instructions": "1. 使用类型注解和 Pydantic 校验\n2. 异步用 async/await\n3. 数据库操作用 SQLAlchemy async\n4. 用 Alembic 管理迁移\n5. 统一异常处理中间件",
         "domain_tags": ["backend", "database"]},
        {"agent_key": "test-engineer", "name": "测试工程师",
         "role": "自动化测试专家",
         "instructions": "1. 用 pytest 写单元测试\n2. API 测试用 httpx + pytest\n3. 覆盖率目标 80%+\n4. 关键路径必须有集成测试",
         "domain_tags": ["testing"]},
        {"agent_key": "code-reviewer", "name": "代码审查员",
         "role": "代码质量和安全审查专家",
         "instructions": "1. 检查是否有未处理的异常\n2. 确保敏感数据不落日志\n3. 检查 SQLAlchemy 查询效率\n4. 验证 Pydantic schema 是否完整",
         "domain_tags": ["backend", "security"]},
    ],
    "typescript": [
        {"agent_key": "frontend-dev", "name": "前端工程师",
         "role": "TypeScript/React 前端开发专家",
         "instructions": "1. 组件遵循单一职责\n2. 状态管理用 Zustand/Pinia\n3. API 调用统一封装\n4. 用 TypeScript strict 模式\n5. 关键交互有 loading/error 态",
         "domain_tags": ["frontend"]},
        {"agent_key": "ui-reviewer", "name": "UI 审查员",
         "role": "UI/UX 质量审查专家",
         "instructions": "1. 检查组件可访问性\n2. 确保响应式适配\n3. 交互状态完整 (hover/active/disabled)\n4. 颜色对比度符合 WCAG",
         "domain_tags": ["frontend"]},
    ],
}


UNIVERSAL_TEMPLATES = [
    {"agent_key": "fullstack-dev", "name": "全栈工程师",
     "role": "全栈开发专家",
     "instructions": "1. 写代码前先理解架构\n2. 遵循项目已有代码风格\n3. 不要重复造轮子\n4. 关键逻辑要加注释\n5. 提交前自测",
     "domain_tags": ["backend", "frontend"]},
    {"agent_key": "code-reviewer", "name": "代码审查员",
     "role": "代码质量和安全审查专家",
     "instructions": "1. 检查 SQL 注入/XSS 风险\n2. 检查硬编码的密钥/密码\n3. 检查异常处理是否完善\n4. 检查关键路径是否有日志",
     "domain_tags": ["backend", "security"]},
]


EXT_TO_LANG = {
    ".java": "java", ".kt": "kotlin",
    ".py": "python",
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript",
    ".go": "go", ".rs": "rust",
    ".cs": "csharp", ".swift": "swift",
    ".vue": "typescript", ".scala": "scala",
}

FRAMEWORK_SIGNALS = {
    "pom.xml": {"lang": "java", "build": "Maven"},
    "build.gradle": {"lang": "java", "build": "Gradle"},
    "build.gradle.kts": {"lang": "java", "build": "Gradle"},
    "settings.gradle": {"lang": "java", "build": "Gradle"},
    "package.json": {"lang": "javascript", "build": "npm"},
    "requirements.txt": {"lang": "python", "build": "pip"},
    "pyproject.toml": {"lang": "python", "build": "Poetry"},
    "go.mod": {"lang": "go", "build": "Go Modules"},
    "Cargo.toml": {"lang": "rust", "build": "Cargo"},
    "CMakeLists.txt": {"lang": "cpp", "build": "CMake"},
}

FRAMEWORK_DETECTS = {
    "Application.java": " + Spring Boot",
    "pom.xml": " + Spring Boot",
    "fastapi": " + FastAPI",
    "Dockerfile": " + Docker",
    "docker-compose": " + Docker Compose",
    "nacos": " + Nacos",
    "MyBatis": " + MyBatis",
    "JPA": " + JPA",
    "redis": " + Redis",
    "kafka": " + Kafka",
    "nginx": " + Nginx",
}


def infer_tech_stack(key_files: list = None, description: str = "") -> str:
    if key_files:
        files = key_files if isinstance(key_files, list) else _json.loads(key_files) if isinstance(key_files, str) else []
    else:
        files = []

    ext_counter = Counter()
    path_set = set()
    detected_frameworks = []

    for f in files:
        if isinstance(f, dict):
            p = f.get("path", "")
            content = f.get("content", "")
        else:
            p = str(f)
            content = ""

        path_set.add(p.replace("\\", "/"))
        filename = Path(p).name

        if filename in FRAMEWORK_SIGNALS:
            detected_frameworks.append(FRAMEWORK_SIGNALS[filename]["build"])

        ext = Path(p).suffix.lower()
        if ext in EXT_TO_LANG:
            ext_counter[EXT_TO_LANG[ext]] += 1

        for keyword, framework in FRAMEWORK_DETECTS.items():
            if keyword in content[:500] and framework not in detected_frameworks:
                detected_frameworks.append(framework)

    # Infer language from files
    lang = ""
    if ext_counter:
        lang = ext_counter.most_common(1)[0][0].title()
        if lang == "Typescript":
            lang = "TypeScript"

    # Infer language from framework signals in paths
    if not lang:
        for fn in path_set:
            basename = Path(fn).name
            if basename in FRAMEWORK_SIGNALS:
                lang = FRAMEWORK_SIGNALS[basename]["lang"].title()
                if lang == "Typescript":
                    lang = "TypeScript"
                break

    if lang:
        result = lang
        # Detect Spring Boot
        if lang == "Java" and any("Application.java" in p or ".xml" in p for p in path_set):
            is_spring = any("SpringBootApplication" in (f.get("content", "") if isinstance(f, dict) else "") for f in files)
            if is_spring or any(fn.endswith("Controller.java") for fn in path_set):
                result += " + Spring Boot"
        if detected_frameworks:
            result += " + " + " + ".join(detected_frameworks[:2])
        return result

    # Fallback to description parsing
    if description:
        KEYWORDS = {"java", "python", "javascript", "typescript", "react", "vue",
                    "spring", "fastapi", "go", "rust", "docker", "kubernetes"}
        found = [kw.title() for kw in KEYWORDS if kw.lower() in description.lower()]
        if found:
            return " + ".join(found[:3])

    return "unknown"


async def phase_register(
    project_name: str,
    description: str = "",
    tech_stack: str = "",
    owner_id: str = "",
    key_files: list = None,
    controller_project_id: int = 0,
) -> dict:
    """Phase 1: Register project with auto-inference."""
    warnings = []
    result = {"project_id": controller_project_id, "warnings": warnings}

    # Infer tech_stack if not provided
    inferred_ts = ""
    if not tech_stack:
        inferred_ts = infer_tech_stack(key_files, description)
        tech_stack = inferred_ts
        if inferred_ts and inferred_ts != "unknown":
            warnings.append(f"tech_stack auto-inferred from key_files: {inferred_ts}")
        elif description:
            tech_stack = description[:200]
            warnings.append("tech_stack inferred from description")

    # Create or update project record
    if not controller_project_id:
        from app.db.database import async_session_factory
        from app.models.project_new import Project as AidpProject
        from sqlalchemy import select

        async with async_session_factory() as db:
            exist = await db.execute(
                select(AidpProject).where(AidpProject.name == project_name)
            )
            proj = exist.scalar_one_or_none()

            if proj:
                controller_project_id = proj.id
                proj.description = description or proj.description
                proj.tech_stack = tech_stack or proj.tech_stack
                if owner_id and not proj.owner_id:
                    proj.owner_id = owner_id
                await db.commit()
                result["project_id"] = controller_project_id
                result["existed"] = True
            else:
                visibility = "private" if owner_id else "public"
                if not owner_id:
                    warnings.append("owner_id not resolved, visibility set to public")

                proj = AidpProject(
                    name=project_name,
                    description=description,
                    status="active",
                    tech_stack=tech_stack,
                    owner_id=owner_id or None,
                    visibility=visibility,
                    init_status="initializing",
                )
                db.add(proj)
                await db.commit()
                await db.refresh(proj)
                controller_project_id = proj.id
                result["project_id"] = controller_project_id

    result["tech_stack"] = tech_stack
    result["phase"] = "register"
    result["status"] = "ok"
    return result


async def phase_index(
    project_id: int,
    project_name: str,
    key_files: list = None,
    docs: list = None,
    tech_stack: str = "",
    description: str = "",
    architecture_summary: str = "",
    nas_path: str = "",
    user_id: int = 0,
) -> dict:
    """Phase 2: Index code, docs, memories, assets."""
    result = {"phase": "index", "status": "ok"}
    errors = []

    # Code indexing
    code_indexed = 0
    try:
        r = await invoke_tool(
            "code-index", "code.create_project",
            {"name": project_name, "path": nas_path or project_name, "controller_project_id": project_id},
            user_id=user_id,
        )
        ci_pid = r.get("output", {}).get("id") if r.get("success") else None

        if ci_pid and key_files:
            batch = await invoke_tool(
                "code-index", "code.index_files",
                {"project_id": ci_pid, "files": key_files[:50]},
                user_id=user_id,
            )
            if batch.get("success"):
                code_indexed = batch.get("output", {}).get("count", len(key_files[:50]))
    except Exception as e:
        errors.append(f"code_index: {e}")
    result["code_indexed"] = code_indexed

    # Docs
    docs_count = 0
    if docs:
        for doc in docs[:50]:
            try:
                # Support both string and dict formats
                if isinstance(doc, str):
                    title = doc
                    content = ""
                elif isinstance(doc, dict):
                    title = doc.get("title") or doc.get("path") or doc.get("name") or "untitled"
                    content = doc.get("content", "")
                else:
                    continue

                r = await invoke_tool(
                    "knowledge-tool", "knowledge.create_document",
                    {"workspace_id": "default", "title": title,
                     "doc_type": "markdown", "content": content,
                     "project_id": str(project_id), "source_uri": title},
                    user_id=user_id,
                )
                if r.get("success"):
                    docs_count += 1
            except Exception as e:
                errors.append(f"doc_index: {e}")
    result["docs_indexed"] = docs_count

    # Memories
    memories = []
    if tech_stack:
        memories.append({"project": project_name, "category": "architecture", "title": "技术栈",
                         "content": f"{project_name}: {tech_stack}", "tags": "tech-stack"})
    if architecture_summary:
        memories.append({"project": project_name, "category": "architecture", "title": "架构概述",
                         "content": architecture_summary, "tags": "architecture,overview"})
    if description:
        memories.append({"project": project_name, "category": "architecture", "title": "项目描述",
                         "content": description, "tags": "description"})

    mem_count = 0
    for entry in memories:
        try:
            r = await invoke_tool("memory-tool", "memory.create", entry, user_id=user_id)
            if r.get("success"):
                mem_count += 1
        except Exception:
            pass
    result["memories_created"] = mem_count

    # Assets
    assets_count = 0
    if key_files:
        for f in key_files[:30]:
            try:
                r = await invoke_tool(
                    "asset-tool", "asset.create",
                    {"name": f.get("path", "unknown"), "content": f.get("content", ""),
                     "asset_type": f.get("type", "code"), "tags": [f.get("type", "code")],
                     "project_id": str(project_id)},
                    user_id=user_id,
                )
                if r.get("success"):
                    assets_count += 1
            except Exception:
                pass
    result["assets_registered"] = assets_count

    # Sync capabilities
    try:
        from app.services.tool_registry import sync_capabilities
        for tn in ["knowledge-tool", "memory-tool", "asset-tool", "code-index"]:
            try:
                await sync_capabilities(tn)
            except Exception:
                pass
    except Exception:
        pass

    if errors:
        result["errors"] = errors
    return result


async def phase_generate_agents(
    project_id: int,
    project_name: str,
    tech_stack: str = "",
    description: str = "",
    architecture_summary: str = "",
) -> dict:
    """Phase 3: Generate project agents with fallback."""
    result = {"phase": "generate_agents", "agents_created": 0, "method": "none"}
    if not project_id:
        result["status"] = "skipped"
        result["reason"] = "no project_id"
        return result

    tech = tech_stack or description or ""
    agents_data = None

    # Strategy 1: LLM generation (only if tech_stack has substance)
    if tech and tech != "unknown" and len(tech) > 5:
        try:
            from app.tools.context_optimizer.services.llm_client import LLMClient
            llm = LLMClient()
            await llm._ensure_config()
            prompt = AGENT_GEN_PROMPT.format(
                name=project_name, tech_stack=tech,
                description=description or "", architecture=architecture_summary or "",
            )
            response = await llm.call(prompt, max_tokens=2000)
            if response:
                response = response.strip()
                if response.startswith("```"):
                    response = response.split("\n", 1)[-1].rsplit("```", 1)[0]
                agents_data = _json.loads(response)
                if not isinstance(agents_data, list):
                    agents_data = agents_data.get("agents", [])
                result["method"] = "llm"
        except Exception as e:
            logger.warning(f"LLM agent generation failed: {e}")

    # Strategy 2: Template matching
    if not agents_data:
        lang = tech.split("+")[0].strip().lower() if tech else ""
        templates = AGENT_TEMPLATES.get(lang, AGENT_TEMPLATES.get("java", UNIVERSAL_TEMPLATES))
        if not any(t.get("agent_key") for t in templates):
            templates = UNIVERSAL_TEMPLATES
        agents_data = [
            {"agent_key": t["agent_key"], "name": t["name"],
             "role": t["role"], "instructions": t["instructions"],
             "domain_tags": t["domain_tags"]}
            for t in templates
        ]
        result["method"] = "template"
        result["template_lang"] = lang or "universal"

    # Strategy 3: Universal fallback
    if not agents_data:
        agents_data = [
            {"agent_key": t["agent_key"], "name": t["name"],
             "role": t["role"], "instructions": t["instructions"],
             "domain_tags": t["domain_tags"]}
            for t in UNIVERSAL_TEMPLATES
        ]
        result["method"] = "universal"

    # Write agents to DB
    from app.modules.agents.models import Agent
    from app.db.database import async_session_factory
    from sqlalchemy import select

    created = 0
    for ad in agents_data:
        if not isinstance(ad, dict):
            continue
        ak = ad.get("agent_key", "")
        name = ad.get("name", ak)
        if not ak:
            ak = f"{project_name.replace('-', '_')}-agent-{created+1}"
            name = ak

        async with async_session_factory() as s:
            exist = await s.execute(
                select(Agent).where(
                    Agent.agent_key == ak, Agent.project_id == project_id,
                    Agent.deleted_at.is_(None),
                )
            )
            if exist.scalar_one_or_none():
                continue

            agent = Agent(
                name=name, agent_key=ak,
                role=ad.get("role", ""),
                instructions=ad.get("instructions", ""),
                domain_tags=_json.dumps(ad.get("domain_tags", [])),
                scope="project", project_id=project_id,
                source="auto", source_version=tech,
            )
            s.add(agent)
            await s.commit()
            created += 1

    result["agents_created"] = created
    result["status"] = "ok" if created > 0 else "empty"
    return result


async def phase_verify(project_id: int) -> dict:
    """Phase 4: Verify initialization completeness."""
    from app.db.database import async_session_factory
    from app.models.project_new import Project as AidpProject
    from app.modules.agents.models import Agent
    from sqlalchemy import select, func

    checks = {}
    missing = []
    score = 0
    total_checks = 7

    async with async_session_factory() as db:
        # 1. Project exists with tech_stack
        proj = (await db.execute(select(AidpProject).where(AidpProject.id == project_id))).scalar_one_or_none()
        if proj:
            checks["project"] = True
            checks["tech_stack"] = bool(proj.tech_stack and proj.tech_stack != "unknown")
            checks["owner"] = bool(proj.owner_id)
            checks["visibility"] = proj.visibility or "private"
            if not checks["tech_stack"]:
                missing.append("tech_stack")
            if not checks["owner"]:
                missing.append("owner_id")
        else:
            return {"status": "failed", "error": "project not found", "score": 0}

        # 2. Agents
        agent_count = (
            await db.execute(
                select(func.count()).select_from(Agent).where(
                    Agent.project_id == project_id, Agent.deleted_at.is_(None)
                )
            )
        ).scalar() or 0
        checks["agents"] = agent_count > 0
        checks["agents_count"] = agent_count
        if not checks["agents"]:
            missing.append("agents")

        # 3. Knowledge docs
        try:
            from app.tools.knowledge_tool.db.models import Document
            doc_count = (
                await db.execute(
                    select(func.count()).select_from(Document).where(
                        Document.project_id == str(project_id)
                    )
                )
            ).scalar() or 0
        except Exception:
            doc_count = 0
        checks["documents"] = doc_count > 0
        checks["documents_count"] = doc_count
        if not checks["documents"]:
            missing.append("documents")

        # 4. Memories
        try:
            from app.tools.memory_tool.db.models import MemoryEntry
            mem_count = (
                await db.execute(
                    select(func.count()).select_from(MemoryEntry).where(
                        MemoryEntry.project_id == str(project_id)
                    )
                )
            ).scalar() or 0
        except Exception:
            mem_count = 0
        checks["memories"] = mem_count > 0
        checks["memories_count"] = mem_count
        if not checks["memories"]:
            missing.append("memories")

    score = sum(1 for k in ["project", "tech_stack", "owner", "agents", "documents", "memories"] if checks.get(k)) * 100 // total_checks

    return {
        "phase": "verify",
        "status": "ok",
        "readiness_score": score,
        "checks": checks,
        "missing": missing,
        "next_actions": _build_next_actions(missing, project_id),
    }


def _build_next_actions(missing: list, project_id: int) -> list:
    actions = []
    action_map = {
        "owner_id": f"重新调用 aidp_init 并传入 api_key 参数以绑定 owner",
        "tech_stack": f"调用 aidp_generate_agents({project_id}) 使用 description 推断生成 Agent",
        "agents": f"调用 aidp_generate_agents({project_id}) 重新生成 Agent",
        "documents": f"Agent 扫描项目 README/文档后重新调用 aidp_init 传入 docs 参数",
        "memories": f"传入 architecture_summary 以创建架构记忆",
    }
    for m in missing:
        if m in action_map:
            actions.append(action_map[m])
    if not actions:
        actions.append(f"调用 install_local_scripts 安装本地 git hook 和文件监控")
    return actions


async def phase_finalize(project_id: int, init_result: dict, warnings: list) -> str:
    """Phase 5: Update project init_status."""
    from app.db.database import async_session_factory
    from app.models.project_new import Project as AidpProject
    from sqlalchemy import select

    verify = init_result.get("verify", {})
    score = verify.get("readiness_score", 0)

    if score >= 80:
        status = "initialized"
    elif score >= 40:
        status = "partial"
    else:
        status = "failed"

    try:
        async with async_session_factory() as db:
            proj = (await db.execute(select(AidpProject).where(AidpProject.id == project_id))).scalar_one_or_none()
            if proj:
                proj.init_status = status
                proj.init_result = _json.dumps(init_result, ensure_ascii=False)
                proj.init_warnings = _json.dumps(warnings, ensure_ascii=False)
                await db.commit()
    except Exception as e:
        logger.warning(f"Failed to finalize project {project_id}: {e}")

    return status


async def init_project(
    project_name: str,
    description: str = "",
    tech_stack: str = "",
    nas_path: str = "",
    docs: list = None,
    key_files: list = None,
    architecture_summary: str = "",
    user_id: int = 0,
    controller_project_id: int = 0,
    owner_id: str = "",
) -> dict:
    """Full 5-phase initialization: register → index → agents → verify → finalize."""
    warnings = []
    phases = {}

    # Phase 1: Register
    reg = await phase_register(
        project_name=project_name, description=description,
        tech_stack=tech_stack, owner_id=owner_id,
        key_files=key_files, controller_project_id=controller_project_id,
    )
    pid = reg["project_id"]
    tech_stack = reg.get("tech_stack", tech_stack)
    warnings.extend(reg.get("warnings", []))
    phases["register"] = reg

    # Phase 2: Index
    idx = await phase_index(
        project_id=pid, project_name=project_name,
        key_files=key_files, docs=docs, tech_stack=tech_stack,
        description=description, architecture_summary=architecture_summary,
        nas_path=nas_path, user_id=user_id,
    )
    phases["index"] = idx

    # Phase 3: Generate agents
    gen = await phase_generate_agents(
        project_id=pid, project_name=project_name,
        tech_stack=tech_stack, description=description,
        architecture_summary=architecture_summary,
    )
    phases["generate_agents"] = gen

    # Phase 4: Verify
    ver = await phase_verify(pid)
    phases["verify"] = ver

    # Phase 5: Finalize
    status = await phase_finalize(pid, phases, warnings)
    phases["finalize"] = {"status": status}

    # Build summary
    idx_data = phases.get("index", {})
    gen_data = phases.get("generate_agents", {})
    ver_data = phases.get("verify", {})

    return {
        "project_id": pid,
        "project_name": project_name,
        "tech_stack": tech_stack,
        "init_status": status,
        "phases": phases,
        "summary": {
            "code_indexed": idx_data.get("code_indexed", 0),
            "docs_indexed": idx_data.get("docs_indexed", 0),
            "memories_created": idx_data.get("memories_created", 0),
            "assets_registered": idx_data.get("assets_registered", 0),
            "agents_created": gen_data.get("agents_created", 0),
            "agent_method": gen_data.get("method", "unknown"),
        },
        "readiness": ver_data,
        "warnings": warnings,
        "next_actions": ver_data.get("next_actions", []),
    }


async def load_agent_instructions(project_name: str = "", agent_type: str = "main") -> dict:
    """Stage 0: Load Agent Instructions from database."""
    from app.models.instructions import AgentInstruction
    from app.db.database import async_session_factory
    from sqlalchemy import select

    async with async_session_factory() as session:
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


async def load_project_context(project_name: str, query: str = "") -> dict:
    context = {"project_name": project_name, "query": query}
    try:
        mem_result = await invoke_tool("memory-tool", "memory.search", {"project": project_name, "query": query, "limit": 10})
        if mem_result.get("success"):
            context["memories"] = mem_result.get("output", [])
    except Exception as e:
        context["memories_error"] = str(e)
    if query:
        try:
            ctx_result = await invoke_tool("memory-tool", "memory.context", {"project": project_name, "query": query, "limit": 10})
            if ctx_result.get("success"):
                context["context_package"] = ctx_result.get("output", {})
        except Exception as e:
            context["context_package_error"] = str(e)
        try:
            kn_result = await invoke_tool("knowledge-tool", "knowledge.search", {"query": query, "top_k": 8})
            if kn_result.get("success"):
                context["knowledge"] = kn_result.get("output", {})
        except Exception as e:
            context["knowledge_error"] = str(e)
        try:
            asset_result = await invoke_tool("asset-tool", "asset.search", {"query": query, "top_k": 8})
            if asset_result.get("success"):
                context["assets"] = asset_result.get("output", {})
        except Exception as e:
            context["assets_error"] = str(e)
        try:
            skill_result = await invoke_tool("skillrouter", "resolve_task", {"task": query, "top_k": 5})
            if skill_result.get("success"):
                context["skills"] = skill_result.get("output", {})
        except Exception as e:
            context["skills_error"] = str(e)
    return context