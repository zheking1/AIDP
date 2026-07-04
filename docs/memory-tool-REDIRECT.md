# Memory Tool 改造计划

基于 agentmemory 和 codebase-memory-mcp 的深度分析

---

## 目录

1. [现状分析](#1-现状分析)
2. [agentmemory 亮点深度分析](#2-agentmemory-亮点深度分析)
3. [codebase-memory-mcp 亮点深度分析](#3-codebase-memory-mcp-亮点深度分析)
4. [改造方案总览](#4-改造方案总览)
5. [详细改造计划](#5-详细改造计划)
6. [实施路线图](#6-实施路线图)

---

## 1. 现状分析

### 1.1 当前 memory-tool 能力

| 能力 | 状态 | 问题 |
|------|------|------|
| CRUD 操作 | ✅ 基本可用 | 字段命名不一致（前端 project_id vs 后端 project） |
| 搜索 | ⚠️ 基础 | 仅 ILIKE 子串匹配，无语义搜索，无排序算法 |
| 上下文查询 | ⚠️ 基础 | 仅包装 search，无智能筛选 |
| 分页 | ❌ 缺失 | 无 offset/cursor 支持 |
| 认证 | ❌ 缺失 | 无 auth 中间件 |
| 向量搜索 | ❌ 缺失 | 无 embedding 模型 |
| 全文搜索 | ❌ 缺失 | 无 tsvector/tsquery |
| 记忆分层 | ❌ 缺失 | 所有记忆扁平存储 |
| 自动捕获 | ❌ 缺失 | 完全手动 |
| 隐私过滤 | ❌ 缺失 | 无密钥剥离 |
| 矛盾检测 | ❌ 缺失 | 可能存储冲突记忆 |
| 衰减评分 | ❌ 缺失 | 所有记忆同等权重 |
| 知识图谱 | ❌ 缺失 | 无关系建模 |

### 1.2 关键差距

**与 agentmemory 的差距：**
- 无记忆分层（Working → Episodic → Semantic → Procedural）
- 无自动捕获（需要手动调用 API）
- 无隐私过滤（可能存储敏感信息）
- 无矛盾检测（冲突记忆共存）
- 无衰减机制（旧记忆永远有效）
- 无引用溯源（无法追踪记忆来源）

**与 codebase-memory-mcp 的差距：**
- 无知识图谱（无关系建模）
- 无图查询语言（仅 SQL）
- 无结构化分析（无 AST 解析）

---

## 2. agentmemory 亮点深度分析

### 2.1 四层记忆整合（4-Tier Memory Consolidation）

#### 2.1.1 概念模型

```
┌─────────────────────────────────────────────────────────┐
│                    Working Memory                        │
│  (原始观察：工具调用、用户输入、错误日志)                  │
│  生命周期：会话期间                                      │
│  存储：内存/临时表                                        │
└─────────────────────┬───────────────────────────────────┘
                      │ 压缩/整合
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   Episodic Memory                        │
│  (会话摘要：做了什么、结果如何)                           │
│  生命周期：永久                                          │
│  存储：mem_entry 表                                      │
└─────────────────────┬───────────────────────────────────┘
                      │ 提取/抽象
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   Semantic Memory                        │
│  (事实/知识：项目结构、技术栈、约定)                      │
│  生命周期：永久（可能衰减）                              │
│  存储：mem_entry 表 + 向量索引                           │
└─────────────────────┬───────────────────────────────────┘
                      │ 模式识别
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  Procedural Memory                       │
│  (工作流/决策模式：如何做 X、为什么选择 Y)                │
│  生命周期：永久                                          │
│  存储：mem_entry 表 + 知识图谱                           │
└─────────────────────────────────────────────────────────┘
```

#### 2.1.2 对我们的提升

| 提升维度 | 具体效果 |
|----------|----------|
| **上下文质量** | AI 获得分层记忆，而非扁平列表 |
| **Token 效率** | 按需加载不同层级，减少 60-80% token |
| **检索精度** | 语义搜索 + 分层过滤，R@5 提升至 90%+ |
| **记忆演化** | 支持记忆从短期到长期的自然演变 |

#### 2.1.3 改造细节

**数据模型变更：**

```sql
-- 新增字段
ALTER TABLE mem_entry ADD COLUMN memory_tier VARCHAR(20) DEFAULT 'episodic';
-- 取值：working / episodic / semantic / procedural

ALTER TABLE mem_entry ADD COLUMN parent_id INTEGER REFERENCES mem_entry(id);
-- 用于追踪记忆演化（working → episodic → semantic）

ALTER TABLE mem_entry ADD COLUMN source_type VARCHAR(50);
-- 来源类型：manual / auto / hook / import

ALTER TABLE mem_entry ADD COLUMN source_ref VARCHAR(512);
-- 来源引用：文件路径、commit hash、会话 ID

ALTER TABLE mem_entry ADD COLUMN embedding VECTOR(384);
-- 向量嵌入（pgvector）

ALTER TABLE mem_entry ADD COLUMN access_count INTEGER DEFAULT 0;
-- 访问计数（用于衰减计算）

ALTER TABLE mem_entry ADD COLUMN last_accessed_at TIMESTAMP;
-- 最后访问时间（用于衰减计算）

ALTER TABLE mem_entry ADD COLUMN confidence FLOAT DEFAULT 1.0;
-- 置信度（0-1）
```

**记忆整合服务：**

```python
class MemoryConsolidationService:
    """记忆整合服务 - 将 Working Memory 整合为更高级别"""
    
    async def consolidate_working_to_episodic(self, session_id: str):
        """将Working Memory压缩为Episodic Memory"""
        # 1. 获取会话所有 Working Memory
        # 2. 使用 LLM 压缩为摘要
        # 3. 创建 Episodic Memory
        # 4. 标记 Working Memory 为已整合
        
    async def consolidate_episodic_to_semantic(self, project: str):
        """从多个Episodic Memory提取Semantic Memory"""
        # 1. 聚合相关 Episodic Memory
        # 2. 使用 LLM 提取事实/知识
        # 3. 创建 Semantic Memory
        # 4. 建立 parent_id 关系
        
    async def extract_procedural(self, project: str):
        """从Semantic Memory提取Procedural Memory"""
        # 1. 识别重复出现的模式
        # 2. 使用 LLM 提取工作流/决策
        # 3. 创建 Procedural Memory
        # 4. 建立知识图谱关系
```

---

### 2.2 自动捕获钩子（Auto-Capture Hooks）

#### 2.2.1 概念模型

```
AI Agent 执行流程：
    │
    ├─ SessionStart ──────→ 记录会话开始，加载上下文
    │
    ├─ UserPromptSubmit ──→ 记录用户输入（可选）
    │
    ├─ PreToolUse ────────→ 记录工具调用前状态
    │
    ├─ PostToolUse ───────→ 记录工具调用结果
    │   │
    │   └─ 自动判断是否需要存储为 Memory
    │       - 文件创建/修改 → 存储
    │       - 命令执行成功 → 存储
    │       - 错误发生 → 存储
    │       - 重要决策 → 存储
    │
    ├─ PostToolUseFailure → 记录失败原因
    │
    └─ SessionEnd ────────→ 整合会话记忆
```

#### 2.2.2 对我们的提升

| 提升维度 | 具体效果 |
|----------|----------|
| **自动化** | 零手动操作，记忆自动积累 |
| **完整性** | 不遗漏重要信息 |
| **一致性** | 统一的捕获格式 |
| **实时性** | 即时捕获，不依赖人工 |

#### 2.2.3 改造细节

**钩子系统架构：**

```python
# 新增文件：app/hooks/registry.py

from enum import Enum
from typing import Callable, List
from dataclasses import dataclass

class HookEvent(Enum):
    SESSION_START = "session.start"
    USER_PROMPT = "user.prompt"
    PRE_TOOL_USE = "tool.pre_use"
    POST_TOOL_USE = "tool.post_use"
    TOOL_FAILURE = "tool.failure"
    SESSION_END = "session.end"
    MEMORY_CREATED = "memory.created"
    MEMORY_UPDATED = "memory.updated"

@dataclass
class HookContext:
    event: HookEvent
    session_id: str
    user_id: int
    project: str
    data: dict  # 事件相关数据

class HookRegistry:
    def __init__(self):
        self._hooks: dict[HookEvent, List[Callable]] = {}
    
    def register(self, event: HookEvent, handler: Callable):
        self._hooks.setdefault(event, []).append(handler)
    
    async def trigger(self, ctx: HookContext):
        for handler in self._hooks.get(ctx.event, []):
            await handler(ctx)

# 新增文件：app/hooks/auto_capture.py

class AutoCaptureHook:
    """自动捕获钩子"""
    
    def __init__(self, registry: HookRegistry):
        self.registry = registry
        self._register_handlers()
    
    def _register_handlers(self):
        self.registry.register(HookEvent.POST_TOOL_USE, self.on_tool_use)
        self.registry.register(HookEvent.TOOL_FAILURE, self.on_tool_failure)
        self.registry.register(HookEvent.SESSION_END, this.on_session_end)
    
    async def on_tool_use(self, ctx: HookContext):
        """工具调用后自动捕获"""
        tool_name = ctx.data.get("tool_name")
        result = ctx.data.get("result")
        
        # 判断是否需要存储
        if self._should_capture(tool_name, result):
            await self._create_memory(ctx)
    
    def _should_capture(self, tool_name: str, result: dict) -> bool:
        """判断是否需要捕获"""
        capture_rules = {
            "write": True,           # 文件写入
            "edit": True,            # 文件编辑
            "execute": True,         # 代码执行
            "search": False,         # 搜索不捕获
            "read": False,           # 读取不捕获
        }
        return capture_rules.get(tool_name, False)
```

**API 新增端点：**

```python
# 新增：注册钩子
POST /api/hooks/register
{
    "event": "tool.post_use",
    "handler": "auto_capture",
    "config": {
        "capture_tools": ["write", "edit", "execute"],
        "min_importance": 3
    }
}

# 新增：触发钩子
POST /api/hooks/trigger
{
    "event": "tool.post_use",
    "data": {
        "tool_name": "write",
        "file_path": "/src/main.py",
        "success": true
    }
}
```

---

### 2.3 隐私过滤（Privacy Filtering）

#### 2.3.1 概念模型

```
输入文本
    │
    ▼
┌─────────────────────────────────────┐
│         Privacy Filter              │
│                                     │
│  ┌─────────────┐  ┌─────────────┐  │
│  │ Regex Rules │  │ ML Classifier│  │
│  │ - API Keys  │  │ - PII Detect │  │
│  │ - Secrets   │  │ - Name/Email │  │
│  │ - Tokens    │  │ - Phone/ID   │  │
│  └──────┬──────┘  └──────┬──────┘  │
│         │                │          │
│         └───────┬────────┘          │
│                 ▼                   │
│         Filtered Output             │
└─────────────────────────────────────┘
```

#### 2.3.2 对我们的提升

| 提升维度 | 具体效果 |
|----------|----------|
| **安全性** | 防止敏感信息泄露 |
| **合规性** | 满足数据保护要求 |
| **可信度** | 用户更愿意使用 |

#### 2.3.3 改造细节

**过滤规则引擎：**

```python
# 新增文件：app/services/privacy_filter.py

import re
from typing import List, Tuple

class PrivacyFilter:
    """隐私过滤器"""
    
    # 正则规则
    PATTERNS = {
        "api_key": [
            r'(?i)api[_-]?key[_\s]*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
            r'(?i)bearer[_\s]+[a-zA-Z0-9_\-\.]{20,}',
            r'(?i)authorization[_\s]*[=:]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?',
        ],
        "secret": [
            r'(?i)secret[_\s]*[=:]\s*["\']?([a-zA-Z0-9_\-]{16,})["\']?',
            r'(?i)password[_\s]*[=:]\s*["\']?([^"\'\s]{8,})["\']?',
        ],
        "token": [
            r'(?i)token[_\s]*[=:]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?',
            r'ghp_[a-zA-Z0-9]{36}',  # GitHub token
            r'sk-[a-zA-Z0-9]{20,}',   # OpenAI key
        ],
        "private_key": [
            r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',
        ],
        "database_url": [
            r'(?i)(postgres|mysql|mongodb)://[^\s]+',
        ],
    }
    
    def __init__(self):
        self.compiled = {
            key: [re.compile(p) for p in patterns]
            for key, patterns in self.PATTERNS.items()
        }
    
    def filter(self, text: str) -> Tuple[str, List[dict]]:
        """
        过滤敏感信息
        返回: (过滤后的文本, 发现的敏感信息列表)
        """
        findings = []
        filtered = text
        
        for category, patterns in self.compiled.items():
            for pattern in patterns:
                matches = pattern.finditer(filtered)
                for match in matches:
                    findings.append({
                        "category": category,
                        "start": match.start(),
                        "end": match.end(),
                        "original": match.group(),
                        "redacted": self._redact(match.group(), category),
                    })
                    # 替换为脱敏文本
                    filtered = filtered.replace(
                        match.group(), 
                        findings[-1]["redacted"]
                    )
        
        return filtered, findings
    
    def _redact(self, text: str, category: str) -> str:
        """生成脱敏文本"""
        if len(text) <= 8:
            return "***REDACTED***"
        return f"{text[:4]}***{text[-4:]}"
```

**集成到记忆创建流程：**

```python
# 修改：app/services/memory_service.py

class MemoryService:
    def __init__(self):
        self.privacy_filter = PrivacyFilter()
    
    async def create_memory(self, db, project, title, content, **kwargs):
        # 隐私过滤
        filtered_content, findings = self.privacy_filter.filter(content)
        
        if findings:
            # 记录发现的敏感信息
            logger.warning(f"Privacy filter found {len(findings)} sensitive items")
        
        # 创建记忆（使用过滤后的内容）
        return await self._insert_memory(
            db, project, title, filtered_content, **kwargs
        )
```

---

### 2.4 矛盾检测（Contradiction Detection）

#### 2.4.1 概念模型

```
新记忆输入
    │
    ▼
┌─────────────────────────────────────┐
│       Contradiction Detector        │
│                                     │
│  1. 向量相似度搜索                   │
│     (找到相关记忆)                   │
│                                     │
│  2. 语义比较                         │
│     (判断是否矛盾)                   │
│                                     │
│  3. 决策                             │
│     - 无矛盾 → 正常存储              │
│     - 轻微矛盾 → 标记冲突            │
│     - 严重矛盾 → 替换旧记忆          │
│                                     │
└─────────────────────────────────────┘
```

#### 2.4.2 对我们的提升

| 提升维度 | 具体效果 |
|----------|----------|
| **数据质量** | 避免矛盾信息共存 |
| **一致性** | 保持知识库一致性 |
| **可信度** | 提高 AI 回答准确性 |

#### 2.4.3 改造细节

**矛盾检测服务：**

```python
# 新增文件：app/services/contradiction_detector.py

class ContradictionDetector:
    """矛盾检测器"""
    
    # 矛盾信号词
    CONTRADICTION_SIGNALS = {
        "negation": ["不", "没有", "不能", "禁止", "不要", "no", "not", "never", "don't"],
        "change": ["改为", "变成", "现在", "新方案", "changed to", "now", "new approach"],
        "correction": ["修正", "更正", "之前错了", "corrected", "fixed", "wrong before"],
    }
    
    async def check(self, db, new_memory: dict) -> dict:
        """
        检查新记忆是否与现有记忆矛盾
        返回: {
            "has_contradiction": bool,
            "contradicts": List[dict],  # 矛盾的记忆列表
            "severity": "none" | "minor" | "major",
            "action": "store" | "flag" | "replace"
        }
        """
        # 1. 搜索相关记忆
        related = await self._find_related(db, new_memory)
        
        if not related:
            return {"has_contradiction": False, "action": "store"}
        
        # 2. 语义比较
        contradictions = []
        for mem in related:
            if await self._is_contradicting(new_memory, mem):
                contradictions.append(mem)
        
        if not contradictions:
            return {"has_contradiction": False, "action": "store"}
        
        # 3. 判断严重程度
        severity = self._assess_severity(new_memory, contradictions)
        
        return {
            "has_contradiction": True,
            "contradicts": contradictions,
            "severity": severity,
            "action": "replace" if severity == "major" else "flag"
        }
    
    async def _find_related(self, db, memory: dict) -> list:
        """查找相关记忆"""
        # 使用向量搜索找到语义相似的记忆
        # 阈值：相似度 > 0.7
        
    async def _is_contradicting(self, new: dict, existing: dict) -> bool:
        """判断是否矛盾"""
        # 1. 检查信号词
        # 2. 使用 LLM 判断语义矛盾
        
    def _assess_severity(self, new: dict, contradictions: list) -> str:
        """评估矛盾严重程度"""
        # major: 核心事实冲突（如版本号、技术栈）
        # minor: 表述差异或非核心信息冲突
```

**数据库新增字段：**

```sql
ALTER TABLE mem_entry ADD COLUMN conflict_with INTEGER REFERENCES mem_entry(id);
ALTER TABLE mem_entry ADD COLUMN conflict_status VARCHAR(20) DEFAULT 'none';
-- 取值：none / flagged / resolved

ALTER TABLE mem_entry ADD COLUMN superseded_by INTEGER REFERENCES mem_entry(id);
-- 被新记忆替代时设置
```

---

### 2.5 衰减评分（Decay Scoring）

#### 2.5.1 概念模型

```
记忆重要性 = 基础重要性 × 时间衰减 × 访问频率

时间衰减 = e^(-λ × days_since_access)
访问频率加权 = log(access_count + 1)

示例：
- 新创建的记忆：重要性 = 5 × 1.0 × 1.0 = 5.0
- 30天未访问：重要性 = 5 × 0.74 × 1.0 = 3.7
- 90天未访问：重要性 = 5 × 0.41 × 1.0 = 2.0
- 被频繁访问：重要性 = 5 × 0.74 × 2.3 = 8.5
```

#### 2.5.2 对我们的提升

| 提升维度 | 具体效果 |
|----------|----------|
| **检索质量** | 重要记忆排名更高 |
| **上下文效率** | 优先注入高价值记忆 |
| **记忆演化** | 自然淘汰过时信息 |

#### 2.5.3 改造细节

**衰减计算服务：**

```python
# 新增文件：app/services/decay_service.py

import math
from datetime import datetime, timedelta

class DecayService:
    """衰减计算服务"""
    
    # 衰减常数（可配置）
    LAMBDA = 0.005  # 约 200 天半衰期
    
    def calculate_effective_importance(
        self, 
        base_importance: int,
        created_at: datetime,
        last_accessed_at: datetime,
        access_count: int
    ) -> float:
        """计算有效重要性"""
        
        # 时间衰减
        days_since_access = (datetime.utcnow() - last_accessed_at).days
        time_decay = math.exp(-self.LAMBDA * days_since_access)
        
        # 访问频率加权
        frequency_weight = math.log(access_count + 1)
        
        # 有效重要性
        effective = base_importance * time_decay * frequency_weight
        
        return round(effective, 2)
    
    async def update_all_scores(self, db):
        """批量更新所有记忆的衰减分数"""
        # 执行 SQL 更新
        sql = """
            UPDATE mem_entry 
            SET effective_importance = 
                importance * 
                EXP(-0.005 * EXTRACT(EPOCH FROM (NOW() - last_accessed_at)) / 86400) *
                LN(access_count + 1)
            WHERE last_accessed_at IS NOT NULL
        """
        await db.execute(sql)
```

**数据库新增字段：**

```sql
ALTER TABLE mem_entry ADD COLUMN effective_importance FLOAT;
ALTER TABLE mem_entry ADD COLUMN last_accessed_at TIMESTAMP DEFAULT NOW();
ALTER TABLE mem_entry ADD COLUMN access_count INTEGER DEFAULT 0;

-- 索引
CREATE INDEX idx_mem_effective_importance ON mem_entry(effective_importance DESC);
```

**访问时更新：**

```python
# 修改：app/services/memory_service.py

class MemoryService:
    async def get_memory(self, db, memory_id: int):
        # 更新访问计数和时间
        await db.execute("""
            UPDATE mem_entry 
            SET access_count = access_count + 1,
                last_accessed_at = NOW()
            WHERE id = :id
        """, {"id": memory_id})
        
        # 重新计算有效重要性
        await self.decay_service.update_score(db, memory_id)
        
        # 返回记忆
        return await self._get_by_id(db, memory_id)
```

---

### 2.6 引用溯源（Citation Provenance）

#### 2.6.1 概念模型

```
记忆 A（结论）
    │
    ├── 引用 → 观察 B（原始数据）
    │           └── 来源：文件 /src/main.py L42
    │
    ├── 引用 → 观察 C（执行结果）
    │           └── 来源：命令 `npm test` 输出
    │
    └── 引用 → 观察 D（用户确认）
                └── 来源：会话 #12345
```

#### 2.6.2 对我们的提升

| 提升维度 | 具体效果 |
|----------|----------|
| **可信度** | 可追溯结论来源 |
| **可验证性** | 可验证记忆准确性 |
| **调试能力** | 可定位问题根源 |

#### 2.6.3 改造细节

**引用关系表：**

```sql
CREATE TABLE mem_reference (
    id SERIAL PRIMARY KEY,
    source_memory_id INTEGER NOT NULL REFERENCES mem_entry(id),
    target_memory_id INTEGER NOT NULL REFERENCES mem_entry(id),
    reference_type VARCHAR(50) NOT NULL,
    -- 取值：derived_from / supports / contradicts / supplements
    context TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(source_memory_id, target_memory_id, reference_type)
);
```

**引用服务：**

```python
# 新增文件：app/services/provenance_service.py

class ProvenanceService:
    """引用溯源服务"""
    
    async def add_reference(
        self, db,
        source_id: int,
        target_id: int,
        ref_type: str,
        context: str = None
    ):
        """添加引用关系"""
        await db.execute("""
            INSERT INTO mem_reference 
            (source_memory_id, target_memory_id, reference_type, context)
            VALUES (:source, :target, :type, :context)
            ON CONFLICT (source_memory_id, target_memory_id, reference_type) 
            DO NOTHING
        """, {
            "source": source_id,
            "target": target_id,
            "type": ref_type,
            "context": context
        })
    
    async def get_provenance(self, db, memory_id: int) -> dict:
        """获取记忆的完整溯源链"""
        # 获取所有引用
        refs = await db.fetch_all("""
            SELECT r.*, m.title, m.content
            FROM mem_reference r
            JOIN mem_entry m ON m.id = r.target_memory_id
            WHERE r.source_memory_id = :id
        """, {"id": memory_id})
        
        # 递归构建溯源树
        tree = await self._build_provenance_tree(db, memory_id)
        
        return {
            "memory_id": memory_id,
            "references": refs,
            "provenance_tree": tree
        }
```

---

## 3. codebase-memory-mcp 亮点深度分析

### 3.1 知识图谱（Knowledge Graph）

#### 3.1.1 概念模型

```
节点类型：
- Decision（决策）
- Pattern（模式）
- Bug（问题）
- Workflow（工作流）
- Fact（事实）
- File（文件）
- Function（函数）
- Class（类）
- Module（模块）

关系类型：
- IMPLEMENTS（实现）
- USES（使用）
- DEPENDS_ON（依赖）
- CONTRADICTS（矛盾）
- SUPERSEDES（替代）
- DERIVED_FROM（派生）
```

#### 3.1.2 对我们的提升

| 提升维度 | 具体效果 |
|----------|----------|
| **关系建模** | 理解记忆间的复杂关系 |
| **图查询** | 支持复杂关系查询 |
| **影响分析** | 分析变更影响范围 |

#### 3.1.3 改造细节

**图谱数据模型：**

```sql
-- 节点表
CREATE TABLE mem_node (
    id SERIAL PRIMARY KEY,
    node_type VARCHAR(50) NOT NULL,
    -- 取值：decision/pattern/bug/workflow/fact/file/function/class/module
    memory_id INTEGER REFERENCES mem_entry(id),
    label VARCHAR(512) NOT NULL,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 关系表
CREATE TABLE mem_edge (
    id SERIAL PRIMARY KEY,
    source_node_id INTEGER NOT NULL REFERENCES mem_node(id),
    target_node_id INTEGER NOT NULL REFERENCES mem_node(id),
    edge_type VARCHAR(50) NOT NULL,
    -- 取值：implements/uses/depends_on/contradicts/supersedes/derived_from
    weight FLOAT DEFAULT 1.0,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(source_node_id, target_node_id, edge_type)
);

-- 索引
CREATE INDEX idx_mem_node_type ON mem_node(node_type);
CREATE INDEX idx_mem_edge_source ON mem_edge(source_node_id);
CREATE INDEX idx_mem_edge_target ON mem_edge(target_node_id);
CREATE INDEX idx_mem_edge_type ON mem_edge(edge_type);
```

**图谱服务：**

```python
# 新增文件：app/services/graph_service.py

class GraphService:
    """知识图谱服务"""
    
    async def add_node(
        self, db,
        node_type: str,
        label: str,
        memory_id: int = None,
        properties: dict = None
    ) -> int:
        """添加节点"""
        result = await db.fetch_one("""
            INSERT INTO mem_node (node_type, label, memory_id, properties)
            VALUES (:type, :label, :memory_id, :props)
            RETURNING id
        """, {
            "type": node_type,
            "label": label,
            "memory_id": memory_id,
            "props": json.dumps(properties or {})
        })
        return result["id"]
    
    async def add_edge(
        self, db,
        source_id: int,
        target_id: int,
        edge_type: str,
        weight: float = 1.0,
        properties: dict = None
    ):
        """添加关系"""
        await db.execute("""
            INSERT INTO mem_edge 
            (source_node_id, target_node_id, edge_type, weight, properties)
            VALUES (:source, :target, :type, :weight, :props)
            ON CONFLICT (source_node_id, target_node_id, edge_type)
            DO UPDATE SET weight = :weight, properties = :props
        """, {
            "source": source_id,
            "target": target_id,
            "type": edge_type,
            "weight": weight,
            "props": json.dumps(properties or {})
        })
    
    async def traverse(
        self, db,
        start_node_id: int,
        edge_types: List[str] = None,
        max_depth: int = 3,
        direction: str = "both"  # out/in/both
    ) -> dict:
        """图遍历"""
        # 使用递归 CTE 实现多跳遍历
        sql = """
            WITH RECURSIVE graph_traverse AS (
                SELECT 
                    n.id, n.node_type, n.label, n.memory_id,
                    0 as depth,
                    ARRAY[n.id] as path
                FROM mem_node n
                WHERE n.id = :start_id
                
                UNION ALL
                
                SELECT 
                    n2.id, n2.node_type, n2.label, n2.memory_id,
                    gt.depth + 1,
                    gt.path || n2.id
                FROM mem_edge e
                JOIN mem_node n2 ON (
                    CASE :direction
                        WHEN 'out' THEN e.target_node_id = n2.id
                        WHEN 'in' THEN e.source_node_id = n2.id
                        ELSE (e.source_node_id = n2.id OR e.target_node_id = n2.id)
                    END
                )
                JOIN graph_traverse gt ON (
                    CASE :direction
                        WHEN 'out' THEN e.source_node_id = gt.id
                        WHEN 'in' THEN e.target_node_id = gt.id
                        ELSE (e.source_node_id = gt.id OR e.target_node_id = gt.id)
                    END
                )
                WHERE gt.depth < :max_depth
                AND n2.id != ALL(gt.path)
                AND (:edge_types IS NULL OR e.edge_type = ANY(:edge_types))
            )
            SELECT DISTINCT * FROM graph_traverse
            ORDER BY depth, label
        """
        
        results = await db.fetch_all(sql, {
            "start_id": start_node_id,
            "direction": direction,
            "max_depth": max_depth,
            "edge_types": edge_types
        })
        
        return self._build_graph(results)
    
    async def find_paths(
        self, db,
        source_id: int,
        target_id: int,
        max_depth: int = 5
    ) -> List[List[dict]]:
        """查找两点间路径"""
        sql = """
            WITH RECURSIVE path_finder AS (
                SELECT 
                    ARRAY[n.id] as path,
                    n.id as current_id,
                    0 as depth
                FROM mem_node n
                WHERE n.id = :source_id
                
                UNION ALL
                
                SELECT 
                    pf.path || e.target_node_id,
                    e.target_node_id,
                    pf.depth + 1
                FROM path_finder pf
                JOIN mem_edge e ON e.source_node_id = pf.current_id
                WHERE pf.depth < :max_depth
                AND e.target_node_id != ALL(pf.path)
            )
            SELECT path
            FROM path_finder
            WHERE current_id = :target_id
            ORDER BY array_length(path, 1)
        """
        
        results = await db.fetch_all(sql, {
            "source_id": source_id,
            "target_id": target_id,
            "max_depth": max_depth
        })
        
        return [r["path"] for r in results]
```

---

### 3.2 Cypher 查询语言（简化版）

#### 3.2.1 概念模型

```
用户查询：
    MATCH (d:Decision)-[:USES]->(p:Pattern)
    WHERE d.project = 'my-project'
    RETURN d.title, p.label
    LIMIT 10

解析 → SQL → 执行 → 返回结果
```

#### 3.2.2 对我们的提升

| 提升维度 | 具体效果 |
|----------|----------|
| **查询能力** | 支持复杂图查询 |
| **用户友好** | 类 Neo4j 查询语法 |
| **灵活性** | 支持自定义查询 |

#### 3.2.3 改造细节

**简化查询解析器：**

```python
# 新增文件：app/services/cypher_parser.py

import re
from typing import List, Tuple

class CypherParser:
    """简化版 Cypher 查询解析器"""
    
    # 支持的子句
    CLAUSES = ["MATCH", "WHERE", "RETURN", "ORDER BY", "LIMIT", "SKIP"]
    
    # 支持的操作符
    OPERATORS = ["=", "!=", "<", ">", "<=", ">=", "CONTAINS", "STARTS WITH", "ENDS WITH"]
    
    def parse(self, query: str) -> dict:
        """解析 Cypher 查询"""
        # 1. 提取子句
        clauses = self._extract_clauses(query)
        
        # 2. 解析每个子句
        parsed = {}
        for clause_name, clause_content in clauses.items():
            parsed[clause_name] = self._parse_clause(clause_name, clause_content)
        
        # 3. 转换为 SQL
        sql, params = self._to_sql(parsed)
        
        return {"sql": sql, "params": params}
    
    def _extract_clauses(self, query: str) -> dict:
        """提取子句"""
        clauses = {}
        remaining = query.upper()
        
        for i, clause in enumerate(self.CLAUSES):
            pattern = rf'{clause}\s+(.*?)(?={"|".join(self.CLAUSES[i+1:])}|\Z)'
            match = re.search(pattern, remaining, re.DOTALL | re.IGNORECASE)
            if match:
                clauses[clause] = match.group(1).strip()
        
        return clauses
    
    def _parse_clause(self, clause_name: str, content: str) -> dict:
        """解析单个子句"""
        if clause_name == "MATCH":
            return self._parse_match(content)
        elif clause_name == "WHERE":
            return self._parse_where(content)
        elif clause_name == "RETURN":
            return self._parse_return(content)
        # ... 其他子句
    
    def _to_sql(self, parsed: dict) -> Tuple[str, dict]:
        """转换为 SQL"""
        # 根据解析结果构建 SQL
        # ...
```

**查询 API 端点：**

```python
# 新增：app/api/graph.py

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/graph")

class CypherQueryRequest(BaseModel):
    query: str
    params: dict = {}

@router.post("/query")
async def execute_cypher(request: CypherQueryRequest):
    """执行 Cypher 查询"""
    parser = CypherParser()
    parsed = parser.parse(request.query)
    
    # 执行 SQL
    results = await db.fetch_all(parsed["sql"], parsed["params"])
    
    return {"results": results}
```

---

## 4. 改造方案总览

### 4.1 改造优先级

| 优先级 | 功能 | 来源 | 预期收益 | 实现难度 |
|--------|------|------|----------|----------|
| P0 | 隐私过滤 | agentmemory | 安全性 | ⭐⭐ |
| P0 | 衰减评分 | agentmemory | 检索质量 | ⭐⭐ |
| P1 | 四层记忆整合 | agentmemory | 上下文质量 | ⭐⭐⭐⭐ |
| P1 | 矛盾检测 | agentmemory | 数据一致性 | ⭐⭐⭐ |
| P1 | 引用溯源 | agentmemory | 可信度 | ⭐⭐⭐ |
| P2 | 知识图谱 | codebase-memory | 关系建模 | ⭐⭐⭐⭐ |
| P2 | 自动捕获钩子 | agentmemory | 自动化 | ⭐⭐⭐ |
| P3 | Cypher 查询 | codebase-memory | 查询能力 | ⭐⭐⭐⭐⭐ |

### 4.2 数据模型变更汇总

```sql
-- 记忆表扩展
ALTER TABLE mem_entry ADD COLUMN memory_tier VARCHAR(20) DEFAULT 'episodic';
ALTER TABLE mem_entry ADD COLUMN parent_id INTEGER REFERENCES mem_entry(id);
ALTER TABLE mem_entry ADD COLUMN source_type VARCHAR(50);
ALTER TABLE mem_entry ADD COLUMN source_ref VARCHAR(512);
ALTER TABLE mem_entry ADD COLUMN embedding VECTOR(384);
ALTER TABLE mem_entry ADD COLUMN access_count INTEGER DEFAULT 0;
ALTER TABLE mem_entry ADD COLUMN last_accessed_at TIMESTAMP DEFAULT NOW();
ALTER TABLE mem_entry ADD COLUMN effective_importance FLOAT;
ALTER TABLE mem_entry ADD COLUMN confidence FLOAT DEFAULT 1.0;
ALTER TABLE mem_entry ADD COLUMN conflict_with INTEGER REFERENCES mem_entry(id);
ALTER TABLE mem_entry ADD COLUMN conflict_status VARCHAR(20) DEFAULT 'none';
ALTER TABLE mem_entry ADD COLUMN superseded_by INTEGER REFERENCES mem_entry(id);
ALTER TABLE mem_entry ADD COLUMN privacy_filtered BOOLEAN DEFAULT FALSE;
ALTER TABLE mem_entry ADD COLUMN original_content TEXT;

-- 新增表
CREATE TABLE mem_reference (...);  -- 引用关系
CREATE TABLE mem_node (...);       -- 图谱节点
CREATE TABLE mem_edge (...);       -- 图谱关系
CREATE TABLE mem_hook (...);       -- 钩子配置
CREATE TABLE mem_audit (...);      -- 审计日志
```

### 4.3 新增 API 端点汇总

```
# 隐私过滤
POST /api/privacy/filter          # 测试过滤效果

# 衰减评分
POST /api/decay/update            # 手动触发衰减计算
GET  /api/decay/stats             # 获取衰减统计

# 记忆整合
POST /api/consolidate/working     # 整合 Working Memory
POST /api/consolidate/semantic    # 提取 Semantic Memory
POST /api/consolidate/procedural  # 提取 Procedural Memory

# 矛盾检测
POST /api/conflict/check          # 检查矛盾
POST /api/conflict/resolve        # 解决矛盾

# 引用溯源
POST /api/provenance/add          # 添加引用
GET  /api/provenance/{id}         # 获取溯源链

# 知识图谱
POST /api/graph/node              # 添加节点
POST /api/graph/edge              # 添加关系
POST /api/graph/traverse          # 图遍历
POST /api/graph/query             # Cypher 查询

# 钩子系统
POST /api/hooks/register          # 注册钩子
POST /api/hooks/trigger           # 触发钩子
GET  /api/hooks/list              # 列出钩子
```

---

## 5. 详细改造计划

### 5.1 Phase 1：基础增强（P0）

**目标：** 提升安全性和检索质量

**任务：**
1. 实现隐私过滤器
2. 实现衰减评分
3. 修复前端/后端字段不一致
4. 添加分页支持
5. 添加基础认证

**预计工时：** 3-5 天

**验收标准：**
- [ ] 隐私过滤器可过滤 API Key、密码、Token
- [ ] 衰减评分可配置
- [ ] 所有 API 支持分页
- [ ] 前端字段与后端一致

### 5.2 Phase 2：记忆整合（P1）

**目标：** 实现分层记忆和质量提升

**任务：**
1. 实现四层记忆模型
2. 实现矛盾检测
3. 实现引用溯源
4. 添加向量搜索
5. 实现记忆整合服务

**预计工时：** 7-10 天

**验收标准：**
- [ ] 支持 Working/Episodic/Semantic/Procedural 四层
- [ ] 可检测矛盾记忆
- [ ] 可追溯记忆来源
- [ ] 支持语义搜索

### 5.3 Phase 3：图谱能力（P2-P3）

**目标：** 实现关系建模和高级查询

**任务：**
1. 实现知识图谱数据模型
2. 实现图遍历算法
3. 实现简化版 Cypher 解析器
4. 实现自动捕获钩子
5. 添加图谱可视化（可选）

**预计工时：** 10-15 天

**验收标准：**
- [ ] 支持节点和关系存储
- [ ] 支持多跳图遍历
- [ ] 支持基础 Cypher 查询
- [ ] 钩子系统可配置

---

## 6. 实施路线图

```
Phase 1 (基础增强)          Phase 2 (记忆整合)          Phase 3 (图谱能力)
    │                           │                           │
    ├─ Week 1                   ├─ Week 3-4                 ├─ Week 5-7
    │  - 隐私过滤               │  - 四层模型               │  - 知识图谱
    │  - 衰减评分               │  - 矛盾检测               │  - Cypher
    │  - 分页                   │  - 引用溯源               │  - 钩子系统
    │                           │                           │
    ├─ Week 2                   ├─ Week 5                   ├─ Week 8
    │  - 字段修复               │  - 向量搜索               │  - 集成测试
    │  - 基础认证               │  - 整合服务               │  - 文档
    │                           │                           │
    └─ 交付                    └─ 交付                     └─ 交付
```

---

## 附录：配置项

```python
# app/config.py 新增配置

class MemoryConfig:
    # 隐私过滤
    PRIVACY_FILTER_ENABLED: bool = True
    PRIVACY_PATTERNS: dict = {}  # 自定义模式
    
    # 衰减评分
    DECAY_LAMBDA: float = 0.005  # 衰减常数
    DECAY_UPDATE_INTERVAL: int = 3600  # 更新间隔（秒）
    
    # 记忆整合
    CONSOLIDATION_ENABLED: bool = True
    WORKING_TTL: int = 86400  # Working Memory TTL（秒）
    EPISODIC_COMPRESS_THRESHOLD: int = 10  # 压缩阈值
    
    # 矛盾检测
    CONFLICT_DETECTION_ENABLED: bool = True
    CONFLICT_SIMILARITY_THRESHOLD: float = 0.7
    
    # 知识图谱
    GRAPH_ENABLED: bool = True
    GRAPH_MAX_DEPTH: int = 5
    
    # 向量搜索
    VECTOR_ENABLED: bool = True
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
```
