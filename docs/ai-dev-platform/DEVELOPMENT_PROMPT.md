# AIDP AI 开发总控提示词

本文档是把 AIDP 文档集交给 AI 编码工具开发时使用的总控提示词。使用方式：先把本文件交给 AI，再按当前阶段补充对应模块文档。不要一次性把全部工具文档塞入同一个上下文，避免 AI 混淆边界。

## 1. 开发目标

你要开发的是 AIDP，一套“主服务 + N 个可选工具”的私有化 AI 编程基础设施平台。

核心目标：

- `aidp-controller` 作为主服务，负责项目、会话、工具注册、工具安装、权限、审计、MCP 编排和工具调用。
- 每个工具都能独立运行，也能被 `aidp-controller` 托管。
- 工具之间通过统一工具协议通信，不允许 controller 直接调用工具内部函数。
- MVP 先实现个人和小团队可用的单机/Compose 部署，不默认做复杂分布式。
- 系统必须支持后续开源：别人可以只安装一个工具，也可以安装整套平台。

核心闭环：

```text
用户需求
  -> controller 编排
  -> knowledge-tool 检索文档
  -> asset-tool 检索代码资产和历史方案
  -> AI 生成或修改代码
  -> sandbox-tool 执行/构建/测试
  -> quality-tool 解析质量结果
  -> error-tool 归档错误和解决方案
  -> memory-tool 保存项目上下文和会话摘要
```

## 2. 强制技术栈

必须遵守：

- 全栈统一 Python + FastAPI。
- `aidp-controller`：Python + FastAPI + FastMCP。
- `admin-console`：Jinja2 + Alpine.js + Tailwind CSS。
- `aidp-cli`：Python。
- 所有工具：Python + FastAPI。
- 数据库：PostgreSQL + pgvector。
- 缓存：Redis。
- ORM/迁移：SQLAlchemy 2.0 (async) 或 SQL migration，优先保持简单透明。
- 默认部署：Docker Compose。

禁止默认引入：

- Nacos、Kubernetes、复杂服务注册中心。
- 重型企业框架。
- 微服务治理套件。
- 不必要的消息队列。
- 任何与当前文档技术栈无关的默认工程结构。

如确实需要 Redis、MinIO、Qdrant、Go runner 等组件，必须先说明为什么 MVP 需要它，以及不用它会缺失什么能力。

## 3. 必读文档顺序

开发任何模块前，先读：

1. `docs/ai-dev-platform/README.md`
2. `docs/ai-dev-platform/09-technology-stack.md`
3. `docs/ai-dev-platform/common/tool-contract.md`
4. `docs/ai-dev-platform/common/engineering-standards.md`
5. `docs/ai-dev-platform/08-controller-plus-tools-architecture.md`

开发 controller 时，再读：

1. `docs/ai-dev-platform/controller/README.md`
2. `docs/ai-dev-platform/controller/AI_IMPLEMENTATION.md`
3. `docs/ai-dev-platform/controller/01-requirements.md`
4. `docs/ai-dev-platform/controller/02-architecture.md`
5. `docs/ai-dev-platform/controller/03-module-design.md`
6. `docs/ai-dev-platform/controller/04-api-capabilities.md`
7. `docs/ai-dev-platform/controller/05-data-model.md`
8. `docs/ai-dev-platform/controller/06-development-plan.md`
9. `docs/ai-dev-platform/controller/07-testing-acceptance.md`

开发某个工具时，只读取该工具目录下的文档：

```text
docs/ai-dev-platform/tools/{tool-name}/README.md
docs/ai-dev-platform/tools/{tool-name}/AI_IMPLEMENTATION.md
docs/ai-dev-platform/tools/{tool-name}/01-requirements.md
docs/ai-dev-platform/tools/{tool-name}/02-architecture.md
docs/ai-dev-platform/tools/{tool-name}/03-module-design.md
docs/ai-dev-platform/tools/{tool-name}/04-api-capabilities.md
docs/ai-dev-platform/tools/{tool-name}/05-data-model.md
docs/ai-dev-platform/tools/{tool-name}/06-development-plan.md
docs/ai-dev-platform/tools/{tool-name}/07-testing-acceptance.md
```

## 4. 推荐开发顺序

不要同时开发全部模块。严格按阶段推进。

### Phase 0：仓库和工程骨架

交付：

