# Sandbox-Tool 工具优化设计文档

## 1. 现状分析

### 1.1 当前架构
```
tools/sandbox-tool/app/
├── api/
│   └── tool.py              # MCP接口
├── services/
│   ├── sandbox_manager.py   # 沙箱管理
│   ├── code_executor.py     # 代码执行
│   └── security.py          # 安全检查
└── models/
    └── sandbox.py           # 沙箱模型
```

### 1.2 现有能力
| 能力 | 实现方式 | 问题 |
|------|----------|------|
| 代码执行 | Docker容器 | 启动慢，资源占用高 |
| 安全检查 | 基础沙箱 | 无法防止所有攻击 |
| 资源限制 | 静态配置 | 无法动态调整 |
| 执行结果 | 文本输出 | 无结构化输出 |

### 1.3 核心问题
1. **启动慢**：每次创建新容器需要5-10秒
2. **资源占用高**：每个容器占用256MB内存
3. **安全限制**：基础沙箱无法防止所有攻击
4. **无超时机制**：长时间运行的任务无法终止
5. **无状态管理**：执行上下文丢失

---

## 2. 优化目标

| 目标 | 指标 | 当前值 | 目标值 |
|------|------|--------|--------|
| 启动时间 | 冷启动时间 | 5-10s | <2s |
| 资源占用 | 内存占用 | 256MB | <128MB |
| 安全性 | 攻击防护 | 基础 | 高级 |
| 超时控制 | 任务终止 | 无 | 有 |
| 状态管理 | 执行上下文 | 丢失 | 保留 |

---

## 3. 优化设计

### 3.1 模块一：容器池化

#### 3.1.1 容器池管理器

**新增文件：`app/services/container_pool.py`**
```python
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import docker

@dataclass
class PooledContainer:
    """池化容器"""
    container_id: str
    image: str
    status: str  # 'ready', 'busy', 'stale'
    created_at: datetime
    last_used: datetime
    memory_limit: int
    cpu_limit: float

class ContainerPool:
    """容器池管理器"""
    
    def __init__(
        self,
        min_size: int = 5,
        max_size: int = 20,
        idle_timeout: int = 300,  # 5分钟
        cleanup_interval: int = 60  # 1分钟
    ):
        self.min_size = min_size
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        self.cleanup_interval = cleanup_interval
        
        self.pool: Dict[str, PooledContainer] = {}
        self.client = docker.from_env()
        
        # 启动清理任务
        self._cleanup_task = None
    
    async def initialize(self):
        """初始化容器池"""
        # 预热容器
        for i in range(self.min_size):
            container = await self._create_container()
            self.pool[container.container_id] = container
        
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def acquire(self, requirements: Dict = None) -> PooledContainer:
        """获取容器"""
        # 查找可用容器
        for container in self.pool.values():
            if container.status == 'ready':
                container.status = 'busy'
                container.last_used = datetime.now()
                return container
        
        # 没有可用容器，创建新的
        if len(self.pool) < self.max_size:
            container = await self._create_container()
            container.status = 'busy'
            self.pool[container.container_id] = container
            return container
        
        # 等待容器释放
        return await self._wait_for_container()
    
    async def release(self, container_id: str):
        """释放容器"""
        if container_id in self.pool:
            container = self.pool[container_id]
            container.status = 'ready'
            container.last_used = datetime.now()
            
            # 清理容器状态
            await self._clean_container(container_id)
    
    async def _create_container(self, requirements: Dict = None) -> PooledContainer:
        """创建容器"""
        # 配置资源限制
        memory_limit = requirements.get('memory_limit', 128 * 1024 * 1024) if requirements else 128 * 1024 * 1024
        cpu_limit = requirements.get('cpu_limit', 0.5) if requirements else 0.5
        
        # 创建容器
        container = self.client.containers.run(
            image='sandbox-python:latest',
            detach=True,
            mem_limit=memory_limit,
            cpu_quota=int(cpu_limit * 100000),
            network_mode='none',  # 禁用网络
            read_only=True,  # 只读文件系统
            tmpfs={'/tmp': 'size=64m'},  # 临时文件系统
            remove=False
        )
        
        return PooledContainer(
            container_id=container.id,
            image='sandbox-python:latest',
            status='ready',
            created_at=datetime.now(),
            last_used=datetime.now(),
            memory_limit=memory_limit,
            cpu_limit=cpu_limit
        )
    
    async def _clean_container(self, container_id: str):
        """清理容器"""
        try:
            container = self.client.containers.get(container_id)
            
            # 清理临时文件
            container.exec_run('rm -rf /tmp/*')
            
            # 清理环境变量
            container.exec_run('env -i /bin/sh')
            
        except Exception as e:
            print(f"Failed to clean container {container_id}: {e}")
    
    async def _wait_for_container(self, timeout: int = 30) -> PooledContainer:
        """等待容器释放"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            for container in self.pool.values():
                if container.status == 'ready':
                    container.status = 'busy'
                    container.last_used = datetime.now()
                    return container
            
            await asyncio.sleep(0.1)
        
        raise TimeoutError("No container available within timeout")
    
    async def _cleanup_loop(self):
        """清理循环"""
        while True:
            await asyncio.sleep(self.cleanup_interval)
            await self._cleanup_stale_containers()
    
    async def _cleanup_stale_containers(self):
        """清理过期容器"""
        now = datetime.now()
        stale_containers = []
        
        for container_id, container in self.pool.items():
            if container.status == 'ready':
                idle_time = (now - container.last_used).seconds
                if idle_time > self.idle_timeout:
                    stale_containers.append(container_id)
        
        # 删除过期容器
        for container_id in stale_containers:
            await self._remove_container(container_id)
            del self.pool[container_id]
        
        # 确保最小池大小
        while len(self.pool) < self.min_size:
            container = await self._create_container()
            self.pool[container.container_id] = container
    
    async def _remove_container(self, container_id: str):
        """删除容器"""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove()
        except Exception as e:
            print(f"Failed to remove container {container_id}: {e}")
    
    def get_stats(self) -> Dict:
        """获取池统计"""
        stats = {
            'total': len(self.pool),
            'ready': 0,
            'busy': 0,
            'stale': 0
        }
        
        for container in self.pool.values():
            if container.status == 'ready':
                stats['ready'] += 1
            elif container.status == 'busy':
                stats['busy'] += 1
            elif container.status == 'stale':
                stats['stale'] += 1
        
        return stats
```

