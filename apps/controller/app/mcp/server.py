import json
from fastmcp import FastMCP
from app.services.tool_registry import list_tools, health_check_tool, health_check_all, sync_capabilities
from app.services.tool_invoker import invoke_tool, get_invocation_history
from app.services.project_init_service import init_project, load_agent_instructions

mcp = FastMCP("aidp-controller")


@mcp.tool()
async def invoke_tool_mcp(tool_name: str, capability: str, arguments: str = "{}", user_id: int = 0) -> str:
    """Invoke a registered tool with the given capability and arguments."""
    try:
        args = json.loads(arguments) if isinstance(arguments, str) else arguments
    except json.JSONDecodeError:
        args = {}
    result = await invoke_tool(tool_name, capability, args, user_id=user_id)
    return json.dumps(result, indent=2)


@mcp.tool()
async def list_registered_tools(status: str = "") -> str:
    """List all registered tools."""
    tools = await list_tools(status=status or None)
    return json.dumps(tools, indent=2)


@mcp.tool()
async def check_tool_health(tool_name: str = "") -> str:
    """Check health of a specific tool or all tools."""
    if tool_name:
        result = await health_check_tool(tool_name)
    else:
        result = await health_check_all()
    return json.dumps(result, indent=2)


@mcp.tool()
async def sync_tool_capabilities(tool_name: str) -> str:
    """Sync capabilities from a tool's manifest."""
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
    """Initialize a project in AIDP: register project, import docs, store architecture knowledge, index assets."""
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
    project_name: str,
    task: str = "",
    agent_type: str = "main",
) -> str:
    """Instructions-First Staged Context Engine.

    Stage 0: Load Agent Instructions from DB
    Stage 1: Analyze user intent via skill-router (identifies required tools, queries, budget)
    Stage 2: Parallel knowledge retrieval from memory/knowledge/code-index/asset
    Stage 3: Skill matching
    Stage 4: Context assembly

    Call this before starting any development task.
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

    return json.dumps(result, indent=2)


@mcp.tool()
async def aidp_instructions(
    project_name: str,
    task: str,
    agent_type: str = "subagent:sandbox-tool",
) -> str:
    """Generate subagent instructions from project context.

    Use this when you need to create a subagent for a specific task.
    The returned instructions include role, task, context, and tool permissions
    that should be passed directly to the subagent.

    Args:
        project_name: Project name
        task: The specific task the subagent should perform
        agent_type: Subagent type identifier (e.g., "subagent:sandbox-tool")
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