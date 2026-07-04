# 最小安装 Profile 说明

本文档不是另一套架构，而是 [08-controller-plus-tools-architecture.md](./08-controller-plus-tools-architecture.md) 的最小安装裁剪方案。

目标架构仍然是：

```text
aidp-controller + N 个可选安装工具
```

最小安装只是在这个架构下少装工具，而不是把系统改成单体。

## 1. 最小安装目标

最小安装用于：

- 个人试用。
- 本地开发。
- 只验证 controller 和工具安装机制。
- 只使用某一个工具，例如 knowledge-tool。

最小安装不追求完整 AI 编程闭环。

## 2. Profile 分级

### 2.1 core profile

```text
aidp-controller
postgres
```

能力：

- 用户、工作区、项目管理。
- 工具注册表。
- 工具安装接口。
- MCP 基础入口。
- 审计和 trace。

不包含：

- 文档检索。
- 代码资产检索。
- 沙箱执行。
- 质量校验。

### 2.2 knowledge profile

```text
aidp-controller
postgres + pgvector
knowledge-tool
```

能力：

- 文档上传。
- 文档切片。
- 向量检索。
- MCP `knowledge.search`。

适合只想部署私有知识库的用户。

### 2.3 coding profile

```text
aidp-controller
postgres + pgvector
knowledge-tool
asset-tool
sandbox-tool
quality-tool
memory-tool
```

能力：

- 文档检索。
- 代码资产检索。
- 沙箱执行。
- 质量校验。
- 上下文记忆。
- AI 编程闭环。

### 2.4 full profile

```text
aidp-controller
postgres + pgvector
minio
knowledge-tool
asset-tool
sandbox-tool
quality-tool
memory-tool
error-tool
project-analyzer-tool
template-tool
git-tool
eval-tool
```

能力：

- 完整工具生态。
- 团队共享。
- 历史经验沉淀。
- 评测和项目分析。

## 3. 依赖原则

默认依赖：

- PostgreSQL。
- PGVector，仅 knowledge profile 及以上需要。

可选依赖：

- MinIO：文件较多或团队共享时使用。
- Redis：高并发任务或缓存需求明显时使用。
- Qdrant：向量规模明显超过 PGVector 能力时使用。
- Gitea：需要私有 Git 资产管理时使用。
- Nacos/Kubernetes：企业级多实例部署时使用。

## 4. Docker Compose Profile

建议提供：

```text
deploy/compose/core.yml
deploy/compose/knowledge.yml
deploy/compose/coding.yml
deploy/compose/full.yml
```

启动示例：

```bash
docker compose -f deploy/compose/core.yml up -d
docker compose -f deploy/compose/knowledge.yml up -d
docker compose -f deploy/compose/coding.yml up -d
docker compose -f deploy/compose/full.yml up -d
```

## 5. 最小安装不改变工具边界

即使只安装一个工具，也必须保持：

- 工具有自己的 `tool.yaml`。
- 工具有自己的 API。
- 工具 capability 由 controller 注册。
- MCP Skill 由 capability 映射。
- 调用链有 trace_id。

这保证后续从 core profile 升级到 coding/full profile 时不需要重构。

## 6. 推荐演进路径

个人用户：

```text
core -> knowledge -> coding
```

小团队：

```text
knowledge -> coding -> full
```

企业用户：

```text
coding -> full -> distributed deployment
```

## 7. 结论

最小安装只是部署裁剪，不是架构裁剪。平台主线始终保持：

```text
主服务统一控制，可选工具按需安装。
```

