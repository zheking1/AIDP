# importer-tool 开发计划

## 1. 开发顺序

### Phase 1 — 基础框架（3 天）

| 任务 | 工时 | 产出 |
|------|:----:|------|
| 工具脚手架（FastAPI + 工具协议接口） | 0.5d | `/health`、`/manifest`、`/capabilities` |
| 配置加载 | 0.5d | `config.yaml` 解析 |
| ContentAcquirer — text/url/file 来源 | 1d | 三种来源内容获取 |
| ContentAcquirer — directory 扫描 | 0.5d | 目录递归扫描 + 白名单过滤 |
| `POST /tool/invoke` 路由框架 | 0.5d | capability 路由分发 |

**Phase 1 交付**: 可获取 text/url/file/directory 内容，工具协议接口就绪。

### Phase 2 — 编排核心（4 天）

| 任务 | 工时 | 产出 |
|------|:----:|------|
| ContentClassifier — 规则分类引擎 | 1d | 基于文件名+特征的 type 分类 |
| ContentCategorizer — 标签推荐 | 0.5d | tags/category/severity 推荐 |
| QualityGate — 调用质量检查 API | 1d | 集成 `POST /api/quality/check` |
| QualityGate — 规则&技能专有检查 | 0.5d | severity 必填、instruction 必填 |
| ImportOrchestrator — 状态机 | 1d | 编排 5 步流程，状态流转 |

**Phase 2 交付**: 可完成单文件完整导入流程（含质量检查和标签推荐）。

### Phase 3 — 对话确认（2 天）

| 任务 | 工时 | 产出 |
|------|:----:|------|
| ConversationManager — 会话管理 | 1d | session 创建、状态查询、确认接口 |
| 批量导入流程编排 | 0.5d | 目录扫描→分类→汇总→确认→批量写入 |
| 幂等防重逻辑 | 0.5d | checksum 比对、版本更新提示 |

**Phase 3 交付**: 完整的对话式导入体验，支持单次和批量。

### Phase 4 — 持久化（2 天）

| 任务 | 工时 | 产出 |
|------|:----:|------|
| ContentPersister — knowledge 写入 | 0.5d | `POST /api/knowledge/documents` |
| ContentPersister — skill 写入 | 0.5d | `POST /api/skills` + files |
| ContentPersister — rule 写入 | 0.5d | `POST /api/rules` |
| ContentPersister — plan 写入 | 0.5d | knowledge + tag:plan |

**Phase 4 交付**: 四种类型都可成功持久化到 controller。

### Phase 5 — 完善与测试（2 天）

| 任务 | 工时 | 产出 |
|------|:----:|------|
| 日志记录（it_import_log） | 0.5d | 导入历史可追溯 |
| `importer.history` 接口 | 0.5d | 查询导入历史 |
| 错误处理与重试 | 0.5d | 结构化错误、retry 标记 |
| 集成测试 | 0.5d | 端到端测试 |

**Phase 5 交付**: 完整工具，可接入生产使用。

## 2. 总计

| Phase | 天数 | 累积 |
|-------|:----:|:----:|
| Phase 1 — 基础框架 | 3d | 3d |
| Phase 2 — 编排核心 | 4d | 7d |
| Phase 3 — 对话确认 | 2d | 9d |
| Phase 4 — 持久化 | 2d | 11d |
| Phase 5 — 完善与测试 | 2d | 13d |

**总工期: 13 个工作日**

## 3. 依赖条件

- [ ] controller 的 `POST /api/quality/check` 可用。
- [ ] controller 的 `POST /api/knowledge/documents` 可用。
- [ ] controller 的 `POST /api/skills` 可用（含 files 支持）。
- [ ] controller 的 `POST /api/rules` 可用（如不存在需先创建）。

## 4. 文件清单

### 新建文件

```
apps/importer-tool/
├── main.py                       # 应用入口 + 工具协议接口
├── config.yaml                   # 配置文件
├── app/
│   ├── __init__.py
│   ├── orchestrator.py           # ImportOrchestrator 编排器
│   ├── acquirer.py               # ContentAcquirer
│   ├── classifier.py             # ContentClassifier
│   ├── categorizer.py            # ContentCategorizer
│   ├── quality_gate.py           # QualityGate
│   ├── persister.py              # ContentPersister
│   ├── conversation.py           # ConversationManager
│   ├── models.py                 # 数据模型
│   ├── database.py               # DB 连接
│   └── utils.py                  # 工具函数 (checksum, http client)
├── migrations/
│   └── 001_init.sql              # 初始表结构
├── requirements.txt
├── Dockerfile
└── tests/
    ├── test_acquirer.py
    ├── test_classifier.py
    ├── test_orchestrator.py
    └── test_integration.py
```

### 无侵入

- 不修改 controller 现有 API。
- 不修改 knowledge/skills/rules 模块。
- 不修改 quality 模块。

## 5. 风险和缓解

| 风险 | 缓解 |
|------|------|
| controller API 缺乏批量接口 | 逐条调用，增加并发 |
| 目录扫描大项目时耗时 | 限制 max_files=500，支持 pattern 过滤 |
| 分类准确率不够 | 支持用户手动修正，预留 AI 增强接口 |
| quality check 不可用 | 降级为内置基础检查（lint + security） |