#### 3.1.2 容器复用策略

```python
class ContainerReuseStrategy:
    """容器复用策略"""
    
    def __init__(self, pool: ContainerPool):
        self.pool = pool
        self.reuse_history = {}
    
    async def get_container(self, task_type: str, requirements: Dict) -> PooledContainer:
        """获取容器（带复用策略）"""
        
        # 1. 检查是否有相同任务类型的容器
        if task_type in self.reuse_history:
            container_id = self.reuse_history[task_type]
            if container_id in self.pool.pool:
                container = self.pool.pool[container_id]
                if container.status == 'ready':
                    container.status = 'busy'
                    container.last_used = datetime.now()
                    return container
        
        # 2. 获取通用容器
        container = await self.pool.acquire(requirements)
        
        # 3. 更新复用历史
        self.reuse_history[task_type] = container.container_id
        
        return container
```

### 3.2 模块二：增强安全检查

#### 3.2.1 安全规则引擎

**新增文件：`app/services/security_engine.py`**
```python
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import re

class ThreatLevel(Enum):
    """威胁级别"""
    NONE = 'none'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

@dataclass
class SecurityCheck:
    """安全检查结果"""
    passed: bool
    threat_level: ThreatLevel
    violations: List[Dict]
    recommendations: List[str]

class SecurityEngine:
    """安全规则引擎"""
    
    def __init__(self):
        # 危险函数列表
        self.dangerous_functions = {
            'python': [
                'exec', 'eval', 'compile', '__import__',
                'open', 'os.system', 'subprocess.call',
                'socket', 'urllib', 'requests'
            ],
            'javascript': [
                'eval', 'Function', 'setTimeout', 'setInterval',
                'require', 'import', 'fetch', 'XMLHttpRequest'
            ]
        }
        
        # 危险模式
        self.dangerous_patterns = [
            r'__.*__',  # 双下划线属性
            r'import\s+os',  # 导入os模块
            r'from\s+os\s+import',  # 从os导入
            r'import\s+sys',  # 导入sys模块
            r'import\s+subprocess',  # 导入subprocess
            r'os\.system\(',  # 调用os.system
            r'os\.popen\(',  # 调用os.popen
            r'subprocess\.',  # 调用subprocess
            r'exec\(',  # 调用exec
            r'eval\(',  # 调用eval
        ]
        
        # 资源限制
        self.resource_limits = {
            'max_lines': 1000,
            'max_imports': 10,
            'max_functions': 50,
            'max_classes': 20,
            'max_file_size': 1024 * 1024  # 1MB
        }
    
    async def check(self, code: str, language: str) -> SecurityCheck:
        """执行安全检查"""
        violations = []
        recommendations = []
        
        # 1. 检查危险函数
        func_violations = self._check_dangerous_functions(code, language)
        violations.extend(func_violations)
        
        # 2. 检查危险模式
        pattern_violations = self._check_dangerous_patterns(code)
        violations.extend(pattern_violations)
        
        # 3. 检查资源限制
        resource_violations = self._check_resource_limits(code, language)
        violations.extend(resource_violations)
        
        # 4. 检查代码结构
        structure_violations = self._check_code_structure(code, language)
        violations.extend(structure_violations)
        
        # 5. 生成建议
        recommendations = self._generate_recommendations(violations)
        
        # 6. 计算威胁级别
        threat_level = self._calculate_threat_level(violations)
        
        return SecurityCheck(
            passed=len(violations) == 0,
            threat_level=threat_level,
            violations=violations,
            recommendations=recommendations
        )
    
    def _check_dangerous_functions(self, code: str, language: str) -> List[Dict]:
        """检查危险函数"""
        violations = []
        dangerous = self.dangerous_functions.get(language, [])
        
        for func in dangerous:
            if func in code:
                violations.append({
                    'type': 'dangerous_function',
                    'function': func,
                    'severity': 'high',
                    'message': f"使用了危险函数: {func}"
                })
        
        return violations
    
    def _check_dangerous_patterns(self, code: str) -> List[Dict]:
        """检查危险模式"""
        violations = []
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, code):
                violations.append({
                    'type': 'dangerous_pattern',
                    'pattern': pattern,
                    'severity': 'medium',
                    'message': f"匹配到危险模式: {pattern}"
                })
        
        return violations
    
    def _check_resource_limits(self, code: str, language: str) -> List[Dict]:
        """检查资源限制"""
        violations = []
        
        # 检查代码行数
        lines = code.split('\n')
        if len(lines) > self.resource_limits['max_lines']:
            violations.append({
                'type': 'resource_limit',
                'resource': 'lines',
                'current': len(lines),
                'limit': self.resource_limits['max_lines'],
                'severity': 'low',
                'message': f"代码行数超过限制: {len(lines)} > {self.resource_limits['max_lines']}"
            })
        
        return violations
    
    def _check_code_structure(self, code: str, language: str) -> List[Dict]:
        """检查代码结构"""
        violations = []
        
        # 检查导入数量
        imports = re.findall(r'(?:from|import)\s+\w+', code)
        if len(imports) > self.resource_limits['max_imports']:
            violations.append({
                'type': 'structure_limit',
                'structure': 'imports',
                'current': len(imports),
                'limit': self.resource_limits['max_imports'],
                'severity': 'low',
                'message': f"导入数量超过限制: {len(imports)} > {self.resource_limits['max_imports']}"
            })
        
        return violations
    
    def _generate_recommendations(self, violations: List[Dict]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        for violation in violations:
            if violation['type'] == 'dangerous_function':
                recommendations.append(f"避免使用 {violation['function']}，考虑使用安全的替代方案")
            elif violation['type'] == 'dangerous_pattern':
                recommendations.append(f"避免使用危险模式，考虑重构代码")
            elif violation['type'] == 'resource_limit':
                recommendations.append(f"优化代码结构，减少{violation['resource']}数量")
        
        return list(set(recommendations))
    
    def _calculate_threat_level(self, violations: List[Dict]) -> ThreatLevel:
        """计算威胁级别"""
        if not violations:
            return ThreatLevel.NONE
        
        high_count = sum(1 for v in violations if v['severity'] == 'high')
        medium_count = sum(1 for v in violations if v['severity'] == 'medium')
        low_count = sum(1 for v in violations if v['severity'] == 'low')
        
        if high_count > 0:
            return ThreatLevel.CRITICAL
        elif medium_count > 2:
            return ThreatLevel.HIGH
        elif medium_count > 0 or low_count > 3:
            return ThreatLevel.MEDIUM
        elif low_count > 0:
            return ThreatLevel.LOW
        else:
            return ThreatLevel.NONE
```

