# knowledge-tool 需求说明

## 1. 背景

`knowledge-tool` 是 AI 编程平台的文档知识库工具。它负责把通用技术文档、项目私有文档、历史方案、排错记录等资料解析成可检索的知识片段，并通过统一工具协议提供给 `aidp-controller` 和 MCP Agent 调用。

在完整平台中，`knowledge-tool` 是最先落地的 P0 工具。没有它，AI Agent 只能依赖当前对话上下文和模型记忆，无法稳定理解项目规范、历史设计、接口约定、数据库结构和技术手册。

## 2. 产品目标

### 2.1 核心目标

- 提供文档上传、登记、解析、切片、向量化、索引和检索能力。
- 支持独立运行，用户可以只部署 `knowledge-tool` 当作私有知识库检索服务。
- 支持被 `aidp-controller` 托管，能力可以被注册为 MCP Skill。
- 支持工作区和项目级权限隔离，项目 A 的私有文档不能被项目 B 搜索。
- 检索结果必须提供可追溯引用，包括 `document_id`、`chunk_id`、`citation_id`、版本、来源路径和分数。
- MVP 优先支持 Markdown、TXT、源代码文本文件；PDF、Word、HTML 作为增强能力。

### 2.2 非目标

MVP 不实现以下能力：

- 不做完整在线文档编辑器。
- 不做复杂知识图谱推理。
- 不做跨租户公共文档市场。
- 不做重型分布式任务调度。
- 不默认强依赖 Qdrant、MinIO、Redis、Nacos 或 Kubernetes。
- 不直接负责 AI 生成代码，只负责提供检索上下文。

## 3. 用户角色

| 角色 | 使用方式 | 关键诉求 |
|---|---|---|
| 个人开发者 | 独立启动工具，导入项目文档和技术手册 | 快速检索，不要复杂部署 |
| 团队管理员 | 通过 controller 安装工具，配置项目知识库 | 权限隔离、可维护、可审计 |
| AI Agent | 通过 MCP Skill 或 `/tool/invoke` 调用检索能力 | 稳定输入输出、引用来源、低延迟 |
| 文档维护者 | 上传、更新、删除文档 | 可追踪版本、可重建索引 |
| 平台开发者 | 维护工具代码和协议适配 | 模块清晰、可扩展解析器和向量库 |

## 4. 使用场景

### 4.1 技术文档检索

用户导入 TypeScript、Fastify、React、Python、Docker、Frida 等技术文档。AI Agent 在编码前调用 `knowledge.search`，检索当前任务相关框架规范。

验收口径：

- 可以按 `doc_type=tech_manual` 过滤。
- 返回片段必须包含标题路径和来源。
- 同一查询下，关键词和语义都相关的内容优先返回。

### 4.2 项目私有文档检索

团队把 ERP 需求文档、接口规约、数据库表结构、业务流程和历史迭代方案导入指定项目。AI Agent 只能在当前 `workspace_id`、`project_id` 范围内检索。

验收口径：

- 请求必须携带 `workspace_id`。
- 私有文档必须校验 `project_id`。
- 没有权限时返回 `FORBIDDEN`，不能返回空数据伪装成功。

### 4.3 历史方案与排坑日志检索

用户把曾经解决过的构建失败、依赖冲突、SQL 优化、移动端兼容问题整理成文档入库。AI Agent 遇到类似错误时可以检索历史解决方案。

验收口径：

- 支持 `doc_type=troubleshooting`。
- 支持按标签过滤，例如 `typescript`、`fastify`、`postgres`。
- 检索结果必须返回版本和最近更新时间。

### 4.4 代码仓库文档同步

MVP 可以通过文件路径登记 Markdown 和源码文本。后续可接入 `git-tool` 或 `project-analyzer-tool` 批量导入 README、docs、接口说明和源码注释。

验收口径：

- MVP 支持本地文件路径或上传文件。
- 后续增强支持 Git commit hash 和 source line。

## 5. 功能需求

### 5.1 文档登记

系统必须支持创建文档元数据：

- 标题。
- 文档类型。
- 所属工作区。
- 所属项目，可为空，表示工作区公共文档。
- 可见性。
- 版本。
- 标签。
- 来源 URI。
- 文件校验和。
- 元数据 JSON。

文档登记成功后，默认状态为 `created` 或 `uploaded`，不应自动假定已索引成功。

### 5.2 文件接入

MVP 支持：

- 通过 `file_uri` 指向本地文件。
- 通过 multipart 上传文件。
- 通过文本内容直接创建文档。

