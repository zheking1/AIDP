# aidp-controller API 设计

## 1. 工具管理 API

### POST /api/tools/install

```json
{
  "source": "./tools/knowledge-tool",
  "install_mode": "managed",
  "base_url": "http://knowledge-tool:8080",
  "config": {}
}
```

### GET /api/tools

返回已安装工具、状态、版本、capability 数量。

### POST /api/tools/{tool_name}/enable

启用工具。

### POST /api/tools/{tool_name}/disable

停用工具。

### POST /api/tools/{tool_name}/sync-capabilities

重新拉取 `/tool/capabilities`。

## 2. Capability 调用 API

### POST /api/tools/invoke

```json
{
  "trace_id": "tr_01",
  "workspace_id": "ws_01",
  "project_id": "prj_01",
  "session_id": "ses_01",
  "capability": "knowledge.search",
  "input": {
    "query": "订单审批接口规范",
    "top_k": 8
  }
}
```

响应：

```json
{
  "success": true,
  "trace_id": "tr_01",
  "tool": "knowledge-tool",
  "capability": "knowledge.search",
  "output": {},
  "elapsed_ms": 120
}
```

## 3. MCP API

### POST /api/mcp/invoke

MCP 客户端调用入口，内部映射到 `/api/tools/invoke`。

## 4. Workflow API

### POST /api/workflows/runs

```json
{
  "workflow_name": "coding-basic",
  "workspace_id": "ws_01",
  "project_id": "prj_01",
  "session_id": "ses_01",
  "input": {
    "task": "新增销售订单审批接口"
  }
}
```

### GET /api/workflows/runs/{run_id}

返回 workflow run、step 状态、输出摘要。

## 5. Approval API

### GET /api/approvals

查询待审批事项。

### POST /api/approvals/{id}/approve

批准。

### POST /api/approvals/{id}/reject

拒绝。

## 6. Secret API

### POST /api/secrets

创建密钥。

```json
{
  "name": "git-token",
  "scope": "workspace",
  "value": "secret-value",
  "allowed_tools": ["git-tool"]
}
```

### GET /api/secrets

只返回 key、scope、allowed_tools，不返回 value。

## 7. 错误码

| 错误码 | 场景 |
|---|---|
| `VALIDATION_ERROR` | 参数或 schema 错误 |
| `UNAUTHORIZED` | 未登录 |
| `FORBIDDEN` | 无权限或跨项目访问 |
| `NOT_FOUND` | 工具、capability、workflow 不存在 |
| `APPROVAL_REQUIRED` | 需要人工审批 |
| `TOOL_UNAVAILABLE` | 工具不可用 |
| `TIMEOUT` | 工具调用超时 |
| `INTERNAL_ERROR` | 未预期异常 |