### 3.3 模块三：增强超时控制

#### 3.3.1 超时管理器

**新增文件：`app/services/timeout_manager.py`**
```python
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class TimeoutConfig:
    """超时配置"""
    execution_timeout: int = 30  # 执行超时（秒）
    output_timeout: int = 10  # 输出超时（秒）
    cleanup_timeout: int = 5  # 清理超时（秒）
    warning_threshold: float = 0.8  # 警告阈值

class TimeoutManager:
    """超时管理器"""
    
    def __init__(self, config: TimeoutConfig = None):
        self.config = config or TimeoutConfig()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.timeout_history = []
    
    async def execute_with_timeout(
        self,
        func,
        task_id: str,
        timeout: int = None
    ) -> Dict:
        """带超时执行"""
        timeout = timeout or self.config.execution_timeout
        
        # 创建超时任务
        task = asyncio.create_task(func())
        self.active_tasks[task_id] = task
        
        try:
            # 等待完成或超时
            result = await asyncio.wait_for(task, timeout=timeout)
            
            # 记录成功
            self.timeout_history.append({
                'task_id': task_id,
                'status': 'completed',
                'duration': timeout,
                'timestamp': datetime.now()
            })
            
            return {'status': 'completed', 'result': result}
            
        except asyncio.TimeoutError:
            # 超时处理
            task.cancel()
            
            # 记录超时
            self.timeout_history.append({
                'task_id': task_id,
                'status': 'timeout',
                'duration': timeout,
                'timestamp': datetime.now()
            })
            
            return {'status': 'timeout', 'error': f'Execution timed out after {timeout}s'}
            
        finally:
            # 清理
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    async def cancel_task(self, task_id: str):
        """取消任务"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            del self.active_tasks[task_id]
    
    async def cancel_all_tasks(self):
        """取消所有任务"""
        for task_id in list(self.active_tasks.keys()):
            await self.cancel_task(task_id)
    
    def get_active_tasks(self) -> Dict:
        """获取活跃任务"""
        return {
            task_id: {
                'status': task._state if hasattr(task, '_state') else 'unknown',
                'created': task._coro.cr_frame.f_code.co_filename if hasattr(task, '_coro') else 'unknown'
            }
            for task_id, task in self.active_tasks.items()
        }
    
    def get_timeout_stats(self) -> Dict:
        """获取超时统计"""
        if not self.timeout_history:
            return {'total': 0, 'timeouts': 0, 'success_rate': 1.0}
        
        total = len(self.timeout_history)
        timeouts = sum(1 for h in self.timeout_history if h['status'] == 'timeout')
        
        return {
            'total': total,
            'timeouts': timeouts,
            'success_rate': (total - timeouts) / total if total > 0 else 1.0,
            'recent_history': self.timeout_history[-10:]  # 最近10条
        }
```

