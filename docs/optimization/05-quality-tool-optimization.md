# Quality-Tool 工具优化设计文档

## 1. 现状分析

### 1.1 当前架构
```
tools/quality-tool/app/
├── api/
│   └── tool.py              # MCP接口
├── analyzers/
│   ├── complexity.py        # 代码复杂度分析
│   ├── duplication.py       # 重复代码检测
│   ├── coverage.py          # 测试覆盖率分析
│   └── issues.py            # 代码问题检测
└── services/
    └── report_service.py    # 报告生成
```

### 1.2 现有能力
| 能力 | 实现方式 | 问题 |
|------|----------|------|
| 复杂度分析 | 静态分析 | 仅支持Python |
| 重复检测 | 文本相似度 | 无法识别语义重复 |
| 覆盖率分析 | 解析coverage.xml | 依赖外部工具 |
| 问题检测 | 规则匹配 | 规则有限，误报高 |

### 1.3 核心问题
1. **语言支持有限**：仅支持Python，不支持JS/TS/Go等
2. **重复检测粗糙**：仅文本相似度，无法识别语义重复
3. **规则静态**：硬编码规则，无法动态更新
4. **无增量分析**：每次全量分析，效率低
5. **报告简单**：无修复建议，无优先级排序

---

## 2. 优化目标

| 目标 | 指标 | 当前值 | 目标值 |
|------|------|--------|--------|
| 语言支持 | 支持语言数 | 1 | 5+ |
| 重复检测 | 语义重复检测 | 0% | >70% |
| 问题检测 | 准确率 | ~60% | >85% |
| 分析速度 | P95延迟 | ~5s | <2s |
| 修复建议 | 有建议比例 | 0% | >80% |

---

## 3. 优化设计

### 3.1 模块一：多语言分析器

#### 3.1.1 语言适配器架构

**新增文件：`app/analyzers/language_adapter.py`**
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class Language(Enum):
    """支持的语言"""
    PYTHON = 'python'
    JAVASCRIPT = 'javascript'
    TYPESCRIPT = 'typescript'
    GO = 'go'
    JAVA = 'java'

@dataclass
class LanguageConfig:
    """语言配置"""
    name: str
    extensions: list
    parser: str
    complexity_rules: Dict
    quality_rules: Dict

class LanguageAdapter(ABC):
    """语言适配器基类"""
    
    @abstractmethod
    def parse(self, code: str) -> Dict:
        """解析代码"""
        pass
    
    @abstractmethod
    def calculate_complexity(self, ast: Dict) -> float:
        """计算复杂度"""
        pass
    
    @abstractmethod
    def detect_issues(self, ast: Dict) -> List[Dict]:
        """检测问题"""
        pass
    
    @abstractmethod
    def get_metrics(self, ast: Dict) -> Dict:
        """获取指标"""
        pass


