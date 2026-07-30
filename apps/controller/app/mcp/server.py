import json
from fastmcp import FastMCP, Context
from app.services.tool_registry import list_tools, health_check_tool, health_check_all, sync_capabilities
from app.services.tool_invoker import invoke_tool, get_invocation_history
from app.services.project_init_service import init_project, load_agent_instructions
from app.mcp.session_manager import session_manager

mcp = FastMCP(
    "aidp-controller",
    instructions="""AIDP (AI DevOps Platform) 工作流指引:

【必须第一步调用】aidp_context — 在开始任何开发任务前，先调用此工具加载项目上下文。

工具调用顺序:
1. aidp_context(project_name, task) → 获取上下文
2. invoke_tool_mcp(tool_name, capability, arguments) → 执行具体操作
3. 工作完成后: index_changes(task, changed_files, summary) → 更新索引 + 模式分析
4. 可选: promote_evolution(title, description) → 提交优秀模式为系统级实践

复杂任务拆分时:
- aidp_instructions(project_name, task) → 生成 subagent 专用指令

项目管理:
- list_registered_tools() → 查看所有可用工具
- check_tool_health() → 检查工具健康状态
- get_index_rules(project_dir) → 获取扫描规则和本地脚本（aidp_init 前调用）
- aidp_init(...) → 导入新项目到 AIDP
- install_local_scripts(project_dir, project_id) → 安装本地 git hook + 文件监控""",
)


