# aidp-controller 模块设计

## 1. 模块清单

| 模块 | 职责 |
|---|---|
| `config` | 环境变量、YAML、数据库配置合并 |
| `workspace` | tenant/workspace/project/session |
| `auth` | 用户、角色、权限、API token |
| `tool-manager` | 工具安装、卸载、启停、健康检查 |
| `capability-router` | capability 解析、权限校验、工具调用 |
| `mcp-adapter` | MCP Skill 暴露和调用映射 |
| `workflow-runner` | 多工具流程编排 |
| `approval-center` | 人工审批 |
| `secrets-manager` | 密钥加密、授权、注入 |
| `audit-log` | 审计事件 |
| `admin-api` | Web/CLI API |

## 2. tool-manager

核心服务：

- `ToolInstallService`
- `ToolManifestValidator`
- `ToolHealthService`
- `ToolCapabilitySyncService`
- `ToolConfigService`

工具状态：

```text
installed -> healthy -> enabled
installed -> unhealthy
enabled -> disabled
disabled -> enabled
installed -> uninstalled
```

## 3. capability-router

输入：

- capability name。
- request context。
- input。

处理：

1. 查找 enabled capability。
2. 校验用户权限。
3. 校验 JSON Schema。
4. 判断是否需要 approval。
5. 组装 tool invoke 请求。
6. 调用工具。
7. 标准化响应。
8. 写入 invocation log。

## 4. workflow-runner

MVP 支持 YAML workflow：

```yaml
name: coding-basic
steps:
  - id: project_summary
    capability: project.summary
  - id: memory_context
    capability: memory.get_context
  - id: knowledge
    capability: knowledge.search
  - id: sandbox
    capability: sandbox.build.node
  - id: quality
    capability: quality.check
```

步骤状态：

- `pending`
- `running`
- `waiting_approval`
- `succeeded`
- `failed`
- `skipped`

## 5. approval-center

审批对象：

- `tool_invocation`
- `workflow_step`
- `memory_write`
- `git_commit`
- `file_overwrite`
- `secret_access`

审批策略由规则决定：

```text
capability + risk_level + workspace policy -> approval required
```

## 6. secrets-manager

密钥只保存加密值，不返回明文。

工具调用时，controller 只传 secret 引用或在服务端注入临时环境变量。日志、Prompt、审计摘要中只能出现 secret key，不出现 secret value。

## 7. mcp-adapter

MCP Skill 名称直接来自 capability name，例如：

- `knowledge.search`
- `memory.get_context`
- `sandbox.build.node`

adapter 负责把 MCP 请求转换成 controller invoke 请求，并附加 workspace/project/session 上下文。
