# AIDP 技术栈决策

## 1. 决策结论

AIDP 统一采用 **Python + FastAPI** 技术路线。

```text
aidp-controller      Python + FastAPI + FastMCP
skill-router         Python + FastAPI + FastMCP  (已有)
knowledge-tool       Python + FastAPI
sandbox-tool         Python + FastAPI + Docker SDK
quality-tool         Python + FastAPI
memory-tool          Python + FastAPI
admin-console        Jinja2 + Alpine.js + Tailwind CSS
cli                  Python
```

## 2. 统一技术栈的理由

### 2.1 SkillRouter 已有能力

| 能力 | 状态 |
|------|------|
| FastAPI + FastMCP | ✅ 已有 |
| 32 个 MCP 工具 | ✅ 已有 |
| Web UI | ✅ 已有 |
| CLI | ✅ 已有 |
| PostgreSQL + pgvector | ✅ 已有 |
| Redis | ✅ 已有 |
| Docker 部署 | ✅ 已有 |

### 2.2 为什么不换 TypeScript

1. 已有代码资产完整
2. 全 Python 栈降低维护成本
3. Python 在 AI/RAG 生态最丰富
4. FastMCP 已解决 MCP 传输层
5. 避免从零重写

### 2.3 统一栈的优势

```text
一种语言，一套构建，一套部署
```

## 3. 统一技术栈

| 能力 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| MCP 服务 | FastMCP 3.4.2 |
| 数据库 | PostgreSQL + pgvector |
| 缓存 | Redis |
| ORM | SQLAlchemy 2.0 (async) |
| 模板 | Jinja2 |
| 前端 | Alpine.js + Tailwind CSS |
| CLI | Python |
| 测试 | pytest |
| 部署 | Docker Compose |
| 文档解析 | pypdf / python-docx / markdown |
| Docker SDK | docker (Python) |

## 4. 项目结构

```text
openCode/
├── apps/controller/         # 主服务
├── tools/
│   ├── skill-router/        # 已有
│   ├── knowledge-tool/
│   ├── sandbox-tool/
│   ├── quality-tool/
│   └── memory-tool/
├── packages/sdk/
├── deploy/compose/
├── docs/ai-dev-platform/
└── tests/
```

## 5. 工具协议

```yaml
# tool.yaml
apiVersion: aidp.dev/v1
kind: Tool
metadata:
  name: <tool-name>
  version: 0.1.0
runtime:
  modes: [standalone, managed, remote]
  docker:
    image: aidp/<tool-name>:0.1.0
    port: 8080
capabilities:
  - name: <capability>.<action>
    endpoint: POST /api/<capability>/<action>
    timeoutMs: 3000
```

标准接口：

```text
GET  /health
GET  /tool/manifest
GET  /tool/capabilities
POST /tool/invoke
```

## 6. 部署方案

```bash
# 最小安装
docker compose -f deploy/compose/core.yml up -d

# 知识库
docker compose -f deploy/compose/knowledge.yml up -d

# 编程闭环
docker compose -f deploy/compose/coding.yml up -d

# 完整
docker compose -f deploy/compose/full.yml up -d
```

## 7. 个人模式与团队模式

个人模式默认：

- Python + FastAPI。
- PostgreSQL + pgvector。
- Redis。
- 本地文件存储。
- 工具按需启动。

团队模式增强：

- MinIO 可选。
- 多用户权限。
- 审批和审计。
- 多 runner。

## 8. AI 实现约束

- 全栈 Python + FastAPI，不引入 TypeScript。
- 不引入 Nacos、RabbitMQ、Kubernetes。
- 数据模型 PostgreSQL + pgvector。
- 工具通过 HTTP 协议接入。
- 优先单体可运行版本。
- 基于 SkillRouter 演进，不重写。
