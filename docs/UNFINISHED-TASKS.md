# AIDP 未完成任务清单

## 说明

本文档汇总所有 docs 目录下的开发计划中**标记为未完成**的任务。

**最后更新**: 2026-07-07

---

## 一、DEV-PLAN-V3.md 中的未完成任务

### Phase 1: 修复现有断链 ⚠️ 部分完成

| 任务 | 状态 | 说明 |
|------|------|------|
| 修复 aidp_init doc 导入 | ✅ | 已完成 |
| 修复 aidp_init asset 注册 | ✅ | 已完成 |
| 修复 context-optimizer 工具调用 | ✅ | 已完成 |
| 修复 context-optimizer json import | ✅ | 已完成 |
| 修复 code-index Edge 图 | ⚠️ | 待验证 |
| 修复 context-optimizer 去重 bug | ⚠️ | 待验证 |

### Phase 2: Agent Instructions 存储与加载 🚧 进行中

| 任务 | 文件 | 状态 |
|------|------|------|
| 创建 AgentInstruction 数据模型 | `apps/controller/app/db/models.py` | 🚧 待开发 |
| 数据库迁移 | `apps/controller/app/db/init_db.py` | 🚧 待开发 |
| 创建 Instructions CRUD API | `apps/controller/app/api/instructions.py` | 🚧 待开发 |
| Stage 0 加载逻辑 | `project_init_service.py` | 🚧 待开发 |

### Phase 3: 意图分析扩展 🚧 进行中

| 任务 | 文件 | 状态 |
|------|------|------|
| 扩展 analyze_intent 方法 | `skill-router/classification_service.py` | 🚧 待开发 |
| 新增 analyze_intent capability | `skill-router/api/tool.py` | 🚧 待开发 |
| Prompt 优化 | - | 🚧 待开发 |

### Phase 4: 分段检索管线 🚧 进行中

| 任务 | 文件 | 状态 |
|------|------|------|
| StagedRetriever 服务 | `context-optimizer/services/staged_retriever.py` | 🚧 待开发 |
| 更新 tool invoker 端点 | `context-optimizer/api/optimize.py` | 🚧 待开发 |

### Phase 5: 上下文组装 🚧 进行中

| 任务 | 文件 | 状态 |
|------|------|------|
| SkillMatcher 服务 | `context-optimizer/services/skill_matcher.py` | 🚧 待开发 |
| ContextAssembler 服务 | `context-optimizer/services/context_assembler.py` | 🚧 待开发 |
| InstructionAssembler 服务 | `context-optimizer/services/instruction_assembler.py` | 🚧 待开发 |
| assemble-context API | `context-optimizer/api/optimize.py` | 🚧 待开发 |
| assemble-subagent API | `context-optimizer/api/optimize.py` | 🚧 待开发 |

### Phase 6: MCP 集成 🚧 进行中

| 任务 | 文件 | 状态 |
|------|------|------|
| aidp_context 重构 | `controller/mcp/server.py` | 🚧 待开发 |
| aidp_instructions 新增 | `controller/mcp/server.py` | 🚧 待开发 |

### Phase 7: 部署与测试 ⏳ 待开始

| 任务 | 状态 |
|------|------|
| 工具重新构建 Docker 镜像 | ⏳ 待开始 |
| 部署到 NAS | ⏳ 待开始 |
| 单文件修改测试 | ⏳ 待开始 |
| 新功能开发测试 | ⏳ 待开始 |
| Subagent 生成测试 | ⏳ 待开始 |
| 验收清单全部通过 | ⏳ 待开始 |

---

## 二、MASTER-DEVELOPMENT-PLAN.md 中的未完成任务

### Phase 1: 数据归属和权限 🚧 部分完成

| 任务 | 状态 | 备注 |
|------|------|------|
| 创建 users 表 | ✅ | 已完成 |
| 实现用户登录/登出 API | ✅ | 已完成 |
| 实现 session 中间件 | ✅ | 已完成 |
| 创建项目表 (projects) | ✅ | 已完成 |
| 创建项目成员表 | ✅ | 已完成 |
| 创建项目配置表 | ✅ | 已完成 |
| 创建审核表 | ⚠️ | 基础表已创建，完整审核流程待完善 |
| 修改 documents 表归属字段 | ⚠️ | 待完善 |
| 实现权限检查器 | ✅ | 基础权限已实现，细粒度权限待完善 |
| 文档 API 权限过滤 | ⚠️ | 待完善 |
| Web UI 支持登录 | ✅ | 已完成 |
| 集成测试 | ⏳ | 待进行 |

### 后续 Phase 未开始

| Phase | 说明 | 状态 |
|-------|------|------|
| Phase 2: 共享服务 | 模型管理、API密钥、系统设置 | ⏳ 未开始 |
| Phase 3: 工具接入 | 工具发现、代理路由、权限控制 | ⏳ 未开始 |
| Phase 4: 功能完善 | 仪表盘、全局搜索、个人中心 | ⏳ 未开始 |
| Phase 5: 迁移与测试 | 数据迁移、集成测试、UAT | ⏳ 未开始 |

---

## 三、UNIFIED_WEB_UI_DESIGN.md 中的未完成任务

### 开发计划阶段

