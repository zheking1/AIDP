# git-tool 文档索引

`git-tool` 是 AIDP 的 Git 仓库上下文和版本操作辅助工具。它不替代 Git 客户端，而是为 AI Agent 提供安全的仓库读取、变更摘要、提交分析、分支差异、关联 issue/commit 的能力。MVP 默认只读，写操作必须显式开启。

## 必读文档

| 文档 | 内容 |
|---|---|
| [01-requirements.md](./01-requirements.md) | 需求、使用场景、边界 |
| [02-architecture.md](./02-architecture.md) | 架构、仓库访问、安全策略 |
| [03-module-design.md](./03-module-design.md) | 模块职责、diff 解析、提交摘要 |
| [04-api-capabilities.md](./04-api-capabilities.md) | API、capability、请求响应 |
| [05-data-model.md](./05-data-model.md) | 仓库、提交、变更、同步状态 |
| [06-development-plan.md](./06-development-plan.md) | 开发计划和任务拆分 |
| [07-testing-acceptance.md](./07-testing-acceptance.md) | 测试与验收 |
| [AI_IMPLEMENTATION.md](./AI_IMPLEMENTATION.md) | AI 编码实现提示 |

## MVP Capability

| capability | 权限 | 说明 |
|---|---|---|
| `git.repo_status` | `git:read` | 获取仓库状态 |
| `git.diff_summary` | `git:read` | 获取 diff 摘要 |
| `git.commit_history` | `git:read` | 查询提交历史 |
| `git.show_commit` | `git:read` | 查看提交详情 |
| `git.file_history` | `git:read` | 查看文件历史 |
| `git.create_commit` | `git:write` | 可选写操作，创建提交 |

## 完成定义

- 默认只读运行。
- 支持本地仓库路径。
- 支持 status、diff、log、show、file history。
- 所有路径限制在已登记仓库根目录。
- 写操作必须配置启用，并需要 controller 权限。