### 3.4 模块四：增强状态管理

#### 3.4.1 执行上下文管理器

**新增文件：`app/services/context_manager.py`**
```python
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class ExecutionContext:
    """执行上下文"""
    task_id: str
    user_id: str
    project_id: str
    language: str
    created_at: datetime
    updated_at: datetime
    variables: Dict[str, Any]
    imports: List[str]
    output: List[Dict]
    errors: List[Dict]
    status: str

class ContextManager:
    """上下文管理器"""
    
    def __init__(self):
        self.contexts: Dict[str, ExecutionContext] = {}
        self.context_history = []
    
    async def create_context(
        self,
        task_id: str,
        user_id: str,
        project_id: str,
        language: str
    ) -> ExecutionContext:
        """创建上下文"""
        context = ExecutionContext(
            task_id=task_id,
            user_id=user_id,
            project_id=project_id,
            language=language,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            variables={},
            imports=[],
            output=[],
            errors=[],
            status='created'
        )
        
        self.contexts[task_id] = context
        return context
    
    async def update_context(
        self,
        task_id: str,
        updates: Dict[str, Any]
    ) -> Optional[ExecutionContext]:
        """更新上下文"""
        if task_id not in self.contexts:
            return None
        
        context = self.contexts[task_id]
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        context.updated_at = datetime.now()
        
        return context
    
    async def get_context(self, task_id: str) -> Optional[ExecutionContext]:
        """获取上下文"""
        return self.contexts.get(task_id)
    
    async def add_variable(
        self,
        task_id: str,
        name: str,
        value: Any
    ) -> bool:
        """添加变量"""
        if task_id not in self.contexts:
            return False
        
        context = self.contexts[task_id]
        context.variables[name] = value
        context.updated_at = datetime.now()
        
        return True
    
    async def add_import(
        self,
        task_id: str,
        module: str
    ) -> bool:
        """添加导入"""
        if task_id not in self.contexts:
            return False
        
        context = self.contexts[task_id]
        if module not in context.imports:
            context.imports.append(module)
            context.updated_at = datetime.now()
        
        return True
    
    async def add_output(
        self,
        task_id: str,
        output: Dict
    ) -> bool:
        """添加输出"""
        if task_id not in self.contexts:
            return False
        
        context = self.contexts[task_id]
        context.output.append(output)
        context.updated_at = datetime.now()
        
        return True
    
    async def add_error(
        self,
        task_id: str,
        error: Dict
    ) -> bool:
        """添加错误"""
        if task_id not in self.contexts:
            return False
        
        context = self.contexts[task_id]
        context.errors.append(error)
        context.updated_at = datetime.now()
        
        return True
    
    async def close_context(self, task_id: str) -> bool:
        """关闭上下文"""
        if task_id not in self.contexts:
            return False
        
        context = self.contexts[task_id]
        context.status = 'closed'
        context.updated_at = datetime.now()
        
        # 移动到历史
        self.context_history.append(context)
        del self.contexts[task_id]
        
        return True
    
    def get_user_contexts(self, user_id: str) -> List[ExecutionContext]:
        """获取用户的所有上下文"""
        return [
            ctx for ctx in self.contexts.values()
            if ctx.user_id == user_id
        ]
    
    def get_project_contexts(self, project_id: str) -> List[ExecutionContext]:
        """获取项目的所有上下文"""
        return [
            ctx for ctx in self.contexts.values()
            if ctx.project_id == project_id
        ]
```

