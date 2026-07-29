# AIDP 端口与服务映射

## 完整端口表

| 端口 | 服务名 | 容器名 | 类型 | 框架 | 数据库 | 工具名称 (MCP) |
|------|--------|--------|------|------|--------|---------------|
| `8883` | controller | `aidp-controller` | Core | FastAPI + FastMCP | PostgreSQL | `aidp-controller` |
| `8788` | skill-router | 无 (host network) | Tool | FastAPI + FastMCP | PostgreSQL + pgvector + Redis | `skill-router` |
| `18081` | knowledge-tool | 无 (host network) | Tool | FastAPI | SQLite / PostgreSQL | `knowledge-tool` |
| `18082` | asset-tool | 无 (host network) | Tool | FastAPI | SQLite / PostgreSQL | `asset-tool` |
| `18083` | sandbox-tool | `aidp-sandbox` | Tool | FastAPI | PostgreSQL | `sandbox-tool` |
| `18084` | quality-tool | `aidp-quality` | Tool | FastAPI | PostgreSQL | `quality-tool` |
| `18085` | memory-tool | 无 (host network) | Tool | FastAPI | SQLite / PostgreSQL | `memory-tool` |
| `18086` | code-index | 无 (host network) | Tool | FastAPI | SQLite | `code-index` |
| `18087` | doc-index | 无 (host network) | Tool | FastAPI | SQLite | `doc-index` |
| `18088` | context-optimizer | 无 (host network) | Tool | FastAPI | SQLite | `context-optimizer` |
| `18089` | evolution-engine | 无 (host network) | Tool | FastAPI | SQLite | `evolution-engine` |
| `18090` | project-importer | 无 (host network) | Tool | FastAPI | 无 (纯 HTTP 客户端) | - |
| `18091` | file-watcher | 无 (host network) | Tool | FastAPI | SQLite | `file-watcher` |

> 注: `tools/importer-tool/` 也使用端口 `18085`，与 memory-tool 冲突，不同时运行。

## 基础设施端口

| 端口 | 服务 | 版本 | 说明 |
|------|------|------|------|
| `5432` | PostgreSQL | 16+ | 主数据库 (含 pgvector 扩展) |
| `6379` | Redis | 7+ | 缓存服务 |
| `11434` | Ollama (开发) | - | 本地 LLM 服务 (evolution-engine 默认) |
| `8000` | LLM API (开发) | - | LLM 代理端点 |

## 端口范围规划

| 范围 | 用途 | 占用 |
|------|------|------|
| `8000-8999` | 核心服务 | `8883` (controller), `8788` (skill-router) |
| `18080-18099` | 工具服务 | `18081`-`18091` (连续分配) |
| `5400-5499` | 数据库 | `5432` (PostgreSQL) |
| `6300-6399` | 缓存 | `6379` (Redis) |

## 各服务配置文件中的端口声明

| 服务 | 配置文件 | 端口字段 |
|------|---------|---------|
| controller | `apps/controller/app/_config.py:10` | `PORT: int = 8883` |
| controller | `apps/controller/tool.yaml:16` | `port: 8883` |
| controller | `apps/controller/Dockerfile:10` | `EXPOSE 8883` |
| skill-router | `tools/skill-router/Dockerfile:14` | `EXPOSE 8788` |
| knowledge-tool | `tools/knowledge-tool/app/config.py:10` | `PORT: int = 18081` |
| knowledge-tool | `tools/knowledge-tool/Dockerfile:10` | `EXPOSE 18081` |
| asset-tool | `tools/asset-tool/app/config.py:10` | `PORT: int = 18082` |
| asset-tool | `tools/asset-tool/Dockerfile:10` | `EXPOSE 18082` |
| sandbox-tool | `tools/sandbox-tool/app/config.py:10` | `PORT: int = 18083` |
| sandbox-tool | `tools/sandbox-tool/Dockerfile:12` | `EXPOSE 18083` |
| quality-tool | `tools/quality-tool/app/config.py:10` | `PORT: int = 18084` |
| quality-tool | `tools/quality-tool/Dockerfile:12` | `EXPOSE 18084` |
| memory-tool | `tools/memory-tool/app/config.py:10` | `PORT: int = 18085` |
| memory-tool | `tools/memory-tool/Dockerfile:12` | `EXPOSE 18085` |
| code-index | `tools/code-index/app/config.py:7` | `PORT: int = 18086` |
| code-index | `tools/code-index/Dockerfile:7` | `EXPOSE 18086` |
| doc-index | `tools/doc-index/app/config.py:7` | `PORT: int = 18087` |
| doc-index | `tools/doc-index/Dockerfile:7` | `EXPOSE 18087` |
| context-optimizer | `tools/context-optimizer/app/config.py:7` | `PORT: int = 18088` |
| context-optimizer | `tools/context-optimizer/Dockerfile:7` | `EXPOSE 18088` |
| evolution-engine | `tools/evolution-engine/app/config.py:7` | `PORT: int = 18089` |
| evolution-engine | `tools/evolution-engine/Dockerfile:7` | `EXPOSE 18089` |
| project-importer | `tools/project-importer/Dockerfile:6` | `EXPOSE 18090` |
| file-watcher | `tools/file-watcher/app/config.py:7` | `PORT: int = 18091` |
| file-watcher | `tools/file-watcher/Dockerfile:12` | `EXPOSE 18091` |

## 健康检查端点

所有服务统一提供健康检查:

| 服务 | 健康检查 URL |
|------|------------|
| controller | `http://127.0.0.1:8883/health` |
| skill-router | `http://127.0.0.1:8788/health` |
| knowledge-tool | `http://127.0.0.1:18081/health` |
| asset-tool | `http://127.0.0.1:18082/health` |
| sandbox-tool | `http://127.0.0.1:18083/health` |
| quality-tool | `http://127.0.0.1:18084/health` |
| memory-tool | `http://127.0.0.1:18085/health` |
| code-index | `http://127.0.0.1:18086/health` |
| doc-index | `http://127.0.0.1:18087/health` |
| context-optimizer | `http://127.0.0.1:18088/health` |
| evolution-engine | `http://127.0.0.1:18089/health` |
| project-importer | `http://127.0.0.1:18090/health` |
| file-watcher | `http://127.0.0.1:18091/health` |

## 工具调用端点

每个工具提供 `/tool/invoke` 端点，Controller 通过此端点统一调用:

```
POST <tool_endpoint>/tool/invoke
Content-Type: application/json

{
  "capability": "<capability_name>",
  "input": { <args> },
  "trace_id": "<uuid>"
}
```

## Docker 网络配置

所有 docker-compose 服务均配置 `network_mode: host`，因此:
- 服务间通信使用 `127.0.0.1:<port>`
- 无需 docker 内部 DNS 解析
- 端口直接映射到宿主机

## 快速验证

```bash
# 检查所有服务是否运行
for port in 8883 8788 18081 18082 18083 18084 18085 18086 18087 18088 18089 18090 18091; do
  echo -n "Port $port: "
  curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$port/health 2>/dev/null || echo "DOWN"
done

# 从 Controller 查看注册的工具
curl http://127.0.0.1:8883/api/tools
```