- monorepo 目录结构。
- Python 基础包（FastAPI + FastMCP）。
- 统一 lint/test/build 脚本。
- Docker Compose 最小开发环境。
- README 和本地启动说明。

建议目录：

```text
aidp/
  apps/
    controller/
    admin-console/
    cli/
  packages/
    sdk/
    schemas/
  tools/
    knowledge-tool/
    asset-tool/
    memory-tool/
    sandbox-tool/
    quality-tool/
    error-tool/
    project-analyzer-tool/
    template-tool/
    git-tool/
    eval-tool/
  deploy/
    docker-compose/
  docs/
```

### Phase 1：aidp-controller

先实现：

- 健康检查。
- 配置加载。
- PostgreSQL 连接。
- 用户/工作区/项目基础模型。
- 工具注册表。
- `tool.yaml` 解析。
- `/tool/manifest`、`/tool/capabilities` 代理。
- `/tool/invoke` 调用。
- 权限和审计最小闭环。

验收：

- controller 能独立启动。
- 能注册一个 mock tool。
- 能调用 mock tool capability。
- 审计表能记录调用。
- OpenAPI 可生成。

### Phase 2：knowledge-tool

先实现：

- 文档创建和上传。
- Markdown/TXT/source 文本解析。
- 文档切片。
- mock embedding。
- keyword/hybrid search。
- 权限隔离。
- `knowledge.search` capability。

验收：

- Markdown 文档可索引和检索。
- 检索结果带 citation。
- 跨项目隔离通过。
- controller 能调用 `knowledge.search`。

### Phase 3：asset-tool + memory-tool

asset-tool 先实现：

- snippet/config/command/pattern CRUD。
- keyword/mock vector 检索。
- 模板上传和渲染。
- `asset.search`。

memory-tool 先实现：

- memory upsert/search。
- session summary。
- context package。
- 审核状态和过期过滤。

验收：

- AI 可通过 asset-tool 找到可复用片段。
- AI 可通过 memory-tool 获取当前项目上下文。

### Phase 4：sandbox-tool + quality-tool

sandbox-tool 先实现：

- Shell/Python 轻量执行。
- SQL 临时验证。
- Node/TypeScript 构建和测试。
- Python 项目测试。
- 镜像白名单、超时、资源限制、日志采集。

quality-tool 先实现：

- TypeScript 日志解析。
- Python 日志解析。
- test/lint issue 归一化。
- 调用 sandbox-tool。
- `quality.check`。

验收：

- `sandbox.build.node` 可执行 `pnpm test`。
- `sandbox.test.python` 可执行 `pytest`。
- `quality.check` 能返回 file/line/message。
- issue 可直接作为 AI 修复输入。

### Phase 5：error-tool、project-analyzer-tool、template-tool、git-tool、eval-tool

按实际需求逐个实现，不要提前一次性开发完。

优先级：

1. error-tool：沉淀错误和解决方案。
2. project-analyzer-tool：生成项目结构摘要。
3. template-tool：模板包注册、预览、渲染。
4. git-tool：只读 diff/commit 信息和可控提交辅助。
5. eval-tool：回归评测和提示词/工具调用质量评估。

## 5. 每轮开发任务格式

每次只开发一个模块或一个清晰子任务。开始编码前必须输出：

```text
本轮目标：
- ...

读取文档：
- ...

实现范围：
- ...

不做范围：
- ...

验收方式：
- ...
```

完成后必须输出：

```text
完成内容：
- ...

变更文件：
- ...

运行验证：
- ...

未完成/风险：
- ...

下一步建议：
- ...
```

## 6. 工具协议强制要求

每个工具必须提供：

- `tool.yaml`
- `openapi.yaml`
- `config.example.yaml`
- `GET /health`
- `GET /tool/manifest`
- `GET /tool/capabilities`
- `POST /tool/invoke`
- 统一错误响应
- trace_id 透传
- workspace/project 权限二次校验

`/tool/invoke` 请求必须包含：

```json
{
  "trace_id": "tr_01",
  "capability": "knowledge.search",
  "context": {
    "workspace_id": "ws_01",
    "project_id": "prj_01",
    "session_id": "ses_01",
    "user_id": "usr_01"
  },
  "input": {}
}
```

响应必须包含：

```json
{
  "trace_id": "tr_01",
  "tool": "knowledge-tool",
  "capability": "knowledge.search",
  "success": true,
  "output": {},
  "elapsed_ms": 120
}
```

