# Context Pipeline 优化设计文档

## 1. 现状分析

### 1.1 当前架构
```
apps/controller/app/services/context_pipeline.py
├── ContextPipeline                  # 5阶段流水线
├── ContextItem                      # 上下文项
├── ContextAssembly                  # 上下文组装结果
└── get_context_pipeline()           # 工厂函数

Stage 0: Agent Instructions → 角色定义、约束规则
Stage 1: Skill Router        → 意图分析、技能匹配
Stage 2: Knowledge Retrieval → 并行检索4个工具
Stage 3: Context Assembly    → 上下文组装、去重、压缩
Stage 4: Response Generation → 生成响应
```

### 1.2 现有能力
| 能力 | 实现方式 | 问题 |
|------|----------|------|
| 5阶段流水线 | 串行执行 | Stage 2并行检索但无缓存 |
| 上下文组装 | 简单拼接 | 无优先级、无压缩 |
| 工具调用 | MCP转发 | 无结果缓存、无重试 |
| 错误处理 | try/except | 静默失败，无降级 |

### 1.3 核心问题
1. **Stage 2并行检索无缓存**：每次调用都重新检索所有工具
2. **上下文组装简单拼接**：无优先级、无去重、无压缩
3. **工具调用无重试**：单次失败导致整个阶段失败
4. **无结果缓存**：相同查询重复检索
5. **无降级策略**：工具不可用时整个流水线失败

---

## 2. 优化目标

| 目标 | 指标 | 当前值 | 目标值 |
|------|------|--------|--------|
| 流水线延迟 | P95延迟 | ~2s | <1s |
| 缓存命中率 | 相同查询缓存 | 0% | >60% |
| 工具可用性 | 单工具失败影响 | 整体失败 | 降级继续 |
| 上下文质量 | 信息密度 | 低 | 高 |
| 错误恢复 | 重试成功率 | 0% | >80% |

---

## 3. 优化设计

### 3.1 模块一：上下文缓存层

#### 3.1.1 缓存架构

**新增文件：`app/services/context_cache.py`**
```python
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

class ContextCache:
    """上下文缓存管理器"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.cache = {}  # 内存缓存
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def _generate_key(self, stage: str, params: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 对参数进行序列化并哈希
        param_str = json.dumps(params, sort_keys=True, default=str)
        hash_obj = hashlib.md5(f"{stage}:{param_str}".encode())
        return hash_obj.hexdigest()
    
    def get(self, stage: str, params: Dict[str, Any]) -> Optional[Dict]:
        """获取缓存"""
        key = self._generate_key(stage, params)
        
        if key in self.cache:
            entry = self.cache[key]
            # 检查是否过期
            if datetime.now() - entry['timestamp'] < timedelta(seconds=self.ttl_seconds):
                self.stats['hits'] += 1
                return entry['data']
            else:
                # 过期，删除
                del self.cache[key]
                self.stats['evictions'] += 1
        
        self.stats['misses'] += 1
        return None
    
    def set(self, stage: str, params: Dict[str, Any], data: Dict):
        """设置缓存"""
        key = self._generate_key(stage, params)
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }
        
        # 缓存大小限制
        if len(self.cache) > 1000:
            # 删除最旧的条目
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
            self.stats['evictions'] += 1
    
    def invalidate(self, stage: Optional[str] = None):
        """清除缓存"""
        if stage:
            # 清除特定阶段的缓存
            keys_to_delete = [k for k in self.cache if k.startswith(stage)]
            for key in keys_to_delete:
                del self.cache[key]
        else:
            # 清除所有缓存
            self.cache.clear()
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total if total > 0 else 0
        return {
            **self.stats,
            'hit_rate': round(hit_rate, 2),
            'size': len(self.cache)
        }


# 缓存装饰器
def cached(stage: str, ttl: int = 300):
    """缓存装饰器"""
    cache = ContextCache(ttl_seconds=ttl)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成参数键
            params = {k: v for k, v in kwargs.items() if k != 'self'}
            
            # 尝试从缓存获取
            cached_result = cache.get(stage, params)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            cache.set(stage, params, result)
            
            return result
        return wrapper
    return decorator
```

