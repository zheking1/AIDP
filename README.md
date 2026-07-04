# AIDP — AI DevOps Platform

私有化 AI 编程基础设施平台。Controller + N 个可选工具，按需安装。

## 架构

```text
aidp-controller (Python + FastAPI + FastMCP)
  + skill-router    (技能路由引擎)
  + knowledge-tool  (文档知识库)
  + asset-tool      (代码资产管理)
  + sandbox-tool    (代码执行沙箱)
  + quality-tool    (质量校验)
  + memory-tool     (项目记忆)
  + code-index      (代码结构索引)
  + doc-index       (文档索引)
  + context-optimizer (上下文优化)
  + evolution-engine (自演进引擎)
  + project-importer (项目导入器)
```

## 已有工具

| 工具 | 路径 | 端口 | 状态 |
|------|------|------|------|
| skill-router | `tools/skill-router/` | 8788 | ✅ 已完成 |
| knowledge-tool | `tools/knowledge-tool/` | 18081 | ✅ 已完成 |
| asset-tool | `tools/asset-tool/` | 18082 | ✅ 已完成 |
| sandbox-tool | `tools/sandbox-tool/` | 18083 | ✅ 已完成 |
| quality-tool | `tools/quality-tool/` | 18084 | ✅ 已完成 |
| memory-tool | `tools/memory-tool/` | 18085 | ✅ 已完成 |
| code-index | `tools/code-index/` | 18086 | ✅ 已完成 |
| doc-index | `tools/doc-index/` | 18087 | ✅ 已完成 |
| context-optimizer | `tools/context-optimizer/` | 18088 | ✅ 已完成 |
| evolution-engine | `tools/evolution-engine/` | 18089 | ✅ 已完成 |
| project-importer | `tools/project-importer/` | 18090 | ✅ 已完成 |
| controller | `apps/controller/` | 8883 | ✅ 已完成 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.13 + FastAPI + FastMCP |
| 数据库 | PostgreSQL + pgvector |
| 缓存 | Redis |
| Web UI | Jinja2 + Alpine.js + Tailwind CSS |
| 部署 | Docker Compose |

## 目录结构

```text
openCode/
├── apps/
│   └── controller/         # 主服务
├── tools/
│   ├── skill-router/       # 技能路由
│   ├── knowledge-tool/     # 文档知识库
│   ├── asset-tool/         # 代码资产管理
│   ├── sandbox-tool/       # 沙箱执行
│   ├── quality-tool/       # 质量校验
│   ├── memory-tool/        # 项目记忆
│   ├── code-index/         # 代码结构索引
│   ├── doc-index/          # 文档索引
│   ├── context-optimizer/  # 上下文优化
│   ├── evolution-engine/   # 自演进引擎
│   └── project-importer/   # 项目导入器
├── deploy/                 # 部署脚本
├── docs/                   # 设计文档
└── tests/
```

## 快速开始

```bash
# 全量部署到 NAS
powershell deploy\deploy-nas.ps1

# SkillRouter 独立启动
cd tools/skill-router
cp .env.example .env
docker compose up -d
```

## 文档

- [设计文档](docs/ai-dev-platform/README.md)
- [集成架构](docs/ai-dev-platform/INTEGRATED-ARCHITECTURE.md)
- [技术栈](docs/ai-dev-platform/09-technology-stack.md)
- [工具协议](docs/ai-dev-platform/common/tool-contract.md)
