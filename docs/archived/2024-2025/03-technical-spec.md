# AI 编程基础设施平台技术规范

## 1. 通用技术规范

### 1.1 服务规范

- 所有后端服务使用 REST JSON API。
- 所有请求必须携带 `X-Request-Id`，没有则网关生成。
- MCP 调用链必须携带 `trace_id`。
- 所有时间字段使用 ISO-8601。
- 所有 ID 使用 UUID 或雪花 ID，MVP 推荐 UUID。
- 分页参数统一为 `page`, `page_size`。
- 返回结构统一为：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {},
  "trace_id": "uuid"
}
```

错误返回：

```json
{
  "success": false,
  "code": "DOCUMENT_NOT_FOUND",
  "message": "document not found",
  "details": {},
  "trace_id": "uuid"
}
```

### 1.2 权限模型

基础实体：

- tenant：租户。
- workspace：工作空间。
- project：项目。
- user：用户。
- role：角色。
- permission：权限点。

资源必须归属：

```text
tenant_id -> workspace_id -> project_id -> resource_id
```

公共技术文档允许 `project_id` 为空，但必须有 `workspace_id` 或 `tenant_id`。

### 1.3 审计规范

以下操作必须记录审计日志：

- 上传、删除、重建索引文档。
- 调用文档检索。
- 调用代码资产检索。
- 执行沙箱任务。
- 调用质量校验。
- 修改工具配置或 capability 配置。
- 修改项目权限。

审计字段：

- audit_id
- trace_id
- actor_type
- actor_id
- action
- resource_type
- resource_id
- request_summary
- response_summary
- ip
- created_at

## 2. 数据库模型

### 2.1 tenant

```sql
create table tenant (
  id uuid primary key,
  name varchar(128) not null,
  status varchar(32) not null,
  created_at timestamptz not null,
  updated_at timestamptz not null
);
```

### 2.2 workspace

```sql
create table workspace (
  id uuid primary key,
  tenant_id uuid not null,
  name varchar(128) not null,
  slug varchar(128) not null,
  created_at timestamptz not null,
  updated_at timestamptz not null,
  unique (tenant_id, slug)
);
```

### 2.3 project

```sql
create table project (
  id uuid primary key,
  tenant_id uuid not null,
  workspace_id uuid not null,
  name varchar(128) not null,
  slug varchar(128) not null,
  project_type varchar(64) not null,
  tech_stack jsonb not null default '[]',
  status varchar(32) not null,
  created_at timestamptz not null,
  updated_at timestamptz not null,
  unique (workspace_id, slug)
);
```

### 2.4 document

```sql
create table document (
  id uuid primary key,
  tenant_id uuid not null,
  workspace_id uuid not null,
  project_id uuid,
  title varchar(256) not null,
  doc_type varchar(64) not null,
  source_type varchar(64) not null,
  source_uri text,
  object_key text not null,
  mime_type varchar(128),
  version varchar(64),
  visibility varchar(32) not null,
  checksum varchar(128) not null,
  index_status varchar(32) not null,
  tags jsonb not null default '[]',
  metadata jsonb not null default '{}',
  created_by uuid,
  created_at timestamptz not null,
  updated_at timestamptz not null
);
```

`doc_type` 建议枚举：

- tech_doc
- project_doc
- api_spec
- db_schema
- business_flow
- troubleshooting
- coding_standard

### 2.5 document_chunk

```sql
create table document_chunk (
  id uuid primary key,
  document_id uuid not null,
  tenant_id uuid not null,
  workspace_id uuid not null,
  project_id uuid,
  chunk_index int not null,
  content text not null,
  token_count int,
  heading_path text,
  page_number int,
  content_hash varchar(128) not null,
  embedding_model varchar(128) not null,
  metadata jsonb not null default '{}',
  created_at timestamptz not null
);
```

PGVector 扩展字段：

```sql
alter table document_chunk add column embedding vector(1536);
create index document_chunk_embedding_idx
on document_chunk using ivfflat (embedding vector_cosine_ops);
```

如果 embedding 维度变化，必须新建字段或新建表，不允许混用不同维度。

### 2.6 code_asset

```sql
create table code_asset (
  id uuid primary key,
  tenant_id uuid not null,
  workspace_id uuid not null,
  project_id uuid,
  asset_type varchar(32) not null,
  title varchar(256) not null,
  description text,
  language varchar(64),
  framework varchar(128),
  content text,
  object_key text,
  version varchar(64),
  tags jsonb not null default '[]',
  metadata jsonb not null default '{}',
  visibility varchar(32) not null,
  created_by uuid,
  created_at timestamptz not null,
  updated_at timestamptz not null
);
```

`asset_type` 枚举：

- snippet
- template
- pattern
- command
- config

### 2.7 sandbox_job

```sql
create table sandbox_job (
  id uuid primary key,
  tenant_id uuid not null,
  workspace_id uuid not null,
  project_id uuid,
  session_id uuid,
  job_type varchar(64) not null,
  image varchar(256) not null,
  command jsonb not null,
  status varchar(32) not null,
  exit_code int,
  stdout_object_key text,
  stderr_object_key text,
  artifact_object_key text,
  resource_usage jsonb not null default '{}',
  timeout_seconds int not null,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null
);
```

### 2.8 quality_result

```sql
create table quality_result (
  id uuid primary key,
  tenant_id uuid not null,
  workspace_id uuid not null,
  project_id uuid,
  sandbox_job_id uuid,
  ruleset_id uuid,
  passed boolean not null,
  summary text,
  issues jsonb not null default '[]',
  raw_log_object_key text,
  created_at timestamptz not null
);
```

### 2.9 memory_item

```sql
create table memory_item (
  id uuid primary key,
  tenant_id uuid not null,
  workspace_id uuid not null,
  project_id uuid,
  session_id uuid,
  memory_scope varchar(32) not null,
  memory_type varchar(64) not null,
  title varchar(256) not null,
  content text not null,
  importance int not null default 50,
  status varchar(32) not null,
  expires_at timestamptz,
  created_at timestamptz not null,
  updated_at timestamptz not null
);
```

## 3. API 规范

### 3.1 文档上传

`POST /api/documents`

请求：

```json
{
  "workspace_id": "uuid",
  "project_id": "uuid",
  "title": "ERP 销售订单接口规范",
  "doc_type": "api_spec",
  "visibility": "project",
  "version": "v1.0",
  "tags": ["erp", "order", "api"],
  "file_object_key": "upload/tmp/file.pdf"
}
```

响应：

```json
{
  "document_id": "uuid",
  "index_status": "pending"
}
```

### 3.2 文档检索

`POST /api/knowledge/search`

请求：

```json
{
  "tenant_id": "uuid",
  "workspace_id": "uuid",
  "project_id": "uuid",
  "query": "销售订单审批接口字段规则",
  "doc_types": ["api_spec", "business_flow", "db_schema"],
  "tags": ["erp"],
  "top_k": 8,
  "search_mode": "hybrid"
}
```

响应：

```json
{
  "items": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "title": "ERP 销售订单接口规范",
      "content": "审批接口必须校验订单状态...",
      "score": 0.86,
      "source_uri": "minio://docs/order-api.pdf",
      "version": "v1.0",
      "updated_at": "2026-06-27T10:00:00Z",
      "citation_id": "doc:order-api:v1:chunk:12"
    }
  ]
}
```

### 3.3 代码资产检索

`POST /api/assets/search`

请求：

```json
{
  "workspace_id": "uuid",
  "project_id": "uuid",
  "query": "Fastify 审批接口 Handler 示例",
  "asset_types": ["snippet", "pattern", "template"],
  "language": "java",
  "top_k": 5
}
```

响应：

```json
{
  "items": [
    {
      "asset_id": "uuid",
      "asset_type": "snippet",
      "title": "标准审批接口 Controller",
      "content": "public class ApprovalController ...",
      "score": 0.82,
      "tags": ["fastify", "approval"]
    }
  ]
}
```

### 3.4 沙箱执行

`POST /api/sandbox/jobs`

请求：

```json
{
  "workspace_id": "uuid",
  "project_id": "uuid",
  "session_id": "uuid",
  "job_type": "node_build",
  "image": "aidp/node:20",
  "command": ["pnpm", "test"],
  "workspace_object_key": "sandbox/input/project.zip",
  "timeout_seconds": 600,
  "resource_limits": {
    "cpu": "2",
    "memory_mb": 4096,
    "disk_mb": 10240,
    "network": "none"
  }
}
```

响应：

```json
{
  "job_id": "uuid",
  "status": "queued"
}
```

### 3.5 沙箱结果

`GET /api/sandbox/jobs/{job_id}`

响应：

```json
{
  "job_id": "uuid",
  "status": "failed",
  "exit_code": 1,
  "stdout_summary": "Running tests...",
  "stderr_summary": "TypeScript compilation failure at src/services/order-service.ts:42",
  "stdout_uri": "minio://logs/stdout.log",
  "stderr_uri": "minio://logs/stderr.log",
  "artifacts": [],
  "resource_usage": {
    "duration_ms": 18234,
    "max_memory_mb": 1200
  }
}
```

### 3.6 质量校验

`POST /api/quality/check`

请求：

```json
{
  "workspace_id": "uuid",
  "project_id": "uuid",
  "sandbox_job_id": "uuid",
  "ruleset": "typescript-node-default",
  "checks": ["format", "lint", "test", "build"]
}
```

响应：

```json
{
  "result_id": "uuid",
  "passed": false,
  "issues": [
    {
      "severity": "error",
      "check_type": "build",
      "file": "src/services/order-service.ts",
      "line": 42,
      "message": "cannot find symbol: method getStatus()",
      "suggested_fix": "确认 Order 实体是否包含 getStatus 方法，或改为实际字段访问方法。"
    }
  ]
}
```

### 3.7 MCP Skill 调用统一格式

`POST /api/mcp/invoke`

请求：

```json
{
  "trace_id": "uuid",
  "session_id": "uuid",
  "workspace_id": "uuid",
  "project_id": "uuid",
  "skill_name": "knowledge.search",
  "input": {
    "query": "订单审批接口规范",
    "top_k": 8
  }
}
```

响应：

```json
{
  "trace_id": "uuid",
  "skill_name": "knowledge.search",
  "output": {},
  "source_refs": [],
  "elapsed_ms": 320
}
```

## 4. Tool Capability 与 MCP Skill 规范

每个工具通过 `tool.yaml` 声明 capability。aidp-controller 安装工具后，将 capability 映射为 MCP Skill。

每个 capability 必须定义：

- name
- description
- input_schema
- output_schema
- timeout_ms
- retry_policy
- permission_required
- tool_name
- endpoint

示例：

```json
{
  "tool_name": "knowledge-tool",
  "name": "knowledge.search",
  "description": "检索技术文档、项目文档和历史方案",
  "input_schema": {
    "type": "object",
    "required": ["query"],
    "properties": {
      "query": { "type": "string" },
      "top_k": { "type": "integer", "default": 8 },
      "doc_types": { "type": "array", "items": { "type": "string" } }
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "items": { "type": "array" }
    }
  },
  "timeout_ms": 3000,
  "retry_policy": {
    "max_retries": 1
  },
  "permission_required": "knowledge:search",
  "endpoint": "POST /api/knowledge/search"
}
```

## 5. 文档切片规范

默认策略：

- Markdown 按标题层级优先切片。
- PDF 和 Word 先解析为结构化文本，再按段落切片。
- 单 chunk 建议 500-1000 tokens。
- overlap 建议 80-150 tokens。
- 保留标题路径。
- 保留页码或章节信息。
- 代码块不应被截断，除非超过最大 chunk。

chunk metadata 必须包含：

- document_id
- heading_path
- page_number
- chunk_index
- content_hash
- token_count
- doc_type
- tags
- version

## 6. 检索规范

MVP 推荐混合检索：

```text
metadata filter -> keyword search -> vector search -> rerank -> top_k
```

排序参考：

- 向量相似度。
- 关键词命中。
- 文档类型权重。
- 项目私有文档优先于公共技术文档。
- 新版本优先于旧版本。

禁止行为：

- 禁止跨项目返回私有文档。
- 禁止返回没有权限的文档片段。
- 禁止只返回文本不返回来源。

## 7. 沙箱安全规范

容器限制：

- 默认禁用网络。
- 禁止挂载宿主机敏感目录。
- 使用只读基础镜像。
- 工作目录使用临时目录。
- 任务结束必须清理容器和临时卷。
- 限制 CPU、内存、磁盘、进程数。
- 超时强制终止。

镜像白名单：

- `aidp/python:3.12`
- `aidp/shell:ubuntu-22.04`
- `aidp/node:20`
- `aidp/python:3.12`
- `aidp/postgres-test:16`

## 8. 质量规则规范

规则集结构：

```json
{
  "ruleset_id": "typescript-node-default",
  "project_type": "typescript-node",
  "checks": [
    {
      "type": "format",
      "command": ["pnpm", "lint"],
      "required": false
    },
    {
      "type": "test",
      "command": ["pnpm", "test"],
      "required": true
    }
  ]
}
```

issue 结构：

```json
{
  "severity": "error",
  "check_type": "lint",
  "file": "src/app.ts",
  "line": 12,
  "column": 8,
  "message": "unused import",
  "suggested_fix": "删除未使用的 import。"
}
```

## 9. 日志与可观测性

日志字段：

- timestamp
- level
- service
- trace_id
- request_id
- tenant_id
- workspace_id
- project_id
- session_id
- message
- elapsed_ms
- error_code

指标：

- Skill 调用次数、失败率、P95。
- 文档索引任务数量、失败率。
- 检索耗时。
- 沙箱任务耗时、失败率、超时率。
- 质量校验通过率。

## 10. 配置规范

MVP 默认使用本地 YAML、环境变量和数据库配置，不强制引入注册中心。

本地配置建议：

```text
aidp.mcp.skills.yaml
aidp.knowledge.yaml
aidp.sandbox.images.yaml
aidp.quality.rulesets.yaml
aidp.security.yaml
```

工具注册配置示例：

```yaml
tools:
  - name: knowledge-tool
    base_url: http://knowledge-tool:8080
  - name: asset-tool
    base_url: http://asset-tool:8080
  - name: sandbox-tool
    base_url: http://sandbox-tool:8080
```

Nacos 可选使用条件：

- 部署多套环境，配置频繁变更。
- 单个工具或服务存在多实例，需要注册发现。
- 工具配置或 capability 配置需要运行时动态刷新。
- 团队已有 Nacos 运维经验。

敏感配置：

- 数据库密码。
- MinIO 密钥。
- Git token。
- Embedding 服务密钥。

敏感配置必须使用环境变量或密钥管理，不写入 Git。
