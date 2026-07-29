# AIDP 用户隔离 + 项目初始化 完整方案

## 一、整体架构

```
┌─────────────────────────────────────────────────┐
│  opencode (.opencode/opencode.jsonc)            │
│  { "aidp": { "project_id": "xxx", "api_key": "yyy" } } │
│  Agent 启动时读取，每次MCP调用自动携带            │
└──────────────────────┬──────────────────────────┘
                       │ api_key + project_id
                       ▼
┌─────────────────────────────────────────────────┐
│  Controller (MCP Server)                        │
│  ┌─ 验证 api_key → 识别用户                     │
│  └─ 验证 project_id → 确认用户有该项目权限       │
└──────┬──────────────┬──────────────┬────────────┘
       │ user_id      │ user_id      │ user_id
       │ project_id   │ project_id   │ project_id
       ▼              ▼              ▼
   memory-tool   knowledge-tool   code-index
   按 user_id    按 project_id    按 project_id
   隔离数据       隔离数据         隔离数据
```

## 二、改动清单

### 2.1 Controller — 无需改动
- `AuthService.validate_api_key()` 已存在
- `invoke_tool_mcp` 已有 `user_id` 参数
- 只需 Agent 传 api_key，Controller 自动解析 user_id

### 2.2 .opencode/opencode.jsonc — 加配置

```json
{
  "aidp": {
    "project_id": "aidp",
    "api_key": "sk-xxx"
  }
}
```

### 2.3 AGENTS.md — 加规则

```
## 项目上下文传递

Agent 启动时必须：
1. 读取 .opencode/opencode.jsonc → aidp.project_id 和 aidp.api_key
2. 调用 aidp_context 时传入 project_name
3. 调用 invoke_tool_mcp 时传入 project 参数
4. 如需用户隔离，传入 api_key

示例：
  invoke_tool_mcp("memory-tool", "memory.create",
    '{"project": "aidp", "title": "xxx", "content": "yyy", "api_key": "sk-xxx"}')
```

### 2.4 项目初始化流程

```
用户 → aidp_init("my-project", api_key="sk-xxx")
     → Controller 验证 api_key → 获取 user
     → 创建 Project 记录(关联 user_id)
     → 返回 project_id
     → 写入 .opencode/opencode.jsonc
```

### 2.5 数据隔离（各工具）

| 工具 | 隔离方式 | 当前状态 |
|------|---------|----------|
| memory-tool | 按 project + user_id | MemoryEntry 已有 user_id 列，search 已支持 |
| knowledge-tool | 按 workspace_id/project_id | KtDocument 已有 project_id |
| code-index | 按 project_id | Node/Edge 已有 project_id |
| skill-router | 共享 | 无需隔离 |
| quality/sandbox | 共享 | 无状态，无需隔离 |

## 三、单开发者模式（当前阶段）

由于只有一个用户 `lwg9264`，简化处理：
- `api_key` 字段填 `lwg9264` 或留空
- Controller 对无 api_key 的调用默认使用 admin 用户
- project_id 用 `"aidp"`
- 无需复杂权限验证

## 四、实施步骤

| 步骤 | 内容 | 工作量 |
|------|------|--------|
| S1 | `.opencode/opencode.jsonc` 加 aidp 配置块 | 1行 |
| S2 | `AGENTS.md` 加项目上下文规则 | 10行 |
| S3 | Controller `aidp_init` 加 api_key 参数 | 5行 |
| S4 | 各工具 ensure 按 project_id 过滤 | 验证 |

## 五、多用户升级路径

| 阶段 | 改动 |
|------|------|
| 单开发者 | project_id 硬编码 "aidp"，无 api_key 验证 |
| 少量用户 | 每个用户注册时生成 api_key，按 project_id 隔离 |
| 团队 | Controller 加 `users` 表管理，api_key 必填 |
| 企业 | 加 RBAC，project 级别权限控制 |