# 内容晋级审查系统 — 设计文档

## 1. 背景与原则

### 1.1 问题

当前 AIDP 的 scope 体系有三层：`personal` → `project` → `global`。用户只能在 personal 和 project 下创建内容，**不能直接写入 global**。但很多用户创建的规则/技能/知识实际上具有全局复用价值，需要有机制将它们从 personal 提升到 global。

### 1.2 核心原则

| 原则 | 说明 |
|------|------|
| **用户只写 personal/project** | global 必须经过审查管道，禁止直写 |
| **AI 审查，用户决策** | AI 给出分析和建议，最终是否晋升起飞由用户决定 |
| **模型由用户配置** | 用户自行配置审查用的 AI 模型和 API key，系统不绑定任何厂商 |
| **可追溯** | 每条晋级记录保存原始 ID、审查报告、操作日志 |
| **可回退** | 晋级后的 global 内容可撤销，退回 personal |
| **脱敏先行** | 晋级前自动检测并提示需要脱敏的项目特有信息 |

---

## 2. 完整的审查判断维度

### 2.1 AI 审查输出规范

审查模型接收内容 + 元数据，输出结构化 JSON：

```json
{
  "generality_score": 0-100,
  "team_wide_reusable": true/false,
  "recommended_scope": "personal" | "project" | "global",
  "recommended_group": "string or null",
  "contains_project_specifics": [
    {"text": "com.ruoyi", "type": "package_path", "risk": "medium"},
    {"text": "192.168.0.100", "type": "ip_address", "risk": "high"},
    {"text": "jygame_postgres_01", "type": "credential", "risk": "critical"}
  ],
  "redact_suggestions": [
    {"original": "com.ruoyi", "placeholder": "{project_package}"},
    {"original": "192.168.0.100", "placeholder": "{server_ip}"}
  ],
  "improvement_suggestions": [
    "建议增加 abstract 层描述，去除具体实现细节",
    "将具体路径替换为变量占位符"
  ],
  "risk_if_promoted": "low" | "medium" | "high",
  "risk_reason": "string",
  "rationale": "string"
}
```

### 2.2 各维度的判断逻辑

#### generality_score (通用性评分)

| 分值 | 含义 | 示例 |
|------|------|------|
| 0-20 | 高度个人化，仅对个人有用 | 个人工作流快捷键 |
| 21-40 | 项目特有，仅适用于特定项目 | RuoYi 某个具体模块的测试脚本 |
| 41-60 | 部分通用，需脱敏后可复用 | 带有具体 IP 地址的部署文档 |
| 61-80 | 较通用，少量修改可复用 | 编码规范（含项目名） |
| 81-100 | 完全通用，可直接复用 | Git 提交规范、代码审查清单 |

#### contains_project_specifics 检测类型

| type | 说明 | 风险等级 |
|------|------|---------|
| `package_path` | 包路径如 com.ruoyi.xxx | medium |
| `ip_address` | IP 地址 | high |
| `hostname` | 主机名 | medium |
| `credential` | 密码/密钥/Token | critical |
| `project_name` | 项目名称 | low |
| `db_table` | 数据库表名 | medium |
| `api_endpoint` | 具体 API 路径 | low |
| `file_path` | 绝对文件路径 | medium |
| `port_number` | 端口号 | low |
| `email` | 邮箱地址 | medium |

---

## 3. 数据模型扩展

### 3.1 Skill / Rule / KnowledgeDocument 共用扩展字段

在每个模型的 `review_*` 字段组旁添加晋级相关字段：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `promotion_status` | String(20) | `"none"` | none / pending / reviewed / promoted / rejected / rolled_back |
| `promotion_report` | Text | null | JSON: AI 审查报告全文 |
| `promotion_reviewed_at` | DateTime | null | 审查完成时间 |
| `promotion_reviewed_by` | String(100) | null | 审查配置名称（记录用了哪个模型） |
| `promotion_source_id` | String(36) | null | 从 personal 晋升来的原始 ID |
| `promotion_source_scope` | String(20) | null | 来源 scope |
| `promotion_promoted_at` | DateTime | null | 晋升时间 |
| `promoted_by` | String(100) | null | 执行晋升的用户 ID |