#### 3.1.2 Stage 2 并行检索缓存

**修改：`app/services/context_pipeline.py`**
```python
class ContextPipeline:
    def __init__(self):
        self.cache = ContextCache(ttl_seconds=300)
    
    async def stage2_knowledge_retrieval(self, intent: IntentResult, project_id: str) -> List[ContextItem]:
        """Stage 2: 知识检索（带缓存）"""
        # 检查缓存
        cache_key = {
            'intent': intent.intent,
            'tools': intent.suggested_tools,
            'project_id': project_id
        }
        cached_items = self.cache.get('stage2', cache_key)
        if cached_items is not None:
            return cached_items
        
        # 并行检索多个工具
        tasks = []
        for tool_name in intent.suggested_tools:
            task = self._invoke_tool_with_retry(
                tool_name=tool_name,
                capability=f"{tool_name}.search",
                arguments={'query': intent.original_task, 'project_id': project_id}
            )
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 转换为ContextItem
        items = []
        for result in results:
            if isinstance(result, Exception):
                # 记录错误但继续
                logger.warning(f"Tool invocation failed: {result}")
                continue
            items.extend(result)
        
        # 缓存结果
        self.cache.set('stage2', cache_key, items)
        
        return items
```

### 3.2 模块二：上下文组装优化

#### 3.2.1 优先级组装

**新增文件：`app/services/context_assembly.py`**
```python
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

class Priority(Enum):
    """上下文优先级"""
    CRITICAL = 1  # 必须包含（如项目定义、核心配置）
    HIGH = 2      # 高优先级（如相关记忆、核心知识）
    MEDIUM = 3    # 中优先级（如辅助信息）
    LOW = 4       # 低优先级（如历史记录）

@dataclass
class PrioritizedContext:
    """带优先级的上下文"""
    content: str
    priority: Priority
    source: str
    relevance_score: float
    metadata: Dict

class ContextAssembler:
    """上下文组装器"""
    
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
    
    async def assemble(
        self,
        context_items: List[ContextItem],
        intent: IntentResult
    ) -> ContextAssembly:
        """组装上下文（带优先级和压缩）"""
        
        # 1. 转换为优先级上下文
        prioritized = self._prioritize_items(context_items, intent)
        
        # 2. 去重
        deduplicated = self._deduplicate(prioritized)
        
        # 3. 压缩（如果超过token限制）
        compressed = self._compress(deduplicated)
        
        # 4. 排序（按优先级和相关性）
        sorted_items = self._sort(compressed)
        
        # 5. 组装最终上下文
        final_context = self._build_final_context(sorted_items)
        
        return ContextAssembly(
            items=sorted_items,
            total_tokens=self._count_tokens(final_context),
            compression_ratio=len(deduplicated) / len(sorted_items) if sorted_items else 1.0
        )
    
    def _prioritize_items(
        self,
        items: List[ContextItem],
        intent: IntentResult
    ) -> List[PrioritizedContext]:
        """为上下文项分配优先级"""
        prioritized = []
        
        for item in items:
            # 根据来源分配优先级
            if item.source == 'instructions':
                priority = Priority.CRITICAL
            elif item.source in ['memory', 'knowledge']:
                priority = Priority.HIGH
            elif item.source == 'code_index':
                priority = Priority.MEDIUM
            else:
                priority = Priority.LOW
            
            prioritized.append(PrioritizedContext(
                content=item.content,
                priority=priority,
                source=item.source,
                relevance_score=item.relevance_score,
                metadata=item.metadata
            ))
        
        return prioritized
    
    def _deduplicate(self, items: List[PrioritizedContext]) -> List[PrioritizedContext]:
        """去重"""
        seen = set()
        deduplicated = []
        
        for item in items:
            # 使用内容哈希去重
            content_hash = hashlib.md5(item.content.encode()).hexdigest()
            if content_hash not in seen:
                seen.add(content_hash)
                deduplicated.append(item)
        
        return deduplicated
    
    def _compress(self, items: List[PrioritizedContext]) -> List[PrioritizedContext]:
        """压缩（如果超过token限制）"""
        total_tokens = self._count_tokens(' '.join(item.content for item in items))
        
        if total_tokens <= self.max_tokens:
            return items
        
        # 按优先级保留
        compressed = []
        current_tokens = 0
        
        for item in items:
            item_tokens = self._count_tokens(item.content)
            if current_tokens + item_tokens <= self.max_tokens:
                compressed.append(item)
                current_tokens += item_tokens
            else:
                # 尝试截断内容
                remaining_tokens = self.max_tokens - current_tokens
                if remaining_tokens > 100:
                    truncated_content = self._truncate(item.content, remaining_tokens)
                    compressed.append(PrioritizedContext(
                        content=truncated_content,
                        priority=item.priority,
                        source=item.source,
                        relevance_score=item.relevance_score,
                        metadata=item.metadata
                    ))
                break
        
        return compressed
    
    def _sort(self, items: List[PrioritizedContext]) -> List[PrioritizedContext]:
        """排序（按优先级和相关性）"""
        return sorted(items, key=lambda x: (x.priority.value, -x.relevance_score))
    
    def _build_final_context(self, items: List[PrioritizedContext]) -> str:
        """构建最终上下文字符串"""
        sections = []
        
        for item in items:
            sections.append(f"[{item.source.upper()}] {item.content}")
        
        return '\n\n'.join(sections)
    
    def _count_tokens(self, text: str) -> int:
        """估算token数量"""
        # 简单估算：1 token ≈ 4 characters
        return len(text) // 4
    
    def _truncate(self, text: str, max_tokens: int) -> str:
        """截断文本"""
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + '...'
```

