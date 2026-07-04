# aidp-controller 需求说明

## 1. 产品定位

`aidp-controller` 是 AIDP 的主控服务。它负责把多个可选工具组合成真实可用的 AI 编程系统，而不是只提供一组松散 API。

controller 必须满足：

- 个人用户可以单机运行。
- 团队可以多用户共享。
- 工具可选安装。
- 工具可以独立运行，也可以被 controller 托管。
- AI Agent 通过 controller 获取上下文、调用工具、执行工作流。

## 2. 用户角色

| 角色 | 需求 |
|---|---|
| 个人开发者 | 本地安装、少配置、快速用 AI 开发项目 |
| 团队管理员 | 管理用户、项目、工具、权限、密钥 |
| 团队开发者 | 在项目内调用工具、查看任务记录、复用知识 |
| AI Agent | 通过 MCP Skill 和 `/api/tools/invoke` 调用工具 |
| 工具开发者 | 开发符合协议的新工具并被 controller 安装 |

## 3. 核心需求

### 3.1 工具管理

必须支持：

- 安装工具。
- 卸载工具。
- 启用/禁用工具。
- 读取 `tool.yaml`。
- 校验 `openapi.yaml`。
- 拉取 `/tool/capabilities`。
- 健康检查。
- 保存工具配置。
- 查看工具调用历史。

### 3.2 Capability 路由

controller 必须统一处理：

- 权限校验。
- 参数 schema 校验。
- trace_id 生成和传递。
- 调用目标工具。
- 超时和错误包装。
- 审计日志。

### 3.3 MCP 适配

controller 安装工具后，应把工具 capability 映射为 MCP Skill，让 AI 编码代理不直接感知工具部署地址。

### 3.4 工作流编排

MVP 内置标准 AI 编程流程：

```text
project.summary
  -> memory.get_context
  -> knowledge.search
  -> asset.search
  -> template.search/render optional
  -> sandbox.build/run
  -> quality.check
  -> error.search on failure
  -> memory.save_summary
```

### 3.5 审批

以下动作默认需要审批：

- 写入长期记忆并标记 approved。
- 覆盖文件。
- 创建 Git commit。
- 执行危险 sandbox 命令。
- 导出团队资产。
- 修改工具密钥。

### 3.6 密钥管理

必须支持：

- 创建 secret。
- 更新 secret。
- 按工具授权 secret。
- 调用工具时注入 secret 引用。
- 日志和响应中脱敏。

## 4. 非目标

MVP 不做：

- 不做复杂工作流可视化编辑器。
- 不做多实例服务注册中心。
- 不默认引入 Nacos/Kubernetes。
- 不做 SaaS 计费。
- 不直接实现知识库、沙箱等工具业务。

## 5. 非功能需求

- 单机 Docker Compose 可启动。
- 个人模式首次配置不超过 10 分钟。
- 工具调用 P95 额外开销小于 100ms。
- 所有数据按 workspace/project 隔离。
- 所有高风险动作可审计。

## 6. MVP 验收

- 可安装 mock-tool。
- 可调用 mock capability。
- 可安装至少 3 个真实工具。
- 可运行内置 coding workflow。
- 可查看工具调用日志。
- 可创建审批并完成批准/拒绝。
