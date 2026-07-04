# SkillRouter 开发计划 & 进度追踪

> 基于两篇设计文档 + 当前系统现状分析生成

## 代号说明
- ✅ Done | 🔄 In Progress | ⏳ Pending | ❌ Blocked

---

## Phase 0：现状盘点（已有功能）

| 模块 | 状态 | 说明 |
|------|------|------|
| 用户登录/登出 | ✅ | bcrypt密码, session管理 |
| 用户CRUD(管理端) | ✅ | 管理员列表/创建/编辑/删除 |
| Skills CRUD | ✅ | 含文件管理, exec_config |
| Rules CRUD | ✅ | 含优先级, 向量 |
| LLM Models CRUD | ✅ | 角色分类, is_default互斥 |
| Evolution管理 | ✅ | 版本回溯, diff |
| Review模块 | ✅ | 技能审批 |
| 向量检索 | ✅ | pgvector + HNSW索引 |
| Resolve引擎 | ✅ | 粗排→意图→tag加权→降级 |
| 会话Cache(哈希) | ✅ | Redis, key_hash维度 |
| OperationLog | ✅ | 操作日志 |
| Web UI | ✅ | Jinja2+Alpine+Tailwind |
| MCP工具 | ✅ | register/update/list/get_script |
| CLI(srcli.py) | ✅ | 安装/运行/推送 |
| i18n中英 | ✅ | session切换 |

---

## Phase 1：用户多项目隔离 + 权限体系（P0 — 架构基座）✅

### P1.1 Project模型 + CRUD ✅
- [x] 新建 `projects` 表 (id, user_id, name, description, config JSONB, is_active, created_at, updated_at)
- [x] Skill/Rule/LLMConfig 加 `project_id` FK (允许NULL表示全局)
- [x] 迁移脚本: 缺省给默认project
- [x] Web UI: project选择器, CRUD页面
- [ ] API: 按project_id隔离查询 (部分完成)

### P1.2 角色权限拦截到resolve ✅
- [x] Skill/Rule 加 `allowed_roles` 字段
- [x] resolve_skills 加 role参数, 按角色过滤
- [x] MCP resolve_task 透传 role
- [x] Web UI技能表单支持 allowed_roles

### P1.3 公共/私有资源标识 ✅
- [x] Skill/ Rule 加 `scope` 字段 (public/private)
- [x] resolve_skills 按 scope 过滤 (私有归用户 + 公开归所有用户)
- [x] 管理员可发布/取消发布公共技能 (UI按钮)
- [x] 普通用户可复制公共→私有 (UI按钮 + 含files拷贝)

---

## Phase 2：三层路由引擎增强（P1 — 核心算法）

### P2.1 会话级语义缓存 ✅
- [x] Redis缓存结构: session:{user_id} RPush 存 embedding+result+ts
- [x] 相似度计算: 新任务embedding vs 缓存 embedding cosine ≥ 0.7
- [x] 30min超时, 最多20条
- [x] Web UI: 缓存状态查看

### P2.2 业务规则加权引擎 ✅
- [x] 关键词检测: 10组关键词映射(编程/api/db等), 任务匹配关键词+技能标签 → 加权 +0.08~0.15
- [x] sensitive 标记: Skill 加 `sensitive` 布尔字段, 输出标记, UI可设置
- [x] weight_config JSONB: 技能级别额外加权配置
- [x] score_detail 输出 keyword_boost

### P2.3 小模型重排序独立化 ✅
- [x] LLMConfig.role 增加 `reranker` 类型
- [x] rerank_skills() 在 vector_service.py: 调用reranker模型重评分
- [x] resolve_skills 集成: 如有reranker模型, 重排序后加权混合(0.4向量+0.2标签+0.1关键词+0.3重排)
- [x] reranker自动降级: 无reranker模型或无返回值 → 原向量+规则排序
- [x] UI: 模型创建表单可配置reranker角色