class PythonAdapter(LanguageAdapter):
    """Python语言适配器"""
    
    def __init__(self):
        self.config = LanguageConfig(
            name='python',
            extensions=['.py'],
            parser='ast',
            complexity_rules={
                'max_function_length': 50,
                'max_class_length': 200,
                'max_parameters': 5,
                'max_return_points': 3
            },
            quality_rules={
                'naming_convention': 'snake_case',
                'max_line_length': 88,
                'max_imports': 10
            }
        )
    
    def parse(self, code: str) -> Dict:
        """解析Python代码"""
        import ast
        try:
            tree = ast.parse(code)
            return {
                'type': 'module',
                'body': self._parse_body(tree.body),
                'metadata': {
                    'functions': self._count_functions(tree),
                    'classes': self._count_classes(tree),
                    'imports': self._count_imports(tree)
                }
            }
        except SyntaxError as e:
            return {'type': 'error', 'message': str(e)}
    
    def calculate_complexity(self, ast: Dict) -> float:
        """计算圈复杂度"""
        if ast.get('type') == 'error':
            return 0.0
        
        complexity = 1.0
        for node in ast.get('body', []):
            if node['type'] in ['if', 'elif', 'while', 'for', 'try', 'except']:
                complexity += 1
            elif node['type'] == 'function':
                # 递归计算函数复杂度
                func_complexity = self.calculate_complexity(node)
                complexity += func_complexity
        
        return complexity
    
    def detect_issues(self, ast: Dict) -> List[Dict]:
        """检测Python代码问题"""
        issues = []
        
        # 检查函数长度
        for func in self._find_functions(ast):
            if len(func.get('body', [])) > self.config.complexity_rules['max_function_length']:
                issues.append({
                    'type': 'function_too_long',
                    'severity': 'warning',
                    'message': f"函数 {func['name']} 长度超过 {self.config.complexity_rules['max_function_length']} 行",
                    'location': func.get('location', {})
                })
        
        # 检查参数数量
        for func in self._find_functions(ast):
            if len(func.get('parameters', [])) > self.config.complexity_rules['max_parameters']:
                issues.append({
                    'type': 'too_many_parameters',
                    'severity': 'warning',
                    'message': f"函数 {func['name']} 参数数量超过 {self.config.complexity_rules['max_parameters']}",
                    'location': func.get('location', {})
                })
        
        return issues
    
    def get_metrics(self, ast: Dict) -> Dict:
        """获取代码指标"""
        return {
            'functions': self._count_functions(ast),
            'classes': self._count_classes(ast),
            'imports': self._count_imports(ast),
            'complexity': self.calculate_complexity(ast),
            'lines': self._count_lines(ast)
        }


class JavaScriptAdapter(LanguageAdapter):
    """JavaScript/TypeScript语言适配器"""
    
    def __init__(self):
        self.config = LanguageConfig(
            name='javascript',
            extensions=['.js', '.ts', '.jsx', '.tsx'],
            parser='esprima',
            complexity_rules={
                'max_function_length': 40,
                'max_class_length': 150,
                'max_parameters': 4,
                'max_callback_depth': 3
            },
            quality_rules={
                'naming_convention': 'camelCase',
                'max_line_length': 100,
                'max_imports': 15
            }
        )
    
    def parse(self, code: str) -> Dict:
        """解析JavaScript代码"""
        try:
            import esprima
            tree = esprima.parseScript(code, tolerant=True)
            return {
                'type': 'program',
                'body': self._parse_body(tree.body),
                'metadata': {
                    'functions': self._count_functions(tree),
                    'classes': self._count_classes(tree),
                    'imports': self._count_imports(tree)
                }
            }
        except Exception as e:
            return {'type': 'error', 'message': str(e)}
    
    def calculate_complexity(self, ast: Dict) -> float:
        """计算圈复杂度"""
        # 类似Python实现
        pass
    
    def detect_issues(self, ast: Dict) -> List[Dict]:
        """检测JavaScript代码问题"""
        issues = []
        
        # 检查回调地狱
        for func in self._find_functions(ast):
            depth = self._calculate_callback_depth(func)
            if depth > self.config.complexity_rules['max_callback_depth']:
                issues.append({
                    'type': 'callback_hell',
                    'severity': 'warning',
                    'message': f"函数 {func['name']} 回调嵌套深度超过 {self.config.complexity_rules['max_callback_depth']}",
                    'location': func.get('location', {})
                })
        
        return issues
    
    def get_metrics(self, ast: Dict) -> Dict:
        """获取代码指标"""
        return {
            'functions': self._count_functions(ast),
            'classes': self._count_classes(ast),
            'imports': self._count_imports(ast),
            'complexity': self.calculate_complexity(ast),
            'lines': self._count_lines(ast)
        }