#### 3.2.2 上下文压缩策略

```python
class ContextCompressor:
    """上下文压缩器"""
    
    async def compress(self, context: str, target_tokens: int) -> str:
        """压缩上下文"""
        
        current_tokens = self._count_tokens(context)
        if current_tokens <= target_tokens:
            return context
        
        # 策略1：移除冗余信息
        compressed = self._remove_redundancy(context)
        
        # 策略2：提取关键信息
        if self._count_tokens(compressed) > target_tokens:
            compressed = self._extract_key_info(compressed)
        
        # 策略3：总结长段落
        if self._count_tokens(compressed) > target_tokens:
            compressed = self._summarize_paragraphs(compressed)
        
        return compressed
    
    def _remove_redundancy(self, context: str) -> str:
        """移除冗余信息"""
        lines = context.split('\n')
        unique_lines = []
        seen = set()
        
        for line in lines:
            # 使用行内容哈希去重
            line_hash = hashlib.md5(line.encode()).hexdigest()
            if line_hash not in seen:
                seen.add(line_hash)
                unique_lines.append(line)
        
        return '\n'.join(unique_lines)
    
    def _extract_key_info(self, context: str) -> str:
        """提取关键信息"""
        # 保留包含关键词的行
        keywords = ['定义', '配置', '规则', '约束', '重要', '核心', '必须']
        
        key_lines = []
        for line in context.split('\n'):
            if any(keyword in line for keyword in keywords):
                key_lines.append(line)
        
        return '\n'.join(key_lines) if key_lines else context[:1000]
    
    def _summarize_paragraphs(self, context: str) -> str:
        """总结长段落"""
        paragraphs = context.split('\n\n')
        summarized = []
        
        for para in paragraphs:
            if len(para) > 200:
                # 简单总结：保留前200字符
                summarized.append(para[:200] + '...')
            else:
                summarized.append(para)
        
        return '\n\n'.join(summarized)
```

### 3.3 模块三：工具调用重试

#### 3.3.1 重试机制