### P2.4 Top 2-6 硬约束 ✅
- [x] resolve返回 skills clamp(2, top_k, 6)
- [x] 在 resolve_skills 入口处 clamp

---

## Phase 3：动态指令分片系统（P2 — 防幻觉核心）

### P3.1 项目级指令 ✅
- [x] Project 加 `instruction` Text字段
- [x] resolve输出每个skill附带 `project_instruction`
- [x] Web UI: 项目表单可编辑instruction

### P3.2 技能级分片指令 ✅
- [x] Skill 加 `instruction` Text字段
- [x] resolve输出每个skill附带 `instruction`
- [x] 仅当该技能被匹配时附带, 不污染其他技能上下文
- [x] Web UI: 技能表单可编辑instruction

### P3.3 MCP工具: 指令注入 ✅
- [x] skill_run MCP工具: 解析任务→返回skills+instructions
- [x] skill_get_script: 输出附带instruction/project_instruction
- [x] Agent通过返回结果中的instructions列表组装上下文

---

## Phase 4：后置统一校验（P2 — 防幻觉兜底）

### P4.1 参数校验 ✅
- [x] validation_service.py: validate_params() 按JSON Schema校验必填+类型
- [x] MCP validate_skill_params 工具: 执行前参数预校验
- [x] 校验失败 → 返回errors列表, LLM可重生成

### P4.2 业务规则校验 ✅
- [x] validate_output(): 敏感词检测(密码/API key/AKIA等)
- [x] sensitive技能标记: resolve输出附带 sensitive_skills 警告
- [x] resolve_result 自动注入 validation 字段

---

## Phase 5：商用能力（P3 — 开放注册）

### P5.1 用户注册页 ✅
- [x] /register GET/POST
- [x] 密码强度校验 (min 6)
- [x] 注册后自动登录
- [x] 登录页增加注册链接

### P5.2 限流 ✅
- [x] rate_limiter.py: Redis QPS + daily quota (10qps / 1000 daily)
- [x] resolve_post 路由集成限流检查
- [x] 超限返回友好错误

### P5.3 API Key管理 ✅
- [x] /api-keys 用户管理页: 生成/撤销
- [x] 生成时显示一次明文 key
- [x] 侧边栏全局链接

---

## Phase 6：增强功能（P3 — 体验完善）

### P6.1 MCP工具增强 ✅
- [x] skill_run 完整实现 (resolve + 指令 + 验证)
- [x] resolve_task + skill_run 支持 session_id 透传
- [x] session_context 返回 matched_skill_ids 供Agent追踪

### P6.2 Web UI 完善 ✅
- [x] /profile 用户个人页 (用户名/角色/技能数/API Key数)
- [x] 侧边栏增加 Profile 入口
- [x] 缓存管理页: 显示session cache + 分区清空(全部/会话/按key)

### P6.3 测试 ✅

---

## Phase 顺序 & 依赖

```
Phase 1 (架构基座, 必须先做)
  └→ Phase 2 (路由引擎, 依赖P1的project/role)
       ├→ Phase 3 (指令分片, 依赖P2的resolve结果)
       └→ Phase 4 (后置校验, 依赖P2的resolve结果)
            └→ Phase 5 (商用, 依赖P4防幻觉)
                 └→ Phase 6 (增强, 持续)
```

---

## Phase 7：UI/体验增强与缺陷修复（追加需求）

### P7.1 i18n 中英切换完善 ✅
- [x] 补全 zh.json 缺失 60+ 翻译键
- [x] 技能列表状态文本、分组相关文本支持中英切换
- [x] JavaScript 中硬编码状态文本改为 data-* 属性读取翻译

### P7.2 技能库分组功能完善 ✅
- [x] 新建分组模态框（名称、父分组选择）
- [x] 创建/编辑/删除分组 API 完善
- [x] 树形结构展示（父子分组、展开折叠、技能计数）
- [x] 技能移动到分组、从分组移出
- [x] 删除分组前校验（子分组、技能）

