# SkillRouter 三层路由架构 — 开发技术文档

## 一、目标架构

```
┌─────────────┐   resolve_task()   ┌──────────────────────────────────────┐
│   Agent层    │ ──────────────────→ │         MCP SkillRouter 层          │
│ (不参与路由)  │                   │                                      │
│              │ ←────────────────── │  1. 会话缓存复用 (语义相似度≥0.7)     │
│              │   技能列表+规则      │  2. Embedding向量粗筛 + 角色权限过滤  │
└─────────────┘                    │  3. 小模型重排序 (自动降级)           │
                                   │  4. 业务规则加权修正                  │
                                   │  5. 写入会话缓存                      │
                                   └──────────────────────────────────────┘
                                              │
                                              ▼
                                   ┌──────────────────────┐
                                   │     主 LLM           │
                                   │ (仅工具选择+内容输出)  │
                                   └──────────────────────┘
                                              │
                                              ▼
                                   ┌──────────────────────┐
                                   │  后置校验层            │
                                   │ (参数校验+业务规则校验) │
                                   └──────────────────────┘
```

### 模块职责（固定不变）

| 模块 | 职责 | 不做什么 |
|------|------|---------|
| **Agent层** | 接收用户消息、调用 `resolve_task()`、组装精简上下文、执行技能、返回结果 | 不做意图分析、技能匹配、规则判断 |
| **MCP SkillRouter** | 向量召回、小模型重排序、业务规则过滤、权限拦截、会话缓存、接口降级 | 不执行技能、不生成内容 |
| **主LLM** | 工具选择、入参生成、内容输出 | 不感知全量技能、不做路由判断 |
| **小模型** | 仅做技能语义重排序 | 不做深度需求拆解、不做最终决策 |
| **后置校验** | 参数合法性、业务规则、审批拦截 | 不改动LLM输出，退回重试 |

---

## 二、完整执行流程（标准化单轮）

### 前置判断：会话缓存复用

```
输入: task + session_id + user_role
1. 根据 session_id 读取历史会话缓存
2. 计算当前 task 与缓存中历史任务的语义相似度 (cosine)
3. 相似度 ≥ 0.7 → 直接复用缓存技能列表，跳过全部匹配流程
4. 相似度 < 0.7 / 超时 30min / 全新会话 → 执行完整流程
```

### 阶段1：Embedding向量粗筛 + 角色权限过滤

```
1. task → generate_embedding() → pgvector cosine 相似度
2. 召回全局 Top N 候选技能 (N = top_k * 3)
3. 角色权限拦截: 根据 user.role 剔除无权限技能
   - 规则表: 权限映射表 (role → allowed_tags / denied_skills)
4. 输出: 候选池 Pool_A (max 20)
```

### 阶段2：小模型重排序

```
输入: 用户原始需求 + Pool_A (Top 20 技能描述)
1. 调用小模型 (LLMConfig.role='ranker') 对技能重新打分排序
2. 降级兜底:
   - 小模型超时/限流/报错 → 跳过重排序 → 使用向量原始分数
3. 复合需求支持: 识别主次双意图 → 保留主技能 + 附属配套技能
4. 输出: 重排序后的 Pool_B
```

### 阶段3：业务规则加权修正

```
1. 预设硬规则执行:
   - 标签权重提升 (如 security → +0.2)
   - 优先级修正 (Rule.priority 加权)
   - 敏感技能标记 (require_approval = True)
2. 专属兜底规则:
   - 检测到编程/代码/报错/框架/接口开发 → 整体提升开发类技能权重
3. 收敛: 输出 Top 2-6 精简技能
4. 写入会话缓存 (session_id → skill_list + intent_vector)
```

### 后置统一规则校验（最终防幻觉兜底）

```
1. 参数校验:
   - 检测技能调用入参格式、必填项、时间范围
   - 异常 → 退回 LLM 重新生成
2. 业务规则校验:
   - 输出内容权限合规
   - 是否需要审批
   - 是否存在编造内容
3. 校验不通过 → 携带本轮动态规则，让 LLM 自动二次修正
```

---

## 三、与当前系统的差距分析

### 已实现 ✅