| 阶段 | 任务 | 状态 |
|------|------|------|
| 阶段 1: 基础设施 | 数据库模型、认证系统、基础布局 | 🚧 进行中 |
| 阶段 1: 基础设施 | 用户管理 CRUD、角色权限框架 | ✅ 已完成 |
| 阶段 2: 共享服务 | 模型管理、API密钥、系统设置 | 🚧 进行中 |
| 阶段 2: 共享服务 | 审计日志、通知系统 | ⏳ 未开始 |
| 阶段 3: 工具接入 | 工具发现、代理路由、权限控制 | ⏳ 未开始 |
| 阶段 3: 工具接入 | SkillRouter 接入、Knowledge 接入 | ⏳ 未开始 |
| 阶段 4: 功能完善 | 仪表盘、全局搜索、个人中心 | ⏳ 未开始 |
| 阶段 4: 功能完善 | 主题/外观、性能优化 | ⏳ 未开始 |
| 阶段 5: 迁移与测试 | 数据迁移、集成测试、UAT | ⏳ 未开始 |

---

## 四、工具特定文档中的未完成任务

### 4.1 Knowledge Tool

**文档**: `docs/ai-dev-platform/tools/knowledge-tool/06-development-plan.md`

| 阶段 | 任务 | 状态 |
|------|------|------|
| Phase 1: 核心功能 | 文档上传与解析 | ✅ 已完成 |
| Phase 1: 核心功能 | 文档分块与索引 | ✅ 已完成 |
| Phase 2: 搜索 | 向量搜索 | ⚠️ 基础实现，需要 pgvector 优化 |
| Phase 2: 搜索 | 混合搜索 | ⏳ 未开始 |
| Phase 3: 高级功能 | 知识图谱 | ⏳ 未开始 |
| Phase 3: 高级功能 | 文档版本控制 | ⏳ 未开始 |

### 4.2 Memory Tool

**文档**: `docs/ai-dev-platform/tools/memory-tool/06-development-plan.md`

| 阶段 | 任务 | 状态 |
|------|------|------|
| Phase 1: 基础功能 | 记忆 CRUD | ✅ 已完成 |
| Phase 1: 基础功能 | 上下文包生成 | ✅ 已完成 |
| Phase 2: 高级功能 | 记忆图谱可视化 | ⏳ 未开始 |
| Phase 2: 高级功能 | 向量搜索 | ⚠️ 待优化 |
| Phase 2: 高级功能 | 记忆合并 | ⏳ 未开始 |

### 4.3 其他工具

| 工具 | 未完成任务 | 状态 |
|------|-----------|------|
| Asset Tool | 完整的 Web UI | ⚠️ 基础版已完成，生产级待开发 |
| Quality Tool | 完整的 Web UI | ⚠️ 基础版已完成，生产级待开发 |
| Code Index | Web UI（代码浏览器） | ⏳ 未开始 |
| Evolution Engine | 两级进化系统 | 🚧 计划中 |

---

## 五、系统架构相关未完成任务

### 5.1 上下文优化管线

| 组件 | 任务 | 状态 |
|------|------|------|
| Stage 0 | Agent Instructions 加载 | 🚧 待完善 |
| Stage 1 | Intent Analysis 增强 | 🚧 待完善 |
| Stage 2 | Staged Retrieval | 🚧 待完善 |
| Stage 3 | Skill Matching | 🚧 待完善 |
| Stage 4 | Context Assembly | 🚧 待完善 |

### 5.2 MCP 集成

| 任务 | 状态 |
|------|------|
| aidp_context 重构 | 🚧 待完善 |
| aidp_instructions | 🚧 待开发 |
| Tool Manifest 完整支持 | ⚠️ 部分完成 |

---

## 六、技术债务

### 6.1 代码质量

- [ ] 完善单元测试覆盖（当前 < 30%）
- [ ] 统一错误处理机制
- [ ] 完善日志记录
- [ ] 代码文档化

### 6.2 性能优化

- [ ] 数据库查询优化（N+1 问题）
- [ ] Redis 缓存策略
- [ ] 异步任务队列
- [ ] 静态文件 CDN

### 6.3 安全加固

- [ ] API 速率限制
- [ ] SQL 注入防护检查
- [ ] XSS 防护验证
- [ ] 敏感数据加密

---

## 七、按优先级排序的任务清单

### P0 - 最高优先级（立即开始）

1. **Knowledge Tool Web UI** (3周)
   - 文档预览与分块可视化
   - 高级搜索中心
   - 知识库管理

2. **Memory Tool Web UI** (2周)
   - 记忆图谱可视化
   - 向量搜索优化
   - 上下文包生成器

3. **Agent Instructions 系统** (1周)
   - Stage 0-4 完整管线
   - Intent Analysis 增强

### P1 - 高优先级（下一个阶段）

4. **Evolution Engine 重构** (2周)
   - 两级进化系统
   - 管理员审核工作流

5. **上下文管线优化** (1周)
   - 分段检索优化
   - 组装逻辑完善

6. **MCP 集成完善** (1周)
   - aidp_context 重构
   - aidp_instructions

### P2 - 中优先级（后续排期）

7. Asset Tool Web UI (1周)
8. Quality Tool Web UI (3天)
9. 团队协作功能 (2周)
10. 多租户支持 (2周)

### P3 - 低优先级（长期规划）

11. 高级统计分析
12. 自动化工作流
13. 代码质量改进
14. 性能全面优化

---

## 八、建议的近期工作计划

### Sprint 1-3 (3周): Knowledge Tool Web UI
**目标**: 完成生产级文档管理界面

### Sprint 4-5 (2周): Memory Tool Web UI
**目标**: 完成记忆图谱和上下文包功能

### Sprint 6 (1周): Agent Instructions 系统
**目标**: 完成 Stage 0-4 管线

### Sprint 7-8 (2周): Evolution Engine 重构
**目标**: 完成两级进化系统

---

**文档结束**

*本清单将随开发进度定期更新*
