# AIDP 文档目录

## 📁 目录结构

```
docs/
├── README.md                      # 本文档
├── MASTER-PLAN-2026.md            # 2026年综合开发计划（当前主计划）
├── UNFINISHED-TASKS.md            # 未完成任务清单
├── PLANS-SUMMARY.md               # 计划总结
├── plans/                         # 详细开发计划
│   ├── KNOWLEDGE-WEB-UI-PLAN.md   # Knowledge Tool Web UI 计划
│   ├── MEMORY-WEB-UI-PLAN.md      # Memory Tool Web UI 计划
│   └── EVOLUTION-REFACTOR-PLAN.md # Evolution Engine 重构计划
├── ai-dev-platform/               # 平台架构文档
│   ├── README.md                  # 平台概述
│   ├── INTEGRATED-ARCHITECTURE.md # 集成架构
│   ├── DEVELOPMENT_PROMPT.md      # AI开发提示词
│   ├── common/                    # 通用规范
│   │   ├── tool-contract.md       # 工具契约
│   │   └── engineering-standards.md # 工程标准
│   ├── controller/                # Controller 文档
│   │   ├── README.md
│   │   └── AI_IMPLEMENTATION.md
│   └── tools/                     # 工具文档
│       ├── README.md
│       ├── template-tool/         # SkillRouter
│       ├── knowledge-tool/
│       ├── memory-tool/
│       ├── asset-tool/
│       ├── sandbox-tool/
│       ├── quality-tool/
│       ├── git-tool/
│       ├── error-tool/
│       └── project-analyzer-tool/
└── archived/                      # 归档文档
    └── 2024-2025/                 # 2024-2025年已完成的旧计划
        ├── DEV-PLAN-V3.md         # V3开发计划（已完成）
        ├── DEV-PLAN-2026-07-06.md # 2026年7月计划（已完成）
        ├── UNIFIED_WEB_UI_DESIGN.md # Web UI设计（已实现）
        ├── 01-AIDP-SYSTEM-ARCHITECTURE.md
        ├── 03-04-KNOWLEDGE-BASE-*.md
        ├── 06-07-CODE-INDEX-*.md
        └── ... (其他已完成的旧文档)
```

## 📋 快速导航

### 当前开发重点

**Phase 3 已完成** ✅ — Agent Instructions + Stage 0-4 上下文管线 + MCP 集成均已实装。

**P1 - 下一步**：

1. **Evolution Engine 重构** (`plans/EVOLUTION-REFACTOR-PLAN.md`)
   - 两级进化系统（项目级 + 系统级）
   - 版本管理、审核流程、回退

2. **模块 Web UI 完善**
   - Knowledge 分块可视化
   - Memory 时间轴/上下文包生成器
   - Asset/Quality 详情页和图表

### 查看任务清单

- **未完成任务**：`UNFINISHED-TASKS.md`
- **计划总结**：`PLANS-SUMMARY.md`

### 历史文档

已完成的旧计划文档归档在 `archived/2024-2025/` 目录下。

---

**最后更新**: 2026-07-28