### 3.2 PromotionReviewConfig — 审查配置表

```sql
CREATE TABLE IF NOT EXISTS promotion_review_configs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,              -- 配置名称，如 "我的 GPT-4 审查"
    provider VARCHAR(50) NOT NULL,            -- openai / azure / custom / ollama
    model VARCHAR(100) NOT NULL,              -- 模型名
    api_base VARCHAR(500) NOT NULL,           -- API 地址
    api_key_encrypted TEXT NOT NULL,          -- 加密后的 API Key
    system_prompt TEXT,                        -- 自定义 system prompt
    temperature FLOAT DEFAULT 0.3,
    max_tokens INT DEFAULT 2000,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    UNIQUE(user_id, name)
);
```

### 3.3 PromotionLog — 晋级操作日志

```sql
CREATE TABLE IF NOT EXISTS promotion_logs (
    id VARCHAR(36) PRIMARY KEY,
    source_id VARCHAR(36) NOT NULL,           -- 来源内容 ID
    source_scope VARCHAR(20) NOT NULL,         -- personal / project
    target_id VARCHAR(36),                    -- 晋级后的 global ID
    target_scope VARCHAR(20) DEFAULT 'global',
    target_type VARCHAR(20) NOT NULL,          -- skill / rule / knowledge
    action VARCHAR(20) NOT NULL,               -- promoted / rolled_back / rejected
    report TEXT,                               -- 审查报告快照
    config_name VARCHAR(100),                  -- 使用的审查配置名
    triggered_by VARCHAR(100),                 -- 触发方式: auto / manual / scheduled
    user_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
```

---

## 4. 完整晋级流程

### 4.1 状态机

```
                     ┌─ waiting_for_model ──┐
                     │   (等待模型响应)       │
                     └────────┬──────────────┘
                              ▼
none ─→ pending ─→ reviewing ─→ reviewed ─→ promoted ─→ global
                              │
                              ├─→ rejected (退回 personal)
                              │
                              └─→ needs_redaction
                                    │
                                    ▼
                              pending (用户修改后重新提交)
```

### 4.2 流程步骤详述

```
Step 1: 用户创建 personal 规则 "RuoYi 编码规范"
         → scope=personal, promotion_status=none

Step 2: 用户或系统触发晋级审查
         → promotion_status = pending
         → 读取用户配置的活跃模型 (promotion_review_configs WHERE is_active=true)
         → 构建 prompt: 内容 + 元数据 + 审查维度说明

Step 3: 调用 AI 模型
         → POST {api_base}/chat/completions
         → 请求:
           {
             "model": "gpt-4o",
             "messages": [
               {"role": "system", "content": system_prompt},
               {"role": "user", "content": prompt_template.format(content=..., metadata=...)}
             ],
             "response_format": {"type": "json_object"},
             "temperature": 0.3
           }
         → 解析返回的 JSON
         → promotion_status = reviewed
         → 存储 promotion_report

Step 4: 展示审查报告给用户
         ┌──────────────────────────────────────────────┐
         │  📋 晋级审查报告                              │
         │                                              │
         │  通用性评分: 92/100  ★★★★★                   │
         │  建议范围: global                             │
         │  晋升风险: low                                │
         │                                              │
         │  🔍 发现项目特有内容:                          │
         │  · "com.ruoyi" (包路径) → 建议替换为           │
         │    {project_package}                         │
         │  · "192.168.0.100" (IP) → 建议替换为          │
         │    {server_ip}                               │
         │                                              │
         │  💡 改进建议:                                 │
         │  · 建议增加抽象层描述                           │
         │                                              │
         │  [ 接受并晋级 ]  [ 需要修改 ]  [ 拒绝 ]       │
         └──────────────────────────────────────────────┘

Step 5a: 用户选择"接受并晋级"
         → 执行脱敏替换（如果有 redact_suggestions）
         → 创建 global scope 副本
         → source_id = 原 personal ID, source_scope = personal
         → promotion_status = promoted
         → 写入 promotion_logs (action=promoted)

Step 5b: 用户选择"需要修改"
         → 返回编辑器，用户修改后重新提交审查

Step 5c: 用户选择"拒绝"
         → promotion_status = rejected
         → 写入 promotion_logs (action=rejected)
```