**新增文件：`app/services/tool_retry.py`**
```python
import asyncio
from typing import Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum

class RetryStrategy(Enum):
    """重试策略"""
    FIXED = 'fixed'           # 固定间隔
    EXPONENTIAL = 'exponential'  # 指数退避
    FIBONACCI = 'fibonacci'    # 斐波那契退避

@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_exceptions: tuple = (Exception,)

class ToolRetryManager:
    """工具重试管理器"""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.stats = {
            'total_retries': 0,
            'successful_retries': 0,
            'failed_retries': 0
        }
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """带重试执行"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except self.config.retryable_exceptions as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    # 计算延迟
                    delay = self._calculate_delay(attempt)
                    
                    # 等待
                    await asyncio.sleep(delay)
                    
                    self.stats['total_retries'] += 1
                    print(f"Retry {attempt + 1}/{self.config.max_retries} after {delay}s")
        
        # 所有重试都失败
        self.stats['failed_retries'] += 1
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** attempt)
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = self.config.base_delay * self._fibonacci(attempt + 1)
        else:
            delay = self.config.base_delay
        
        return min(delay, self.config.max_delay)
    
    def _fibonacci(self, n: int) -> int:
        """斐波那契数列"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    def get_stats(self) -> Dict:
        """获取重试统计"""
        return self.stats
```

#### 3.3.2 工具调用增强

**修改：`app/services/context_pipeline.py`**
```python
class ContextPipeline:
    def __init__(self):
        self.retry_manager = ToolRetryManager(RetryConfig(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL
        ))
    
    async def _invoke_tool_with_retry(
        self,
        tool_name: str,
        capability: str,
        arguments: Dict
    ) -> List[ContextItem]:
        """带重试的工具调用"""
        async def _invoke():
            return await self._invoke_tool(tool_name, capability, arguments)
        
        try:
            result = await self.retry_manager.execute_with_retry(_invoke)
            return result
        except Exception as e:
            # 记录错误但不中断流水线
            logger.error(f"Tool {tool_name} failed after retries: {e}")
            return []
```

### 3.4 模块四：降级策略

#### 3.4.1 降级管理器

**新增文件：`app/services/fallback_manager.py`**
```python
from typing import Dict, List, Optional
from enum import Enum

class DegradationLevel(Enum):
    """降级级别"""
    FULL = 0        # 完整功能
    PARTIAL = 1     # 部分降级
    MINIMAL = 2     # 最小化降级
    EMERGENCY = 3   # 紧急降级

class FallbackManager:
    """降级管理器"""
    
    def __init__(self):
        self.degradation_level = DegradationLevel.FULL
        self.failed_tools = set()
        self.fallback_strategies = {
            'memory': self._fallback_memory,
            'knowledge': self._fallback_knowledge,
            'code_index': self._fallback_code_index,
            'quality': self._fallback_quality
        }
    
    async def handle_tool_failure(
        self,
        tool_name: str,
        error: Exception
    ) -> Optional[List[ContextItem]]:
        """处理工具失败"""
        self.failed_tools.add(tool_name)
        
        # 更新降级级别
        self._update_degradation_level()
        
        # 执行降级策略
        if tool_name in self.fallback_strategies:
            return await self.fallback_strategies[tool_name](error)
        
        return None
    
    def _update_degradation_level(self):
        """更新降级级别"""
        if len(self.failed_tools) == 0:
            self.degradation_level = DegradationLevel.FULL
        elif len(self.failed_tools) == 1:
            self.degradation_level = DegradationLevel.PARTIAL
        elif len(self.failed_tools) <= 3:
            self.degradation_level = DegradationLevel.MINIMAL
        else:
            self.degradation_level = DegradationLevel.EMERGENCY
    
    async def _fallback_memory(self, error: Exception) -> List[ContextItem]:
        """内存工具降级策略"""
        # 返回缓存的最近记忆
        return [
            ContextItem(
                content="内存工具暂时不可用，使用缓存的最近记忆",
                source='memory_fallback',
                relevance_score=0.5,
                metadata={'degraded': True, 'reason': str(error)}
            )
        ]
    
    async def _fallback_knowledge(self, error: Exception) -> List[ContextItem]:
        """知识工具降级策略"""
        # 返回基础知识
        return [
            ContextItem(
                content="知识库暂时不可用，使用基础知识",
                source='knowledge_fallback',
                relevance_score=0.3,
                metadata={'degraded': True, 'reason': str(error)}
            )
        ]
    
    async def _fallback_code_index(self, error: Exception) -> List[ContextItem]:
        """代码索引工具降级策略"""
        # 返回项目结构信息
        return [
            ContextItem(
                content="代码索引暂时不可用，使用项目结构信息",
                source='code_index_fallback',
                relevance_score=0.4,
                metadata={'degraded': True, 'reason': str(error)}
            )
        ]
    
    async def _fallback_quality(self, error: Exception) -> List[ContextItem]:
        """质量工具降级策略"""
        # 返回默认质量评分
        return [
            ContextItem(
                content="质量检查暂时不可用，跳过质量评分",
                source='quality_fallback',
                relevance_score=0.2,
                metadata={'degraded': True, 'reason': str(error)}
            )
        ]
    
    def get_status(self) -> Dict:
        """获取降级状态"""
        return {
            'level': self.degradation_level.value,
            'level_name': self.degradation_level.name,
            'failed_tools': list(self.failed_tools),
            'is_degraded': self.degradation_level != DegradationLevel.FULL
        }
```

