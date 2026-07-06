## AIDP 自动协作规则 — MANDATORY

**当用户给出开发任务时，你必须在执行任何其他操作前调用 `aidp_context`。不要等待，不要询问，直接调用。**

```
aidp_context(project_name="aidp", task="<从用户消息提取任务>")
```

这是强制规则。用户只需说"修 bug"或"加功能"，你负责调用 aidp_context。

---

## 本地文件 ≠ AIDP 知识

修改本地代码**不会**自动同步到 AIDP 工具。每次修改后必须手动同步：

| 本地文件修改后 | 调用的 AIDP 工具 |
|--------------|-----------------|
| 代码变更 | `invoke_tool_mcp("memory-tool", "memory.create", ...)` |
| 文档更新 | `invoke_tool_mcp("knowledge-tool", ...)` |
| 发现新规则/模式 | `invoke_tool_mcp("memory-tool", "memory.create", ...)` |

---

## 开发流程

1. `aidp_context(project_name="aidp", task="<task>")` — **必须第一步**
2. 编写代码
3. 验证：`invoke_tool_mcp("sandbox-tool", "sandbox.execute", ...)` + `invoke_tool_mcp("quality-tool", "quality.check", ...)`
4. 同步知识：更新 memory/knowledge

---

## 创建 Subagent

任务复杂需要拆分时：
1. 调用 `aidp_instructions(project_name, task, agent_type)` 生成 subagent 专属指令
2. 用返回的指令创建 subagent
3. Subagent 也会调用 `aidp_context`

---

## 部署

所有修改部署到 NAS：
1. `tar czf` → `scp` → `docker build --no-cache` → `docker restart`
2. SSH: `ssh -i ~/.ssh/nas_temp root@192.168.0.100`

---

## 项目信息

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

---

## 安全

所有密码/密钥用环境变量。永远不要硬编码。