---

## 4. API设计

### 4.1 新增/修改的API

#### 容器池状态
```python
@router.get("/api/sandbox/pool/status")
async def get_pool_status():
    """
    获取容器池状态
    
    Response:
    {
        "total": 10,
        "ready": 5,
        "busy": 3,
        "stale": 2,
        "config": {
            "min_size": 5,
            "max_size": 20,
            "idle_timeout": 300
        }
    }
    """
```

#### 安全检查
```python
@router.post("/api/sandbox/security/check")
async def check_security(request: SecurityCheckRequest):
    """
    执行安全检查
    
    Request:
    {
        "code": "import os\nos.system('ls')",
        "language": "python"
    }
    
    Response:
    {
        "passed": false,
        "threat_level": "high",
        "violations": [
            {
                "type": "dangerous_function",
                "function": "os.system",
                "severity": "high",
                "message": "使用了危险函数: os.system"
            }
        ],
        "recommendations": [
            "避免使用 os.system，考虑使用 subprocess 模块"
        ]
    }
    """
```

#### 执行上下文
```python
@router.get("/api/sandbox/context/{task_id}")
async def get_execution_context(task_id: str):
    """
    获取执行上下文
    
    Response:
    {
        "task_id": "task-123",
        "user_id": "user-456",
        "project_id": "aidp",
        "language": "python",
        "created_at": "2025-01-01T00:00:00Z",
        "variables": {"x": 1, "y": 2},
        "imports": ["os", "sys"],
        "output": [{"type": "stdout", "content": "Hello"}],
        "errors": [],
        "status": "running"
    }
    """
```

---

## 5. 任务拆分

### Phase 1：容器池化（2天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T1.1 | 实现ContainerPool | P0 |
| T1.2 | 实现容器复用策略 | P0 |
| T1.3 | 集成到沙箱管理 | P1 |

### Phase 2：安全增强（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T2.1 | 实现SecurityEngine | P1 |
| T2.2 | 集成到代码执行 | P1 |
| T2.3 | 添加安全检查API | P2 |

### Phase 3：超时控制（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T3.1 | 实现TimeoutManager | P1 |
| T3.2 | 集成到代码执行 | P1 |
| T3.3 | 添加超时统计 | P2 |

### Phase 4：状态管理（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T4.1 | 实现ContextManager | P1 |
| T4.2 | 集成到代码执行 | P1 |
| T4.3 | 添加上下文API | P2 |

---

## 6. 依赖和风险

### 6.1 技术依赖
| 依赖 | 用途 | 备选方案 |
|------|------|----------|
| docker | 容器管理 | subprocess |
| asyncio | 异步执行 | threading |
| re | 正则表达式 | 字符串匹配 |

### 6.2 风险点
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 容器逃逸 | 安全漏洞 | 多层安全检查 |
| 资源耗尽 | 系统崩溃 | 资源限制+监控 |
| 状态丢失 | 执行中断 | 状态持久化 |

---

## 7. 验收标准

| 验收项 | 标准 |
|--------|------|
| 容器池化 | 冷启动时间<2s |
| 安全检查 | 能检测危险函数和模式 |
| 超时控制 | 能终止长时间运行的任务 |
| 状态管理 | 能保留执行上下文 |
| 资源限制 | 内存占用<128MB |