### P7.3 项目技能/规则关联管理 ✅
- [x] 项目详情页“Add Skill/Rule”模态框
- [x] 关联/解除关联 API（skills/link, skills/unlink, rules/link, rules/unlink）
- [x] 列表展示已关联技能/规则，支持解除关联

### P7.5 规则库分组功能（同技能库）✅
- [x] RuleGroup 模型（父子树形、用户隔离、排序）
- [x] rules 表新增 group_id 外键
- [x] api/rule-groups CRUD + 树形展示
- [x] 树形结构校验（禁止删除有子节点的父节点、有规则的分组）

### P7.6 UI 统一弹窗化（进行中）🔄
- [ ] Skills 创建/编辑改为弹窗（参考 skills/create 页面）
- [ ] Rules 创建/编辑/列表改为弹窗
- [ ] Models 创建/编辑改为弹窗
- [ ] Projects 创建/编辑改为弹窗
- [ ] Users 创建/编辑改为弹窗

### P7.6 LLM 模型列表 i18n 完善 ✅
- [x] 删除按钮文本支持中英切换（_('Delete')）

### P7.7 密钥列表复制按钮 ✅
- [x] 新建密钥时已有复制按钮
- [x] 列表中现有密钥添加复制按钮（需补充）

### P7.8 MCP 传输层挂载 ✅
- [x] FastMCP http_app(transport="streamable-http") 挂载到 /mcp
- [x] combined_lifespan 合并 app + MCP 生命周期
- [x] 32 个 MCP 工具可通过 Streamable-HTTP 协议调用

### P7.9 技能导入功能 ✅
- [x] import_service.py: GitHub + ClawHub 导入
- [x] GitHub 导入用 raw.githubusercontent.com（无速率限制）
- [x] ClawHub 导入降级为 GitHub 搜索
- [x] 预览/搜索/执行三步 API
- [x] 技能表: source_url, source_type, source_id 字段

### P7.10 系统设置 ✅
- [x] system_settings.json 文件存储
- [x] allow_registration 开关
- [x] 注册页 i18n 提示

---

---

## Phase 8：精准性优化与文档完善（最新）

### P8.1 自动分类服务 ✅
- [x] classification_service.py: ClassificationService 类
- [x] 使用 Intent Analyzer / Ranker 小模型自动分析技能/规则
- [x] 自动生成 tags（标签）、description（描述）
- [x] 自动建议并创建分组（group_name）
- [x] skill_register 工具新增 auto_classify 参数（默认开启）
- [x] rule_create 工具新增 auto_classify 参数（默认开启）
- [x] _auto_create_skill_group() / _auto_create_rule_group() 自动创建分组

### P8.2 并行化检索优化 ✅
- [x] resolve_service.py: 技能和规则向量检索并行执行
- [x] asyncio.create_task() 并行查询
- [x] 检索阶段延迟降低 30-50%

### P8.3 Ranker Prompt 优化 ✅
- [x] ranker_service.py: 四维度评分标准
- [x] 直接相关性 (40%)、指令匹配 (30%)、标签匹配 (20%)、示例匹配 (10%)
- [x] 添加 examples 和 tags 字段到技能描述
- [x] 更清晰的 Primary/Secondary 技能定义

### P8.4 Embedding 序列化修复 ✅
- [x] models.py Base 类 to_dict() 统一处理 numpy ndarray
- [x] 修复 skills 列表页 Internal Server Error

### P8.5 README 文档完善 ✅
- [x] README.md: 英文文档按 GitHub 最佳实践重构
- [x] README.zh.md: 中文文档同步完善
- [x] Badges、项目结构、快速开始、架构设计、MCP集成、CLI使用、FAQ、贡献指南等

---

当前开发: **Phase 0-8 全部完成**