@mcp.tool()
async def invoke_tool_mcp(ctx: Context, tool_name: str, capability: str, arguments: str = "{}", user_id: int = 0, api_key: str = "") -> str:
    """通用工具调用器 — 调用 AIDP 注册的任意工具及其能力。

    通过此工具可以调用 AIDP 平台中注册的所有工具的特定能力。
    先调用 list_registered_tools() 查看可用工具列表和它们支持的能力。

    ⛔ 强制规则: 必须先调用 aidp_context 加载上下文，否则此工具将拒绝执行。

    Args:
        tool_name: 工具名称，例如 "sandbox-tool", "quality-tool", "memory-tool",
                   "knowledge-tool", "skillrouter", "asset-tool"
        capability: 工具能力标识，例如 "sandbox.execute", "quality.check",
                    "memory.search", "memory.create", "knowledge.search"
        arguments: JSON 格式的参数字符串，例如 '{"code": "print(1)", "language": "python"}'
        user_id: 用户 ID (可选，默认 0 表示系统调用)
        api_key: API Key 用于用户认证 (必填，从 MCP 配置 headers 传入)

    Returns:
        JSON 格式的工具调用结果。成功时包含 "success": true 和 "output" 字段。

    常用调用示例:
        # 代码执行验证
        invoke_tool_mcp("sandbox-tool", "sandbox.execute", '{"code": "print(1)", "language": "python"}')
        # 代码质量检查
        invoke_tool_mcp("quality-tool", "quality.check", '{"code": "x=1", "filename": "test.py"}')
        # 检索项目记忆
        invoke_tool_mcp("memory-tool", "memory.search", '{"project": "aidp", "query": "登录问题"}')
        # 归档经验
        invoke_tool_mcp("memory-tool", "memory.create", '{"project": "aidp", "category": "bugfix", "title": "cookie修复", "content": "详细描述", "tags": "cookie,auth"}')
        # 检索知识文档
        invoke_tool_mcp("knowledge-tool", "knowledge.search", '{"query": "API设计规范", "top_k": 3}')
        # 技能路由
        invoke_tool_mcp("skillrouter", "resolve_task", '{"task": "修复登录bug", "api_key": "sk-xxx"}')
    """
    # Resolve api_key: param > headers
    auth_key = api_key
    if not auth_key:
        try:
            request = ctx.request
            if hasattr(request, 'headers'):
                auth_key = request.headers.get("x-api-key", "") or request.headers.get("authorization", "").replace("Bearer ", "")
        except Exception:
            pass

    if not auth_key:
        return json.dumps({
            "success": False,
            "error": {
                "code": "API_KEY_REQUIRED",
                "message": "api_key 是必填参数，请在 MCP 配置中设置 x-api-key header",
                "hint": "在 opencode.json 的 mcp 配置中添加 headers: {\"x-api-key\": \"your-api-key\"}",
            }
        }, indent=2)

    # 强制检查: 是否已调用 aidp_context
    session_id = ctx.session_id or "default"
    allowed, reason = session_manager.can_call_tool(session_id, tool_name)
    if not allowed:
        return json.dumps({
            "success": False,
            "error": {
                "code": "CONTEXT_REQUIRED",
                "message": reason,
                "hint": "请先调用 aidp_context(project_name='aidp', task='你的任务描述')",
            }
        }, indent=2)

    try:
        args = json.loads(arguments) if isinstance(arguments, str) else arguments
    except json.JSONDecodeError:
        args = {}

    # Auto-inject project_id and user_id from session
    session = session_manager.sessions.get(session_id)
    if session:
        if session.user_id and user_id == 0:
            user_id = int(session.user_id) if session.user_id.isdigit() else 0
        if session.project_id and "project_id" not in args:
            args["project_id"] = session.project_id
        if session.project_name and "project" not in args:
            args["project"] = session.project_name

    session_manager.record_tool_call(session_id, f"{tool_name}:{capability}")
    result = await invoke_tool(tool_name, capability, args, user_id=user_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def list_registered_tools(status: str = "") -> str:
    """列出所有已注册的 AIDP 工具及其状态。

    返回所有在 AIDP 平台中注册的工具列表，包括工具名称、支持的能力、健康状态等信息。
    在不确定有哪些工具可用时调用此工具。

    Args:
        status: 可选的状态筛选条件。空字符串表示列出所有工具。
                可用值: "healthy" (健康), "unhealthy" (异常), "unknown" (未知)

    Returns:
        JSON 数组，每个元素包含工具的 name, capabilities, status, last_check 等字段。

    使用场景:
        - 开发前查看可用工具: list_registered_tools()
        - 仅查看健康工具: list_registered_tools(status="healthy")
        - 查看异常工具: list_registered_tools(status="unhealthy")
    """
    tools = await list_tools(status=status or None)
    return json.dumps(tools, indent=2)


@mcp.tool()
async def check_tool_health(tool_name: str = "") -> str:
    """检查工具健康状态 — 验证工具是否正常运行。

    定期调用此工具检查 AIDP 工具的健康状态，确保后续工具调用能够成功。
    建议在每次开发会话开始时调用一次。

    Args:
        tool_name: 可选，指定要检查的工具名称。为空时检查所有工具。

    Returns:
        JSON 格式的健康检查结果。包含每个工具的状态 (healthy/unhealthy/unknown) 和响应时间。

    使用场景:
        - 检查所有工具: check_tool_health()
        - 检查单个工具: check_tool_health(tool_name="sandbox-tool")
        - 如果工具状态为 unhealthy，可能需要联系管理员或稍后重试
    """
    if tool_name:
        result = await health_check_tool(tool_name)
    else:
        result = await health_check_all()
    return json.dumps(result, indent=2)


@mcp.tool()
async def sync_tool_capabilities(tool_name: str) -> str:
    """同步工具能力 — 从工具的 manifest 文件重新加载其能力定义。

    当工具的能力发生变化（如新增能力、修改参数）时，调用此工具同步最新信息。
    通常情况下不需要手动调用，除非工具侧有更新。

    Args:
        tool_name: 要同步的工具名称，例如 "sandbox-tool"

    Returns:
        JSON 格式的同步结果，包含更新的能力列表。

    使用场景:
        - 工具侧发布了新版本，新增了能力
        - 工具的能力参数发生了变化
        - 一般开发流程中不需要调用此工具
    """
    result = await sync_capabilities(tool_name)
    return json.dumps(result, indent=2)


@mcp.tool()
async def manage_models(
    action: str = "list",
    task_type: str = "",
    model_id: int = 0,
    name: str = "",
    provider: str = "",
    model_name: str = "",
    api_base: str = "",
    task_types: str = "[]",
    priority: int = 0,
) -> str:
    """管理模型配置 — 增删改查统一管理，所有工具共用。

    Args:
        action: 操作类型 — "list"(全部), "get"(单个), "create", "update", "delete"
        task_type: 按任务类型过滤，如 "chat", "embedding", "code"。用于 "list" 和 "get_best"
        model_id: 模型ID，用于 "get", "update", "delete"
        name: 模型显示名称
        provider: 提供商，如 OpenAI, DeepSeek, Local
        model_name: 模型标识，如 deepseek-chat, text-embedding-3-small
        api_base: API地址，如 https://api.deepseek.com/v1
        task_types: JSON数组，分配的任务类型，如 ["chat","code"]
        priority: 优先级，数值越高越优先

    Returns:
        JSON 格式的模型列表或操作结果。

    使用场景:
        - 查看所有模型: manage_models(action="list")
        - 获取聊天模型: manage_models(action="list", task_type="chat")
        - 创建新模型: manage_models(action="create", name="GPT-4", provider="OpenAI", model_name="gpt-4", task_types='["chat"]')
    """
    from app.services.model_service import ModelService

    try:
        if action == "list":
            if task_type:
                items = await ModelService.get_by_task(task_type)
            else:
                items = await ModelService.list_models()
            return json.dumps({"items": items, "total": len(items)}, indent=2)

        elif action == "get_best":
            if not task_type:
                return json.dumps({"error": "task_type required for get_best"})
            model = await ModelService.get_best_for_task(task_type)
            return json.dumps({"model": model}, indent=2)

        elif action == "get":
            model = await ModelService.get_model(model_id)
            return json.dumps({"model": model}, indent=2)

        elif action == "create":
            parsed_tasks = json.loads(task_types) if isinstance(task_types, str) else task_types
            model = await ModelService.create_model({
                "name": name, "provider": provider, "model_name": model_name,
                "api_base": api_base or None, "task_types": parsed_tasks, "priority": priority,
            })
            return json.dumps({"success": True, "model": model}, indent=2)

        elif action == "update":
            updates = {}
            if name: updates["name"] = name
            if provider: updates["provider"] = provider
            if model_name: updates["model_name"] = model_name
            if api_base: updates["api_base"] = api_base
            if task_types:
                updates["task_types"] = json.loads(task_types) if isinstance(task_types, str) else task_types
            if priority: updates["priority"] = priority
            model = await ModelService.update_model(model_id, updates)
            return json.dumps({"success": True, "model": model}, indent=2)

        elif action == "delete":
            await ModelService.delete_model(model_id)
            return json.dumps({"success": True, "message": "Deleted"}, indent=2)

        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def aidp_init(
    ctx: Context,
    project_name: str,
    description: str = "",
    tech_stack: str = "",
    nas_path: str = "",
    docs: str = "[]",
    key_files: str = "[]",
    architecture_summary: str = "",
    api_key: str = "",
) -> str:
    """初始化项目到 AIDP — 5阶段：注册→索引→Agent生成→自检→完成。

    系统会自动推断缺失的 tech_stack、补全 owner_id、验证初始化质量。
    支持幂等调用：同名项目已存在则跳过创建。

    Args:
        project_name: 项目唯一名称
        description: 项目描述
        tech_stack: 技术栈（可选，系统自动从 key_files 扩展名推断）
        nas_path: 路径（可选）
        docs: 文档列表 JSON/Array
        key_files: 关键文件列表 JSON/Array [{"path":"...","content":"...","type":"java"}]
        architecture_summary: 架构概述
        api_key: API Key (必填，用于认证和项目归属，从 MCP 配置 headers 传入)

    Returns:
        JSON: {
          project_id, init_status, tech_stack(推断后),
          summary: {code_indexed, docs_indexed, agents_created, ...},
          readiness: {score, checks, missing, next_actions},
          warnings: [...]
        }
    """
    parsed_docs = []
    parsed_files = []
    try:
        parsed_docs = json.loads(docs) if isinstance(docs, str) else docs
    except json.JSONDecodeError:
        pass
    try:
        parsed_files = json.loads(key_files) if isinstance(key_files, str) else key_files
    except json.JSONDecodeError:
        pass

    # === Preflight: validate inputs ===
    if not project_name or not project_name.strip():
        return json.dumps({"success": False, "status": "preflight_failed",
                           "error": "project_name is required"}, ensure_ascii=False, indent=2)

    session_id = ctx.session_id or "default"
    session = session_manager.sessions.get(session_id)
    owner_id = ""

    # Resolve user: param > headers > session
    auth_key = api_key
    if not auth_key:
        try:
            request = ctx.request
            if hasattr(request, 'headers'):
                auth_key = request.headers.get("x-api-key", "") or request.headers.get("authorization", "").replace("Bearer ", "")
        except Exception:
            pass

    if not auth_key:
        return json.dumps({
            "success": False, "status": "preflight_failed",
            "error": {
                "code": "API_KEY_REQUIRED",
                "message": "api_key 是必填参数，请在 MCP 配置中设置 x-api-key header",
                "hint": "在 opencode.json 的 mcp 配置中添加 headers: {\"x-api-key\": \"your-api-key\"}",
            }
        }, ensure_ascii=False, indent=2)

    if auth_key:
        try:
            from app.services.auth_service import AuthService
            user = await AuthService.validate_api_key(auth_key)
            if user:
                owner_id = str(user.id)
                user_name = user.username or ""
                session_manager.mark_authenticated(session_id, owner_id, user_name)
        except Exception:
            pass

    if not owner_id and session and session.user_id:
        owner_id = session.user_id

    # === Phase 1-5: Full initialization ===
    from app.services.project_init_service import init_project

    result = await init_project(
        project_name=project_name, description=description,
        tech_stack=tech_stack, nas_path=nas_path,
        docs=parsed_docs, key_files=parsed_files,
        architecture_summary=architecture_summary,
        user_id=int(owner_id) if owner_id.isdigit() else 0,
        owner_id=owner_id,
    )

    result["success"] = result.get("init_status") != "failed"
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def aidp_reindex(
    project_id: int,
    phase: str = "code",
    key_files: str = "[]",
    docs: str = "[]",
) -> str:
    """单独重做索引阶段 — 某个阶段失败后不用重新初始化整个项目。

    Args:
        project_id: AIDP 项目 ID
        phase: 重做哪个阶段: "code" | "docs" | "memories" | "assets" | "all"
        key_files: 关键文件列表（code/assets 需要）
        docs: 文档列表（docs 需要）

    Returns:
        JSON: {phase, status, count}
    """
    from app.services.project_init_service import phase_index
    from app.db.database import async_session_factory
    from app.models.project_new import Project as AidpProject
    from sqlalchemy import select

    parsed_files = []
    parsed_docs = []
    try:
        parsed_files = json.loads(key_files) if isinstance(key_files, str) else key_files
    except json.JSONDecodeError:
        pass
    try:
        parsed_docs = json.loads(docs) if isinstance(docs, str) else docs
    except json.JSONDecodeError:
        pass

    async with async_session_factory() as db:
        proj = (await db.execute(select(AidpProject).where(AidpProject.id == project_id))).scalar_one_or_none()
        if not proj:
            return json.dumps({"success": False, "error": "project not found"}, ensure_ascii=False, indent=2)

        if phase in ("all", "code", "assets"):
            if not parsed_files:
                return json.dumps({"success": False, "error": "key_files required for code/assets reindex"}, ensure_ascii=False, indent=2)
        if phase in ("all", "docs"):
            if not parsed_docs:
                return json.dumps({"success": False, "error": "docs required for doc reindex"}, ensure_ascii=False, indent=2)

        if phase in ("all",):
            result = await phase_index(
                project_id=project_id, project_name=proj.name,
                key_files=parsed_files, docs=parsed_docs,
                tech_stack=proj.tech_stack or "",
                description=proj.description or "",
            )
        elif phase == "code":
            result = await phase_index(
                project_id=project_id, project_name=proj.name,
                key_files=parsed_files, tech_stack=proj.tech_stack or "",
                description=proj.description or "",
            )
        elif phase == "docs":
            result = await phase_index(
                project_id=project_id, project_name=proj.name,
                docs=parsed_docs, description=proj.description or "",
            )
        elif phase == "memories":
            result = await phase_index(
                project_id=project_id, project_name=proj.name,
                tech_stack=proj.tech_stack or "",
                description=proj.description or "",
            )
        elif phase == "assets":
            result = await phase_index(
                project_id=project_id, project_name=proj.name,
                key_files=parsed_files, description=proj.description or "",
            )
        else:
            return json.dumps({"success": False, "error": f"unknown phase: {phase}"}, ensure_ascii=False, indent=2)

        result["success"] = True
        return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def aidp_generate_agents(
    project_id: int,
    tech_stack: str = "",
) -> str:
    """单独重做 Agent 生成 — 使用模板或 LLM 为项目创建领域 Agent。

    Args:
        project_id: AIDP 项目 ID
        tech_stack: 技术栈（可选，不传则从项目记录读取）

    Returns:
        JSON: {agents_created, method}
    """
    from app.services.project_init_service import phase_generate_agents
    from app.db.database import async_session_factory
    from app.models.project_new import Project as AidpProject
    from sqlalchemy import select

    async with async_session_factory() as db:
        proj = (await db.execute(select(AidpProject).where(AidpProject.id == project_id))).scalar_one_or_none()
        if not proj:
            return json.dumps({"success": False, "error": "project not found"}, ensure_ascii=False, indent=2)

    result = await phase_generate_agents(
        project_id=project_id, project_name=proj.name,
        tech_stack=tech_stack or proj.tech_stack or "",
        description=proj.description or "",
    )
    result["success"] = result.get("agents_created", 0) > 0
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def aidp_verify(
    project_id: int,
) -> str:
    """验证项目初始化完整性 — 返回 readiness 评分 (0-100) 和缺失项。

    检查: project存在 / tech_stack / owner / agents / docs / memories

    Args:
        project_id: AIDP 项目 ID

    Returns:
        JSON: {readiness_score, checks, missing, next_actions}
    """
    from app.services.project_init_service import phase_verify
    result = await phase_verify(project_id)
    result["success"] = True
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def aidp_context(
    ctx: Context,
    project_name: str,
    task: str = "",
    agent_type: str = "main",
    api_key: str = "",
) -> str:
    """【必须第一步调用】AIDP 指令优先分级上下文引擎。

    在开始任何开发任务前必须先调用此工具。它会触发 5 阶段 Pipeline:
    Stage 0: 从数据库加载 Agent Instructions (角色定义、约束规则)
    Stage 1: 通过 skill-router 分析用户意图 (识别所需工具、查询词、预算)
    Stage 2: 从 memory/knowledge/code-index/asset 并行检索知识
    Stage 3: 技能匹配 (自动选择最佳 skill)
    Stage 4: 上下文组装 (输出精炼后的上下文，供后续工具调用使用)

    Args:
        project_name: 项目名称，例如 "aidp"
        task: 当前任务的自然语言描述，例如 "修复登录页面的 cookie 问题"
        agent_type: Agent 类型，可选 "main" (默认) 或 "subagent:sandbox-tool" 等
        api_key: API Key (必填，用于认证，从 MCP 配置 headers 传入)

    Returns:
        JSON 包含各阶段结果和最终组装的上下文。后续步骤使用 invoke_tool_mcp 执行具体操作。

    工作流示例:
        1. 先调用 aidp_context 获取上下文
        2. 再调用 invoke_tool_mcp 执行具体工具
        3. 完成后可选调用 invoke_tool_mcp("memory-tool", "memory.create", {...}) 归档经验
    """
    from app.services.context_pipeline import ContextPipeline
    from app.db.database import async_session_factory
    from app.models.project_new import Project as AidpProject
    from app.services.auth_service import AuthService
    from sqlalchemy import select

    result = {"project_name": project_name, "task": task, "agent_type": agent_type, "stages": {}}
    user_id = ""
    user_name = ""

    # Resolve user: param > headers
    auth_key = api_key
    if not auth_key:
        try:
            request = ctx.request
            if hasattr(request, 'headers'):
                auth_key = request.headers.get("x-api-key", "") or request.headers.get("authorization", "").replace("Bearer ", "")
        except Exception:
            pass

    if not auth_key:
        return json.dumps({
            "success": False,
            "error": {
                "code": "API_KEY_REQUIRED",
                "message": "api_key 是必填参数，请在 MCP 配置中设置 x-api-key header",
                "hint": "在 opencode.json 的 mcp 配置中添加 headers: {\"x-api-key\": \"your-api-key\"}",
            }
        }, ensure_ascii=False, indent=2)

    if auth_key:
        try:
            user = await AuthService.validate_api_key(auth_key)
            if user:
                user_id = str(user.id)
                user_name = user.username or ""
        except Exception:
            pass

    # Authenticate to session
    session_id = ctx.session_id or "default"
    project_id = "0"

    try:
        # Execute 5-Stage Pipeline using local implementation
        async with async_session_factory() as db:
            # Look up project ID by name
            proj_result = await db.execute(
                select(AidpProject).where(AidpProject.name == project_name)
            )
            project = proj_result.scalar_one_or_none()
            project_id = str(project.id) if project else "0"

            pipeline = ContextPipeline(db)
            ctx_result = await pipeline.execute(
                task=task,
                project_id=project_id,
                session_id=ctx.session_id
            )
            
            # Build response from pipeline result
            result["trace_id"] = ctx_result.trace_id
            result["stages"]["stage0_instructions"] = {
                "role": (ctx_result.instructions.get("role", "")[:100]) if ctx_result.instructions else "",
                "rules_count": len(ctx_result.instructions.get("rules", [])) if ctx_result.instructions else 0,
                "loaded_from_db": ctx_result.instructions.get("loaded_from_db", False) if ctx_result.instructions else False,
            }
            
            result["stages"]["stage1_intent"] = {
                "intent": ctx_result.intent.get("intent", "unknown"),
                "domains": ctx_result.intent.get("domains", []),
                "complexity": ctx_result.intent.get("complexity", "simple"),
                "is_compound": ctx_result.intent.get("is_compound", False),
            }
            
            result["stages"]["stage2_retrieval"] = {
                "memories": len(ctx_result.memories),
                "knowledge": len(ctx_result.knowledge),
                "assets": len(ctx_result.assets),
            }
            
            result["stages"]["stage3_skills"] = {
                "matched": len(ctx_result.skills),
                "rules": len(ctx_result.rules),
            }
            
            result["stages"]["stage4_assembly"] = {
                "token_estimate": ctx_result.token_estimate,
                "timing_ms": ctx_result.stage_timings.get("stage_4", 0),
            }
            
            # Include assembled context
            result["context"] = ctx_result.assembled_context.get("system_prompt", "")[:5000]
            result["user_message"] = ctx_result.assembled_context.get("user_message", task)
            result["estimated_tokens"] = ctx_result.token_estimate
            result["stage_timings"] = ctx_result.stage_timings
            result["metadata"] = ctx_result.assembled_context.get("metadata", {})

    except Exception as e:
        import traceback
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()

    # 标记该会话已认证并加载上下文
    session_id = ctx.session_id or "default"
    session_manager.mark_authenticated(session_id, user_id, user_name, project_id, project_name)
    session_manager.mark_context_loaded(session_id, result)
    session_manager.record_tool_call(session_id, "aidp_context")

    return json.dumps(result, indent=2)


@mcp.tool()
async def aidp_instructions(
    project_name: str,
    task: str,
    agent_type: str = "subagent:sandbox-tool",
) -> str:
    """生成 subagent 专用指令 — 为复杂任务创建独立的子代理指令。

    当任务复杂需要拆分时，调用此工具为 subagent 生成专属的指令集。
    返回的指令包含角色定义、任务描述、上下文信息和工具权限。
    将返回的指令直接传递给 subagent 即可使用。

    Args:
        project_name: 项目名称
        task: subagent 需要执行的具体任务描述
        agent_type: subagent 类型标识符，例如:
                    - "subagent:sandbox-tool" (代码执行)
                    - "subagent:quality-tool" (质量检查)
                    - "subagent:memory-tool" (记忆检索)
                    - "subagent:knowledge-tool" (知识检索)

    Returns:
        JSON 包含 subagent_instructions，含 role, task, context, allowed_tools 字段。
        将此结果传递给 Task 工具创建 subagent。

    使用场景:
        - 大型功能开发需要并行处理多个模块
        - 需要专门的工具组合来完成特定子任务
        - 通过拆分任务提高开发效率

    工作流:
        1. 调用 aidp_instructions 生成 subagent 指令
        2. 用返回的 instructions 创建 subagent
        3. Subagent 内部也会调用 aidp_context 加载自己的上下文
    """
    from app.services.context_pipeline import ContextPipeline
    from app.db.database import async_session_factory
    from app.db.auth_models import Project
    from sqlalchemy import select

    result = {"project_name": project_name, "task": task, "agent_type": agent_type}

    try:
        # Execute pipeline for subagent
        async with async_session_factory() as db:
            # Look up project ID by name
            proj_result = await db.execute(
                select(Project).where(Project.name == project_name)
            )
            project = proj_result.scalar_one_or_none()
            project_id = str(project.id) if project else "0"

            pipeline = ContextPipeline(db)
            ctx_result = await pipeline.execute(
                task=task,
                project_id=project_id
            )
            
            # Generate subagent-specific instructions
            domain = ctx_result.intent.get("domains", [project_name])[0] if ctx_result.intent.get("domains") else project_name
            
            result["subagent_instructions"] = {
                "agent_type": agent_type,
                "role": f"You are a specialized subagent for {domain}. {ctx_result.instructions.get('role', '')[:200]}",
                "task": task,
                "specialization": domain,
                "context": {
                    "relevant_memories": [m.get('title') for m in ctx_result.memories[:3]],
                    "relevant_knowledge": [k.get('title') for k in ctx_result.knowledge[:3]],
                    "available_skills": [s.get('name') for s in ctx_result.skills[:3]],
                    "constraints": ctx_result.instructions.get('constraints', {}),
                },
                "allowed_tools": [
                    "memory-tool",
                    "knowledge-tool", 
                    "asset-tool",
                    "sandbox-tool",
                    "quality-tool"
                ],
                "parent_trace_id": ctx_result.trace_id,
            }
            
            result["trace_id"] = ctx_result.trace_id

    except Exception as e:
        import traceback
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()

    return json.dumps(result, indent=2)


@mcp.tool()
async def promote_evolution(
    title: str,
    description: str = "",
    changes: str = "{}",
    affected_tools: str = "[]",
    version: str = "0.1.0",
    project_id: int = 0,
) -> str:
    """提出进化提案 — 将项目中的优秀模式/经验提交为进化提案。

    工作完成后，如果发现值得推广的模式（如新的错误处理方式、API 设计风格、
    模块化方案等），通过此工具提交给管理员审核。审核通过后会成为系统级最佳实践。

    Args:
        title: 提案标题，例如 "FastAPI 统一错误处理模式"
        description: 详细描述这个模式的内容和价值
        changes: JSON 格式的变更内容，例如 '{"added":["error_handler.py"], "description":"新增统一错误处理中间件"}'
        affected_tools: JSON 数组，影响的工具列表，例如 '["memory","knowledge"]'
        version: 版本号，格式 semver，例如 "0.1.0"
        project_id: 来源项目 ID (可选)

    Returns:
        JSON 包含提案 ID 和审核状态 (pending)

    使用场景:
        - 开发完成后发现可复用的设计模式
        - Bug 修复后总结出通用的修复方案
        - 从项目中提取出值得跨项目共享的经验
    """
    from app.db.database import async_session_factory
    from app.modules.evolution.models import EvolutionVersion

    parsed_changes = {}
    parsed_tools = []
    try:
        parsed_changes = json.loads(changes) if isinstance(changes, str) else changes
    except json.JSONDecodeError:
        pass
    try:
        parsed_tools = json.loads(affected_tools) if isinstance(affected_tools, str) else affected_tools
    except json.JSONDecodeError:
        pass

    try:
        async with async_session_factory() as db:
            version_obj = EvolutionVersion(
                version=version,
                level="project",
                title=title,
                description=description,
                source_project_id=project_id,
                changes=parsed_changes,
                affected_tools=parsed_tools,
                review_status="pending",
                review_log=[],
            )
            db.add(version_obj)
            await db.commit()
            await db.refresh(version_obj)

            return json.dumps({
                "success": True,
                "version_id": version_obj.id,
                "title": title,
                "status": "pending",
                "message": f"进化提案「{title}」已提交，等待管理员审核。",
                "hint": "管理员可通过 /admin/evolution 查看和审核提案。"
            }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool()
async def list_evolutions(level: str = "", status: str = "") -> str:
    """列出进化版本 — 查看所有进化提案。

    Args:
        level: 筛选级别 — "project" (项目级), "system" (系统级), "" (全部)
        status: 筛选状态 — "pending" (待审核), "approved" (已批准), "rejected" (已拒绝), "" (全部)

    Returns:
        JSON 包含进化版本列表和统计信息

    使用场景:
        - 查看有哪些已批准的系统级最佳实践可用
        - 检查自己提交的提案审核进度
        - 查找可复用的通用方案
    """
    from app.db.database import async_session_factory
    from app.modules.evolution.models import EvolutionVersion
    from sqlalchemy import select, desc

    try:
        async with async_session_factory() as db:
            q = select(EvolutionVersion)
            if level:
                q = q.where(EvolutionVersion.level == level)
            if status:
                q = q.where(EvolutionVersion.review_status == status)
            q = q.order_by(desc(EvolutionVersion.created_at)).limit(50)

            result = await db.execute(q)
            versions = result.scalars().all()

            system_versions = [
                {"id": v.id, "version": v.version, "title": v.title,
                 "description": v.description[:200] if v.description else "",
                 "affected_tools": v.affected_tools,
                 "changes": v.changes}
                for v in versions if v.level == "system"
            ]

            return json.dumps({
                "success": True,
                "total": len(versions),
                "system_versions": system_versions,
                "all_versions": [
                    {"id": v.id, "version": v.version, "level": v.level,
                     "title": v.title, "review_status": v.review_status,
                     "description": v.description[:150] if v.description else "",
                     "created_at": v.created_at.isoformat() if v.created_at else None}
                    for v in versions
                ]
            }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool()
async def analyze_and_evolve(
    task: str,
    result: str = "",
    event_type: str = "success",
    project_id: int = 0,
) -> str:
    """智能进化分析 — 调用 evolution-engine 的 LLM 分析工作成果，自动提取可复用模式。

    每当完成一个开发任务后，调用此工具来分析本次工作的结果，
    系统会使用 LLM 从中提取可复用的模式和经验，置信度高时自动创建进化提案。

    Args:
        task: 已完成的任务描述
        result: 工作结果简述（做了什么、效果如何）
        event_type: 事件类型 — "success" (成功模式), "error" (错误修复), "optimization" (优化)
        project_id: 项目 ID (可选)

    Returns:
        JSON 包含分析结果和是否自动创建了进化提案
    """
    try:
        from app.tools.evolution_engine.app.db.database import async_session_factory as evo_session
        from app.tools.evolution_engine.app.services.event_collector import EventCollector
        from app.tools.evolution_engine.app.services.llm_pattern_analyzer import LLMPatternAnalyzer
        from app.tools.evolution_engine.app.services.evolution_router import EvolutionRouter
        from app.tools.evolution_engine.app.services.tool_updater import ToolUpdater

        async with evo_session() as evo_db:
            collector = EventCollector(evo_db)
            event = await collector.collect(event_type, "mcp", task, result, {"project_id": project_id})

            analyzer = LLMPatternAnalyzer(evo_db)
            analysis = await analyzer.analyze(event_type, task, result, {"project_id": project_id})
            await analyzer.save_analysis(event.id, analysis)

            router_inst = EvolutionRouter()
            targets = router_inst.route(analysis)

            updater = ToolUpdater(evo_db)
            await updater.apply_evolution(event.id, targets, analysis.get("update_type", "经验"))
            await collector.mark_processed(event.id)

            confidence = analysis.get("confidence", 0)
            if confidence >= 0.5:
                return json.dumps({
                    "success": True,
                    "auto_proposed": True,
                    "confidence": confidence,
                    "analysis": {
                        "category": analysis.get("category"),
                        "pattern": analysis.get("success_pattern") or analysis.get("fix_pattern"),
                        "root_cause": analysis.get("root_cause"),
                        "update_type": analysis.get("update_type"),
                        "affected_tools": targets,
                    },
                    "message": f"已将模式「{analysis.get('success_pattern') or analysis.get('fix_pattern', '')}」提交为进化提案，等待管理员审核。",
                    "hint": "管理员可通过 /admin/evolution 审核此提案。",
                }, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "success": True,
                    "auto_proposed": False,
                    "confidence": confidence,
                    "analysis": analysis,
                    "message": "分析完成但置信度不足，未自动创建提案。可手动通过 promote_evolution 提交。",
                }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "hint": "Evolution engine 分析失败，手动通过 promote_evolution 提交也可以。",
        }, ensure_ascii=False, indent=2)


@mcp.tool()
async def index_changes(
    ctx: Context,
    task: str = "",
    changed_files: str = "[]",
    summary: str = "",
    project_id: str = "",
) -> str:
    """索引代码变更 — 完成开发任务后调用，增量更新索引并分析模式。

    将本次任务中修改的文件提交到 code-index 进行增量索引，
    同时分析变更内容，发现可复用模式后自动创建进化提案。

    Args:
        task: 本次完成的任务描述，例如 "修复了登录页面的 cookie 失效"
        changed_files: JSON 数组，修改的文件列表
                       格式: '[{"path":"src/auth.py","content":"...","language":"python"}]'
                       为空时尝试从 session 中获取项目信息
        summary: 变更总结（做了什么、为什么），用于模式分析
        project_id: 项目 ID，为空时从 session 自动获取

    Returns:
        JSON 包含索引结果和模式分析

    使用场景:
        - 完成一个功能开发后立即调用，保持索引最新
        - 修复 Bug 后调用，让 AIDP 学到修复模式
        - 重构后调用，更新代码结构信息
    """
    result = {
        "success": True,
        "indexed_code_files": 0,
        "indexed_doc_files": 0,
        "patterns_found": [],
        "evolution_proposed": False,
        "project_id": project_id,
    }

    # 1. Resolve project_id from session
    session_id = ctx.session_id or "default"
    session = session_manager.sessions.get(session_id)
    pid = project_id or (session.project_id if session else "")

    if not pid:
        return json.dumps({
            "success": False,
            "error": "No project_id. Call aidp_context first, provide project_id, or ensure .opencode/watcher.json exists.",
        }, ensure_ascii=False, indent=2)

    result["project_id"] = pid

    # 2. Parse changed_files
    files = []
    try:
        files = json.loads(changed_files) if isinstance(changed_files, str) else changed_files
    except json.JSONDecodeError:
        files = []

    if not files:
        result["message"] = "No changed files provided. Skipping indexing."
        if summary:
            result["message"] += " Summary recorded for analysis."
        return json.dumps(result, ensure_ascii=False, indent=2)

    # 3. Index code files
    code_files = [f for f in files if not f.get("path", "").endswith((".md",".txt",".rst",".adoc"))]
    if code_files:
        try:
            idx_result = await invoke_tool(
                "code-index", "code.index_files",
                {"project_id": int(pid), "files": code_files}
            )
            if idx_result.get("success"):
                result["indexed_code_files"] = len(code_files)
        except Exception as e:
            result["indexed_code_files"] = 0

    # 4. Index doc files
    doc_files = [f for f in files if f.get("path", "").endswith((".md",".txt",".rst",".adoc"))]
    if doc_files:
        try:
            docs = [{"title": f.get("path", "").rsplit("/",1)[-1].rsplit(".",1)[0],
                     "content": f.get("content", ""),
                     "filename": f.get("path", ""),
                     "source_uri": f.get("path", "")} for f in doc_files]
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                await client.post(
                    "http://127.0.0.1:8883/api/classification/import",
                    json={"auto_classify": True, "auto_create_kb": True, "documents": docs},
                )
            result["indexed_doc_files"] = len(doc_files)
        except Exception:
            pass

    # 5. Pattern analysis via evolution-engine (if task + summary provided)
    if task and summary and code_files:
        try:
            from app.tools.evolution_engine.db.database import async_session_factory as evo_session
            from app.tools.evolution_engine.services.event_collector import EventCollector
            from app.tools.evolution_engine.services.llm_pattern_analyzer import LLMPatternAnalyzer

            async with evo_session() as evo_db:
                collector = EventCollector(evo_db)
                event = await collector.collect(
                    "success", "mcp_index_changes", task, summary,
                    {"project_id": pid, "files_count": len(code_files)}
                )

                analyzer = LLMPatternAnalyzer(evo_db)
                analysis = await analyzer.analyze("success", task, summary,
                    {"project_id": pid, "files_count": len(code_files)})
                await analyzer.save_analysis(event.id, analysis)
                await collector.mark_processed(event.id)

                confidence = analysis.get("confidence", 0)
                result["patterns_found"] = [{
                    "category": analysis.get("category", ""),
                    "pattern": analysis.get("success_pattern") or analysis.get("fix_pattern", ""),
                    "confidence": confidence,
                }]

                if confidence >= 0.5:
                    # Auto-propose evolution
                    from app.db.database import async_session_factory
                    from app.modules.evolution.models import EvolutionVersion

                    async with async_session_factory() as db:
                        version = EvolutionVersion(
                            version="0.1.0",
                            level="project",
                            title=analysis.get("success_pattern") or analysis.get("fix_pattern") or task[:100],
                            description=f"任务: {task}\n总结: {summary}\n模式: {analysis.get('success_pattern') or analysis.get('fix_pattern', '')}",
                            source_project_id=int(pid) if pid.isdigit() else 0,
                            changes={"pattern": analysis.get("success_pattern") or analysis.get("fix_pattern")},
                            affected_tools=["code-index"],
                            review_status="pending",
                            review_log=[],
                        )
                        db.add(version)
                        await db.commit()
                        result["evolution_proposed"] = True
        except Exception as e:
            result["patterns_error"] = str(e)[:100]

    session_manager.record_tool_call(session_id, "index_changes")
    return json.dumps(result, ensure_ascii=False, indent=2)


def _load_script_content(filename: str) -> str:
    """Load script content from disk (dev) or embedded fallback (prod)."""
    import os as _os
    base = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
    path = _os.path.join(base, "scripts", filename)
    if _os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass

    if filename == "sync_changes.py":
        return '''"""
Git post-commit hook helper: 自动同步本地变更到系统索引
每次 git commit 后调用，只同步变动的文件（差量更新）

安装: aidp_init.py 自动写入 .git/hooks/post-commit
手动: python scripts/sync_changes.py --project-id 42
"""

import os, re, sys, json, argparse, subprocess, urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTROLLER_URL = os.environ.get("AIDP_CONTROLLER_URL", "http://192.168.0.100:8883")

CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".cs", ".rb", ".php", ".swift", ".kt"}
DOC_EXTENSIONS = {".md", ".txt", ".rst", ".adoc"}
SKIP_DIRS = {"node_modules", "__pycache__", ".git", ".venv", "venv", "dist", "build", ".idea", "target", "vendor", "bin", "obj"}

def load_project_id():
    config_path = os.path.join(PROJECT_ROOT, ".opencode", "watcher.json")
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                return json.load(f).get("project_id", 0)
        except Exception:
            pass
    return 0

def get_token():
    cfg = os.path.join(PROJECT_ROOT, ".opencode", "watcher.json")
    if os.path.exists(cfg):
        try:
            with open(cfg) as f:
                return json.load(f).get("api_key", "")
        except Exception:
            pass
    return os.environ.get("AIDP_API_KEY", "")

def get_changed_files():
    try:
        result = subprocess.run(["git", "diff", "--name-only", "HEAD~1", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            return []
        return [f for f in result.stdout.strip().split("\\n") if f]
    except Exception:
        return []

def should_skip(path):
    parts = path.replace("\\\\", "/").split("/")
    return any(p in SKIP_DIRS or p.startswith(".") for p in parts)

def sync_code_files(file_paths, project_id):
    token = get_token()
    batch = []
    for fp in file_paths:
        abs_path = os.path.join(PROJECT_ROOT, fp)
        if not os.path.exists(abs_path):
            continue
        ext = os.path.splitext(fp)[1].lower()
        lang_map = {".py":"python",".js":"javascript",".ts":"typescript",".jsx":"javascript",".tsx":"typescript",".java":"java",".go":"go",".rs":"rust",".rb":"ruby",".php":"php",".c":"c",".cpp":"cpp",".cs":"csharp"}
        lang = lang_map.get(ext, "unknown")
        if lang == "unknown":
            continue
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if content.strip():
                batch.append({"path": fp.replace("\\\\", "/"), "content": content, "language": lang})
        except Exception:
            pass
    if not batch:
        return
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-API-Key"] = token
    for i in range(0, len(batch), 10):
        chunk = batch[i:i+10]
        payload = json.dumps({"capability": "code.index_files", "arguments": {"project_id": project_id, "files": chunk}})
        req = urllib.request.Request(f"{CONTROLLER_URL}/api/tools/code-index/invoke", data=payload.encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                print(f"  [code] synced {len(chunk)} files -> project {project_id}")
        except Exception as e:
            print(f"  [code] sync error: {e}")

def sync_doc_files(file_paths):
    token = get_token()
    docs = []
    for fp in file_paths:
        abs_path = os.path.join(PROJECT_ROOT, fp)
        if not os.path.exists(abs_path):
            continue
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if content.strip():
                title = os.path.splitext(os.path.basename(fp))[0]
                docs.append({"title":title,"content":content,"filename":fp.replace("\\\\","/"),"source_uri":fp.replace("\\\\","/")})
        except Exception:
            pass
    if not docs:
        return
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-API-Key"] = token
    payload = json.dumps({"auto_classify": True, "auto_create_kb": True, "documents": docs})
    req = urllib.request.Request(f"{CONTROLLER_URL}/api/classification/import", data=payload.encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            print(f"  [doc] synced {len(docs)} files")
    except Exception as e:
        print(f"  [doc] sync error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Sync changed files from git commit to AIDP index")
    parser.add_argument("--project-id", "-p", type=int, default=0, help="AIDP project ID")
    args = parser.parse_args()
    project_id = args.project_id or load_project_id()
    if not project_id:
        print("[sync] ERROR: No project_id")
        sys.exit(1)
    files = get_changed_files()
    if not files:
        print("[sync] No changed files")
        return
    code_files, doc_files = [], []
    for fp in files:
        if should_skip(fp):
            continue
        ext = os.path.splitext(fp)[1].lower()
        if ext in CODE_EXTENSIONS:
            code_files.append(fp)
        elif ext in DOC_EXTENSIONS:
            doc_files.append(fp)
    if code_files:
        print(f"[sync] Syncing {len(code_files)} code files...")
        sync_code_files(code_files, project_id)
    if doc_files:
        print(f"[sync] Syncing {len(doc_files)} doc files...")
        sync_doc_files(doc_files)

if __name__ == "__main__":
    main()'''

    # Default: empty
    return ""


_SYNC_CHANGES_SCRIPT = None
_FILE_WATCHER_SCRIPT = None


def _get_sync_changes_script() -> str:
    global _SYNC_CHANGES_SCRIPT
    if _SYNC_CHANGES_SCRIPT is None:
        _SYNC_CHANGES_SCRIPT = _load_script_content("sync_changes.py")
    return _SYNC_CHANGES_SCRIPT


@mcp.tool()
async def get_index_rules(
    ctx: Context,
    project_dir: str = "",
    project_type: str = "auto",
) -> str:
    """获取代码索引的扫描规则和本地安装脚本 — 在 aidp_init 之前调用。

    返回完整的扫描配置 + 两个本地脚本（git hook + 文件监控），
    Agent 按规则扫描本地项目后，写入脚本并启动后台监控。

    Args:
        project_dir: 项目根目录绝对路径, 如 "D:\\\\Project\\\\web\\\\RuoYi-Cloud-Plus"
                     留空则只返回扫描规则，不含项目特定的脚本
        project_type: 项目类型提示: "java" | "python" | "frontend" | "auto"
                      影响 include_extensions 和 priority_patterns 的权重

    Returns:
        JSON 包含:
        - scan_config: 扫描配置（排除规则、文件类型、优先级等）
        - agent_checklist: Agent 自主分析的步骤和质询清单
        - setup_scripts: 本地脚本内容（git hook + file watcher + sync_changes）
    """
    import platform as _platform

    os_name = _platform.system().lower()
    controller_url = "http://192.168.0.100:8883"
    dir_clean = project_dir.rstrip("/").rstrip("\\\\") if project_dir else ""

    scan_config = {
        "max_file_size_kb": 100,
        "max_total_files": 50,
        "include_extensions": {
            "java": [".java"],
            "python": [".py"],
            "javascript": [".js", ".jsx"],
            "typescript": [".ts", ".tsx"],
            "go": [".go"],
            "rust": [".rs"],
            "yaml": [".yml", ".yaml"],
            "json": [".json"],
            "xml": [".xml"],
            "sql": [".sql"],
            "markdown": [".md"],
            "html": [".html"],
            "css": [".css", ".scss"],
            "vue": [".vue"],
            "kotlin": [".kt"],
            "csharp": [".cs"],
        },
        "priority_patterns": [
            "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
            "package.json", "tsconfig.json", "requirements.txt", "pyproject.toml",
            "Cargo.toml", "go.mod", "CMakeLists.txt", "Makefile",
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
            "README.md", "CHANGELOG.md", "CONTRIBUTING.md",
            "**/Application.java", "**/*Application.java",
            "**/*Controller.java", "**/*Service.java", "**/*ServiceImpl.java",
            "**/*Config.java", "**/*Configuration.java", "**/*Mapper.java",
            "**/main.py", "**/app.py", "**/settings.py", "**/config.py",
            "**/index.ts", "**/main.ts", "**/App.tsx", "**/App.vue",
            "**/*.module.ts", "src/main/**", "src/**/__init__.py",
        ],
        "path_exclude": [
            "**/node_modules/**", "**/target/**", "**/build/**", "**/dist/**",
            "**/.git/**", "**/__pycache__/**", "**/.venv/**", "**/venv/**",
            "**/logs/**", "**/coverage/**", "**/.idea/**", "**/.vscode/**",
            "**/vendor/**", "**/bin/**", "**/obj/**", "**/.mypy_cache/**",
            "**/.pytest_cache/**", "**/egg-info/**", "**/.tox/**",
            "**/.next/**", "**/.nuxt/**", "**/doc/**", "**/docs/**",
            "**/docker/**", "**/data/**", "**/assets/**", "**/public/**",
        ],
        "file_exclude": [
            "*.min.js", "*.min.css", "*.map", "*.pyc", "*.class",
            "*.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
            "*.flattened-pom.xml", "*.iml", ".DS_Store",
        ],
    }

    agent_checklist = {
        "step_1": "使用 glob 工具递归扫描项目文件。例如: glob '**/*.java' '**/*.xml' '**/pom.xml'。覆盖所有 include_extensions 中的扩展名",
        "step_2": "路径过滤: 剔除所有匹配 path_exclude 模式的文件。注意 **/target/** 等模式匹配任意深度",
        "step_3": "文件过滤: 剔除匹配 file_exclude 的文件，剔除大小 > max_file_size_kb 或 0 字节的文件",
        "step_4": "自主分析 — 对剩余候选文件，逐一回答:",
        "step_4a": "  这个文件是手写的业务/框架代码？还是自动生成的？(mybatis-generator/swagger/proto 生成的代码排除)",
        "step_4b": "  这个文件是核心源码？还是测试数据/配置文件示例？(test fixtures, *.sql 只留 schema DDL)",
        "step_4c": "  根级构建配置文件 (pom.xml, package.json 等) 是否已纳入？",
        "step_5": "排序: 匹配 priority_patterns 的文件优先。其次按模块重要性排列 (入口类 > Controller > Service > Config > Model > Util)",
        "step_6": "截断: 总数不超过 max_total_files 个",
        "qa_checklist": [
            "是否混入了自动生成的代码 (generated, auto-generated, swagger, proto)？",
            "根级构建配置文件和 README 都纳入了吗？",
            "各模块/包的主入口类是否遗漏？",
            "有没有大数据文件 (>100KB) 混入？",
            "项目中是否有其他非标准构建目录需要额外排除？(如 .gradle/, out/, classes/)",
        ],
    }

    result = {
        "success": True,
        "scan_config": scan_config,
        "agent_checklist": agent_checklist,
        "setup_scripts": {},
        "controller_url": controller_url,
    }

    if dir_clean:
        sync_script = _get_sync_changes_script()

        git_hook_path = dir_clean + "/.git/hooks/post-commit"
        if os_name == "windows":
            git_hook_content = (
                f'@echo off\r\n'
                f'python "%~dp0\\..\\..\\scripts\\sync_changes.py" -p {{PROJECT_ID}}\r\n'
            )
        else:
            git_hook_content = (
                f'#!/bin/sh\n'
                f'python "$(dirname "$0")/../../scripts/sync_changes.py" -p {{PROJECT_ID}}\n'
            )

        result["setup_scripts"] = {
            "sync_changes_py": {
                "description": "增量同步脚本，git hook 调用",
                "path": dir_clean + "/scripts/sync_changes.py",
                "content": sync_script,
                "note": "Agent 需创建 scripts/ 目录并写入此文件",
            },
            "git_hook": {
                "description": "post-commit 钩子",
                "path": git_hook_path,
                "content": git_hook_content,
                "os": os_name,
                "note": "Agent 需写入此文件。{{PROJECT_ID}} 在 aidp_init 后由 install_local_scripts 替换为实际 ID。Linux/Mac 需 chmod +x",
            },
            "watcher_config": {
                "description": "项目配置，供脚本读取 project_id 和 api_key",
                "path": dir_clean + "/.opencode/watcher.json",
                "content_template": {
                    "project_id": "{{PROJECT_ID}}",
                    "project_root": dir_clean,
                    "controller_url": controller_url,
                    "api_key": "{{API_KEY}}",
                    "layers": {"git_hook": True, "file_watcher": True, "agent": True},
                },
                "note": "Agent 在 aidp_init 后调用 install_local_scripts 获取带 ID 的完整配置",
            },
            "file_watcher_cmd": {
                "description": "文件监控启动命令",
                "install_deps": "pip install watchdog",
                "command": f"python {dir_clean}/scripts/sync_changes.py --project-id {{PROJECT_ID}}",
                "alt_full_watcher": f"python {dir_clean}/scripts/file_watcher.py -d {dir_clean} -p {{PROJECT_ID}}",
                "os": os_name,
                "note": "Agent 需以后台进程启动。Windows: Start-Process -NoNewWindow, Linux/Mac: nohup ... &",
            },
        }

    result["operations"] = [
        {
            "id": 1, "action": "scan_project",
            "instruction": "用 glob 扫描项目代码文件。示例: glob '**/*.java' '**/*.xml' '**/pom.xml' '**/*.yml' '**/*.md'。覆盖 include_extensions 中所有扩展名",
            "verify": "列出文件名列表，确认 ≥20 个代码文件 + 构建配置文件",
            "failure_action": "扩大扫描范围，检查是否排除了 src/main 目录。Glob 可能不返回隐藏目录——显式指定每个文件类型"
        },
        {
            "id": 2, "action": "infer_tech_stack",
            "instruction": "统计 key_files 扩展名分布。读取 pom.xml / build.gradle / package.json 提取框架名和版本号。格式: 'Java 17 + Spring Boot 3.x + Maven'",
            "verify": "tech_stack 不为空，包含编程语言名 + 框架名",
            "failure_action": "读取项目根级 README.md 手动提取技术栈描述"
        },
        {
            "id": 3, "action": "build_key_files",
            "instruction": "读取 ≤50 个优先级文件（构建配置 + 各模块入口类 + Controller + Service + Config），每个 ≤100KB",
            "verify": "key_files 列表 ≥10 个，包含构建文件和至少3个模块的入口类",
            "failure_action": "减少文件数到核心5-10个，确保未超过大小限制100KB"
        },
        {
            "id": 4, "action": "call_aidp_init",
            "instruction": "aidp_init(project_name=..., description=..., tech_stack=..., key_files=[...])。系统会自动推断缺失参数",
            "verify": "返回 project_id 且 readiness.score ≥ 40。如果 < 100，检查 readiness.missing 列表",
            "failure_action": "根据 readiness.next_actions 补全参数。tech_stack未推断→传入显式值。agents未生成→用 aidp_generate_agents 单独重做"
        },
        {
            "id": 5, "action": "verify_init",
            "instruction": "aidp_verify(project_id)。确认 readiness score",
            "verify": "score ≥ 60，agents > 0，documents > 0",
            "failure_action": "aidp_reindex(project_id, phase='docs') 或 aidp_generate_agents(project_id, tech_stack='...')"
        },
        {
            "id": 6, "action": "install_local_tools",
            "instruction": "install_local_scripts(project_dir, project_id)。获取 watcher.json, git hook, sync_changes.py",
            "verify": ".git/hooks/post-commit 文件存在，.opencode/watcher.json 含正确 project_id",
            "failure_action": "手动创建目录 scripts/ 和 .opencode/，分别写入各文件"
        },
        {
            "id": 7, "action": "start_watcher",
            "instruction": "pip install watchdog && 后台启动文件监控。Windows: Start-Process -NoNewWindow。继续执行其他任务，监控在后台运行",
            "verify": "进程列表中有 python 进程运行 sync_changes.py 或 file_watcher.py",
            "failure_action": "确认 watchdog 已安装，Python 版本 ≥3.8"
        },
    ]

    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def install_local_scripts(
    ctx: Context,
    project_dir: str,
    project_id: int,
    api_key: str = "",
    layers: str = "all",
) -> str:
    """安装本地索引脚本 — 返回 Agent 写入本地文件系统的配置和脚本。

    在 aidp_init 成功后调用，获取带实际 project_id 的脚本和配置。

    Args:
        project_dir: 项目根目录绝对路径, 如 "D:\\Project\\web\\RuoYi-Cloud-Plus"
        project_id: AIDP 项目 ID (aidp_init 返回)
        api_key: API Key (必填，用于脚本鉴权，从 MCP 配置 headers 传入)
        layers: 安装哪些层 (默认 all):
                "all" — 全部安装
                "git_hook" — 仅 git hook
                "file_watcher" — 仅 file watcher
                "watcher_config" — 仅 watcher.json

    Returns:
        JSON 包含:
        - watcher_config: .opencode/watcher.json 完整内容
        - sync_changes_script: scripts/sync_changes.py 完整脚本内容
        - git_hook_script: .git/hooks/post-commit 脚本
        - file_watcher_cmd: 启动命令

    Agent 执行指令:
        1. write_file(files.sync_changes_script.path, files.sync_changes_script.content)
        2. write_file(files.watcher_config.path, files.watcher_config.content)
        3. write_file(files.git_hook_script.path, files.git_hook_script.content)
        4. execute(files.install_cmd, ...) 安装 watchdog
        5. execute(files.file_watcher_cmd.command, background=true)
    """
    import platform as _platform
    from datetime import datetime

    os_name = _platform.system().lower()
    controller_url = "http://192.168.0.100:8883"
    dir_clean = project_dir.rstrip("/").rstrip("\\")

    # Resolve api_key: param > headers
    auth_key = api_key
    if not auth_key:
        try:
            request = ctx.request
            if hasattr(request, 'headers'):
                auth_key = request.headers.get("x-api-key", "") or request.headers.get("authorization", "").replace("Bearer ", "")
        except Exception:
            pass

    if not auth_key:
        return json.dumps({
            "success": False,
            "error": {
                "code": "API_KEY_REQUIRED",
                "message": "api_key 是必填参数，请在 MCP 配置中设置 x-api-key header",
                "hint": "在 opencode.json 的 mcp 配置中添加 headers: {\"x-api-key\": \"your-api-key\"}",
            }
        }, ensure_ascii=False, indent=2)

    api_key = auth_key

    watcher_config = {
        "project_id": project_id,
        "project_name": "",
        "project_root": dir_clean,
        "controller_url": controller_url,
        "api_key": api_key,
        "created_at": datetime.now().isoformat(),
        "layers": {
            "git_hook": layers in ("all", "git_hook"),
            "file_watcher": layers in ("all", "file_watcher"),
            "agent": True,
        },
    }

    sync_script = _get_sync_changes_script()

    git_hook_content = ""
    if os_name == "windows":
        git_hook_content = (
            f'@echo off\r\n'
            f'python "%~dp0\\..\\..\\scripts\\sync_changes.py" -p {project_id}\r\n'
        )
    else:
        git_hook_content = (
            f'#!/bin/sh\n'
            f'python "$(dirname "$0")/../../scripts/sync_changes.py" -p {project_id}\n'
        )

    sync_script_path = dir_clean + "/scripts/sync_changes.py"
    hook_path = dir_clean + "/.git/hooks/post-commit"
    watcher_path = dir_clean + "/.opencode/watcher.json"

    files = {
        "sync_changes_script": {
            "description": "增量同步脚本 (git hook 调用，含 code + doc 同步逻辑)",
            "path": sync_script_path,
            "content": sync_script,
            "note": "Agent 需创建 scripts/ 目录并写入此文件",
        },
        "watcher_config": {
            "description": "项目配置文件",
            "path": watcher_path,
            "content": watcher_config,
            "note": "Agent 需创建 .opencode/ 目录并写入此 JSON",
        },
        "git_hook_script": {
            "description": "Git post-commit 钩子",
            "path": hook_path,
            "content": git_hook_content,
            "os": os_name,
            "note": "Agent 需写入此文件。Linux/Mac 需 chmod +x",
        },
    }

    if layers in ("all", "file_watcher"):
        files["install_cmd"] = {
            "command": "pip install watchdog",
            "os": "cross-platform",
            "note": "Agent 需先执行此命令安装依赖",
        }
        files["file_watcher_cmd"] = {
            "description": "文件监控 (基于 watchdog 或 git diff 轮询)",
            "command": f"python {sync_script_path} --project-id {project_id}",
            "alt_git_poll": f"powershell -Command \"while($true){{python {sync_script_path} -p {project_id}; Start-Sleep 5}}\"" if os_name == "windows" else f"watch -n 5 'python {sync_script_path} -p {project_id}'",
            "os": os_name,
            "note": "Agent 需后台启动。Windows: Start-Process -NoNewWindow, Linux/Mac: nohup ... &",
        }

    return json.dumps({
        "success": True,
        "project_id": project_id,
        "project_dir": project_dir,
        "controller_url": controller_url,
        "files": files,
        "agent_actions": [
            f"mkdir -p {dir_clean}/scripts/",
            f"mkdir -p {dir_clean}/.opencode/",
            f"写入 {sync_script_path}",
            f"写入 {watcher_path}",
            f"写入 {hook_path}",
            "pip install watchdog (如需要完整文件监控)",
            f"后台启动文件监控",
        ],
    }, ensure_ascii=False, indent=2)