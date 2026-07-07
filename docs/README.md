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

### 当前开发重点（P0）

1. **Knowledge Tool Web UI** (`plans/KNOWLEDGE-WEB-UI-PLAN.md`)
   - 文档预览与分块可视化
   - 高级搜索中心
   - 知识库管理

2. **Memory Tool Web UI** (`plans/MEMORY-WEB-UI-PLAN.md`)
   - 记忆图谱可视化
   - 向量搜索
   - 上下文包生成器

3. **Agent Instructions 系统** (`MASTER-PLAN-2026.md` 第3节)
   - Stage 0-4 完整管线

### 查看任务清单

- **未完成任务**：`UNFINISHED-TASKS.md`
- **计划总结**：`PLANS-SUMMARY.md`

### 历史文档

已完成的旧计划文档归档在 `archived/2024-2025/` 目录下。

---

**最后更新**: 2026-07-07
