# 开发工作流

**源文件**: `.opencode/AGENTS.md`

## 强制工作流 (5 步)

```
1. aidp_context()    →  加载上下文 (必须第一步)
2. 搜索已有知识     →  避免重复造轮子
3. 编写代码          →  实现功能
4. 验证              →  sandbox-tool + quality-tool
5. 知识沉淀          →  强制归档到 AIDP
```

## 第 1 步: 加载上下文 (强制)

**每次开发任务，第一个操作必须是**:

```
aidp_context(project_name="openCode", task="<用户任务描述>")
```

规则: 不要等待，不要询问，直接调用。用户只需说"修 bug"或"加功能"，Agent 负责调用。

**原因**: 这是 `aidp_context` → 5 阶段上下文管线的入口，未先调用则后续 `invoke_tool_mcp` 返回 `CONTEXT_REQUIRED` 错误。

## 第 2 步: 搜索已有知识

避免重复工作:

```
# 搜索代码结构
invoke_tool_mcp("code-index", "code.search.semantic",
    '{"project_id":2,"query":"<关键词>"}')

# 搜索项目记忆
invoke_tool_mcp("memory-tool", "memory.search",
    '{"project":"openCode","query":"<关键词>"}')
```

## 第 3 步: 编写代码

编写代码时遵循项目编码规范 (`02-code-style.md`)。所有修改在本地进行。

## 第 4 步: 验证

使用 AIDP 工具验证代码:

```
# 执行测试代码
invoke_tool_mcp("sandbox-tool", "sandbox.execute",
    '{"code":"...", "language":"python"}')

# 检查代码质量
invoke_tool_mcp("quality-tool", "quality.check",
    '{"code":"...", "filename":"test.py"}')
```

## 第 5 步: 知识沉淀 (强制)

**修改本地代码不会自动同步到 AIDP 工具**。每次修改后必须手动同步:

| 场景 | 操作 | 说明 |
|------|------|------|
| 发现一个规则 (必须/禁止) | `POST /api/classification/import` → `rule` | 存入规则引擎 |
| 发现可复用的技能 | `invoke_tool_mcp("skill-router", "skill_register", ...)` | 注册到技能库 |
| 架构/设计决策 | `POST /api/classification/import` → `knowledge doc` | 存入知识库 |
| 项目级知识/记忆 | `invoke_tool_mcp("memory-tool", "memory.create", ...)` | 存入记忆库 |
| 写完新功能 | 更新 `docs/` 下对应文档 | 文件监听自动同步 |

### 项目上下文传递 (必须)

调用 AIDP 工具时必须带上项目标识:

| 工具 | 上下文参数 |
|------|-----------|
| `memory-tool` | `"project": "openCode"` |
| `knowledge-tool` | `"project_id": "openCode"` 或 `"workspace_id": "openCode"` |
| `code-index` | `"project_id": 3` |
| `skill-router` | 自动从 Controller 获取 |
| `sandbox-tool` / `quality-tool` | 不需要 |

### API Key

从 `.opencode/opencode.jsonc` 的 `aidp.api_key` 字段读取，传入 `invoke_tool_mcp` 的 `api_key` 参数。未配置则默认使用 admin 用户。

**注意**: 当前 `opencode.jsonc` 未包含 `aidp.api_key` 字段，仅包含 `"$schema"` 和 `"instructions": ["AGENTS.md"]`。

## 创建 Subagent

任务复杂需要拆分时:

1. 调用 `aidp_instructions(project_name="openCode", task, agent_type)` 生成 subagent 专属指令
2. 用返回的指令创建 subagent
3. Subagent 也会遵循相同的工作流 (首先调用 `aidp_context`)

## 使用示例: 完整工作流

```python
# Step 1: 加载上下文 (必须先做)
aidp_context(project_name="openCode", task="修复登录页 cookie 问题")

# Step 2: 搜索记忆中的 cookie 相关经验
invoke_tool_mcp("memory-tool", "memory.search",
    '{"project":"openCode","query":"cookie 登录"}')

# Step 2: 搜索代码中的 cookie 相关实现
invoke_tool_mcp("code-index", "code.search.semantic",
    '{"project_id":3,"query":"session cookie login"}')

# Step 3: 编写代码...
# (修改 apps/controller/app/web/routes.py 中的 cookie 处理)

# Step 4: 验证修复
invoke_tool_mcp("sandbox-tool", "sandbox.execute",
    '{"code":"# test cookie...", "language":"python"}')

# Step 5: 保存记忆 (强制)
invoke_tool_mcp("memory-tool", "memory.create", '{
    "project": "openCode",
    "category": "bugfix",
    "title": "修复登录页 cookie 问题",
    "content": "修改了 routes.py 中的 cookie 处理逻辑..."
}')
```

## 本地文件 ≠ AIDP 知识

| 本地文件修改后 | 需要调用的 AIDP 工具 |
|---------------|-------------------|
| 代码变更 | `memory-tool` → `memory.create` |
| 文档更新 | `knowledge-tool` API |
| 发现新规则/模式 | `memory-tool` → `memory.create` |

**重要**: 如果开发完成后不做知识沉淀，AIDP 系统的搜索能力将永远是空的。

## 部署流程

所有修改最终部署到 NAS (`192.168.0.100`):

```
1. 打包:   tar czf deploy.tar.gz ...
2. 上传:   scp deploy.tar.gz root@192.168.0.100:/opt/aidp/
3. 构建:   ssh -i ~/.ssh/nas_temp root@192.168.0.100 \
           "cd /opt/aidp && docker build --no-cache"
4. 重启:   ssh -i ~/.ssh/nas_temp root@192.168.0.100 \
           "docker restart <container>"
```

SSH 密钥路径: `~/.ssh/nas_temp`

## 项目服务信息

| 服务 | 端口 | 角色 |
|------|------|------|
| controller | 8883 | 中央调度器，MCP 端点 |
| skill-router | 8788 | 意图分析 + 技能匹配 |
| knowledge-tool | 18081 | 文档索引 + 搜索 |
| asset-tool | 18082 | 代码资产 |
| sandbox-tool | 18083 | 代码执行沙箱 |
| quality-tool | 18084 | 代码质量检查 |
| memory-tool | 18085 | 项目记忆存储 |
| code-index | 18086 | 代码结构索引 |
| context-optimizer | 18088 | 分阶段检索 + 上下文组装 |

## 安全规则

- 所有密码/密钥使用环境变量，**永远不要硬编码**
- PR 前检查 `SECRET_KEY` 和 `DATABASE_URL` 是否在环境变量中
- 参考 `quality-tool` 的 `hardcoded-secret` 规则检查