后续支持：

- MinIO/S3 对象存储。
- Git 仓库批量同步。
- 网页抓取。
- Wiki.js 或 Docmost 同步。

### 5.3 文档解析

MVP 必须支持：

- Markdown。
- TXT。
- JSON/YAML/XML 作为文本文档。
- TypeScript/Python/SQL/Dart 等源码文本。

增强支持：

- PDF。
- Word。
- HTML。
- OpenAPI 文档结构化解析。
- 数据库 DDL 解析。

### 5.4 文档切片

切片必须保留：

- `document_id`
- `chunk_index`
- `heading_path`
- `content`
- `content_hash`
- `token_count`
- `source_start_line`
- `source_end_line`
- `page_number`

默认切片策略：

- Markdown 优先按标题层级切片。
- TXT 按段落切片。
- 源码优先按类、函数、方法切片；解析失败时按行数切片。
- 默认 `chunk_size=800` tokens。
- 默认 `overlap=120` tokens。

### 5.5 向量化

系统必须提供 `EmbeddingService` 抽象：

- `embed(text)`
- `embed_batch(texts)`

MVP 提供：

- `mock` embedding provider，用于本地开发和无外部模型场景。
- 可配置真实 embedding provider，具体实现可在项目开发阶段接入。

向量维度必须记录在索引元数据中，防止模型切换后旧向量不可用。

### 5.6 索引管理

系统必须支持：

- 单文档索引。
- 单文档重建索引。
- 删除文档时删除对应 chunk 和索引。
- 索引任务状态查询。
- 索引失败记录错误信息。

索引任务状态：

```text
pending -> running -> succeeded
pending -> running -> failed
pending -> canceled
```

### 5.7 检索

必须提供 `knowledge.search` capability。

检索能力必须支持：

- query。
- top_k。
- workspace filter。
- project filter。
- doc_type filter。
- tag filter。
- visibility filter。
- search_mode：`keyword`、`vector`、`hybrid`。
- min_score。
- include_content。

默认检索流程：

```text
权限过滤
  -> metadata filter
  -> keyword search
  -> vector search
  -> score merge
  -> rerank optional
  -> source refs
```

### 5.8 引用追踪

每个检索结果必须返回：

- `citation_id`
- `document_id`
- `chunk_id`
- `title`
- `version`
- `source_uri`
- `heading_path`
- `score`

`citation_id` 推荐格式：

```text
doc:{document_id}:v:{version}:chunk:{chunk_index}
```

### 5.9 权限隔离

权限规则：

- `visibility=global`：平台公共文档，可被所有工作区搜索，默认仅管理员可写。
- `visibility=workspace`：工作区共享文档，同一 `workspace_id` 可搜索。
- `visibility=project`：项目私有文档，必须匹配 `workspace_id` 和 `project_id`。

工具内部必须二次校验权限，不能完全信任 controller。

## 6. 非功能需求

### 6.1 性能

MVP 目标：

- 1000 篇 Markdown 文档，P95 检索延迟小于 1500ms。
- 单篇 1MB Markdown 文档索引时间小于 15 秒，mock embedding 场景。
- `top_k <= 20` 时响应体默认小于 256KB。

### 6.2 可靠性

- 索引任务失败不能影响已存在可用索引。
- 重建索引应先写入新 chunk，再替换活跃版本，避免检索窗口期为空。
- 删除文档必须软删除优先，物理清理由后台任务处理。

### 6.3 可观测性

日志必须包含：

- `trace_id`
- `workspace_id`
- `project_id`
- `document_id`
- `job_id`
- `capability`
- `elapsed_ms`
- `error_code`

### 6.4 安全

- 禁止读取未授权本地路径。
- 上传文件大小必须限制。
- MIME 类型必须校验。
- 源文件内容不能出现在错误日志中。
- 检索接口必须限制 `top_k` 上限。

## 7. MVP 验收范围

MVP 完成时必须支持：

- 独立启动 `knowledge-tool`。
- controller 托管安装。
- `tool.yaml`、`openapi.yaml`、`config.example.yaml`。
- `GET /health`。
- `GET /tool/manifest`。
- `GET /tool/capabilities`。
- `POST /tool/invoke`。
- 创建文档。
- 上传或登记 Markdown/TXT。
- 索引 Markdown/TXT。
- PGVector 或 mock vector store 检索。
- `knowledge.search` 返回引用来源。
- 跨项目隔离测试通过。