```

#### 3.1.2 语言管理器

```python
class LanguageManager:
    """语言管理器"""
    
    def __init__(self):
        self.adapters = {
            Language.PYTHON: PythonAdapter(),
            Language.JAVASCRIPT: JavaScriptAdapter(),
            Language.TYPESCRIPT: JavaScriptAdapter(),
        }
    
    def get_adapter(self, file_path: str) -> Optional[LanguageAdapter]:
        """根据文件扩展名获取适配器"""
        for language, adapter in self.adapters.items():
            if any(file_path.endswith(ext) for ext in adapter.config.extensions):
                return adapter
        return None
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return [lang.value for lang in self.adapters.keys()]
```

### 3.2 模块二：语义重复检测

#### 3.2.1 语义相似度计算

**新增文件：`app/analyzers/semantic_duplication.py`**
```python
from typing import List, Dict, Tuple
import numpy as np

class SemanticDuplicationDetector:
    """语义重复检测器"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.embedding_provider = None  # 需要注入
    
    async def detect(
        self,
        code_blocks: List[Dict]
    ) -> List[Dict]:
        """检测语义重复代码"""
        
        # 1. 生成代码embedding
        embeddings = await self._generate_embeddings(code_blocks)
        
        # 2. 计算相似度矩阵
        similarity_matrix = self._compute_similarity_matrix(embeddings)
        
        # 3. 聚类相似代码块
        clusters = self._cluster_similar_blocks(code_blocks, similarity_matrix)
        
        # 4. 过滤低相似度集群
        significant_clusters = [
            cluster for cluster in clusters
            if cluster['similarity'] >= self.similarity_threshold
        ]
        
        return significant_clusters
    
    async def _generate_embeddings(self, code_blocks: List[Dict]) -> List[np.ndarray]:
        """生成代码embedding"""
        if not self.embedding_provider:
            # 使用简单的文本向量化作为fallback
            return [self._text_to_vector(block['content']) for block in code_blocks]
        
        # 使用embedding提供商
        embeddings = await self.embedding_provider.generate(
            [block['content'] for block in code_blocks]
        )
        return [emb.vector for emb in embeddings]
    
    def _text_to_vector(self, text: str) -> np.ndarray:
        """简单文本向量化（TF-IDF风格）"""
        words = text.lower().split()
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # 创建向量（使用词汇表）
        vocabulary = list(set(words))
        vector = np.zeros(len(vocabulary))
        for i, word in enumerate(vocabulary):
            vector[i] = word_counts.get(word, 0)
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector
    
    def _compute_similarity_matrix(self, embeddings: List[np.ndarray]) -> np.ndarray:
        """计算相似度矩阵"""
        n = len(embeddings)
        matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                similarity = self._cosine_similarity(embeddings[i], embeddings[j])
                matrix[i][j] = similarity
                matrix[j][i] = similarity
        
        return matrix
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot_product / (norm1 * norm2 + 1e-10)
    
    def _cluster_similar_blocks(
        self,
        code_blocks: List[Dict],
        similarity_matrix: np.ndarray
    ) -> List[Dict]:
        """聚类相似代码块"""
        n = len(code_blocks)
        visited = set()
        clusters = []
        
        for i in range(n):
            if i in visited:
                continue
            
            cluster = [i]
            visited.add(i)
            
            for j in range(i+1, n):
                if j in visited:
                    continue
                
                if similarity_matrix[i][j] >= self.similarity_threshold:
                    cluster.append(j)
                    visited.add(j)
            
            if len(cluster) > 1:
                # 计算集群平均相似度
                similarities = [
                    similarity_matrix[cluster[0]][j]
                    for j in cluster[1:]
                ]
                avg_similarity = sum(similarities) / len(similarities)
                
                clusters.append({
                    'blocks': [code_blocks[idx] for idx in cluster],
                    'similarity': avg_similarity,
                    'count': len(cluster)
                })
        
        return clusters
```

### 3.3 模块三：动态规则引擎

#### 3.3.1 规则定义

**新增文件：`app/analyzers/rule_engine.py`**
```python
from typing import List, Dict, Callable, Any
from dataclasses import dataclass
from enum import Enum
import json

class Severity(Enum):
    """问题严重程度"""
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'

class RuleCategory(Enum):
    """规则类别"""
    COMPLEXITY = 'complexity'
    NAMING = 'naming'
    STRUCTURE = 'structure'
    PERFORMANCE = 'performance'
    SECURITY = 'security'

@dataclass
class QualityRule:
    """质量规则"""
    id: str
    name: str
    description: str
    category: RuleCategory
    severity: Severity
    check_function: Callable
    fix_suggestion: str
    auto_fixable: bool = False

class RuleEngine:
    """规则引擎"""
    
    def __init__(self):
        self.rules: List[QualityRule] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """加载默认规则"""
        # 复杂度规则
        self.rules.append(QualityRule(
            id='COMPLEXITY_001',
            name='函数复杂度过高',
            description='函数圈复杂度超过阈值',
            category=RuleCategory.COMPLEXITY,
            severity=Severity.WARNING,
            check_function=self._check_function_complexity,
            fix_suggestion='考虑将函数拆分为更小的函数'
        ))
        
        # 命名规则
        self.rules.append(QualityRule(
            id='NAMING_001',
            name='变量命名不规范',
            description='变量命名不符合命名规范',
            category=RuleCategory.NAMING,
            severity=Severity.INFO,
            check_function=self._check_naming_convention,
            fix_suggestion='使用符合规范的命名'
        ))
        
        # 结构规则
        self.rules.append(QualityRule(
            id='STRUCTURE_001',
            name='函数过长',
            description='函数行数超过阈值',
            category=RuleCategory.STRUCTURE,
            severity=Severity.WARNING,
            check_function=self._check_function_length,
            fix_suggestion='将长函数拆分为多个小函数'
        ))
    
    async def check(self, ast: Dict, file_path: str) -> List[Dict]:
        """执行规则检查"""
        issues = []
        
        for rule in self.rules:
            try:
                rule_issues = await rule.check_function(ast, file_path)
                for issue in rule_issues:
                    issues.append({
                        'rule_id': rule.id,
                        'rule_name': rule.name,
                        'severity': rule.severity.value,
                        'category': rule.category.value,
                        'message': issue['message'],
                        'location': issue.get('location', {}),
                        'fix_suggestion': rule.fix_suggestion,
                        'auto_fixable': rule.auto_fixable
                    })
            except Exception as e:
                print(f"Rule {rule.id} check failed: {e}")
        
        return issues
    
    def add_rule(self, rule: QualityRule):
        """添加自定义规则"""
        self.rules.append(rule)
    
    def remove_rule(self, rule_id: str):
        """移除规则"""
        self.rules = [r for r in self.rules if r.id != rule_id]
    
    def get_rules(self) -> List[Dict]:
        """获取所有规则"""
        return [
            {
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'category': rule.category.value,
                'severity': rule.severity.value,
                'auto_fixable': rule.auto_fixable
            }
            for rule in self.rules
        ]
    
    async def _check_function_complexity(self, ast: Dict, file_path: str) -> List[Dict]:
        """检查函数复杂度"""
        issues = []
        
        for func in self._find_functions(ast):
            complexity = self._calculate_complexity(func)
            if complexity > 10:  # 默认阈值
                issues.append({
                    'message': f"函数 {func.get('name', 'anonymous')} 圈复杂度为 {complexity}，超过阈值10",
                    'location': func.get('location', {})
                })
        
        return issues
    
    async def _check_naming_convention(self, ast: Dict, file_path: str) -> List[Dict]:
        """检查命名规范"""
        issues = []
        
        # 检查变量命名
        for var in self._find_variables(ast):
            name = var.get('name', '')
            if not name.startswith('_') and not name.islower():
                issues.append({
                    'message': f"变量 {name} 命名不符合snake_case规范",
                    'location': var.get('location', {})
                })
        
        return issues
    
    async def _check_function_length(self, ast: Dict, file_path: str) -> List[Dict]:
        """检查函数长度"""
        issues = []
        
        for func in self._find_functions(ast):
            length = len(func.get('body', []))
            if length > 50:  # 默认阈值
                issues.append({
                    'message': f"函数 {func.get('name', 'anonymous')} 长度为 {length} 行，超过阈值50",
                    'location': func.get('location', {})
                })
        
        return issues
```

#### 3.3.2 规则配置文件

**新增文件：`config/rules.json`**
```json
{
  "rules": [
    {
      "id": "CUSTOM_001",
      "name": "自定义复杂度规则",
      "description": "检查特定函数的复杂度",
      "category": "complexity",
      "severity": "warning",
      "threshold": 15,
      "enabled": true
    }
  ],
  "thresholds": {
    "complexity": {
      "warning": 10,
      "error": 20
    },
    "function_length": {
      "warning": 50,
      "error": 100
    },
    "parameters": {
      "warning": 5,
      "error": 10
    }
  }
}
```

### 3.4 模块四：增量分析

#### 3.4.1 增量分析器

**新增文件：`app/analyzers/incremental_analyzer.py`**
```python
import hashlib
from typing import Dict, List, Optional
from datetime import datetime

class IncrementalAnalyzer:
    """增量分析器"""
    
    def __init__(self):
        self.cache = {}  # 文件哈希 -> 分析结果
        self.analysis_history = []  # 分析历史
    
    async def analyze_incremental(
        self,
        files: List[Dict],
        force_full: bool = False
    ) -> Dict:
        """增量分析"""
        
        if force_full:
            return await self._full_analysis(files)
        
        # 1. 检测变更文件
        changed_files, unchanged_files = self._detect_changes(files)
        
        # 2. 仅分析变更文件
        changed_results = []
        for file in changed_files:
            result = await self._analyze_file(file)
            changed_results.append(result)
            
            # 更新缓存
            file_hash = self._calculate_hash(file['content'])
            self.cache[file['path']] = {
                'hash': file_hash,
                'result': result,
                'timestamp': datetime.now()
            }
        
        # 3. 合并结果
        all_results = changed_results + [
            self.cache[f['path']]['result']
            for f in unchanged_files
            if f['path'] in self.cache
        ]
        
        return {
            'files_analyzed': len(changed_files),
            'files_cached': len(unchanged_files),
            'results': all_results,
            'analysis_type': 'incremental'
        }
    
    def _detect_changes(self, files: List[Dict]) -> tuple:
        """检测变更文件"""
        changed = []
        unchanged = []
        
        for file in files:
            file_hash = self._calculate_hash(file['content'])
            
            if file['path'] in self.cache:
                cached_hash = self.cache[file['path']]['hash']
                if file_hash == cached_hash:
                    unchanged.append(file)
                else:
                    changed.append(file)
            else:
                changed.append(file)
        
        return changed, unchanged
    
    def _calculate_hash(self, content: str) -> str:
        """计算文件哈希"""
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _analyze_file(self, file: Dict) -> Dict:
        """分析单个文件"""
        # 这里调用实际的分析逻辑
        return {
            'file': file['path'],
            'issues': [],
            'metrics': {},
            'timestamp': datetime.now()
        }
    
    async def _full_analysis(self, files: List[Dict]) -> Dict:
        """全量分析"""
        results = []
        for file in files:
            result = await self._analyze_file(file)
            results.append(result)
            
            # 更新缓存
            file_hash = self._calculate_hash(file['content'])
            self.cache[file['path']] = {
                'hash': file_hash,
                'result': result,
                'timestamp': datetime.now()
            }
        
        return {
            'files_analyzed': len(files),
            'files_cached': 0,
            'results': results,
            'analysis_type': 'full'
        }
    
    def get_analysis_history(self) -> List[Dict]:
        """获取分析历史"""
        return self.analysis_history
```

---

## 4. API设计

### 4.1 新增/修改的API

#### 多语言分析
```python
@router.post("/api/quality/analyze/language")
async def analyze_by_language(request: LanguageAnalysisRequest):
    """
    按语言分析代码
    
    Request:
    {
        "file_path": "main.py",
        "content": "def hello(): print('Hello')",
        "language": "python"
    }
    
    Response:
    {
        "language": "python",
        "metrics": {
            "functions": 1,
            "complexity": 1.0,
            "lines": 1
        },
        "issues": [],
        "suggestions": []
    }
    """
```

#### 语义重复检测
```python
@router.post("/api/quality/detect/duplication/semantic")
async def detect_semantic_duplication(request: SemanticDuplicationRequest):
    """
    检测语义重复代码
    
    Request:
    {
        "code_blocks": [
            {"path": "a.py", "content": "..."},
            {"path": "b.py", "content": "..."}
        ],
        "similarity_threshold": 0.85
    }
    
    Response:
    {
        "clusters": [
            {
                "blocks": ["a.py", "b.py"],
                "similarity": 0.92,
                "suggestion": "考虑将重复代码提取为公共函数"
            }
        ],
        "total_duplicates": 2
    }
    """
```

#### 动态规则管理
```python
@router.get("/api/quality/rules")
async def get_quality_rules():
    """
    获取所有质量规则
    
    Response:
    {
        "rules": [
            {
                "id": "COMPLEXITY_001",
                "name": "函数复杂度过高",
                "category": "complexity",
                "severity": "warning",
                "auto_fixable": false
            }
        ],
        "total": 10
    }
    """
```

#### 增量分析
```python
@router.post("/api/quality/analyze/incremental")
async def analyze_incremental(request: IncrementalAnalysisRequest):
    """
    增量分析代码
    
    Request:
    {
        "files": [
            {"path": "main.py", "content": "..."}
        ],
        "force_full": false
    }
    
    Response:
    {
        "files_analyzed": 2,
        "files_cached": 8,
        "analysis_type": "incremental",
        "results": [...]
    }
    """
```

---

## 5. 任务拆分

### Phase 1：多语言支持（2天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T1.1 | 实现LanguageAdapter基类 | P0 |
| T1.2 | 实现PythonAdapter | P0 |
| T1.3 | 实现JavaScriptAdapter | P1 |
| T1.4 | 实现LanguageManager | P1 |

### Phase 2：语义重复检测（2天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T2.1 | 实现语义相似度计算 | P0 |
| T2.2 | 实现重复检测算法 | P0 |
| T2.3 | 集成到分析流程 | P1 |

### Phase 3：动态规则引擎（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T3.1 | 实现RuleEngine | P1 |
| T3.2 | 实现规则配置加载 | P1 |
| T3.3 | 添加规则管理API | P2 |

### Phase 4：增量分析（1天）
| 任务 | 描述 | 优先级 |
|------|------|--------|
| T4.1 | 实现变更检测 | P1 |
| T4.2 | 实现增量分析 | P1 |
| T4.3 | 集成到分析流程 | P2 |

---

## 6. 依赖和风险

### 6.1 技术依赖
| 依赖 | 用途 | 备选方案 |
|------|------|----------|
| esprima | JS/TS解析 | 手动解析 |
| ast | Python解析 | 无 |
| numpy | 向量计算 | 纯Python |

### 6.2 风险点
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 解析器兼容性 | 某些语法无法解析 | 优雅降级，跳过无法解析的文件 |
| 语义重复误报 | 正常代码被标记 | 调整阈值，添加白名单 |
| 增量分析缓存 | 缓存不一致 | 定期清理缓存 |

---

## 7. 验收标准

| 验收项 | 标准 |
|--------|------|
| 多语言支持 | 能分析Python和JavaScript代码 |
| 语义重复检测 | 能检测出语义相似的代码块 |
| 动态规则 | 能通过配置文件添加/修改规则 |
| 增量分析 | 仅分析变更文件，速度提升50%+ |
| 问题报告 | 报告包含修复建议和优先级 |
