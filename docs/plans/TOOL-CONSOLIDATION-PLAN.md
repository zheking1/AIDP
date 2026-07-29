# AIDP 工具整合方案 —— 多容器 → 单容器

> **版本**: v1.0  
> **日期**: 2026-07-29  
> **状态**: 规划中

---

## 1. 动机

### 当前问题

```
Controller     :8883      ← 主进程
SkillRouter    :8788      ← 独立容器, 含 torch+transformers
KnowledgeTool  :18081     ← 独立容器, 含 torch+transformers
MemoryTool     :18085     ← 独立容器
AssetTool      :18082     ← 独立容器
SandboxTool    :18083     ← 独立容器
QualityTool    :18084     ← 独立容器
ContextOpt     :18088     ← 独立容器
EvolutionEng   :18089     ← 独立容器
```

| 问题 | 影响 |
|------|------|
| 9 个容器各装一份 Python 依赖 | torch(526MB) + CUDA(1.5GB) × 3 = 6GB 浪费 |
| 部署一次要 build 7 次、上传 7 次 | 每次部署 5-10 分钟 |
| 服务间 HTTP 调用有网络开销 | 每次调用 1-3ms 延迟 |
| Controller 已包含各工具的模块代码 | 代码重复维护 |
| 独立 tool Web UI 已废弃 | `tools/*/app/web/` 目录无用 |
| 模型配置各管各的 | 刚统一到 Controller，但仍需各工具查询 |

### 目标

```
AIDP Controller  :8883      ← 唯一容器
  ├── /                    ← Workspace (现有)
  ├── /admin/*             ← 管理页 (现有)
  ├── /api/knowledge/*     ← 原 knowledge-tool:18081
  ├── /api/memory/*        ← 原 memory-tool:18085
  ├── /api/assets/*        ← 原 asset-tool:18082
  ├── /api/sandbox/*       ← 原 sandbox-tool:18083
  ├── /api/quality/*       ← 原 quality-tool:18084
  ├── /tool/skill-router/* ← 原 skill-router:8788
  ├── /tool/context-opt/*  ← 原 context-optimizer:18088
  ├── /tool/evolution/*    ← 原 evolution-engine:18089
  └── /mcp                 ← MCP Server (现有)
```

---

## 2. 改造范围

### 2.1 代码搬移

把 `tools/{name}/app/` 完整搬到 `apps/controller/app/tools/{name}/`：

```
tools/
├── skill-router/app/       → apps/controller/app/tools/skill-router/
├── knowledge-tool/app/     → apps/controller/app/tools/knowledge-tool/
├── memory-tool/app/        → apps/controller/app/tools/memory-tool/
├── asset-tool/app/         → apps/controller/app/tools/asset-tool/
├── sandbox-tool/app/       → apps/controller/app/tools/sandbox-tool/
├── quality-tool/app/       → apps/controller/app/tools/quality-tool/
├── context-optimizer/app/  → apps/controller/app/tools/context-optimizer/
└── evolution-engine/app/   → apps/controller/app/tools/evolution-engine/
```

> `tools/` 源目录保留不删，git 提交后等验证通过再清理。

### 2.2 依赖合并

各工具 `requirements.txt` 的增量依赖合并到 Controller：

| 工具 | 新增依赖 |
|------|----------|
| skill-router | `PyYAML`（已有）, `httpx`（已有） |
| knowledge-tool | `sentence-transformers`（已有）, `beautifulsoup4`（已有） |
| context-optimizer | 无新增 |
| evolution-engine | 无新增 |

**结论**: Controller 的 `requirements.txt` 已包含所有依赖，无需改动。

### 2.3 路由挂载

`apps/controller/app/main.py` 修改：

```python
# 挂载各工具 FastAPI app 到指定路径前缀
from app.tools.skill_router.app.main import app as skill_router_app
from app.tools.knowledge_tool.app.main import app as knowledge_tool_app
# ... 其余类似

app.mount("/tool/skill-router", skill_router_app)
app.mount("/tool/knowledge", knowledge_tool_app)
# ...
```