| 功能 | 位置 | 说明 |
|------|------|------|
| Embedding向量粗筛 | `vector_service.py` | pgvector cosine_distance |
| HNSW索引 | `init_db.py` | skills.embedding + rules.embedding |
| 意图分析 | `vector_service.py` | LLM analyze_intent |
| Degrade降级 | `resolve_service.py` | LLM超时→embedding_only→tag_only |
| Tag权重打分 | `resolve_service.py` | compute_tag_score |
| Cache | `cache_service.py` | SHA256 key_hash 维度 |
| Cycle检测 | `resolve_service.py` | DFS dependencies |
| 结果结构化返回 | `resolve_service.py` | skills[] + rules[] |
| 小模型配置 | `models.py` LLMConfig | role='Intent Analyzer' / 'Embedding' |
| Review审批 | `review_service.py` | pre_review + run_review |
| MCP Tools | `mcp/tools.py` | 45+ 工具 |
| CLI | `cli/srcli.py` | 注册/安装/运行/推送 |
| Web UI | `web/templates/` | 20+ 页面 |
| 会话级语义缓存 | `cache_service.py` | cosine ≥0.7 复用 + 30min TTL |
| 角色权限过滤 | `resolve_service.py` + `SkillPermission` 表 | user.role + SkillPermission |
| 小模型独立重排序 | `ranker_service.py` | LLMConfig.role='Ranker' |
| 小模型自动降级 | `resolve_service.py` | 超时→embedding_only |
| 业务规则加权 | `resolve_service.py` | KEYWORD_WEIGHTS + compute_keyword_boost |
| Top 2-6 硬约束 | `resolve_service.py` | clamp(2, top_k, 6) |
| 后置参数校验 | `validation_service.py` | validate_params() |
| 后置业务规则校验 | `validation_service.py` | validate_resolve_result() |
| 多轮复合意图 | `resolve_service.py` | is_compound + sub_intent |
| **自动分类** | `classification_service.py` | Intent Analyzer 自动生成 tags/description/group |
| **并行检索优化** | `resolve_service.py` | asyncio.create_task 并行查询 |
| **Ranker Prompt 优化** | `ranker_service.py` | 四维度评分标准 |
| **Examples 字段** | `models.py` Skill | examples ARRAY(Text) |

### 缺失/待实现 ❌

| 功能 | 优先级 | 说明 |
|------|--------|------|
| Skill进化反馈循环 | P1 | 追踪技能实际使用率，数据驱动权重调优 |
| Precision@k监控 | P2 | 量化推荐的精准度指标 |
| 多语言支持 | P2 | 日语等更多语言 |
| 技能市场/公共注册表 | P3 | 公开技能分享平台 |
| 技能组合(链式调用) | P3 | 多个技能协同工作 |
| Agent记忆集成 | P3 | 与外部记忆系统对接 |
| 技能实时热重载 | P3 | 无需重启更新技能 |
| CLI规则管理命令 | P2 | srcli rule list/create/update/delete |

---

## 四、数据模型变更

### 4.1 新增 SkillPermission 表 ✅

```python
class SkillPermission(Base):
    __tablename__ = "skill_permissions"
    id: UUID (PK)
    skill_id: UUID (FK → skills.id)
    allowed_roles: ARRAY(String)  # ['admin', 'user', ...]
    denied_roles: ARRAY(String)   # []
    created_at: DateTime
```

### 4.2 Skill 新增 examples 字段 ✅

```python
class Skill(Base):
    # 现有字段...
    examples: ARRAY(Text)  # 使用示例，如 ["将Excel转换为CSV格式"]
```

### 4.2 User.role 规范化

```python
# 现有 role: 'admin' | 'user'
# 新增预定义角色体系
ROLES = ['super_admin', 'admin', 'developer', 'user', 'readonly']
```

### 4.3 LLMConfig 新增 role='ranker'

```python
# 在现有 role 枚举中新增:
LLM_ROLES = ['Intent Analyzer', 'Embedding', 'Review', 'Ranker']
```

### 4.4 会话缓存结构

```redis
# Key: session:{session_id}:resolve_cache
# Value:
{
  "task": "原始任务文本",
  "intent_vector": [float, ...],  # 用于语义相似度对比
  "skills": [...],                 # 匹配的技能列表
  "rules": [...],
  "matched_at": "ISO timestamp",
  "ttl_minutes": 30
}
```

---

## 五、API 变更

### resolve_task MCP Tool 入参扩展 ✅

```python
# 目标:
resolve_task(
    task: str,
    session_id: str = "",       # 会话ID
    user_id: str = "",          # 用户ID
    mode: str = "auto",
    hint_tags: list = None,
)
```

### skill_register 工具扩展 ✅

```python
# 新增参数:
skill_register(
    name: str,
    content: str,
    tags: list = None,
    dependencies: list = None,
    description: str = None,      # 新增: 自动分类生成
    group_name: str = None,       # 新增: 自动创建分组
    auto_classify: bool = True,   # 新增: 启用自动分类
    api_key: str = None,
)
```

### rule_create 工具扩展 ✅

```python
# 新增参数:
rule_create(
    name: str,
    content: str,
    tags: list = None,
    priority: int = 0,
    group_name: str = None,       # 新增: 自动创建分组
    auto_classify: bool = True,   # 新增: 启用自动分类
    api_key: str = None,
)
```

