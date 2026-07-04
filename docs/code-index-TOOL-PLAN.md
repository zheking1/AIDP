# Code Index Tool 规划文档

为大型微服务项目提供代码结构理解能力

---

## 目录

1. [定位与目标](#1-定位与目标)
2. [核心能力模型](#2-核心能力模型)
3. [架构设计](#3-架构设计)
4. [数据模型](#4-数据模型)
5. [API 设计](#5-api-设计)
6. [与现有工具集成](#6-与现有工具集成)
7. [参考项目](#7-参考项目)
8. [实施计划](#8-实施计划)

---

## 1. 定位与目标

### 1.1 工具定位

**Code Index Tool** 是 AIDP 工具链中的**代码结构理解引擎**，负责：

- 解析代码库结构（AST、依赖、API）
- 构建知识图谱（模块、类、函数、关系）
- 为其他工具提供代码导航能力
- 支持 AI 快速定位和理解代码

### 1.2 目标用户

| 用户 | 场景 | 期望效果 |
|------|------|----------|
| AI Agent | "找到用户认证逻辑" | 秒级定位到具体函数 |
| AI Agent | "修改这个接口会影响什么" | 返回影响范围 |
| AI Agent | "这个模块依赖哪些公共库" | 返回依赖图 |
| 开发者 | 理解新项目架构 | 可视化架构图 |

### 1.3 与其他工具的关系

```
┌─────────────────────────────────────────────────────────┐
│                    Skill Router                          │
│                    (任务路由)                            │
└───────────────┬─────────────────────────────────────────┘
                │
    ┌───────────┼───────────┬───────────┬───────────┐
    ▼           ▼           ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Knowledge│ │ Asset  │ │ Memory │ │Quality │ │ CODE   │
│  Tool  │ │  Tool  │ │  Tool  │ │  Tool  │ │ INDEX  │
│(文档)  │ │(片段)  │ │(经验)  │ │(检查)  │ │(结构)  │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘
                                          │
                                          ▼
                                 ┌─────────────────┐
                                 │  代码结构理解    │
                                 │  - 模块依赖     │
                                 │  - 函数索引     │
                                 │  - API 发现     │
                                 │  - 调用链       │
                                 │  - 架构识别     │
                                 └─────────────────┘
```

---

## 2. 核心能力模型

### 2.1 能力矩阵

| 能力 | 描述 | 输入 | 输出 | 优先级 | 来源 |
|------|------|------|------|--------|------|
| **项目扫描** | 扫描目录结构，识别模块 | 项目路径 | 模块列表 | P0 | 基础 |
| **依赖分析** | 分析模块间依赖关系 | 模块列表 | 依赖图 | P0 | 基础 |
| **函数索引** | 索引所有函数/方法 | 源文件 | 函数列表 | P0 | 基础 |
| **类索引** | 索引所有类/接口 | 源文件 | 类列表 | P0 | 基础 |
| **增量解析** | 只解析变更文件 | 文件变更 | 更新的索引 | P0 | CodeGraph |
| **并发控制** | 多项目并行索引 | 多个项目 | 索引任务队列 | P0 | 新增 |
| **错误恢复** | 索引失败自动重试 | 失败任务 | 恢复的索引 | P0 | 新增 |
| **API 发现** | 发现 REST/Feign/MQ 接口 | 源文件 | API 列表 | P1 | 基础 |
| **调用链追踪** | 追踪函数调用关系 | 函数 | 调用图 | P1 | 基础 |
| **动态调度追踪** | 跟踪回调、接口→实现 | 函数 | 动态调用图 | P1 | CodeGraph |
| **Hybrid LSP** | 语义类型解析 | 源文件 | 类型信息 | P1 | codebase-memory |
| **CLI 接口** | 命令行交互 | 命令 | 结果 | P1 | 新增 |
| **架构识别** | 识别分层/设计模式 | 项目结构 | 架构描述 | P2 | 基础 |
| **影响分析** | 分析代码变更影响范围 | 变更文件 | 影响报告 | P2 | 基础 |
| **智能搜索** | 语义搜索代码 | 查询 | 匹配结果 | P2 | 基础 |
| **死代码检测** | 识别无用代码 | 代码库 | 死代码列表 | P2 | codebase-memory |
| **跨服务链接** | HTTP 路由↔调用点匹配 | 微服务 | 跨服务图 | P2 | codebase-memory |
| **Cypher 查询** | 图查询语言 | Cypher 查询 | 结果 | P2 | codebase-memory |
| **索引压缩** | 压缩存储 | 索引 | 压缩索引 | P2 | codebase-memory |
| **社区检测** | 识别模块边界 | 图谱 | 社区划分 | P3 | codebase-memory |

### 2.2 支持的语言

**Phase 1（核心）：**
- Java（Spring Boot / Spring Cloud）
- Python（FastAPI / Django / Flask）
- TypeScript/JavaScript（Node.js / NestJS）

**Phase 2（扩展）：**
- Go
- Rust
- C#

**Phase 3（全量）：**
- 通过 Tree-sitter 支持 100+ 语言

### 2.3 ruoyi-cloud-plus 场景示例

```
项目: ruoyi-cloud-plus (Spring Cloud 微服务)

扫描结果:
├── 模块数: 25
├── Java 文件: 850+
├── 函数/方法: 12,000+
├── API 端点: 500+
├── 依赖关系: 340+

AI 查询示例:
Q: "用户认证流程"
→ 定位: ruoyi-auth/AuthController.login()
→ 调用链: AuthController → AuthService → RemoteUserService → SysUserMapper
→ 依赖: common-security, common-redis, ruoyi-api

Q: "修改 SysUser 实体影响"
→ 直接影响: SysUserMapper, SysUserServiceImpl, SysUserController
→ 间接影响: SysUserDTO (ruoyi-api), AuthController, TokenService
→ 影响范围: 3 个模块, 15 个文件
```

---

## 3. 架构设计

### 3.1 设计原则（借鉴 CodeGraph）

| 原则 | 描述 | 来源 |
|------|------|------|
| **预构建图谱** | 索引一次，查询即时 | CodeGraph |
| **单一强工具** | 一个 `code.explore` 工具做所有事 | CodeGraph |
| **SQLite + FTS5** | 本地存储，零依赖，并发安全 | CodeGraph |
| **OS 原生监听** | 实时同步，索引永不陈旧 | CodeGraph |
| **语言特定解析** | Tree-sitter AST，语言特定查询 | CodeGraph + codebase-memory |
| **框架感知** | 识别 Spring Boot/FastAPI 等框架模式 | CodeGraph |

### 3.2 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Code Index Tool                         │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    MCP Layer                             │ │
│  │  code.explore (单一强工具，做所有事)                      │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  Service Layer                          │ │
│  │                                                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │ │
│  │  │ Indexer  │  │ Resolver │  │ Watcher  │             │ │
│  │  │ Service  │  │ Service  │  │ Service  │             │ │
│  │  └──────────┘  └──────────┘  └──────────┘             │ │
│  │                                                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │ │
│  │  │ Graph    │  │ Search   │  │ Impact   │             │ │
│  │  │ Service  │  │ Service  │  │ Analyzer │             │ │
│  │  └──────────┘  └──────────┘  └──────────┘             │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  Parser Layer (Tree-sitter)              │ │
│  │                                                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │ │
│  │  │  Java    │  │ Python   │  │  TS/JS   │  ...        │ │
│  │  │  Parser  │  │  Parser  │  │  Parser  │             │ │
│  │  └──────────┘  └──────────┘  └──────────┘             │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  Storage Layer                          │ │
│  │                                                         │ │
│  │  ┌─────────────────────────────────────────────────┐   │ │
│  │  │              SQLite + FTS5                       │   │ │
│  │  │  - 节点表 (nodes)                                │   │ │
│  │  │  - 边表 (edges)                                  │   │ │
│  │  │  - FTS5 全文搜索索引                              │   │ │
│  │  │  - WAL 模式 (并发读不阻塞写)                      │   │ │
│  │  └─────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  Watcher Layer                          │ │
│  │  OS-native file watching (FSEvents/inotify/ReadDir)     │ │
│  │  2s debounce → incremental re-index                     │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 处理流程（借鉴 CodeGraph Pipeline）

```
┌─────────────────────────────────────────────────────────────┐
│                    索引 Pipeline                              │
│                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  Extraction │───▶│  Storage    │───▶│  Resolution │      │
│  │  (提取)     │    │  (存储)     │    │  (解析)     │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│        │                  │                  │               │
│        ▼                  ▼                  ▼               │
│  Tree-sitter AST     SQLite + FTS5     引用→定义            │
│  提取节点+边         写入数据库        import→文件           │
│                                           │                 │
│                                           ▼                 │
│                                    ┌─────────────┐         │
│                                    │  Auto-sync  │         │
│                                    │  (自动同步)  │         │
│                                    └─────────────┘         │
│                                           │                 │
│                                           ▼                 │
│                                    OS-native watcher        │
│                                    2s debounce              │
│                                    incremental re-index     │
└─────────────────────────────────────────────────────────────┘
```

**四个阶段详解：**

| 阶段 | 描述 | 输入 | 输出 |
|------|------|------|------|
| **Extraction** | Tree-sitter 解析 AST，提取节点和边 | 源文件 | 节点列表 + 边列表 |
| **Storage** | 写入 SQLite，建立 FTS5 索引 | 节点/边 | 数据库记录 |
| **Resolution** | 解析引用关系（函数调用→定义，import→文件） | 原始边 | 解析后的边 |
| **Auto-sync** | OS 文件监听，增量更新 | 文件变更 | 更新后的索引 |

### 3.3 部署模式

**模式 A：独立服务（推荐）**
```
http://192.168.0.100:18086/  # Code Index Tool
├── /api/index/*             # 索引管理
├── /api/graph/*             # 图谱查询
├── /api/search/*            # 搜索接口
└── /health                  # 健康检查
```

**模式 B：嵌入现有工具**
- 嵌入 knowledge-tool 或 asset-tool
- 适合轻量级场景

### 3.4 引擎层设计（补充）

#### 3.4.1 增量解析引擎

```
┌─────────────────────────────────────────────────────────────┐
│                    增量解析引擎                               │
│                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │   File      │───▶│   Checksum  │───▶│   Parser    │      │
│  │   Watcher   │    │   Diff      │    │   Queue     │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│        │                  │                  │               │
│        ▼                  ▼                  ▼               │
│  OS-native watcher   文件 MD5 对比      只解析变更文件       │
│  2s debounce         跳过未变更文件     优先级队列排序       │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    并发控制器                             │ │
│  │                                                         │ │
│  │  - 项目级锁：同一项目串行索引                            │ │
│  │  - 文件级锁：并发解析不同文件                            │ │
│  │  - 资源限制：最大并行解析数 (CPU * 0.75)                 │ │
│  │  - 队列管理：优先级队列 + 重试机制                       │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**增量解析流程：**
```python
class IncrementalParser:
    """增量解析器 - 只解析变更文件"""
    
    async def on_file_changed(self, file_path: str, change_type: str):
        """文件变更回调"""
        # 1. 计算文件 checksum
        new_checksum = await self.compute_checksum(file_path)
        old_checksum = await self.get_stored_checksum(file_path)
        
        # 2. 跳过未变更文件
        if new_checksum == old_checksum:
            return
        
        # 3. 根据变更类型处理
        if change_type == "modified":
            await self.reparse_file(file_path)
        elif change_type == "deleted":
            await self.remove_file(file_path)
        elif change_type == "created":
            await self.parse_file(file_path)
        
        # 4. 更新 checksum
        await self.store_checksum(file_path, new_checksum)
        
        # 5. 触发引用解析
        await self.resolve_references(file_path)
```

#### 3.4.2 并发控制器

```python
class ConcurrencyController:
    """并发控制器 - 管理多项目并行索引"""
    
    def __init__(self, max_parallel: int = None):
        self.max_parallel = max_parallel or min(4, os.cpu_count())
        self.semaphore = asyncio.Semaphore(self.max_parallel)
        self.project_locks: Dict[str, asyncio.Lock] = {}
        self.task_queue: asyncio.PriorityQueue = []
    
    async def acquire_project(self, project_id: str):
        """获取项目锁（同一项目串行）"""
        if project_id not in self.project_locks:
            self.project_locks[project_id] = asyncio.Lock()
        await self.project_locks[project_id].acquire()
        await self.semaphore.acquire()  # 全局并发限制
    
    async def release_project(self, project_id: str):
        """释放项目锁"""
        self.project_locks[project_id].release()
        self.semaphore.release()
    
    async def submit_task(self, priority: int, task: Callable):
        """提交索引任务"""
        await self.task_queue.put((priority, time.time(), task))
    
    async def process_queue(self):
        """处理任务队列"""
        while True:
            priority, timestamp, task = await self.task_queue.get()
            async with self.semaphore:
                await task()
```

#### 3.4.3 错误恢复引擎

```python
class ErrorRecoveryEngine:
    """错误恢复引擎 - 索引失败自动重试"""
    
    MAX_RETRIES = 3
    RETRY_DELAY = [1, 5, 15]  # 指数退避
    
    async def safe_parse(self, file_path: str) -> bool:
        """安全解析文件，失败自动重试"""
        for attempt in range(self.MAX_RETRIES):
            try:
                await self.parse_file(file_path)
                return True
            except ParseError as e:
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY[attempt]
                    logger.warning(f"Parse failed, retry in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Parse failed after {self.MAX_RETRIES} attempts: {e}")
                    await self.record_failure(file_path, e)
                    return False
    
    async def record_failure(self, file_path: str, error: Exception):
        """记录失败文件"""
        await db.execute("""
            INSERT INTO index_failures (file_path, error_message, attempt_count)
            VALUES (?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                error_message = excluded.error_message,
                attempt_count = excluded.attempt_count,
                updated_at = CURRENT_TIMESTAMP
        """, (file_path, str(error), self.MAX_RETRIES))
    
    async def retry_failures(self):
        """重试所有失败文件"""
        failures = await db.fetch_all(
            "SELECT file_path FROM index_failures WHERE attempt_count < ?",
            (self.MAX_RETRIES,)
        )
        for failure in failures:
            await self.safe_parse(failure["file_path"])
```

#### 3.4.4 索引状态管理

```sql
-- 索引任务表
CREATE TABLE index_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    task_type TEXT NOT NULL,  -- full/reincremental/cleanup
    status TEXT NOT NULL,     -- pending/running/completed/failed
    progress FLOAT DEFAULT 0,
    total_files INTEGER DEFAULT 0,
    processed_files INTEGER DEFAULT 0,
    failed_files INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 失败文件表
CREATE TABLE index_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    error_message TEXT,
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文件 checksum 表
CREATE TABLE file_checksums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    checksum TEXT NOT NULL,
    last_indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.1 存储方案（借鉴 CodeGraph）

**选择 SQLite + FTS5 而非 PostgreSQL：**

| 维度 | SQLite + FTS5 | PostgreSQL |
|------|---------------|------------|
| **部署** | 零依赖，单文件 | 需要安装服务 |
| **性能** | 本地 I/O，极快 | 网络开销 |
| **并发** | WAL 模式，读不阻塞写 | 需要连接池 |
| **全文搜索** | FTS5 内置 | 需要 pg_trgm |
| **适合场景** | 本地工具，单机 | 服务端，多机 |

**文件结构：**
```
.codeindex/
├── codeindex.db          # 主数据库
├── codeindex.db-wal      # WAL 日志
├── codeindex.db-shm      # 共享内存
└── codeindex.json        # 项目配置
```

### 4.2 核心表结构

```sql
-- 节点表（统一存储所有实体）
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_type TEXT NOT NULL,        -- project/module/class/function/endpoint
    name TEXT NOT NULL,
    qualified_name TEXT,            -- 完整限定名
    file_path TEXT,
    line_start INTEGER,
    line_end INTEGER,
    language TEXT,
    framework TEXT,
    metadata TEXT DEFAULT '{}',     -- JSON 扩展字段
    project_id INTEGER,
    parent_id INTEGER,              -- 父节点（类→模块，函数→类）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 边表（统一存储所有关系）
CREATE TABLE edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES nodes(id),
    target_id INTEGER NOT NULL REFERENCES nodes(id),
    edge_type TEXT NOT NULL,        -- calls/imports/extends/implements/depends_on
    metadata TEXT DEFAULT '{}',     -- JSON 扩展字段
    provenance TEXT DEFAULT 'direct', -- direct/heuristic/inferred
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(source_id, target_id, edge_type)
);

-- 文件表（追踪文件状态）
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    language TEXT,
    size_bytes INTEGER,
    checksum TEXT,
    last_indexed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 项目表
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL,
    language TEXT,
    framework TEXT,
    module_count INTEGER DEFAULT 0,
    file_count INTEGER DEFAULT 0,
    indexed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.3 FTS5 全文搜索索引

```sql
-- 符号搜索索引
CREATE VIRTUAL TABLE nodes_fts USING fts5(
    name,
    qualified_name,
    file_path,
    content=nodes,
    content_rowid=id
);

-- 触发器：保持 FTS 索引同步
CREATE TRIGGER nodes_ai AFTER INSERT ON nodes BEGIN
    INSERT INTO nodes_fts(rowid, name, qualified_name, file_path)
    VALUES (new.id, new.name, new.qualified_name, new.file_path);
END;

CREATE TRIGGER nodes_ad AFTER DELETE ON nodes BEGIN
    INSERT INTO nodes_fts(nodes_fts, rowid, name, qualified_name, file_path)
    VALUES ('delete', old.id, old.name, old.qualified_name, old.file_path);
END;

CREATE TRIGGER nodes_au AFTER UPDATE ON nodes BEGIN
    INSERT INTO nodes_fts(nodes_fts, rowid, name, qualified_name, file_path)
    VALUES ('delete', old.id, old.name, old.qualified_name, old.file_path);
    INSERT INTO nodes_fts(rowid, name, qualified_name, file_path)
    VALUES (new.id, new.name, new.qualified_name, new.file_path);
END;
```

### 4.4 性能索引

```sql
-- 节点查询索引
CREATE INDEX idx_nodes_type ON nodes(node_type);
CREATE INDEX idx_nodes_project ON nodes(project_id);
CREATE INDEX idx_nodes_parent ON nodes(parent_id);
CREATE INDEX idx_nodes_name ON nodes(name);
CREATE INDEX idx_nodes_file ON nodes(file_path);

-- 边查询索引
CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
CREATE INDEX idx_edges_type ON edges(edge_type);

-- 文件查询索引
CREATE INDEX idx_files_language ON files(language);
```

---

## 5. 引擎层详解（补充）

### 5.1 Hybrid LSP 引擎（借鉴 codebase-memory-mcp）

**核心问题：** 单纯 AST 解析无法获取类型信息、接口实现、跨文件引用。Hybrid LSP 结合语法分析和 LSP 语义分析。

```
┌─────────────────────────────────────────────────────────────┐
│                    Hybrid LSP Engine                          │
│                                                               │
│  Phase 1: Syntactic (Tree-sitter)                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  - 快速提取节点、边、符号                                │ │
│  │  - 无需类型解析，纯语法分析                              │ │
│  │  - 支持 100+ 语言                                       │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                          ▼                                    │
│  Phase 2: Semantic (LSP)                                     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  - 类型解析：接口→实现，回调→函数                        │ │
│  │  - 跨文件引用：import→定义，using→声明                   │ │
│  │  - 语义补全：类型推断、泛型解析                           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  Phase 3: Resolution (Post-parse)                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  - 接口→实现映射                                        │ │
│  │  - 回调追踪                                             │ │
│  │  - 跨服务 HTTP 链接                                      │ │
│  │  - 动态调度解析                                          │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**实现细节：**

```python
class HybridLSP:
    """Hybrid LSP 引擎 - 语法+语义双阶段"""
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.treesitter_parser = TreeSitterParser()  # Phase 1
        self.lsp_client = None  # Phase 2 (延迟初始化)
        self.type_cache = {}  # 类型信息缓存
    
    async def parse_file(self, file_path: str) -> ParseResult:
        """双阶段解析"""
        # Phase 1: 快速语法分析
        syntactic_result = await self.treesitter_parser.parse(file_path)
        
        # Phase 2: 语义分析（如果 LSP 可用）
        semantic_result = await self.semantic_analysis(file_path)
        
        # 合并结果
        return self.merge_results(syntactic_result, semantic_result)
    
    async def semantic_analysis(self, file_path: str) -> SemanticResult:
        """LSP 语义分析"""
        if not self.lsp_client:
            self.lsp_client = await self.init_lsp()
        
        # 获取类型信息
        types = await self.lsp_client.get_type_info(file_path)
        
        # 获取接口实现
        implementations = await self.lsp_client.get_implementations(file_path)
        
        # 获取引用
        references = await self.lsp_client.get_references(file_path)
        
        return SemanticResult(
            types=types,
            implementations=implementations,
            references=references
        )
    
    async def init_lsp(self):
        """初始化 LSP 客户端"""
        # 根据项目语言选择 LSP
        if self.is_java_project():
            return JavaLSPClient()
        elif self.is_python_project():
            return PythonLSPClient()
        elif self.is_typescript_project():
            return TypeScriptLSPClient()
```

### 5.2 动态调度追踪（借鉴 CodeGraph）

**核心问题：** Java 的回调、接口实现、动态代理无法通过静态 AST 分析完全解析。

```
┌─────────────────────────────────────────────────────────────┐
│                    Dynamic Dispatch Tracker                  │
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  Interface →    │  │  Callback →     │                   │
│  │  Implementation │  │  Function       │                   │
│  │                 │  │                 │                   │
│  │  @Controller    │  │  @EventListener │                   │
│  │  @Service       │  │  @Async         │                   │
│  │  @Component     │  │  @Scheduled     │                   │
│  └─────────────────┘  └─────────────────┘                   │
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  HTTP Route →   │  │  Event →        │                   │
│  │  Handler        │  │  Listener       │                   │
│  │                 │  │                 │                   │
│  │  @GetMapping    │  │  ApplicationEvent│                  │
│  │  @PostMapping   │  │  @EventListener │                   │
│  └─────────────────┘  └─────────────────┘                   │
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  MQ Consumer →  │  │  Dynamic Proxy  │                   │
│  │  Handler        │  │  → Target       │                   │
│  │                 │  │                 │                   │
│  │  @RabbitListener│  │  JDK Proxy      │                   │
│  │  @KafkaListener │  │  CGLIB Proxy    │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

**实现细节：**

```python
class DynamicDispatchTracker:
    """动态调度追踪器"""
    
    def __init__(self, lsp: HybridLSP):
        self.lsp = lsp
        self.dispatch_map = {}  # 接口→实现映射
    
    async def track_dispatches(self, file_path: str):
        """追踪文件中的动态调度"""
        ast = await self.lsp.parse_file(file_path)
        
        dispatches = []
        
        # 1. 接口→实现
        for interface in ast.interfaces:
            implementations = await self.find_implementations(interface)
            dispatches.append(DispatchEdge(
                source=interface,
                target=implementations,
                dispatch_type="interface_implementation"
            ))
        
        # 2. 回调追踪
        for callback in ast.callbacks:
            target = await self.resolve_callback(callback)
            dispatches.append(DispatchEdge(
                source=callback,
                target=target,
                dispatch_type="callback"
            ))
        
        # 3. HTTP 路由→处理函数
        for route in ast.routes:
            handler = await self.resolve_route_handler(route)
            dispatches.append(DispatchEdge(
                source=route,
                target=handler,
                dispatch_type="http_route"
            ))
        
        return dispatches
    
    async def find_implementations(self, interface: InterfaceNode):
        """查找接口的所有实现"""
        # 使用 LSP 的 implementation 能力
        implementations = await self.lsp.lsp_client.get_implementations(
            interface.file_path,
            interface.line,
            interface.column
        )
        return implementations
    
    async def resolve_callback(self, callback: CallbackNode):
        """解析回调目标"""
        # 1. @EventListener → 查找对应的 ApplicationEvent
        # 2. @Async → 查找异步执行的函数
        # 3. @Scheduled → 查找定时执行的函数
        pass
```

### 5.3 死代码检测（借鉴 codebase-memory-mcp）

```python
class DeadCodeDetector:
    """死代码检测器"""
    
    async def detect(self, project_id: int) -> List[DeadCode]:
        """检测死代码"""
        dead_codes = []
        
        # 1. 未使用的函数/方法
        unused_functions = await self.detect_unused_functions(project_id)
        dead_codes.extend(unused_functions)
        
        # 2. 未使用的类
        unused_classes = await self.detect_unused_classes(project_id)
        dead_codes.extend(unused_classes)
        
        # 3. 未使用的变量
        unused_variables = await self.detect_unused_variables(project_id)
        dead_codes.extend(unused_variables)
        
        # 4. 未使用的 import
        unused_imports = await self.detect_unused_imports(project_id)
        dead_codes.extend(unused_imports)
        
        return dead_codes
    
    async def detect_unused_functions(self, project_id: int):
        """检测未使用的函数"""
        # 查找所有函数
        functions = await db.fetch_all(
            "SELECT * FROM nodes WHERE node_type = 'function' AND project_id = ?",
            (project_id,)
        )
        
        unused = []
        for func in functions:
            # 检查是否有调用边
            has_calls = await db.fetch_one(
                "SELECT COUNT(*) as cnt FROM edges WHERE target_id = ? AND edge_type = 'calls'",
                (func["id"],)
            )
            if has_calls["cnt"] == 0:
                unused.append(DeadCode(
                    node=func,
                    reason="no_callers",
                    confidence=0.8
                ))
        
        return unused
```

### 5.4 跨服务 HTTP 链接（借鉴 codebase-memory-mcp）

```python
class CrossServiceLinker:
    """跨服务 HTTP 链接器"""
    
    async def link_services(self, project_id: int):
        """链接微服务间的 HTTP 调用"""
        # 1. 找到所有 HTTP 端点
        endpoints = await db.fetch_all(
            "SELECT * FROM nodes WHERE node_type = 'endpoint' AND project_id = ?",
            (project_id,)
        )
        
        # 2. 找到所有 HTTP 客户端调用
        clients = await db.fetch_all(
            "SELECT * FROM edges WHERE edge_type = 'http_call' AND source_id IN (SELECT id FROM nodes WHERE project_id = ?)",
            (project_id,)
        )
        
        # 3. 匹配路由
        for client in clients:
            matched_endpoint = self.match_route(client, endpoints)
            if matched_endpoint:
                await db.execute(
                    "INSERT INTO edges (source_id, target_id, edge_type) VALUES (?, ?, 'cross_service_call')",
                    (client["source_id"], matched_endpoint["id"])
                )
    
    def match_route(self, client: Edge, endpoints: List[Node]) -> Optional[Node]:
        """匹配 HTTP 路由"""
        # 解析客户端调用的 URL
        url = client["metadata"].get("url", "")
        
        for endpoint in endpoints:
            # 匹配路径参数
            if self.path_matches(url, endpoint["metadata"].get("path", "")):
                return endpoint
        
        return None
```

### 5.5 索引压缩（借鉴 codebase-memory-mcp）

```python
class IndexCompressor:
    """索引压缩器"""
    
    async def compress(self, project_id: int):
        """压缩索引"""
        # 1. 统计重复节点
        duplicates = await self.find_duplicates(project_id)
        
        # 2. 合并重复节点
        for duplicate_group in duplicates:
            await self.merge_duplicates(duplicate_group)
        
        # 3. 压缩边表
        await self.compress_edges(project_id)
        
        # 4. 清理孤立节点
        await self.cleanup_orphans(project_id)
    
    async def find_duplicates(self, project_id: int):
        """查找重复节点"""
        # 查找相同 qualified_name 的节点
        duplicates = await db.fetch_all("""
            SELECT qualified_name, COUNT(*) as cnt
            FROM nodes
            WHERE project_id = ?
            GROUP BY qualified_name
            HAVING cnt > 1
        """, (project_id,))
        
        return duplicates
    
    async def merge_duplicates(self, duplicate_group):
        """合并重复节点"""
        # 保留最完整的节点，删除其他
        nodes = await db.fetch_all(
            "SELECT * FROM nodes WHERE qualified_name = ?",
            (duplicate_group["qualified_name"],)
        )
        
        # 选择最完整的节点
        best_node = max(nodes, key=lambda n: self.completeness_score(n))
        
        # 合并边
        for node in nodes:
            if node["id"] != best_node["id"]:
                await self.transfer_edges(node["id"], best_node["id"])
                await db.execute("DELETE FROM nodes WHERE id = ?", (node["id"],))
```

### 5.6 社区检测（借鉴 codebase-memory-mcp）

```python
class CommunityDetector:
    """社区检测器 - 使用 Louvain 算法"""
    
    async def detect_communities(self, project_id: int) -> List[Community]:
        """检测模块社区"""
        # 1. 构建图
        graph = await self.build_graph(project_id)
        
        # 2. 运行 Louvain 算法
        communities = self.louvain_detect(graph)
        
        # 3. 保存社区信息
        await self.save_communities(project_id, communities)
        
        return communities
    
    def louvain_detect(self, graph: nx.Graph) -> List[Community]:
        """Louvain 社区检测"""
        import networkx as nx
        from community import community_louvain
        
        # 运行 Louvain 算法
        partition = community_louvain.best_partition(graph)
        
        # 整理社区
        communities = {}
        for node, community_id in partition.items():
            if community_id not in communities:
                communities[community_id] = Community(
                    id=community_id,
                    nodes=[],
                    edges=[]
                )
            communities[community_id].nodes.append(node)
        
        return list(communities.values())
```

---

## 5. API 设计

### 5.1 单一强工具设计（借鉴 CodeGraph）

**核心理念：** 一个 `code.explore` 工具做所有事，Agent 不需要选择工具。

```yaml
# tool.yaml
name: code-index
version: 0.1.0
description: 代码结构理解引擎 - 一个工具探索整个代码库
transport: http

capabilities:
  - name: code.explore
    description: |
      代码库探索的唯一入口。支持：
      - 符号搜索（类/函数/方法）
      - API 端点搜索
      - 调用链追踪
      - 影响分析
      - 模块依赖查询
      - 文件内容获取
    endpoint: POST /api/explore
    permission: code:explore
```

### 5.2 统一探索 API

```
POST /api/explore
```

**请求类型：**

```json
// 1. 符号搜索
{
    "action": "search_symbol",
    "query": "UserAuth",
    "project_id": 1,
    "filters": {
        "node_type": "class",
        "language": "java"
    }
}

// 2. API 搜索
{
    "action": "search_api",
    "query": "/api/user",
    "project_id": 1,
    "filters": {
        "method": "POST"
    }
}

// 3. 调用链追踪
{
    "action": "trace_calls",
    "symbol_id": 1234,
    "direction": "both",
    "max_depth": 5
}

// 4. 影响分析
{
    "action": "analyze_impact",
    "file_path": "src/main/java/.../SysUser.java",
    "change_type": "modify"
}

// 5. 模块依赖
{
    "action": "get_dependencies",
    "module_name": "ruoyi-system",
    "depth": 2
}

// 6. 获取文件内容
{
    "action": "get_file",
    "file_path": "src/main/java/.../SysUser.java",
    "line_range": [1, 100]
}
```

**响应格式：**

```json
{
    "success": true,
    "action": "search_symbol",
    "data": {
        "results": [
            {
                "id": 1234,
                "name": "SysUserService",
                "type": "class",
                "file": "ruoyi-system/src/.../SysUserService.java",
                "line": 25,
                "signature": "public interface SysUserService",
                "snippet": "public interface SysUserService extends IService<SysUser> {...}"
            }
        ],
        "total": 1,
        "query_time_ms": 12
    }
}
```

### 5.3 内部 API（服务间调用）

```
# 索引管理
POST   /api/internal/index/scan      # 扫描项目
GET    /api/internal/index/status    # 索引状态
DELETE /api/internal/index/project   # 删除项目

# 图谱查询（内部使用）
GET    /api/internal/graph/node/{id} # 获取节点
GET    /api/internal/graph/edges     # 获取边
POST   /api/internal/graph/traverse  # 图遍历
```

### 5.5 CLI 接口（补充）

**核心理念：** 开发者需要命令行交互，不依赖 Web UI。

```python
# cli.py - Code Index Tool CLI
import click
import asyncio
from pathlib import Path

@click.group()
@click.option('--project', '-p', default='.', help='Project root path')
@click.pass_context
def cli(ctx, project):
    """Code Index Tool - 代码结构理解引擎"""
    ctx.ensure_object(dict)
    ctx.obj['project'] = Path(project).absolute()

@cli.command()
@click.option('--full', is_flag=True, help='Full re-index')
@click.pass_context
def index(ctx, full):
    """索引项目"""
    project = ctx.obj['project']
    click.echo(f"Indexing project: {project}")
    
    if full:
        asyncio.run(full_index(project))
    else:
        asyncio.run(incremental_index(project))
    
    click.echo("Indexing complete")

@cli.command()
@click.argument('query')
@click.option('--type', '-t', default='symbol', help='Search type: symbol/api/file')
@click.pass_context
def search(ctx, query, type):
    """搜索代码"""
    project = ctx.obj['project']
    results = asyncio.run(search_code(project, query, type))
    
    for result in results:
        click.echo(f"{result['file']}:{result['line']} - {result['name']}")

@cli.command()
@click.argument('symbol')
@click.option('--direction', '-d', default='both', help='Direction: upstream/downstream/both')
@click.option('--depth', default=3, help='Max depth')
@click.pass_context
def trace(ctx, symbol, direction, depth):
    """追踪调用链"""
    project = ctx.obj['project']
    chain = asyncio.run(trace_calls(project, symbol, direction, depth))
    
    print_call_chain(chain)

@cli.command()
@click.argument('file_path')
@click.pass_context
def impact(ctx, file_path):
    """分析变更影响"""
    project = ctx.obj['project']
    impacts = asyncio.run(analyze_impact(project, file_path))
    
    for impact in impacts:
        click.echo(f"{impact['type']}: {impact['description']}")

@cli.command()
@click.pass_context
def stats(ctx):
    """项目统计"""
    project = ctx.obj['project']
    stats = asyncio.run(get_stats(project))
    
    click.echo(f"Modules: {stats['modules']}")
    click.echo(f"Files: {stats['files']}")
    click.echo(f"Functions: {stats['functions']}")
    click.echo(f"Classes: {stats['classes']}")
    click.echo(f"APIs: {stats['apis']}")

@cli.command()
@click.pass_context
def graph(ctx):
    """生成架构图"""
    project = ctx.obj['project']
    graph = asyncio.run(generate_graph(project))
    
    # 输出 Mermaid 格式
    click.echo(graph.to_mermaid())

if __name__ == '__main__':
    cli()
```

**CLI 使用示例：**
```bash
# 索引项目
code-index index --full

# 搜索符号
code-index search "UserAuth" --type symbol

# 追踪调用链
code-index trace "AuthController.login" --direction downstream --depth 4

# 分析变更影响
code-index impact "ruoyi-auth/src/main/java/.../AuthController.java"

# 项目统计
code-index stats

# 生成架构图
code-index graph > architecture.mmd
```

### 5.4 请求/响应示例

**场景：AI 需要理解 ruoyi-cloud-plus 的用户认证流程**

```json
// 步骤 1：搜索认证相关符号
POST /api/explore
{
    "action": "search_symbol",
    "query": "Auth",
    "project_id": 1,
    "filters": {"node_type": "class"}
}

Response:
{
    "results": [
        {"id": 101, "name": "AuthController", "file": "ruoyi-auth/.../AuthController.java"},
        {"id": 102, "name": "AuthService", "file": "ruoyi-auth/.../AuthService.java"},
        {"id": 103, "name": "TokenService", "file": "ruoyi-common/.../TokenService.java"}
    ]
}

// 步骤 2：追踪 AuthController 的调用链
POST /api/explore
{
    "action": "trace_calls",
    "symbol_id": 101,
    "direction": "downstream",
    "max_depth": 4
}

Response:
{
    "root": {"name": "AuthController.login"},
    "chain": [
        {"depth": 1, "calls": ["AuthService.authenticate"]},
        {"depth": 2, "calls": ["RemoteUserService.getUserByUsername"]},
        {"depth": 3, "calls": ["SysUserMapper.selectUserByUsername"]}
    ]
}

// 步骤 3：分析修改 AuthService 的影响
POST /api/explore
{
    "action": "analyze_impact",
    "symbol_id": 102,
    "change_type": "modify"
}

Response:
{
    "direct_impact": [
        {"name": "AuthController", "reason": "calls AuthService"},
        {"name": "TokenService", "reason": "depends on AuthService"}
    ],
    "indirect_impact": [
        {"name": "SysUserController", "reason": "uses TokenService"}
    ],
    "affected_modules": ["ruoyi-auth", "ruoyi-common"],
    "risk_level": "high"
}
```

---

## 6. 与现有工具集成

### 6.1 集成架构

```
用户请求
    │
    ▼
┌─────────────────┐
│  Skill Router   │
│  (路由决策)     │
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┬────────┐
    ▼         ▼        ▼        ▼        ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│Memory │ │Knowle-│ │Asset  │ │ CODE  │ │Skill  │
│ Tool  │ │dge    │ │ Tool  │ │ INDEX │ │Router │
│       │ │Tool   │ │       │ │       │ │       │
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───────┘
    │         │         │         │
    ▼         ▼         ▼         ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│记忆   │ │文档   │ │代码   │ │代码   │
│经验   │ │知识   │ │片段   │ │结构   │
└───────┘ └───────┘ └───────┘ └───────┘
```

### 6.2 工具间协作场景

**场景 1：AI 需要理解代码**
```
1. Skill Router 识别任务类型 → "代码理解"
2. 调用 Code Index → 获取代码结构
3. 调用 Knowledge Tool → 获取相关文档
4. 组合结果 → 返回给 AI
```

**场景 2：AI 需要修改代码**
```
1. Skill Router 识别任务类型 → "代码修改"
2. 调用 Code Index → 定位目标代码
3. 调用 Code Index → 分析影响范围
4. 调用 Asset Tool → 获取代码模板
5. 调用 Quality Tool → 检查修改
6. 调用 Memory Tool → 记录决策
```

**场景 3：AI 需要调试问题**
```
1. Skill Router 识别任务类型 → "调试"
2. 调用 Code Index → 追踪调用链
3. 调用 Memory Tool → 查找类似问题
4. 调用 Knowledge Tool → 查找解决方案
5. 调用 Sandbox Tool → 验证修复
```

### 6.3 MCP 工具定义

```yaml
# tool.yaml
name: code-index
version: 0.1.0
description: 代码结构理解引擎，提供代码导航、依赖分析、影响分析能力
transport: http

capabilities:
  - name: code.index.scan
    description: 扫描并索引项目
    endpoint: POST /api/index/scan
    permission: code:index:scan
    
  - name: code.search.symbol
    description: 搜索代码符号（类/函数/变量）
    endpoint: POST /api/search/symbol
    permission: code:search:symbol
    
  - name: code.search.api
    description: 搜索 API 端点
    endpoint: POST /api/search/api
    permission: code:search:api
    
  - name: code.graph.dependency
    description: 获取模块依赖图
    endpoint: GET /api/graph/dependencies
    permission: code:graph:read
    
  - name: code.analysis.impact
    description: 分析代码变更影响
    endpoint: POST /api/analysis/impact
    permission: code:analysis:impact
    
  - name: code.analysis.trace
    description: 追踪函数调用链
    endpoint: POST /api/analysis/trace
    permission: code:analysis:trace
```

---

## 7. 参考项目

### 7.1 已分析

#### 7.1.1 codebase-memory-mcp

| 维度 | 描述 |
|------|------|
| **核心能力** | Tree-sitter 解析、知识图谱、Cypher 查询 |
| **可借鉴** | 图谱数据模型、图遍历算法、Cypher 查询语言 |
| **适用场景** | 代码结构理解、关系建模 |

#### 7.1.2 agentmemory

| 维度 | 描述 |
|------|------|
| **核心能力** | 自动捕获、分层记忆、隐私过滤 |
| **可借鉴** | 4 层记忆整合、钩子系统、矛盾检测 |
| **适用场景** | 会话记忆、经验积累 |

#### 7.1.3 CodeGraph（重点参考）

| 维度 | 描述 |
|------|------|
| **GitHub** | https://github.com/colbymchenry/codegraph |
| **核心架构** | 预构建知识图谱 + SQLite + FTS5 + MCP |
| **解析方案** | Tree-sitter AST 解析（20+ 语言） |
| **存储方案** | SQLite WAL 模式 + FTS5 全文搜索 |
| **工具设计** | 单一强工具 `codegraph_explore` |
| **同步策略** | OS 原生文件监听 + 2s 防抖 |
| **独特能力** | 跨语言桥接、动态调度追踪、框架感知路由 |

**CodeGraph 关键设计决策：**

| 决策 | 理由 | 我们可借鉴 |
|------|------|-----------|
| **单一强工具** | Agent 不需要选择工具，减少选择错误 | ✅ 采用 |
| **预构建图谱** | 索引一次，查询即时，比 grep 快 10x | ✅ 采用 |
| **SQLite + FTS5** | 本地、零依赖、并发安全 | ✅ 采用 |
| **OS 原生文件监听** | 实时同步，索引永不陈旧 | ✅ 采用 |
| **动态调度追踪** | 跟踪回调、接口→实现，grep 做不到 | ✅ 采用 |
| **框架感知路由** | 17 种框架，URL→handler 映射 | ✅ 采用 |
| **跨语言桥接** | Swift↔ObjC, RN native↔JS | ⚠️ Phase 3 |

**CodeGraph 性能基准：**

| 代码库 | 语言 | 规模 | Tool Calls | 时间 | Tokens |
|--------|------|------|------------|------|--------|
| VS Code | TypeScript | ~10k 文件 | -81% | -11% | -64% |
| Django | Python | ~3k 文件 | -77% | -13% | -60% |
| Excalidraw | TypeScript | ~640 文件 | -40% | -27% | -25% |

**核心启示：**
- 预构建图谱 vs 运行时爬取：索引时间换查询速度
- 单一工具 > 多个窄工具：Agent 导向更重要
- FTS5 足够强大：不需要向量数据库也能高效搜索

### 7.2 其他可能的参考

| 项目 | 能力 | 参考价值 |
|------|------|----------|
| **Sourcegraph** | 代码搜索、导航 | 搜索算法、索引策略 |
| **tree-sitter** | 增量解析 | 解析器架构 |
| **LSP** | 语言服务协议 | 符号解析标准 |
| **Joern** | 代码属性图 | 安全分析、调用链 |
| **Sourcetrail** | 代码可视化 | 架构可视化 |

---

## 8. 实施计划

### 8.1 Phase 1：基础索引 + 引擎层（P0）- 3 周

**目标：** 能扫描 Java 项目并建立基础索引，支持增量解析和并发控制

**任务：**
1. SQLite + FTS5 存储层搭建
2. Tree-sitter Java 解析器集成
3. 项目结构扫描（识别模块）
4. 类/函数/方法提取
5. 单一探索工具 `code.explore` 实现
6. 基础符号搜索 API
7. **增量解析引擎**（文件 checksum + 变更检测）
8. **并发控制器**（项目级锁 + 全局并行限制）
9. **错误恢复引擎**（重试 + 指数退避 + 失败记录）
10. **索引状态管理**（任务表 + 进度追踪）

**技术选型：**
- 存储：SQLite + FTS5（借鉴 CodeGraph）
- 解析：tree-sitter-java
- API：FastAPI + 单一端点
- 并发：asyncio.Semaphore + 项目级锁

**预计工时：** 15-18 天

**验收标准：**
- [ ] 能扫描 ruoyi-cloud-plus
- [ ] 能列出所有模块和文件
- [ ] 能搜索类名/函数名（FTS5）
- [ ] 能获取符号定义和源码
- [ ] 索引时间 < 60s（1000 文件）
- [ ] 增量索引 < 5s（单文件变更）
- [ ] 多项目并行索引不冲突
- [ ] 索引失败自动重试 3 次

### 8.2 Phase 2：图谱能力 + 语义分析（P1）- 3 周

**目标：** 构建知识图谱，支持调用链、影响分析、动态调度追踪

**任务：**
1. 边（关系）提取：calls/imports/extends/implements
2. 引用解析：函数调用→定义，import→文件
3. 调用链追踪算法
4. 影响分析算法
5. 模块依赖图构建
6. **Hybrid LSP 引擎**（语法+语义双阶段）
7. **动态调度追踪**（回调、接口→实现、HTTP 路由→处理函数）
8. **CLI 接口**（click 命令行工具）

**技术选型：**
- 图存储：SQLite 边表（不需要独立图数据库）
- 遍历：递归 CTE SQL
- 解析：语言特定的 Tree-sitter 查询
- LSP：pygls（Python Language Server Protocol）

**预计工时：** 15-18 天

**验收标准：**
- [ ] 能构建调用关系图
- [ ] 能查询函数调用链（上下游）
- [ ] 能分析代码变更影响范围
- [ ] 能显示模块依赖关系
- [ ] 调用链查询 < 100ms
- [ ] 能追踪接口→实现
- [ ] 能解析回调目标
- [ ] CLI 支持搜索/追踪/统计

### 8.3 Phase 3：自动同步 + 高级能力（P2）- 3 周

**目标：** 实时同步 + 框架感知 + Python/TS 支持 + 图查询

**任务：**
1. OS 原生文件监听（FSEvents/inotify）
2. 增量索引（只处理变更文件）
3. 框架感知（Spring Boot 注解、FastAPI 路由）
4. Python 解析器（tree-sitter-python）
5. TypeScript 解析器（tree-sitter-typescript）
6. Web UI
7. **死代码检测**（未使用的函数/类/变量）
8. **跨服务 HTTP 链接**（微服务路由匹配）
9. **Cypher 查询支持**（图查询语言）
10. **索引压缩**（重复节点合并、边表压缩）

**技术选型：**
- 文件监听：watchdog（Python）或 chokidar（Node.js）
- 增量索引：文件 checksum 对比
- 框架：注解/装饰器模式匹配
- 图查询：自定义 Cypher→SQL 转换器

**预计工时：** 15-18 天

**验收标准：**
- [ ] 文件修改后自动更新索引（< 5s）
- [ ] 能识别 Spring Boot @RestController
- [ ] 能识别 FastAPI @app.get
- [ ] 支持 Python 项目索引
- [ ] 支持 TypeScript 项目索引
- [ ] 能检测死代码
- [ ] 能链接跨服务 HTTP 调用
- [ ] 支持 Cypher 查询
- [ ] 索引体积减少 30%+

### 8.4 Phase 4：全量能力（P3）- 2 周

**目标：** 社区检测 + Go/Rust 支持 + 性能优化

**任务：**
1. **社区检测**（Louvain 算法，识别模块边界）
2. Go 解析器（tree-sitter-go）
3. Rust 解析器（tree-sitter-rust）
4. C# 解析器（tree-sitter-c-sharp）
5. 性能优化（批量插入、索引优化）
6. 监控指标（Prometheus）

**预计工时：** 10-12 天

**验收标准：**
- [ ] 能检测社区划分
- [ ] 支持 Go 项目索引
- [ ] 支持 Rust 项目索引
- [ ] 支持 C# 项目索引
- [ ] 10k 文件索引 < 2 分钟
- [ ] 查询延迟 P95 < 200ms

### 8.5 路线图

```
Phase 1 (Week 1-3)           Phase 2 (Week 4-6)           Phase 3 (Week 7-9)           Phase 4 (Week 10-11)
    │                             │                             │                             │
    ├─ SQLite + FTS5              ├─ 调用链追踪                 ├─ 文件监听                   ├─ 社区检测
    ├─ Tree-sitter Java           ├─ 影响分析                   ├─ 增量索引                   ├─ Go/Rust/C#
    ├─ 单一探索工具               ├─ 依赖图                     ├─ 框架感知                   ├─ 性能优化
    ├─ 符号搜索                   ├─ Hybrid LSP                 ├─ Python/TS                  ├─ 监控指标
    ├─ 项目扫描                   ├─ 动态调度追踪               ├─ Web UI                     │
    ├─ 增量解析                   ├─ CLI 接口                   ├─ 死代码检测                 │
    ├─ 并发控制                   │                             ├─ 跨服务链接                 │
    ├─ 错误恢复                   │                             ├─ Cypher 查询                │
    ├─ 索引状态                   │                             ├─ 索引压缩                   │
    │                             │                             │                             │
    └─ 交付                      └─ 交付                       └─ 交付                       └─ 交付
```

---

## 附录

### A. 配置项

```python
# app/config.py

class CodeIndexConfig:
    # 存储配置
    DB_PATH: str = ".codeindex/codeindex.db"
    AUTO_SYNC: bool = True
    SYNC_DEBOUNCE_MS: int = 2000
    
    # 索引配置
    MAX_FILE_SIZE: int = 1024 * 1024  # 1MB
    EXCLUDE_PATTERNS: list = [
        "**/test/**", "**/target/**", "**/node_modules/**",
        "**/.git/**", "**/build/**", "**/dist/**"
    ]
    
    # 解析配置
    SUPPORTED_LANGUAGES: list = ["java", "python", "typescript"]
    FRAMEWORK_DETECT: bool = True
    
    # 图谱配置
    MAX_GRAPH_DEPTH: int = 10
    
    # 搜索配置
    SEARCH_RESULTS_LIMIT: int = 100
    FTS5_ENABLED: bool = True
```

### B. Tree-sitter 查询示例（Java）

```python
# Java 类提取
JAVA_CLASS_QUERY = """
(class_declaration
  name: (identifier) @name
  interfaces: (interface_list)? @interfaces
  body: (class_body) @body) @class
"""

# Java 方法提取
JAVA_METHOD_QUERY = [
    """
    (method_declaration
      name: (identifier) @name
      parameters: (formal_parameters) @params
      type: (type_identifier)? @return_type
      body: (block) @body) @method
    """,
    """
    (constructor_declaration
      name: (identifier) @name
      parameters: (formal_parameters) @params
      body: (constructor_body) @body) @constructor
    """
]

# Java 注解提取
JAVA_ANNOTATION_QUERY = """
(annotation
  name: (identifier) @name
  arguments: (annotation_argument_list)? @args) @annotation
"""

# Spring Boot 路由提取
SPRING_ROUTE_QUERY = """
(annotation
  name: (identifier) @annotation_name
  arguments: (annotation_argument_list
    (element_value_pair
      key: (identifier) @key
      value: (string_literal) @path))) @route
where @annotation_name == "GetMapping" 
   or @annotation_name == "PostMapping"
   or @annotation_name == "RequestMapping"
"""
```

### C. 与 ruoyi-cloud-plus 的集成示例

```bash
# 扫描项目
curl -X POST http://192.168.0.100:18086/api/explore \
  -H "Content-Type: application/json" \
  -d '{
    "action": "search_symbol",
    "query": "SysUser",
    "project_id": 1
  }'

# 追踪调用链
curl -X POST http://192.168.0.100:18086/api/explore \
  -H "Content-Type: application/json" \
  -d '{
    "action": "trace_calls",
    "symbol_id": 1234,
    "direction": "both",
    "max_depth": 5
  }'

# 分析影响
curl -X POST http://192.168.0.100:18086/api/explore \
  -H "Content-Type: application/json" \
  -d '{
    "action": "analyze_impact",
    "file_path": "ruoyi-system/src/main/java/.../SysUser.java",
    "change_type": "modify"
  }'
```

### D. 参考项目对比

| 维度 | CodeGraph | codebase-memory-mcp | 我们的方案 |
|------|-----------|---------------------|-----------|
| **解析器** | Tree-sitter | Tree-sitter | Tree-sitter |
| **存储** | SQLite + FTS5 | SQLite (WAL) | SQLite + FTS5 |
| **工具设计** | 单一强工具 | 14 个工具 | 单一强工具 |
| **同步** | OS 原生监听 | Git 轮询 | OS 原生监听 |
| **查询** | SQL + FTS5 | Cypher | SQL + FTS5 |
| **部署** | Node.js 单文件 | C 二进制 | Python + Docker |
| **独特能力** | 跨语言桥接 | 图查询 | 框架感知 |