## 7. 数据和权限要求

所有核心表必须带：

- `workspace_id`
- `project_id`，可为空但必须有明确语义
- `created_at`
- `updated_at`
- `created_by`

所有查询必须做 scope 过滤：

- global 数据可全局读，默认仅管理员写。
- workspace 数据仅同 workspace 可读。
- project 数据必须匹配 workspace_id + project_id。
- session 数据必须匹配 session_id。

不能只依赖 controller 做权限检查；工具内部必须二次校验。

## 8. 测试和验收要求

每个模块至少提供：

- 单元测试。
- API 测试。
- repository 或集成测试。
- `/tool/invoke` 协议测试。
- 关键权限隔离测试。
- 错误响应测试。

优先验证：

- happy path。
- validation error。
- forbidden scope。
- dependency unavailable。
- trace_id 是否透传。

不允许只实现接口但没有测试。

## 9. 安全要求

必须遵守：

- controller 不直接执行不可信命令。
- sandbox 默认无网络。
- sandbox 禁止 privileged。
- sandbox 禁止任意 hostPath。
- sandbox 禁止默认挂载 Docker socket。
- 上传 zip 必须防路径穿越。
- 日志必须脱敏 token、password、secret、Authorization。
- 错误响应不能泄露本地绝对路径和敏感配置。
- 下载文件必须校验权限。

## 10. 文档和代码一致性要求

实现时如果发现文档与代码冲突：

1. 优先遵守 `09-technology-stack.md`、`common/tool-contract.md`、`common/engineering-standards.md`。
2. 再遵守当前模块的 `AI_IMPLEMENTATION.md`。
3. 再遵守当前模块的详细设计文档。
4. 不要擅自引入文档未定义的重型依赖。
5. 如果需要调整设计，先修改文档，再改代码。

## 11. 禁止事项

禁止：

- 一次性开发全部工具。
- 工具之间直接 import 对方代码。
- controller 直接访问工具数据库表。
- 用内存 map 替代需要持久化的核心数据。
- 绕过 `tool.yaml` 注册 capability。
- 绕过 `/tool/invoke` 做工具调用。
- 默认启用复杂分布式部署。
- 默认开放 sandbox 网络。
- 在日志里打印完整文档、完整代码资产或密钥。

## 12. 推荐第一条开发指令

如果从零开始开发，第一条给 AI 的任务建议是：

```text
请根据 docs/ai-dev-platform/DEVELOPMENT_PROMPT.md、
docs/ai-dev-platform/README.md、
docs/ai-dev-platform/09-technology-stack.md、
docs/ai-dev-platform/common/tool-contract.md、
docs/ai-dev-platform/common/engineering-standards.md、
docs/ai-dev-platform/controller/AI_IMPLEMENTATION.md
和 docs/ai-dev-platform/controller/*.md，
先实现 aidp-controller 的 MVP：
1. Python + FastAPI + FastMCP 工程骨架；
2. PostgreSQL 配置和基础迁移；
3. tool.yaml 注册表；
4. /health、/tool registry API；
5. /tool/invoke 代理 mock tool；
6. trace_id、统一错误、审计记录；
7. 单元测试和 API 测试。

不要实现管理后台，不要实现真实工具，不要引入重型分布式组件。
完成后给出启动命令、测试命令、变更文件和下一步建议。
```

## 13. 推荐工具开发指令模板

开发某个工具时使用：

```text
请根据 docs/ai-dev-platform/DEVELOPMENT_PROMPT.md、
docs/ai-dev-platform/common/tool-contract.md、
docs/ai-dev-platform/common/engineering-standards.md
以及 docs/ai-dev-platform/tools/{tool-name}/ 下的全部文档，
实现 {tool-name} 的 MVP。

必须遵守：
1. 工具可 standalone 启动；
2. 工具可被 aidp-controller 托管；
3. 必须提供 tool.yaml、openapi.yaml、config.example.yaml；
4. 必须实现 /health、/tool/manifest、/tool/capabilities、/tool/invoke；
5. 必须实现文档中标记为 MVP 的 capability；
6. 必须提供测试；
7. 不要开发其它工具；
8. 不要引入文档未要求的重型依赖。

请先输出本轮实现计划，然后开始编码，最后运行测试并汇报结果。
```