### 4.3 脱敏规则

系统根据 redact_suggestions 自动执行文本替换：

```python
def apply_redactions(content: str, suggestions: list[dict]) -> str:
    for s in suggestions:
        content = content.replace(s["original"], s["placeholder"])
    return content
```

脱敏后的内容作为 global 版本存储。如果用户确认时修改了脱敏方案，以用户手动编辑为准。

---

## 5. 审查模型配置

### 5.1 配置管理 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/promotion/configs` | GET | 列出用户的审查配置 |
| `/api/promotion/configs` | POST | 创建配置 |
| `/api/promotion/configs/{id}` | PUT | 更新配置 |
| `/api/promotion/configs/{id}` | DELETE | 删除配置 |
| `/api/promotion/configs/{id}/test` | POST | 测试配置（发一条测试 prompt） |

### 5.2 API Key 安全

- API Key 在存储时用 AES-256-GCM 加密，密钥由 controller 管理
- 前端展示时始终 masked: `sk-****...ab12`
- 测试时解密后调用，不记入日志
- 用户可在配置中引用环境变量如 `${IMPORTER_OPENAI_KEY}`，在 controller 环境变量中设置

### 5.3 配置示例

```json
{
  "name": "我的 GPT-4 审查",
  "provider": "openai",
  "model": "gpt-4o",
  "api_base": "https://api.openai.com/v1",
  "api_key": "sk-xxx...",
  "system_prompt": "你是一个团队知识库审查专家。判断用户内容是否适合晋升为团队全局规则/技能/知识。请严格按 JSON 格式输出。",
  "temperature": 0.3,
  "max_tokens": 2000,
  "is_active": true
}
```

也支持本地模型：

```json
{
  "name": "本地 ollama",
  "provider": "ollama",
  "model": "qwen2.5:14b",
  "api_base": "http://192.168.0.100:11434/v1",
  "api_key": "ollama",
  "system_prompt": "...",
  "is_active": false
}
```

### 5.4 默认 System Prompt

如果用户不自定义，使用内置 prompt：

```
你是一个内容审查专家。你需要判断用户提交的内容是否适合从个人范围提升到团队全局范围。

请严格按 JSON 格式输出以下维度：
1. generality_score: 0-100，内容通用性评分
2. team_wide_reusable: true/false，是否整个团队都能复用
3. recommended_scope: "personal"|"project"|"global"
4. contains_project_specifics: 数组，列出内容中项目特有信息
5. redact_suggestions: 数组，建议替换的文本对
6. risk_if_promoted: "low"|"medium"|"high"
7. rationale: 判断理由

注意：
- 包含密码、IP、密钥等内容必须标记 high risk
- 包含具体包路径、项目名可建议脱敏后晋升
- 仅是个人速记、草稿建议保留 personal
```

---

## 6. 触发机制

### 6.1 创建时自动触发

在 importer-tool 的 `handle_import` 流程中，persist 完成后追加审查步骤：

```python
# 在 persist 成功后
if scope == "personal" and user_has_active_config():
    item.promotion_status = "pending"
    # 异步或同步触发审查
    await trigger_promotion_review(item, user_id)
```

### 6.2 批量审查

```
POST /api/promotion/review/batch
{
  "target_type": "rule",         // 可选: skill / rule / knowledge
  "scope": "personal",
  "config_id": "cfg_xxx",        // 使用的审查配置，不传则用用户 active config
  "dry_run": false               // true=只生成报告不存储
}
```

响应：

```json
{
  "total": 15,
  "reviewed": 15,
  "results": [
    {"id": "rule_001", "generality_score": 92, "recommend": "promote"},
    {"id": "rule_002", "generality_score": 15, "recommend": "keep"},
    ...
  ],
  "summary": {
    "recommend_promote": 3,
    "recommend_keep": 10,
    "recommend_reject": 2
  }
}
```

### 6.3 定时任务

用户通过 `POST /api/promotion/schedule` 配置定时扫描：