### 2.4 内部调用改写（核心）

**原则**: 原来走 `httpx.post("http://127.0.0.1:{port}/api/...")` 的全部改为直接 `import` 调用。

涉及文件清单：

| 文件 | 改动 | 说明 |
|------|:---:|------|
| `app/services/tool_invoker.py` | 3处 HTTP → import | **核心**: 所有工具调用的统一入口，改一处全生效 |
| `app/services/context_pipeline.py` | 5处 HTTP → import | Stage 1-4 管线 |
| `app/services/project_init_service.py` | 3处 HTTP → import | 项目初始化 |
| `app/services/tool_retry.py` | 1处 | 重试逻辑 |
| `app/modules/evolution/routes.py` | 1处 | 智能进化分析 |
| `app/mcp/server.py` | 1处 | MCP analyze_and_evolve |

改造前：
```python
async with httpx.AsyncClient() as client:
    resp = await client.post("http://127.0.0.1:18089/api/events", json={...})
    data = resp.json()
```

改造后：
```python
from app.tools.evolution_engine.app.api.events import collect_event
# 直接调用路由处理函数, 或提取服务层
```

### 2.5 删除内容

| 删除 | 说明 |
|------|------|
| `tools/*/app/web/` | 独立 Web UI，已被 Controller 淘汰 |
| `tools/*/Dockerfile` | 不再需要独立构建 |
| `tools/*/docker-compose.yml` | 同上 |
| `docker-compose.yml` 中 6 个 service | 只留 controller + postgres |
| `deploy/` 脚本 `$tools` 列表 | 删除 8 个工具项 |
| 各工具 `config.py` 中的 `PORT` 字段 | 统一走 8883 |

### 2.6 不改动的内容

| 保留 | 说明 |
|------|------|
| 数据库结构 | 所有工具共用同一个 PostgreSQL，无需迁移 |
| 前端 UI | Controller 已有所有模块的模板 |
| MCP 工具 | Controller MCP 已封装各工具 |
| API 路径 | 内部改实现，对外接口不变 |
| 业务逻辑 | 只改调用方式，不改业务 |

---

## 3. 执行步骤

### Phase 1: 搬代码 + 跑通 (1h)

- [ ] 复制 `tools/*/app/` 到 `apps/controller/app/tools/*/`
- [ ] `main.py` 挂载各工具路由
- [ ] 本地启动，验证所有端点可访问
- [ ] 跑全量 CRUD 测试

### Phase 2: 改内部调用 (1.5h)

- [ ] 改造 `tool_invoker.py`
- [ ] 改造 `context_pipeline.py`
- [ ] 改造 `project_init_service.py`
- [ ] 改造 `evolution/routes.py`
- [ ] 改造 `mcp/server.py`
- [ ] 移除 ports 配置
- [ ] 跑全量 CRUD + LLM 调用测试

### Phase 3: 清理 + 部署 (0.5h)

- [ ] 删除独立 Web UI 目录
- [ ] 精简 `docker-compose.yml`
- [ ] 精简 `deploy/deploy-now.ps1`
- [ ] NAS 部署验证
- [ ] 停止并清理旧容器

---

## 4. 风险与回退

| 风险 | 缓解 |
|------|------|
| 工具间端口冲突 | 已不存在，全部走 8883 |
| 依赖冲突 | Controller 已有所有依赖，未新增 |
| 性能下降 | 去掉 HTTP 开销，只快不慢 |
| 单点故障 | 当前已是——Controller 挂了其他工具也用不了 |

**回退**: git revert 即可。数据库无变更，零数据风险。

---

## 5. 改造后效果

| 指标 | 改造前 | 改造后 |
|------|--------|--------|
| 容器数 | 9 | 1 |
| 部署时间 | 5-10 分钟 | 30 秒 |
| 磁盘占用（镜像） | ~3.5GB | ~600MB |
| 服务间调用延迟 | 1-3ms (HTTP) | 0ms (函数) |
| build 次数 | 7 次 | 1 次 |
| requirements.txt | 7 个 | 1 个 |

---

**待确认后执行**