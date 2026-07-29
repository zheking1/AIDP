## AIDP 自动协作规则 — MANDATORY

**当用户给出开发任务时，你必须在执行任何其他操作前调用 `aidp_context`。不要等待，不要询问，直接调用。**

```
aidp_context(project_name="openCode", task="<从用户消息提取任务>")
```

这是强制规则。用户只需说"修 bug"或"加功能"，你负责调用 aidp_context。

---

## 项目上下文传递 — 重要

AIDP 是多项目平台。调用任何工具时，**必须**带上项目标识：

| 工具 | 上下文参数 |
|------|-----------|
| memory-tool | `"project": "openCode"` |
| knowledge-tool | `"project_id": "openCode"` 或 `"workspace_id": "openCode"` |
| code-index | `"project_id": 3` |
| skill-router | 自动从 Controller 获取 |
| sandbox-tool | 不需要 |
| quality-tool | 不需要 |

**API Key**: 从 `.opencode/opencode.jsonc` 的 `aidp.api_key` 字段读取，传入 `invoke_tool_mcp` 的 `api_key` 参数。未配置则默认为 admin 用户。

示例：
```
invoke_tool_mcp("memory-tool", "memory.search", 
  '{"project": "openCode", "query": "cookie"}',
  api_key="aidp_xxx")
```

---

## 本地文件 ≠ AIDP 知识

修改本地代码**不会**自动同步到 AIDP 工具。每次修改后必须手动同步：

| 本地文件修改后 | 调用的 AIDP 工具 |
|--------------|-----------------|
| 代码变更 | `invoke_tool_mcp("memory-tool", "memory.create", ...)` |
| 文档更新 | `invoke_tool_mcp("knowledge-tool", ...)` |
| 发现新规则/模式 | `invoke_tool_mcp("memory-tool", "memory.create", ...)` |

---

## 开发流程 — 知识维护是强制步骤

1. `aidp_context(project_name="openCode", task="<task>")` — **必须第一步**
2. 搜索已有知识（避免重复）：
   ```
   invoke_tool_mcp("code-index", "code.search.semantic", '{"project_id":2,"query":"<关键词>"}')
   invoke_tool_mcp("memory-tool", "memory.search", '{"project":"openCode","query":"<关键词>"}')
   ```
3. 编写代码 / 实现功能
4. 验证：`sandbox-tool` + `quality-tool`
5. **知识沉淀（强制）** — 下面的分类，做完什么就存什么：

   | 场景 | 操作 |
   |------|------|
   | 发现一个**规则**（必须/禁止/不得） | `POST /api/classification/import` 存为 rule |
   | 发现一个**可复用的技能** | `invoke_tool_mcp("skill-router", "skill_register", ...)` |
   | 发现**架构/设计决策** | `POST /api/classification/import` 存为 knowledge doc |
   | 发现**项目级知识/记忆** | `invoke_tool_mcp("memory-tool", "memory.create", ...)` |
   | 写完了**新功能** | 更新 docs/ 下对应文档 → 文件监听自动同步 |

   > **为什么这是强制的**：每次开发沉淀的知识，下次搜索就能找到。不做的话系统永远是空的。

---

## 创建 Subagent

任务复杂需要拆分时：
1. 调用 `aidp_instructions(project_name="openCode", task, agent_type)` 生成 subagent 专属指令
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
