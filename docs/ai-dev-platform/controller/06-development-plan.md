# aidp-controller 开发计划

## 1. 里程碑

| 里程碑 | 周期 | 交付 |
|---|---:|---|
| M1 工程骨架 | 1-2 天 | Python + FastAPI + PostgreSQL + OpenAPI |
| M2 Workspace/Auth | 2-3 天 | 默认用户、workspace、project、权限 |
| M3 Tool Manager | 3-4 天 | 安装、启停、health、capability sync |
| M4 Capability Router | 2-3 天 | `/api/tools/invoke`、权限、schema、审计 |
| M5 MCP Adapter | 2-3 天 | capability 映射 MCP Skill |
| M6 Workflow Runner | 3-5 天 | 内置 coding-basic workflow |
| M7 Approval/Secrets | 3-4 天 | 审批中心、密钥管理、脱敏 |
| M8 Admin API/CLI | 3-5 天 | 管理台 API、CLI 最小命令 |

## 2. AI 编码任务

1. 创建 monorepo 基础结构：`apps/controller`、`tools/`。
2. 实现 FastAPI 服务、配置、日志、统一错误。
3. 实现 PostgreSQL migration。
4. 实现 workspace/project/session。
5. 实现 tool.yaml parser 和 schema 校验。
6. 实现 tool install/enable/disable/sync。
7. 实现 capability-router。
8. 实现 invocation audit。
9. 实现 approval-center。
10. 实现 secrets-manager。
11. 实现 workflow-runner。
12. 实现 MCP adapter。
13. 实现 CLI：`aidp tool install`、`aidp tool list`、`aidp invoke`。

## 3. 风险控制

| 风险 | 控制 |
|---|---|
| 主服务变重 | 单体模块化，不引入微服务注册中心 |
| 工具调用不可控 | capability-router 统一权限、schema、审计 |
| AI 高风险动作 | approval-center 默认拦截 |
| 密钥泄露 | secrets-manager 加密、脱敏、授权 |
| workflow 复杂化 | MVP 只支持 YAML 顺序流程和简单条件 |

## 4. MVP 交付清单

- `apps/controller`
- `apps/cli`
- `packages/schemas`
- `tool.yaml` JSON Schema
- `workflow.yaml` JSON Schema
- `docker-compose.yml`
- mock-tool 示例
- controller OpenAPI
- controller 测试集
