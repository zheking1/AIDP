# Code Index Tool 开发计划

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术选型](#2-技术选型)
3. [Phase 1: 基础索引 + 引擎层](#3-phase-1-基础索引--引擎层)
4. [Phase 2: 图谱能力 + 语义分析](#4-phase-2-图谱能力--语义分析)
5. [Phase 3: 自动同步 + 高级能力](#5-phase-3-自动同步--高级能力)
6. [Phase 4: 全量能力](#6-phase-4-全量能力)
7. [风险评估](#7-风险评估)
8. [资源需求](#8-资源需求)

---

## 1. 项目概述

### 1.1 项目范围

为 AIDP 系统构建 Code Index Tool，提供代码结构理解能力。

### 1.2 项目目标

- 支持 AI Agent 快速定位和理解代码
- 提供调用链追踪和影响分析能力
- 支持增量索引和实时同步
- 支持多语言和多框架

### 1.3 项目周期

- Phase 1: 3 周（基础索引 + 引擎层）
- Phase 2: 3 周（图谱能力 + 语义分析）
- Phase 3: 3 周（自动同步 + 高级能力）
- Phase 4: 2 周（全量能力）
- **总计: 11 周**

---

## 2. 技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| **语言** | Python 3.13 | 统一技术栈 |
| **Web 框架** | FastAPI | 异步、高性能 |
| **存储** | SQLite + FTS5 | 零依赖、本地性能好 |
| **解析器** | Tree-sitter | 多语言支持、增量解析 |
| **LSP** | pygls | Python LSP 实现 |
| **图谱** | NetworkX | 纯 Python |
| **CLI** | click | 成熟的 CLI 框架 |
| **文件监听** | watchdog | 跨平台 |

---

## 3. Phase 1: 基础索引 + 引擎层（P0）

**周期**: 3 周（15-18 天）

### 3.1 目标

能扫描 Java 项目并建立基础索引，支持增量解析和并发控制。

### 3.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 项目结构搭建 | 1 天 | 无 |
| SQLite + FTS5 存储层 | 2 天 | 无 |
| Tree-sitter Java 解析器集成 | 3 天 | 无 |
| 项目结构扫描（识别模块） | 2 天 | 解析器 |
| 类/函数/方法提取 | 2 天 | 解析器 |
| 单一探索工具 `code.explore` 实现 | 2 天 | 存储层 |
| 基础符号搜索 API | 1 天 | 存储层 |
| 增量解析引擎 | 2 天 | 存储层 |
| 并发控制器 | 1 天 | 增量解析 |
| 错误恢复引擎 | 1 天 | 并发控制 |
| 索引状态管理 | 1 天 | 错误恢复 |
| 测试 | 2 天 | 全部 |

### 3.3 技术实现

**存储层**:
```python
# app/db/models.py
class Node(Base):
    __tablename__ = "nodes"
    
    id = Column(Integer, primary_key=True)
    node_type = Column(String, nullable=False)  # project/module/class/function
    name = Column(String, nullable=False)
    qualified_name = Column(String)
    file_path = Column(String)
    line_start = Column(Integer)
    line_end = Column(Integer)
    language = Column(String)
    framework = Column(String)
    metadata = Column(JSON, default={})
    project_id = Column(Integer, ForeignKey("projects.id"))
    parent_id = Column(Integer, ForeignKey("nodes.id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Edge(Base):
    __tablename__ = "edges"
    
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
    edge_type = Column(String, nullable=False)  # calls/imports/extends/implements
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now())
```

**增量解析引擎**:
```python
# app/services/incremental_parser.py
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

**并发控制器**:
```python
# app/services/concurrency_controller.py
class ConcurrencyController:
    """并发控制器 - 管理多项目并行索引"""
    
    def __init__(self, max_parallel: int = None):
        self.max_parallel = max_parallel or min(4, os.cpu_count())
        self.semaphore = asyncio.Semaphore(self.max_parallel)
        self.project_locks: Dict[str, asyncio.Lock] = {}
    
    async def acquire_project(self, project_id: str):
        """获取项目锁（同一项目串行）"""
        if project_id not in self.project_locks:
            self.project_locks[project_id] = asyncio.Lock()
        await self.project_locks[project_id].acquire()
        await self.semaphore.acquire()
    
    async def release_project(self, project_id: str):
        """释放项目锁"""
        self.project_locks[project_id].release()
        self.semaphore.release()
```

**错误恢复引擎**:
```python
# app/services/error_recovery.py
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
```

### 3.4 验收标准

- [ ] 能扫描 ruoyi-cloud-plus
- [ ] 能列出所有模块和文件
- [ ] 能搜索类名/函数名（FTS5）
- [ ] 能获取符号定义和源码
- [ ] 索引时间 < 60s（1000 文件）
- [ ] 增量索引 < 5s（单文件变更）
- [ ] 多项目并行索引不冲突
- [ ] 索引失败自动重试 3 次

---

## 4. Phase 2: 图谱能力 + 语义分析（P1）

**周期**: 3 周（15-18 天）

### 4.1 目标

构建知识图谱，支持调用链、影响分析、动态调度追踪。

### 4.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 边（关系）提取：calls/imports/extends/implements | 2 天 | Phase 1 |
| 引用解析：函数调用→定义，import→文件 | 2 天 | 边提取 |
| 调用链追踪算法 | 2 天 | 引用解析 |
| 影响分析算法 | 2 天 | 调用链 |
| 模块依赖图构建 | 2 天 | 影响分析 |
| Hybrid LSP 引擎 | 3 天 | Phase 1 |
| 动态调度追踪 | 2 天 | Hybrid LSP |
| CLI 接口 | 2 天 | Phase 1 |
| 测试 | 2 天 | 全部 |

### 4.3 技术实现

**Hybrid LSP 引擎**:
```python
# app/services/hybrid_lsp.py
class HybridLSP:
    """Hybrid LSP 引擎 - 语法+语义双阶段"""
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.treesitter_parser = TreeSitterParser()  # Phase 1
        self.lsp_client = None  # Phase 2 (延迟初始化)
        self.type_cache = {}
    
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
        
        types = await self.lsp_client.get_type_info(file_path)
        implementations = await self.lsp_client.get_implementations(file_path)
        references = await self.lsp_client.get_references(file_path)
        
        return SemanticResult(
            types=types,
            implementations=implementations,
            references=references
        )
```

**动态调度追踪**:
```python
# app/services/dispatch_tracker.py
class DispatchTracker:
    """动态调度追踪器"""
    
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
```

**CLI 接口**:
```python
# cli.py
import click
import asyncio

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
    if full:
        asyncio.run(full_index(project))
    else:
        asyncio.run(incremental_index(project))

@cli.command()
@click.argument('query')
@click.option('--type', '-t', default='symbol', help='Search type')
@click.pass_context
def search(ctx, query, type):
    """搜索代码"""
    project = ctx.obj['project']
    results = asyncio.run(search_code(project, query, type))
    for result in results:
        click.echo(f"{result['file']}:{result['line']} - {result['name']}")
```

### 4.4 验收标准

- [ ] 能构建调用关系图
- [ ] 能查询函数调用链（上下游）
- [ ] 能分析代码变更影响范围
- [ ] 能显示模块依赖关系
- [ ] 调用链查询 < 100ms
- [ ] 能追踪接口→实现
- [ ] 能解析回调目标
- [ ] CLI 支持搜索/追踪/统计

---

## 5. Phase 3: 自动同步 + 高级能力（P2）

**周期**: 3 周（15-18 天）

### 5.1 目标

实时同步 + 框架感知 + Python/TS 支持 + 图查询。

### 5.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| OS 原生文件监听（watchdog） | 2 天 | Phase 1 |
| 增量索引（只处理变更文件） | 2 天 | 文件监听 |
| 框架感知（Spring Boot、FastAPI） | 3 天 | Phase 2 |
| Python 解析器（tree-sitter-python） | 2 天 | Phase 1 |
| TypeScript 解析器（tree-sitter-typescript） | 2 天 | Phase 1 |
| Web UI | 3 天 | Phase 2 |
| 死代码检测 | 2 天 | Phase 2 |
| 跨服务 HTTP 链接 | 2 天 | Phase 2 |
| Cypher 查询支持 | 3 天 | Phase 2 |
| 索引压缩 | 2 天 | Phase 2 |
| 测试 | 2 天 | 全部 |

### 5.3 技术实现

**框架感知**:
```python
# app/services/framework_detector.py
class FrameworkDetector:
    """框架检测器"""
    
    JAVA_FRAMEWORKS = {
        "spring_boot": {
            "annotations": ["@RestController", "@Controller", "@Service", "@Repository"],
            "imports": ["org.springframework"],
            "patterns": ["*Controller.java", "*Service.java", "*Repository.java"]
        },
        "spring_cloud": {
            "annotations": ["@FeignClient", "@EnableDiscoveryClient"],
            "imports": ["org.springframework.cloud"]
        }
    }
    
    PYTHON_FRAMEWORKS = {
        "fastapi": {
            "decorators": ["@app.get", "@app.post", "@app.put", "@app.delete"],
            "imports": ["fastapi"]
        },
        "django": {
            "decorators": ["@login_required", "@csrf_exempt"],
            "imports": ["django"]
        }
    }
    
    async def detect_framework(self, project_path: str) -> List[str]:
        """检测项目框架"""
        frameworks = []
        
        # 检查 Java
        if await self.has_java(project_path):
            java_frameworks = await self.detect_java_framework(project_path)
            frameworks.extend(java_frameworks)
        
        # 检查 Python
        if await self.has_python(project_path):
            python_frameworks = await self.detect_python_framework(project_path)
            frameworks.extend(python_frameworks)
        
        return frameworks
```

**死代码检测**:
```python
# app/services/dead_code_detector.py
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
```

### 5.4 验收标准

- [ ] 文件修改后自动更新索引（< 5s）
- [ ] 能识别 Spring Boot @RestController
- [ ] 能识别 FastAPI @app.get
- [ ] 支持 Python 项目索引
- [ ] 支持 TypeScript 项目索引
- [ ] 能检测死代码
- [ ] 能链接跨服务 HTTP 调用
- [ ] 支持 Cypher 查询
- [ ] 索引体积减少 30%+

---

## 6. Phase 4: 全量能力（P3）

**周期**: 2 周（10-12 天）

### 6.1 目标

社区检测 + Go/Rust 支持 + 性能优化。

### 6.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 社区检测（Louvain 算法） | 3 天 | Phase 2 |
| Go 解析器（tree-sitter-go） | 2 天 | Phase 1 |
| Rust 解析器（tree-sitter-rust） | 2 天 | Phase 1 |
| C# 解析器（tree-sitter-c-sharp） | 2 天 | Phase 1 |
| 性能优化（批量插入、索引优化） | 2 天 | 全部 |
| 监控指标（Prometheus） | 1 天 | 全部 |

### 6.3 技术实现

**社区检测**:
```python
# app/services/community_detector.py
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
        
        partition = community_louvain.best_partition(graph)
        
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

### 6.4 验收标准

- [ ] 能检测社区划分
- [ ] 支持 Go 项目索引
- [ ] 支持 Rust 项目索引
- [ ] 支持 C# 项目索引
- [ ] 10k 文件索引 < 2 分钟
- [ ] 查询延迟 P95 < 200ms

---

## 7. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **Tree-sitter 解析错误** | 中 | 高 | 使用官方语法、fallback 机制 |
| **LSP 初始化慢** | 高 | 中 | 延迟初始化、缓存 |
| **大项目内存问题** | 中 | 高 | 增量解析、流式处理 |
| **多语言支持复杂** | 高 | 中 | 优先支持核心语言 |

---

## 8. 资源需求

### 8.1 开发资源

| 资源 | 数量 | 说明 |
|------|------|------|
| **开发人员** | 1-2 人 | Python + FastAPI |
| **开发环境** | 1 套 | 本地开发 |
| **测试环境** | 1 套 | NAS 部署 |

### 8.2 基础设施

| 资源 | 规格 | 说明 |
|------|------|------|
| **NAS** | 192.168.0.100 | 部署环境 |
| **PostgreSQL** | 127.0.0.1:5432 | 结构化存储 |
| **Redis** | 192.168.0.100:6379 | 缓存 |

### 8.3 依赖关系

| 依赖 | 版本 | 说明 |
|------|------|------|
| **Python** | 3.13 | 运行环境 |
| **FastAPI** | latest | Web 框架 |
| **SQLite** | 3.x | 存储 |
| **Tree-sitter** | latest | 解析器 |
| **pygls** | latest | LSP 实现 |
| **NetworkX** | latest | 图谱 |
| **click** | latest | CLI |
| **watchdog** | latest | 文件监听 |