### 返回值扩展 ✅

```python
# 新增字段:
{
  "cache_source": "session|request|none",  # 缓存来源
  "session_skills": [...],                  # 命中会话缓存时的技能列表
  "permission_filtered": int,               # 被权限过滤的技能数
  "ranker_used": bool,                     # 是否使用了小模型重排序
  "rule_boosts_applied": [...],            # 应用的规则加权列表
  "degrade_info": {...},                   # 降级信息
  "latency_ms": int,                       # 处理延迟
}
```

---

## 六、实施阶段

### 阶段 1: 会话缓存 + 权限过滤 (P0) ✅ 已完成

| 步骤 | 文件 | 状态 |
|------|------|------|
| 1.1 新增 SkillPermission 表 + migration | `models.py`, `init_db.py` | ✅ |
| 1.2 修改 resolve_skills 支持 user_role 权限过滤 | `resolve_service.py` | ✅ |
| 1.3 新增 session 缓存读写 (Redis) | `cache_service.py` | ✅ |
| 1.4 session 语义相似度判断 | `resolve_service.py`, `vector_service.py` | ✅ |
| 1.5 更新 resolve_task MCP tool 入参 + 返回值 | `mcp/tools.py` | ✅ |
| 1.6 Web UI 权限管理页面 | `web/routes.py`, templates | ✅ |

### 阶段 2: 小模型重排序 (P1) ✅ 已完成

| 步骤 | 文件 | 状态 |
|------|------|------|
| 2.1 LLMConfig 支持 role='Ranker' | `models.py` | ✅ |
| 2.2 新增 ranker_service.py (调用小模型+降级) | 新文件 | ✅ |
| 2.3 resolve_skills 集成 ranker 阶段 | `resolve_service.py` | ✅ |
| 2.4 Model管理页支持 ranker 角色 | templates | ✅ |
| 2.5 Ranker Prompt 优化 | `ranker_service.py` | ✅ |

### 阶段 3: 业务规则加权 (P1) ✅ 已完成

| 步骤 | 文件 | 状态 |
|------|------|------|
| 3.1 规则引擎: 关键词→标签权重映射 | `resolve_service.py` | ✅ |
| 3.2 Rule.priority 加权到技能评分 | `resolve_service.py` | ✅ |
| 3.3 Web UI 规则配置页面 | templates | ✅ |
| 3.4 并行检索优化 | `resolve_service.py` | ✅ |

### 阶段 4: 后置校验 + 收敛约束 (P2) ✅ 已完成

| 步骤 | 文件 | 状态 |
|------|------|------|
| 4.1 resolve 结果 Top 2-6 硬约束 | `resolve_service.py` | ✅ |
| 4.2 参数校验 service | `validation_service.py` | ✅ |
| 4.3 MCP 返回前校验 hook | `mcp/tools.py` | ✅ |

### 阶段 5: 自动分类 (新增) ✅ 已完成

| 步骤 | 文件 | 状态 |
|------|------|------|
| 5.1 ClassificationService 服务 | `classification_service.py` | ✅ |
| 5.2 skill_register 自动分类 | `mcp/tools.py` | ✅ |
| 5.3 rule_create 自动分类 | `mcp/tools.py` | ✅ |
| 5.4 自动创建分组 | `mcp/tools.py` | ✅ |
| 5.5 Skill.examples 字段 | `models.py` | ✅ |

---

## 七、核心约束（开发中不可违背）

1. **小模型只做重排序** — 禁止让小模型承担复杂需求拆解、代码逻辑分析
2. **每轮 ≤6 个技能** — 严格控制上下文 token 消耗
3. **全局 system prompt 永不堆砌业务规则** — 所有规则由 SkillRouter 动态按需注入
4. **小模型故障必须自动降级** — 不允许整条链路崩溃
5. **会话缓存 30min 自动过期** — 避免数据陈旧

---

## 八、关键接口契约

### resolve_task 标准化返回结构

```python
{
    "skills": [{
        "id": "uuid",
        "name": "str",
        "description": "str",
        "content": "str",
        "exec_config": {...},
        "match_score": 0.0-1.0,
        "is_primary": bool,
        "require_approval": bool,
    }],
    "rules": [...],
    "intent_analysis": {...},
    "meta": {
        "cache_source": "session|request|none",
        "latency_ms": int,
        "resolve_id": "uuid",
        "degrade_info": {...},
    }
}
```

### 后置校验返回格式

```python
{
    "valid": bool,
    "errors": [{"field": "param_name", "message": "str"}],
    "approval_required": bool,
    "dynamic_rules": ["rule1", "rule2"],
}
```
