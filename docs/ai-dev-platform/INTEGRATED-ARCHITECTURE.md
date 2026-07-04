# AIDP 集成架构

## 1. 总体方案

```text
用户 / AI Agent
    │
    │  MCP (Streamable-HTTP)
    ▼
┌──────────────────────────────────────────┐
│  aidp-controller (Python + FastAPI)       │
│  ├── 工具注册/安装/编排                    │
│  ├── 用户/项目/会话/权限/审计               │
│  └── MCP 暴露 (FastMCP)                   │
├──────────────────────────────────────────┤
│  工具层（按需安装）                         │
│  ├── skill-router: 技能路由引擎            │
│  ├── knowledge-tool: 文档知识库            │
│  ├── asset-tool: 代码资产管理              │
│  ├── sandbox-tool: Docker 沙箱            │
│  ├── quality-tool: 质量校验               │
│  └── memory-tool: 项目记忆                │
└──────────────────────────────────────────┘
         │           │           │
    ┌────▼───┐  ┌───▼────┐  ┌──▼──────┐
    │PostgreSQL│  │ Redis  │  │ Docker  │
    │+pgvector │  │        │  │         │
    └────────┘  └────────┘  └─────────┘
```

## 2. 工具清单

| 工具 | 路径 | 优先级 | 状态 |
|------|------|--------|------|
| skill-router | `tools/skill-router/` | P0 | ✅ 已完成 |
| knowledge-tool | `tools/knowledge-tool/` | P0 | ⏳ 待开发 |
| asset-tool | `tools/asset-tool/` | P0 | ⏳ 待开发 |
| sandbox-tool | `tools/sandbox-tool/` | P0 | ⏳ 待开发 |
| quality-tool | `tools/quality-tool/` | P0 | ⏳ 待开发 |
| memory-tool | `tools/memory-tool/` | P0 | ⏳ 待开发 |
| error-tool | `tools/error-tool/` | P1 | ⏳ 待开发 |
| project-analyzer-tool | `tools/project-analyzer-tool/` | P1 | ⏳ 待开发 |

## 3. SkillRouter 能力映射

SkillRouter 已有能力直接作为 AIDP 工具使用：

| SkillRouter 能力 | AIDP 角色 |
|------------------|-----------|
| resolve_task | 技能路由 |
| skill_register/update/delete | 技能管理 |
| rule_create/update/delete | 规则引擎 |
| model_add/list | LLM 配置 |
| skill_review/approve/reject | 审核流程 |
| evolution_submit/rollback | 版本管理 |
| cache_flush | 缓存管理 |
| Web UI | 管理后台 |
| CLI (srcli.py) | 命令行工具 |

## 4. 编排流程

```text
用户: "根据 ERP 销售订单规则新增审批接口"

Step 1: 加载项目上下文
  controller -> memory-tool -> memory.get_context

Step 2: 检索相关文档
  controller -> knowledge-tool -> knowledge.search

Step 3: 检索可复用代码资产
  controller -> asset-tool -> asset.search

Step 4: 匹配技能
  controller -> skill-router -> resolve_task

Step 5: LLM 生成代码
  Agent 基于上下文生成代码

Step 6: 沙箱编译
  controller -> sandbox-tool -> sandbox.build

Step 7: 质量校验
  controller -> quality-tool -> quality.check

Step 8: 修复循环（如有问题）
  Agent 根据 issue 修复 → 重新 Step 6-7

Step 9: 归档经验
  controller -> memory-tool -> memory.upsert_project
```

## 5. 工具协议

每个工具必须提供：

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
# 最小安装（仅 controller + skill-router）
docker compose -f deploy/compose/core.yml up -d

# 知识库安装
docker compose -f deploy/compose/knowledge.yml up -d

# 编程闭环
docker compose -f deploy/compose/coding.yml up -d

# 完整安装
docker compose -f deploy/compose/full.yml up -d
```

## 7. 效果度量

| 指标 | 目标 |
|------|------|
| 建议采纳率 | >70% |
| 生成通过率 | >60% |
| 修复成功率 | >80% |
| 上下文节省量 | >60% |
| 延迟 P95 | <15s |

## 8. 开发优先级

```text
第一阶段: Controller 编排层
第二阶段: knowledge-tool + asset-tool
第三阶段: sandbox-tool + quality-tool
第四阶段: memory-tool
第五阶段: 编程闭环
```