```json
{
  "enabled": true,
  "cron": "0 2 * * 0",           // 每周日凌晨2点
  "target_types": ["rule", "skill", "knowledge"],
  "min_generality_score": 60,    // 只审查评分可能 >= 60 的
  "config_id": "cfg_xxx",
  "auto_promote": false          // 是否自动晋级（建议 false，需确认）
}
```

### 6.4 手动触发

- 在 personal 内容的详情页添加"申请晋级"按钮
- 调用 `POST /api/promotion/review/{content_id}`

---

## 7. 回退机制

### 7.1 撤销晋级

用户或管理员可以撤销已晋级的 global 内容：

```
POST /api/promotion/{content_id}/rollback
{
  "reason": "该规则不适用于新项目架构"
}
```

操作：

1. global 内容 soft-delete 或标记 promotion_status = rolled_back
2. 对应的 personal 内容解除关联（可重新编辑）
3. 写入 promotion_logs (action=rolled_back)
4. 通知已使用该 global 规则的项目（可选）

### 7.2 版本覆盖

如果 personal 内容更新后重新晋级：

1. 检查是否已存在关联的 global 记录
2. 存在 → 提示用户"已存在晋升版本，是否覆盖？"
3. 确认后创建 global 新版本，旧版保留在历史中

---

## 8. 与 importer-tool 的集成

### 8.1 新增 Capability

| Capability | 说明 |
|-----------|------|
| `importer.promotion_review` | 对指定内容执行晋级审查 |
| `importer.promotion_apply` | 执行晋升（脱敏+创建 global） |
| `importer.promotion_config` | 管理审查配置 |
| `importer.promotion_batch` | 批量审查 personal 内容 |

### 8.2 对话示例

```
用户: 把这条规则晋升为全局
Agent → importer.promotion_review(content_id="rule_001")
       → 返回审查报告
       → "此规则通用性评分 92，建议晋升 global，
          需要脱敏 com.ruoyi → {project_package}
          是否执行？"
用户: 确认
Agent → importer.promotion_apply(content_id="rule_001", apply_redactions=true)
       → "已晋升为全局规则，ID: rule_global_003，
          原 personal 版本已关联"
```

### 8.3 导入流程中集成

在现有 import 流程中新增步骤：

```
acquire → classify → quality_check → categorize → persist → [NEW] promotion_review
                                                               ↓
                                                         需用户配置模型?
                                                         ├─ 是 → 异步审查
                                                         └─ 否 → 跳过
```

---

## 9. 权限与安全

| 操作 | 权限要求 |
|------|---------|
| 创建审查配置 | 本人 |
| 查看审查报告 | 内容所有者 + 管理员 |
| 执行晋升 | 内容所有者 |
| 撤销晋升 | 内容所有者 + 管理员 |
| 全局回退 | 管理员 |
| 查看晋升日志 | 本人 + 管理员 |

### 安全约束

- API Key 加密存储，解密后仅存在于内存中，调用完即销毁
- 审查请求中不包含用户 API Key 本身
- 审查日志不记录完整 API 请求/响应体（仅存报告摘要）
- 脱敏替换后的内容不可逆（用户需自行备份原版）

---

## 10. 非功能需求

| 指标 | 目标 |
|------|------|
| 单条审查耗时 | < 10s (含模型调用) |
| 批量审查 100 条 | < 5min (可异步) |
| API Key 加密 | AES-256-GCM |
| 审查失败降级 | 不影响原内容，返回错误信息 |
| 数据保留 | 晋升日志永久保留 |

---

## 11. 实施计划

| Phase | 内容 | 工期 |
|-------|------|------|
| P0 | 数据模型扩展 + DB 迁移 | 1d |
| P0 | 审查配置 CRUD API | 1d |
| P0 | AI 模型调用器（通用 provider 抽象） | 2d |
| P1 | 单条晋级审查 + 报告生成 | 2d |
| P1 | 脱敏引擎 + 晋升执行 | 1d |
| P1 | importer-tool capability 集成 | 1d |
| P2 | 批量审查 + 定时任务 | 2d |
| P2 | 回退机制 | 1d |
| P2 | 晋升日志 UI | 1d |
| P3 | 通知系统（晋升"待确认"提醒） | 1d |

**总工期: 13 个工作日**