---

## 4. API设计

### 4.1 新增/修改的API

#### 上下文缓存状态
```python
@router.get("/api/pipeline/cache/status")
async def get_cache_status():
    """
    获取上下文缓存状态
    
    Response:
    {
        "cache_stats": {
            "hits": 150,
            "misses": 50,
            "hit_rate": 0.75,
            "evictions": 10,
            "size": 128
        },
        "suggestions": [
            "缓存命中率良好",
            "考虑增加缓存TTL以提高命中率"
        ]
    }
    """
```

#### 流水线降级状态
```python
@router.get("/api/pipeline/degradation/status")
async def get_degradation_status():
    """
    获取流水线降级状态
    
    Response:
    {
        "degradation_level": "PARTIAL",
        "level_name": "PARTIAL",
        "failed_tools": ["memory"],
        "is_degraded": true,
        "fallback_active": true,
        "recommendations": [
            "检查memory-tool服务状态",
            "查看memory-tool日志排查问题"
        ]
    }
    """
```

#### 手动触发整理
```python
@router.post("/api/pipeline/consolidate")
async def consolidate_context():
    """
    手动触发上下文整理
    
    Response:
    {
        "consolidated_items": 25,
        "removed_duplicates": 5,
        "compression_ratio": 0.8,
        "execution_time_ms": 150
    }
    """
```

---

## 5. 任务拆分

### Phase 1：缓存层（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T1.1 | 实现ContextCache类 | P0 |
| T1.2 | 实现缓存装饰器 | P0 |
| T1.3 | 集成到Stage 2 | P0 |
| T1.4 | 添加缓存状态API | P1 |

### Phase 2：上下文组装优化（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T2.1 | 实现优先级分配 | P0 |
| T2.2 | 实现去重逻辑 | P0 |
| T2.3 | 实现压缩策略 | P1 |
| T2.4 | 集成到流水线 | P1 |

### Phase 3：重试机制（0.5天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T3.1 | 实现ToolRetryManager | P1 |
| T3.2 | 集成到工具调用 | P1 |
| T3.3 | 添加重试统计 | P2 |

### Phase 4：降级策略（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T4.1 | 实现FallbackManager | P1 |
| T4.2 | 实现各工具降级策略 | P1 |
| T4.3 | 集成到流水线 | P1 |
| T4.4 | 添加降级状态API | P2 |

---

## 6. 依赖和风险

### 6.1 技术依赖
| 依赖 | 用途 | 备选方案 |
|------|------|----------|
| hashlib | 缓存键生成 | uuid |
| asyncio | 并行检索 | threading |
| dataclasses | 数据结构 | dict |

### 6.2 风险点
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 缓存污染 | 返回错误数据 | 缓存键包含版本号 |
| 降级策略不当 | 丢失重要信息 | 降级时保留核心信息 |
| 重试风暴 | 系统过载 | 限制重试次数和频率 |

---

## 7. 验收标准

| 验收项 | 标准 |
|--------|------|
| 缓存命中率 | 相同查询缓存命中率>60% |
| 流水线延迟 | P95延迟<1s |
| 重试成功率 | 单工具重试成功率>80% |
| 降级效果 | 单工具失败不影响整体流水线 |
| 上下文质量 | 去重后无重复信息 |
