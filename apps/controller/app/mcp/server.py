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
它会触发 5 阶段 Pipeline: 加载 Instructions → 意图分析 → 知识检索 → 技能匹配 → 上下文组装。

工具调用顺序:
1. aidp_context(project_name, task) → 获取上下文
2. invoke_tool_mcp(tool_name, capability, arguments) → 执行具体操作
3. 工作完成后可选: invoke_tool_mcp("memory-tool", "memory.create", {...}) → 归档经验

复杂任务拆分时:
- aidp_instructions(project_name, task) → 生成 subagent 专用指令

项目管理:
- list_registered_tools() → 查看所有可用工具
- check_tool_health() → 检查工具健康状态
- aidp_init(...) → 导入新项目到 AIDP""",
)


@mcp.tool()
async def invoke_tool_mcp(ctx: Context, tool_name: str, capability: str, arguments: str = "{}", user_id: int = 0) -> str:
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
async def aidp_init(
    project_name: str,
    description: str = "",
    tech_stack: str = "",
    nas_path: str = "",
    docs: str = "[]",
    key_files: str = "[]",
    architecture_summary: str = "",
) -> str:
    """初始化项目到 AIDP — 将新项目导入平台进行管理。

    当需要将一个尚未在 AIDP 中的项目导入时调用。会自动扫描项目目录、
    识别技术栈、存储架构信息、建立知识索引。
    已存在的项目不需要重复初始化。

    Args:
        project_name: 项目唯一名称，例如 "my-web-app"
        description: 项目描述 (可选)
        tech_stack: 技术栈描述，例如 "Python 3.13 + FastAPI + PostgreSQL"
        nas_path: 项目在 NAS 上的路径 (可选)，例如 "/home/docker/projects/my-app"
        docs: JSON 数组格式的文档列表，例如 '[{"title": "README", "content": "..."}]'
        key_files: JSON 数组格式的关键文件列表，例如 '[{"path": "main.py", "content": "...", "type": "python"}]'
        architecture_summary: 架构概述 (可选)

    Returns:
        JSON 格式的初始化结果，包含 project_id 和索引状态。

    使用场景:
        - 新项目首次接入 AIDP
        - 项目有重大架构变更时重新初始化
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

    result = await init_project(
        project_name=project_name,
        description=description,
        tech_stack=tech_stack,
        nas_path=nas_path,
        docs=parsed_docs,
        key_files=parsed_files,
        architecture_summary=architecture_summary,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def aidp_context(
    ctx: Context,
    project_name: str,
    task: str = "",
    agent_type: str = "main",
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

    Returns:
        JSON 包含各阶段结果和最终组装的上下文。后续步骤使用 invoke_tool_mcp 执行具体操作。

    工作流示例:
        1. 先调用 aidp_context 获取上下文
        2. 再调用 invoke_tool_mcp 执行具体工具
        3. 完成后可选调用 invoke_tool_mcp("memory-tool", "memory.create", {...}) 归档经验
    """
    import httpx

    result = {"project_name": project_name, "task": task, "agent_type": agent_type, "stages": {}}

    try:
        # Stage 0: Load Instructions
        instructions = await load_agent_instructions(project_name, agent_type)
        result["stages"]["stage0_instructions"] = {
            "role": instructions.get("role", "")[:100],
            "rules_count": len(instructions.get("rules", [])),
        }

        if not task:
            result["instructions"] = instructions
            return json.dumps(result, indent=2)

        # Stage 1: Intent Analysis via skill-router
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "http://127.0.0.1:8788/tool/invoke",
                json={
                    "trace_id": "",
                    "capability": "analyze_intent",
                    "context": {},
                    "input": {"task": task, "instructions": instructions},
                },
                headers={"Content-Type": "application/json"},
            )
            intent = {}
            if resp.status_code == 200:
                data = resp.json()
                intent = data.get("output", {}) if data.get("success") else {}

            if not intent or not intent.get("required_tools"):
                intent = {
                    "intent": {"primary": "understand", "domain": project_name},
                    "required_tools": ["memory-tool"],
                    "search_queries": {"memory-tool": [task[:100]]},
                    "budget_hints": {"total": 6000, "memory-tool": 6000},
                    "relevant_rules": [],
                }

            result["stages"]["stage1_intent"] = {
                "primary": intent.get("intent", {}).get("primary", "?"),
                "domain": intent.get("intent", {}).get("domain", "?"),
                "required_tools": intent.get("required_tools", []),
            }

            # Stage 2: Staged Retrieval via context-optimizer
            resp2 = await client.post(
                "http://127.0.0.1:18088/api/staged-retrieve",
                json={
                    "required_tools": intent.get("required_tools", []),
                    "search_queries": intent.get("search_queries", {}),
                    "budget_hints": intent.get("budget_hints", {}),
                },
                headers={"Content-Type": "application/json"},
            )
            staged_results = {}
            if resp2.status_code == 200:
                staged_results = resp2.json()

            result["stages"]["stage2_retrieval"] = {
                "tools_queried": list(staged_results.keys()),
            }

            # Stage 3: Skill Matching
            skills = []
            try:
                resp3 = await client.post(
                    "http://127.0.0.1:8788/tool/invoke",
                    json={
                        "trace_id": "",
                        "capability": "resolve_task",
                        "context": {},
                        "input": {"task": task, "mode": "auto", "top_k": 3, "api_key": "sk-1234567890"},
                    },
                    headers={"Content-Type": "application/json"},
                )
                if resp3.status_code == 200:
                    data3 = resp3.json()
                    if data3.get("success") and data3.get("output"):
                        out = data3["output"]
                        if isinstance(out, dict):
                            skills = out.get("data", {}).get("skills", [])[:3]
            except Exception:
                pass

            result["stages"]["stage3_skills"] = {
                "matched": len(skills),
            }

            # Stage 4: Context Assembly via context-optimizer
            resp4 = await client.post(
                "http://127.0.0.1:18088/api/assemble-context",
                json={
                    "instructions": instructions,
                    "intent": intent,
                    "staged_results": staged_results,
                    "skills": skills,
                },
                headers={"Content-Type": "application/json"},
            )
            assembled = {}
            if resp4.status_code == 200:
                assembled = resp4.json()

            result["context"] = assembled.get("context", "No context assembled")[:5000]
            result["estimated_tokens"] = assembled.get("estimated_tokens", 0)
            result["stages"]["stage4_assembly"] = {
                "sections": assembled.get("sections", 0),
                "estimated_tokens": assembled.get("estimated_tokens", 0),
            }

    except Exception as e:
        result["error"] = str(e)

    # 标记该会话已加载上下文
    session_id = ctx.session_id or "default"
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
    import httpx

    result = {"project_name": project_name, "task": task, "agent_type": agent_type}

    try:
        # Stage 0: Load parent instructions
        parent_instructions = await load_agent_instructions(project_name, "main")

        # Stage 1: Intent analysis
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "http://127.0.0.1:8788/tool/invoke",
                json={
                    "trace_id": "",
                    "capability": "analyze_intent",
                    "context": {},
                    "input": {"task": task, "instructions": parent_instructions},
                },
                headers={"Content-Type": "application/json"},
            )
            intent = {}
            if resp.status_code == 200:
                data = resp.json()
                intent = data.get("output", {}) if data.get("success") else {}

            domain = intent.get("intent", {}).get("domain", project_name)

            # Stage 2: Retrieval
            resp2 = await client.post(
                "http://127.0.0.1:18088/api/staged-retrieve",
                json={
                    "required_tools": intent.get("required_tools", ["memory-tool", "code-index"]),
                    "search_queries": intent.get("search_queries", {}),
                    "budget_hints": intent.get("budget_hints", {}),
                },
                headers={"Content-Type": "application/json"},
            )
            staged_results = {}
            if resp2.status_code == 200:
                staged_results = resp2.json()

            # Stage 3: Skills
            skills = []
            try:
                resp3 = await client.post(
                    "http://127.0.0.1:8788/tool/invoke",
                    json={
                        "trace_id": "",
                        "capability": "resolve_task",
                        "context": {},
                        "input": {"task": task, "mode": "auto", "top_k": 2, "api_key": "sk-1234567890"},
                    },
                    headers={"Content-Type": "application/json"},
                )
                if resp3.status_code == 200:
                    data3 = resp3.json()
                    if data3.get("success") and data3.get("output"):
                        out = data3["output"]
                        if isinstance(out, dict):
                            skills = out.get("data", {}).get("skills", [])[:2]
            except Exception:
                pass

            # Stage 4: Generate subagent instructions
            resp4 = await client.post(
                "http://127.0.0.1:18088/api/assemble-subagent",
                json={
                    "task": task,
                    "parent_instructions": parent_instructions,
                    "domain": domain,
                    "context": staged_results,
                    "skills": skills,
                },
                headers={"Content-Type": "application/json"},
            )
            if resp4.status_code == 200:
                result["subagent_instructions"] = resp4.json()
            else:
                result["subagent_instructions"] = {
                    "agent_type": agent_type,
                    "role": f"Subagent for {domain}",
                    "task": task,
                    "context": {"relevant_files": [], "patterns": [], "constraints": []},
                    "allowed_tools": ["code-index", "quality-tool", "sandbox-tool"],
                }

    except Exception as e:
        result["error"] = str(e)

    return json.dumps(result, indent=2)