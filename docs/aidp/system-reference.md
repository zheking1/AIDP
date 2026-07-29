# AIDP 系统参考手册 — 各工具详细设计

> **版本**: v1.0  
> **日期**: 2026-07-29  
> **用途**: 完整了解每个模块的设计、流程和实现

---

## 目录

1. [Controller — 统一入口](#1-controller)
2. [5 阶段上下文管线](#2-5-阶段上下文管线)
3. [知识库 Knowledge](#3-知识库-knowledge)
4. [记忆 Memory](#4-记忆-memory)
5. [技能 Skill Router](#5-技能-skill-router)
6. [代码沙箱 Sandbox](#6-代码沙箱-sandbox)
7. [质量检查 Quality](#7-质量检查-quality)
8. [代码资产 Asset](#8-代码资产-asset)
9. [进化引擎 Evolution](#9-进化引擎-evolution)
10. [上下文优化器 Context Optimizer](#10-上下文优化器-context-optimizer)
11. [MCP 服务层](#11-mcp-服务层)
12. [三层文件索引系统](#12-三层文件索引系统)

---

## 1. Controller

### 设计理念

Controller 是 AIDP 的单一入口。所有请求——Web UI 页面渲染、REST API 调用、MCP 工具调用——都通过它。它不直接执行业务逻辑，而是编排各模块和工具的能力。

```
请求 → Controller (:8883)
         ├─ Web UI  → Jinja2 模板 + Alpine.js SPA
         ├─ REST API → 15 个模块的路由
         └─ MCP     → 13 个工具, FastMCP Streamable-HTTP
```

### 数据模型

```
Controller 主表（PostgreSQL, 全模块共享）:

aidp_projects         项目
agent_instructions     Agent 指令模板 (per project)
tool_registry          工具注册表
tool_invocation        工具调用日志
evolution_versions     进化版本

各模块独立模型: 见对应章节
```

### 跨模块隔离机制

| 模式 | 字段 | 模块 | 默认 |
|------|------|------|:---:|
| scope | global/personal/project + user_id | Skills, Rules, Agents | personal |
| visibility | private/team/public + owner | Knowledge | private |
| project_id | 仅 project_id 过滤 | Memory, Workflows, Assets | 无默认 |
| level | project/system | Evolution | project |

### 统一认证

```
Web UI: Session + Cookie (aidp_session)
MCP:    x-api-key Header → AuthService.validate_api_key() → 用户绑定
        用户绑定后所有后续调用自动注入 user_id + project_id
```

---

## 2. 5 阶段上下文管线

### 设计理念

AI Agent 开发前需要充分了解项目背景——但每次都手动收集上下文太低效。管线化处理：一条 `aidp_context` 调用自动完成全过程。

### 执行流程

```
aidp_context(project_name="my-app", task="修复登录 bug")

┌─────────────────────────────────────────────────────┐
│ Stage 0: 加载 Instructions                          │
│   SELECT FROM agent_instructions                    │
│   WHERE project_id=X AND agent_type='main'          │
│   → {role, constraints, rules}                     │
├─────────────────────────────────────────────────────┤
│ Stage 1: 意图分析                                    │
│   └─ skill-router.analyze_intent(task)              │
│   → {intent, domains, complexity, is_compound}      │
├─────────────────────────────────────────────────────┤
│ Stage 2: 并行检索                                    │
│   ├─ memory-tool.search(project, query, ...)        │
│   ├─ knowledge-tool.search(query, project_id, ...)  │
│   └─ asset-tool.search(query, tags, ...)            │
│   → 3路并行, 缓存300秒                              │
├─────────────────────────────────────────────────────┤
│ Stage 3: 技能匹配                                    │
│   └─ skill-router.skill_run(task, tags, mode=auto)  │
│   → {skills[], rules[], instructions}               │
├─────────────────────────────────────────────────────┤
│ Stage 4: 上下文组装                                  │
│   ├─ 优先级排序: instructions > intent > code > skills > knowledge > memories > assets │
│   ├─ Token 预算: 8,000 max                          │
│   └─ 去重 + 压缩 → assembled_context                 │
└─────────────────────────────────────────────────────┘

返回: { system_prompt, user_message, metadata, token_estimate }
```

### 关键文件

- `apps/controller/app/services/context_pipeline.py:395` — 管线主类
- `apps/controller/app/services/context_assembly.py` — 上下文组装器
- `apps/controller/app/services/context_cache.py` — 缓存层 (TTL 300s)

---

## 3. 知识库 Knowledge

### 设计理念

三层知识体系：framework → template → project，子KB自动继承父KB的知识。支持文档上传、URL导入、自动分块、向量索引。

### 数据模型

```
aidp_knowledge_bases    知识库
  ├─ id, name, slug
  ├─ kb_level: framework/template/project  (三层体系)
  ├─ parent_id → 继承父KB知识
  ├─ visibility: private/team/public
  └─ chunk_size: 800, chunk_overlap: 120

aidp_knowledge_documents  文档
  ├─ base_id → KB
  ├─ title, content, category
  ├─ source_type: manual/web_import/upload
  └─ index_status: pending/indexing/indexed

aidp_document_chunks      分块
  ├─ document_id
  ├─ chunk_index, content
  └─ embedding (向量存储)
```

### API 端点

```
GET  /api/knowledge/bases           列表知识库 (层级树)
POST /api/knowledge/bases           创建知识库
GET  /api/knowledge/documents       列出文档 (分页+筛选)
POST /api/knowledge/documents       创建文档
GET  /api/knowledge/search          全文搜索
POST /api/knowledge/search/semantic 语义搜索 (向量)
GET  /api/knowledge/documents/{id}/chunks  查看分块
POST /api/knowledge/import-web/analyze     URL分析
POST /api/knowledge/import-web/direct-import  直接导入URL
GET  /api/knowledge/graph            知识图谱 (D3.js)
GET  /api/knowledge/stats            统计概览
```

### 访问控制

```
读:  public → 所有人
     team → 注册用户
     private → 仅所有者

写:  private + owner → owner
     强制检查 write-guard
```

---

## 4. 记忆 Memory

### 设计理念

记录项目开发经验、bug修复、架构决策等内容。支持语义搜索、D3力导向图谱、上下文包打包。

### 数据模型

```
aidp_memory_entries      记忆条目
  ├─ project_id, user_id
  ├─ category: architecture/decision/pattern/issue/bug/other
  ├─ memory_tier: episodic(情景)/semantic(语义)/procedural(程序)
  ├─ confidence_score: 0.0-1.0
  └─ parent_id → 记忆继承

aidp_memory_relations    记忆关系
  ├─ source_id → target_id
  └─ relation_type, strength

aidp_context_packages    上下文包
  ├─ name, description
  ├─ memory_ids[] → 打包的记忆
  └─ generated_context → 自动生成的文本上下文
```

### API 端点

```
GET    /api/memory/memories         列表(+分页+搜索)
POST   /api/memory/memories         创建记忆
GET    /api/memory/memories/{id}    获取详情
DELETE /api/memory/memories/{id}    删除记忆
POST   /api/memory/search           搜索记忆
GET    /api/memory/stats            统计
GET    /api/memory/graph            图谱数据 (nodes+links)
GET    /api/memory/timeline         时间轴 (按月分组)

GET    /api/memory/context/list     上下文包列表
POST   /api/memory/context/generate 创建上下文包 (自动生成文本)
GET    /api/memory/context/{id}     获取包详情
POST   /api/memory/context/preview  预览包内容
```

---

## 5. 技能 Skill Router

### 设计理念

意图分析 + 技能匹配 + 语义重排。根据任务描述从技能库匹配最佳技能。

### 核心流程

```
1. 意图分析 (vector_service.py)
   └─ analyze_intent(task)
      └─ LLM 调用 → {intent, domains, complexity, tags_needed}

2. 技能匹配 (skill_service.py)
   └─ 基于 tags + semantic search 匹配技能
      └─ 向量相似度 + 标签匹配

3. 语义重排 (ranker_service.py)
   └─ 用 BGE-Reranker-v2-m3 对候选技能重新排序
      └─ 返回 top_k 个最高分技能

4. 规则匹配 (rule_service.py)
   └─ 匹配相关的编码规则和约束
```

### 三层作用域

```
global     → 管理员维护，全局可见
personal   → 用户私有，仅自己可见
project    → 项目内共享，项目成员可见
```

---

## 6. 代码沙箱 Sandbox

### 设计理念

安全执行 AI 生成的代码。子进程隔离、超时控制、无网络访问。

### 执行流程

```
输入:
  {
    "code": "print(1+1)",
    "language": "python"
  }

执行:
  1. 创建临时目录
  2. 写入代码文件
  3. subprocess.run() 启动子进程
  4. 捕获 stdout/stderr
  5. 超时控制 (默认30s)
  6. 清理临时文件

输出:
  {
    "stdout": "2",
    "stderr": "",
    "exit_code": 0
  }
```

### API 端点

```
POST /api/sandbox/execute    执行代码
GET  /api/sandbox/history    执行历史
```

---

## 7. 质量检查 Quality

### 设计理念

代码提交前自动检查规范性和安全性。

### 检查类型

```
Lint 检查:
  ├─ 行长度 > 120 → warning
  ├─ 行尾空格 → warning
  └─ 文件末尾缺失换行 → info

安全扫描:
  ├─ 硬编码密码/API密钥/私钥 → critical
  ├─ eval()/exec() 调用 → medium
  └─ pickle.loads() 反序列化 → medium
```

### API 端点

```
POST /api/quality/check         执行检查
GET  /api/quality/history       历史记录 (含趋势)
GET  /api/quality/history/{id}  单条详情
```

---

## 8. 代码资产 Asset

### 设计理念

存储和管理代码片段、模板、配置等可复用代码资产。支持标签分类、全文搜索。

### 数据模型

```
aidp_assets
  ├─ title, description
  ├─ asset_type: snippet/template/config/component/utility
  ├─ language, content
  └─ tags[]
```

### API 端点

```
GET    /api/assets/list       列表 (搜索+筛选)
POST   /api/assets/create     创建
GET    /api/assets/{id}       详情
DELETE /api/assets/{id}       删除
GET    /api/assets/stats      统计
```

---

## 9. 进化引擎 Evolution

### 设计理念

项目级经验 → 管理员审核 → 系统级最佳实践。AI 分析代码变更、提取模式、自动提案。

### 核心流程

```
1. 工作完成
   └─ analyze_and_evolve(task, result) 或 index_changes()

2. LLM 模式分析
   └─ EvolutionEngine (app/tools/evolution_engine/)
   └─ 分析代码变更 → {category, pattern, confidence}

3. 自动提案 (confidence ≥ 0.5)
   └─ EvolutionVersion 创建 → review_status=pending

4. 管理员审核
   └─ /admin/evolution → approve/reject/request_changes
   └─ approve → level=system → 全平台可用

5. 版本管理
   └─ semver 版本号
   └─ 变更日志 review_log[]
   └─ system级可回退 (不能直接删除)
```

### 数据模型

```
evolution_versions
  ├─ version (semver), level (project/system)
  ├─ title, description
  ├─ changes (JSON), affected_tools[]
  ├─ review_status: pending/approved/rejected/needs_modification
  ├─ review_log[] → 审核历史
  └─ is_rollback_point, parent_version
```

### API 端点

```
POST   /api/evolution/propose            提交提案
POST   /api/evolution/analyze-and-propose 智能分析+提案
GET    /api/evolution/versions           列表 (筛选level/status)
GET    /api/evolution/versions/{id}      详情
PUT    /api/evolution/versions/{id}      更新
DELETE /api/evolution/versions/{id}      删除 (非system)
POST   /api/evolution/review             审核 (approve/reject/changes)
POST   /api/evolution/versions/{id}/publish   发布
POST   /api/evolution/versions/{id}/rollback  回退
GET    /api/evolution/stats              统计
```

---

## 10. 上下文优化器 Context Optimizer

### 设计理念

多工具检索结果的融合优化：去重、排序、Token 预算管理。

### 核心服务

```
RequirementAnalyzer    分析任务 → 需求识别 → 工具分配
BudgetAllocator        根据需求分配 Token 预算给各工具
StagedRetriever        并行调用 6 个工具检索
                         (memory-tool, knowledge-tool, code-index,
                          asset-tool, sandbox-tool, quality-tool)
ResultRefiner          去重 + 重排序 + 截断
ContextAssembler       组装最终上下文包 (Stage 4)
```

### 管线集成

```
Stage 2 并行检索:
  ├─ 知识类 → knowledge-tool + memory-tool
  ├─ 代码类 → code-index + asset-tool
  └─ 执行类 → sandbox-tool + quality-tool
  所有调用并行执行, 用 asyncio.gather
```

---

## 11. MCP 服务层

### 13 个工具 + 会话认证

```
工作流工具 (3):
  aidp_context        5阶段管线 + 用户认证
  invoke_tool_mcp     通用工具调用 (自动注入project_id)
  index_changes       增量索引 + 模式分析

初始化工具 (3):
  aidp_init          项目初始化 (9步骤)
  aidp_instructions  Subagent指令生成
  install_local_scripts 安装本地脚本

进化工具 (3):
  promote_evolution  提交进化提案
  list_evolutions    查看系统级最佳实践
  analyze_and_evolve LLM模式分析

管理工具 (4):
  list_registered_tools  工具列表
  check_tool_health      健康检查
  manage_models          模型管理
  sync_tool_capabilities 同步工具能力
```

### 会话生命周期

```
连接 → session_created
  │
  ├─ aidp_context(x-api-key)
  │   └─ API Key 验证 → 用户绑定
  │   └─ project_name 查询 → project 绑定
  │   └─ 5 阶段管线执行
  │
  ├─ invoke_tool_mcp → 自动注入 user_id + project_id
  │
  └─ 30分钟无活动 → session_timeout
```

---

## 12. 三层文件索引系统

### Layer 1 — Git Post-Commit Hook（最可靠）

```
git commit → .git/hooks/post-commit
  └─ sync_changes.py → git diff HEAD~1 HEAD
     └─ 代码文件 → POST /api/tools/code-index/invoke
     └─ 文档文件 → POST /api/classification/import
```

### Layer 2 — Agent MCP index_changes（最智能）

```
Agent 完成工作 → index_changes(task, files, summary)
  └─ 代码文件 → tool_invoker.invoke("code-index", "code.index_files", ...)
  └─ 文档文件 → POST /api/classification/import
  └─ LLM 分析 → evolution-engine → pattern 发现 → 自动提案
```

### Layer 3 — file_watcher.py（最实时）

```
文件保存 → watchdog Observer
  └─ ChangeBuffer 3秒防抖
     └─ 批量推送 → sync_code() + sync_docs()
```

### 配置

```json
// .opencode/watcher.json
{
  "project_id": 42,
  "project_root": "/path/to/project",
  "controller_url": "http://192.168.0.100:8883",
  "layers": {
    "git_hook": true,
    "file_watcher": true,
    "agent": true
  }
}
```